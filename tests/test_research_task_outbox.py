from copy import deepcopy
from contextlib import closing
import sqlite3

import pytest

from cain.research_tasks import TaskConflict, TaskOutbox


SECRET = bytes.fromhex("22" * 32)


def task():
    def ref(kind, name):
        return {"kind": kind, "name": name, "version": "v1"}

    return {
        "schema_version": "ResearchTaskV1",
        "task_id": "TASK-CAIN-001",
        "research_id": "RESEARCH-001",
        "parent_task_id": None,
        "hypothesis_id": "H6",
        "domain": "crypto",
        "request_type": "BACKTEST_EXISTING_HYPOTHESIS",
        "protocol_ref": ref("protocol", "backtest-standard"),
        "dataset_constraint_ref": ref("dataset", "btc-daily-pit"),
        "baseline_refs": [ref("baseline", "majority-direction")],
        "cost_model_ref": ref("cost_model", "spot-standard"),
        "evidence_refs": [ref("evidence", "cain-receipt-001")],
        "bounded_parameters": {
            "symbol": "BTCUSDT",
            "horizon_days": 7,
            "max_observations": 500,
            "fee_bps": 10,
            "slippage_bps": 5,
        },
        "priority_hint": "HIGH",
        "created_at": "2026-09-19T22:30:00Z",
        "expires_at": "2026-09-20T22:30:00Z",
        "requested_by": "qa-cain-f3",
        "provenance": {
            "cain_source_sha": "6f9d254776b2a3c251f6cce14529087c57ebbeae",
            "retrieval_receipt_ids": ["receipt-001"],
            "proposal_model": "deterministic-fixture",
        },
    }


def outbox(path):
    return TaskOutbox(path, publisher_identity="cain-qa", key_id="cain-f3-key", secret=SECRET)


def test_proposal_is_durable_and_idempotent(tmp_path):
    path = tmp_path / "outbox.db"
    first = outbox(path).propose(task())
    assert first["status"] == "proposed" and first["outbox_status"] == "PENDING"
    restarted = outbox(path)
    second = restarted.propose(dict(reversed(list(task().items()))))
    assert second["status"] == "duplicate"
    assert restarted.pending() == [first["envelope"]]
    assert restarted.state(task()["task_id"])["attempt_count"] == 0


def test_same_task_id_with_different_payload_conflicts(tmp_path):
    store = outbox(tmp_path / "outbox.db")
    store.propose(task())
    changed = deepcopy(task())
    changed["bounded_parameters"]["fee_bps"] = 11
    with pytest.raises(TaskConflict):
        store.propose(changed)
    assert len(store.pending()) == 1


def test_secret_is_not_persisted(tmp_path):
    path = tmp_path / "outbox.db"
    outbox(path).propose(task())
    with closing(sqlite3.connect(path)) as db:
        stored = b"".join(
            value if isinstance(value, bytes) else str(value).encode()
            for row in db.execute("SELECT * FROM task_outbox")
            for value in row
            if value is not None
        )
    assert SECRET not in stored


def test_delivery_attempt_ack_retry_dead_letter_and_reconciliation_survive_restart(tmp_path):
    path = tmp_path / "outbox.db"
    store = outbox(path)
    envelope = store.propose(task())["envelope"]
    store.record_send(task()["task_id"], envelope["message_id"])
    assert outbox(path).state(task()["task_id"])["attempt_count"] == 1
    retry = outbox(path).fail_delivery(
        task()["task_id"], envelope["message_id"], "CRIPTO_OFFLINE", max_attempts=2
    )
    assert retry["status"] == "RETRYABLE"
    outbox(path).record_send(task()["task_id"], envelope["message_id"])
    dead = outbox(path).fail_delivery(
        task()["task_id"], envelope["message_id"], "CRIPTO_OFFLINE", max_attempts=2
    )
    assert dead["status"] == "DEAD_LETTER"
    assert outbox(path).reconcile() == {"pending": 0, "published": 0, "dead_letters": 1}


def test_ack_is_correlated_and_idempotent(tmp_path):
    path = tmp_path / "outbox.db"
    store = outbox(path)
    envelope = store.propose(task())["envelope"]
    store.record_send(task()["task_id"], envelope["message_id"])
    with pytest.raises(ValueError, match="ACK_CONFLICT"):
        store.acknowledge(task()["task_id"], "00" * 32, processed_at=task()["created_at"])
    first = store.acknowledge(
        task()["task_id"], envelope["message_id"], processed_at=task()["created_at"]
    )
    second = outbox(path).acknowledge(
        task()["task_id"], envelope["message_id"], processed_at=task()["created_at"]
    )
    assert first["status"] == second["status"] == "PUBLISHED"
    assert outbox(path).reconcile()["published"] == 1
