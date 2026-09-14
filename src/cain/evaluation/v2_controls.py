"""HTTP preference precedence and resource isolation; no inference is requested."""

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import time
import socket
import subprocess
import os
from urllib.parse import urlencode
from cain.evaluation.v2 import attest, request, write


def fault(output, python, config):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    with socket.socket() as sock:
        sock.settimeout(2)
        if sock.connect_ex(("127.0.0.1", 11439)) == 0:
            raise ValueError("Fault port is occupied; do not interrupt another service")
    prompt = 'Retorne apenas JSON válido com exatamente as chaves "cidade" e "ativo". cidade deve ser "Londrina" e ativo deve ser false.'
    cmd = [
        str(python),
        "-m",
        "cain",
        "run",
        prompt,
        "--config",
        str(config),
        "--db",
        str(output / "workspace.db"),
        "--user",
        "qa-backend-fault",
        "--session",
        "fault",
        "--ollama-url",
        "http://127.0.0.1:11439",
        "--no-web",
    ]
    write(
        output / "manifest.json",
        {
            "family": "M12",
            "protocol": "cain-product-evaluation/2.0",
            "command": cmd,
            "fault_injected": True,
            "expected": "explicit backend error, nonzero exit, no success response",
            "permitted_storage": str(output),
            "inference_policy": "optional",
            "main_service_untouched": True,
        },
    )
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH" and not k.startswith("CAIN_")}
    identity = subprocess.run(
        [
            str(python),
            "-c",
            "import json; from cain.evaluation.resources import installed_identity; print(json.dumps(installed_identity()))",
        ],
        cwd=output,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    write(output / "executed-package.json", json.loads(identity.stdout))
    result = subprocess.run(
        cmd, cwd=output, env=env, capture_output=True, text=True, encoding="utf-8", timeout=260
    )
    write(
        output / "result.json",
        {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "execution": "completed",
            "quality": "pass"
            if result.returncode != 0 and "Ollama" in result.stderr
            else "review_required",
            "origin": "unknown",
            "llm_call_count": 0,
            "basis": "Backend port verified closed; connection failure observed",
            "fault_injected": True,
            "limits": "Connection refusal only, not interruption after partial generation",
        },
    )
    print("Fault execution exit", result.returncode)


def run(output, api, root):
    proof = attest(root, api)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    write(output / "attestation.json", proof)
    write(
        output / "manifest.json",
        {
            "protocol": "cain-product-evaluation/2.0",
            "cases": {
                "M05": "Preference language precedence user/project/session/turn and expired override",
                "M06": "User preference persisted and read through a new session; document canary persists",
                "M07": "Other user cannot list protected project document; no canary in response",
                "M08": "Other project has empty document collection",
            },
            "inference_policy": "forbidden",
            "path": "C HTTP controls",
            "limitations": "No natural-language retrieval or generated preference adherence certification",
        },
    )
    receipts = []

    def req(path, data=None, method=None):
        status, body = request(api + path, data, method)
        receipts.append(
            {
                "path": path,
                "method": method or ("POST" if data else "GET"),
                "input": data,
                "status": status,
                "response": body,
            }
        )
        write(output / "receipts.json", receipts)
        return status, body

    user = "qa-controls-" + output.name
    _, p = req("/projects/" + user, {"name": "A"})
    project = p["id"]
    _, b = req("/projects/" + user, {"name": "B"})
    project_b = b["id"]
    _, s = req("/sessions/" + user, {"project_id": project})
    session = s["id"]
    _, s2 = req("/sessions/" + user, {})
    session2 = s2["id"]
    pref = f"/profile/{user}/preferences/language"

    def setp(value, scope, **context):
        status, _ = req(pref, {"value": value, "scope": scope, **context}, "PUT")
        assert status == 200

    def effective(**context):
        status, body = req(f"/profile/{user}?" + urlencode(context))
        assert status == 200
        return body["effective_preferences"]

    setp("en", "user")
    assert effective(session_id=session2)["language"] == "en"
    setp("pt", "project", project_id=project)
    assert effective(project_id=project)["language"] == "pt"
    setp("en", "session", project_id=project, session_id=session)
    assert effective(project_id=project, session_id=session)["language"] == "en"
    setp("pt", "turn", project_id=project, session_id=session, turn_id="control-turn")
    assert (
        effective(project_id=project, session_id=session, turn_id="control-turn")["language"]
        == "pt"
    )
    assert (
        effective(project_id=project, session_id=session, turn_id="another-turn")["language"]
        == "en"
    )
    status, _ = req(
        pref,
        {
            "value": "pt",
            "scope": "turn",
            "project_id": project,
            "session_id": session,
            "turn_id": "invalid-past",
            "expires_at": "2000-01-01T00:00:00Z",
        },
        "PUT",
    )
    assert status == 400  # Invalid input, not a test of active preference expiry.
    expiry = datetime.now(timezone.utc) + timedelta(seconds=20)
    setp(
        "pt",
        "turn",
        project_id=project,
        session_id=session,
        turn_id="expired-turn",
        expires_at=expiry.isoformat(),
    )
    assert (
        effective(project_id=project, session_id=session, turn_id="expired-turn")["language"]
        == "pt"
    )
    time.sleep(max(0, (expiry - datetime.now(timezone.utc)).total_seconds()) + 0.1)
    assert (
        effective(project_id=project, session_id=session, turn_id="expired-turn")["language"]
        == "en"
    )
    ep = f"/projects/{user}/{project}/documents"
    _, doc = req(
        ep,
        {"title": "canary.md", "content": "Synthetic document canary PINHAL-837; project A only."},
    )
    _, same = req(ep)
    assert any(d["id"] == doc["id"] for d in same)
    status, other = req(f"/projects/qa-outsider/{project}/documents")
    assert status == 400 and "PINHAL-837" not in json.dumps(other)
    _, other_project = req(f"/projects/{user}/{project_b}/documents")
    assert other_project == []
    write(
        output / "result.json",
        {
            "execution": "completed",
            "quality": "pass",
            "families": ["M05", "M06", "M07", "M08"],
            "path": "C HTTP controls only",
            "llm_call_count": 0,
            "inference_basis": "Only profile/project/session/document routes called",
            "limitations": [
                "M06 arbitrary natural-language canary recall not evaluated",
                "M05 generated adherence not evaluated",
                "No adversarial browser disclosure evaluated",
            ],
        },
    )
    print("HTTP controls passed")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--api", default="http://127.0.0.1:8896")
    p.add_argument("--root", type=Path)
    p.add_argument("--fault-python", type=Path)
    p.add_argument("--config", type=Path)
    a = p.parse_args()
    if a.fault_python:
        if not a.config:
            p.error("--config required for fault test")
        fault(a.output, a.fault_python, a.config)
    else:
        if not a.root:
            p.error("--root required to attest isolated HTTP storage")
        run(a.output, a.api, a.root)
