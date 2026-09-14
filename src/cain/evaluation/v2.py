"""Versioned product evaluation. No implicit model calls, production data or promotions.

Run this module's --help. Serve may be launched with the installed Python while
the evaluator lives in a candidate checkout; executed package identity is recorded.
"""

from __future__ import annotations

import argparse
import base64
from collections import Counter
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from urllib.parse import urlsplit
import uuid

from cain.evaluation.quality import _strict_json
from cain.evaluation.resources import installed_identity

PROTOCOL = "cain-product-evaluation/2.0"
FAMILIES = [f"{level}{i:02}" for level in "BMA" for i in range(1, 13)]
INSTRUMENT = "v2-runner/4"


def local_url(value):
    p = urlsplit(value)
    if (
        p.scheme != "http"
        or p.hostname not in {"127.0.0.1", "localhost", "::1"}
        or p.username
        or p.password
        or p.query
        or p.fragment
        or p.path not in {"", "/"}
    ):
        raise ValueError("Evaluation endpoints must be loopback HTTP origins")
    return value.rstrip("/")


def attest(root, api):
    api = local_url(api)
    status, observed = request(api + "/evaluation/attestation", timeout=10)
    expected = read(Path(root) / "server-attestation.json")
    if status != 200 or observed != expected or observed["root"] != str(Path(root).resolve()):
        raise ValueError("API does not attest the declared QA storage")
    return observed


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def append(path, value):
    with Path(path).open("a", encoding="utf-8") as f:
        f.write(json.dumps(value, ensure_ascii=False) + "\n")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def records(path):
    return (
        [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()]
        if Path(path).exists()
        else []
    )


def request(url, data=None, method=None, timeout=250):
    req = Request(
        url,
        data=None if data is None else json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urlopen(req, timeout=timeout) as response:
            return response.status, json.loads(response.read())
    except HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            raw = json.loads(raw)
        except ValueError:
            pass
        return e.code, raw


def validate_design(catalog, rubrics):
    assert catalog["protocol"] == PROTOCOL
    assert sorted(catalog["families"]) == sorted(FAMILIES)
    seen = set()
    required = {
        "case_id",
        "case_version",
        "family_id",
        "level",
        "capability",
        "severity",
        "origin",
        "split",
        "preconditions",
        "state",
        "messages",
        "fixtures",
        "paths",
        "evidence",
        "inference_policy",
        "budget",
        "integrity",
        "evaluator",
    }
    for c in catalog["cases"]:
        if not required.issubset(c) or c["case_id"] in seen or c["family_id"] not in FAMILIES:
            raise ValueError("Incomplete or duplicate case contract")
        if not c["messages"] or not all(type(x) is str and x for x in c["messages"]):
            raise ValueError("Exact messages required")
        if c["case_id"] not in rubrics or set(c["paths"]) - {"A", "B", "C", "D"}:
            raise ValueError("Missing rubric or invalid path")
        if c["split"] not in {"development", "regression", "confirmation"}:
            raise ValueError("Invalid split")
        if "expected" in c or "rubric" in c:
            raise ValueError("Answer keys belong in evaluator file")
        seen.add(c["case_id"])
    return catalog


def evaluate(response, rubric):
    """No repair, stripping or regex-based semantic certification."""
    checks = []
    # Exactly one transport line terminator may be removed; never spaces/Markdown.
    normalized = (
        response[:-2]
        if response.endswith("\r\n")
        else response[:-1]
        if response.endswith("\n")
        else response
    )
    if "exact" in rubric:
        checks.append({"name": "literal", "passed": normalized == rubric["exact"]})
    if "json" in rubric:
        try:
            value = _strict_json(response)
            expected = rubric["json"]
            ok = (
                type(value) is dict
                and value.keys() == expected.keys()
                and all(type(value[k]) is type(v) and value[k] == v for k, v in expected.items())
            )
        except (ValueError, TypeError):
            ok = False
        checks.append({"name": "json_keys_types_values", "passed": ok})
    if "forbidden_word" in rubric:
        checks.append(
            {
                "name": "forbidden_whole_word",
                "passed": not bool(
                    re.search(r"\b" + re.escape(rubric["forbidden_word"]) + r"\b", response, re.I)
                ),
            }
        )
    if "max_words" in rubric:
        checks.append(
            {"name": "word_limit", "passed": len(response.split()) <= rubric["max_words"]}
        )
    quality = (
        "fail"
        if any(not x["passed"] for x in checks)
        else ("review_required" if rubric.get("semantic_required", True) else "pass")
    )
    return {
        "quality": quality,
        "checks": checks,
        "evaluator": "v2-deterministic/1",
        "semantic_review": "pending" if rubric.get("semantic_required", True) else "not_required",
    }


def isolation(root, config):
    """Require explicit dedicated storage and no global document inputs."""
    from cain.settings import load_settings

    s = load_settings(config)
    runtime = Path(root).resolve() / "runtime"
    if s.db_path.resolve() != runtime / "workspace.db" or s.source_paths or s.allow_public_urls:
        raise ValueError("QA storage/document/network preconditions failed")
    if runtime.is_symlink() or getattr(runtime, "is_junction", lambda: False)():
        raise ValueError("QA runtime cannot redirect storage")
    return {
        "db": str(s.db_path.resolve()),
        "research_db": str(runtime / "research.db"),
        "documents": str(runtime / "knowledge"),
        "embedding_cache": str(runtime / "workspace.embeddings.sqlite3"),
        "source_paths": [],
        "public_urls": False,
        "settings": {k: str(v) if isinstance(v, Path) else v for k, v in vars(s).items()},
    }


def prepare(root, config, catalog, rubrics):
    import tomllib

    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    runtime = root / "runtime"
    runtime.mkdir(exist_ok=False)
    data = tomllib.loads(Path(config).read_text(encoding="utf-8"))
    data["llm"]["base_url"] = "http://127.0.0.1:11436"
    data["storage"] = {"path": (runtime / "workspace.db").as_posix()}
    data["search"]["paths"] = []
    data["search"]["allow_public_urls"] = False
    lines = []
    for group, values in data.items():
        lines.append("[" + group + "]")
        for k, v in values.items():
            lines.append(k + " = " + json.dumps(v, ensure_ascii=False))
    (root / "qa.toml").write_text("\n".join(lines), encoding="utf-8")
    design = validate_design(read(catalog), read(rubrics))
    write(root / "catalog.json", design)
    write(root / "rubrics.json", read(rubrics))
    write(root / "isolation.json", isolation(root, root / "qa.toml"))
    write(
        root / "plan.json",
        {
            "protocol": PROTOCOL,
            "catalog_hash": digest(root / "catalog.json"),
            "rubrics_hash": digest(root / "rubrics.json"),
            "frozen_at": datetime.now(timezone.utc).isoformat(),
            "generation_cap": 100,
            "series_only": True,
            "hidden_retries": False,
            "source": str(Path(__file__).resolve()),
            "instrument_hash": digest(__file__),
            "confirmation": "none reserved; creator and reviewer are implementer",
            "first_subset": [
                "B01",
                "B03",
                "B04",
                "B06",
                "B10",
                "B12",
                "M01",
                "M02",
                "M04",
                "M10",
                "M11",
                "A05",
                "A06",
            ],
        },
    )


def serve(root, port, backend):
    """Transparent HTTP recorder. Request/response bytes are forwarded unchanged."""
    import uvicorn
    from cain.api import create_app

    root = Path(root).resolve()
    backend = local_url(backend)
    proof = isolation(root, root / "qa.toml")
    write(
        root / "executed-package.json",
        {
            "identity": installed_identity(),
            "isolation": proof,
            "instrument_file": str(Path(__file__).resolve()),
            "instrument_hash": digest(__file__),
        },
    )
    cap = read(root / "plan.json")["generation_cap"]

    class Proxy(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            self.forward()

        def do_POST(self):
            self.forward()

        def forward(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            entry = {
                "at": datetime.now(timezone.utc).isoformat(),
                "path": self.path,
                "request_id": uuid.uuid4().hex,
                "method": self.command,
                "request_base64": base64.b64encode(body).decode(),
                "request_sha256": hashlib.sha256(body).hexdigest(),
                "case": read(root / "active.json") if (root / "active.json").exists() else None,
            }
            start = time.perf_counter()
            append(root / "dispatch.jsonl", entry)
            status, raw = 502, b'{"error":"observer transport failure"}'
            try:
                if self.path not in {
                    "/api/generate",
                    "/api/tags",
                    "/api/version",
                    "/api/embed",
                    "/api/embeddings",
                }:
                    raise ValueError("Endpoint outside QA observation contract")
                if (
                    self.path == "/api/generate"
                    and sum(x["path"] == "/api/generate" for x in records(root / "transport.jsonl"))
                    >= cap
                ):
                    raise ValueError("Frozen generation cap reached")
                req = Request(
                    backend + self.path,
                    data=body if self.command == "POST" else None,
                    headers={"Content-Type": "application/json"},
                    method=self.command,
                )
                try:
                    with urlopen(req, timeout=245) as response:
                        status, raw = response.status, response.read()
                except HTTPError as e:
                    status, raw = e.code, e.read()
                entry["forwarded"] = True
            except Exception as e:
                entry["error"] = f"{type(e).__name__}: {e}"
            entry.update(
                seconds=time.perf_counter() - start,
                status=status,
                response_base64=base64.b64encode(raw).decode(),
            )
            append(root / "transport.jsonl", entry)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    proxy = ThreadingHTTPServer(("127.0.0.1", 11436), Proxy)
    threading.Thread(target=proxy.serve_forever, daemon=True).start()
    # No injected provider: normal provider factory, routing, memory and retrieval.
    app = create_app(
        db_path=Path(proof["db"]),
        config_path=root / "qa.toml",
        research_policy=root / "runtime/research-policy.json",
        research_db=Path(proof["research_db"]),
    )
    attestation = {
        "root": str(root),
        "storage": proof,
        "instance": uuid.uuid4().hex,
        "package": installed_identity()["source_tree_sha256"],
        "instrument": INSTRUMENT,
        "config_hash": digest(root / "qa.toml"),
    }
    write(root / "server-attestation.json", attestation)

    @app.get("/evaluation/attestation")
    def qa_attestation():
        return attestation

    write(root / "openapi.json", app.openapi())
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


def observed_generation_count(calls, dispatch):
    """An observer timeout does not prove that the backend did no work."""
    if len(calls) != len(dispatch) or any(x.get("forwarded") is not True for x in calls):
        return None
    return len(calls)


def origin(result, calls):
    if not isinstance(result, dict):
        return "unknown"
    text = result.get("response", "")
    for c in reversed(calls):
        try:
            raw = json.loads(base64.b64decode(c["response_base64"]))
            request_body = json.loads(base64.b64decode(c["request_base64"]))
            if raw.get("response") == text:
                return "llm_structured" if "format" in request_body else "llm_text"
        except (ValueError, KeyError):
            pass
    if result.get("selected_agent") == "busca":
        return "retrieval_only"
    if (
        result.get("route_reason") in {"social_greeting", "conversation_rule:arithmetic"}
        and not calls
    ):
        return "deterministic"
    return "unknown"


def run(root, run_id, selected, paths, api, catalog_path=None, rubrics_path=None):
    root = Path(root).resolve()
    if set(paths) - {"A", "C"} or not paths:
        raise ValueError("This adapter executes A/C only; use replay for B and real browser for D")
    design, rubrics = (
        read(catalog_path or root / "catalog.json"),
        read(rubrics_path or root / "rubrics.json"),
    )
    validate_design(design, rubrics)
    plan = read(root / "plan.json")
    if (
        digest(root / "catalog.json") != plan["catalog_hash"]
        or digest(root / "rubrics.json") != plan["rubrics_hash"]
    ):
        raise ValueError("Frozen inputs changed; prepare another root")
    isolation(root, root / "qa.toml")
    api = local_url(api)
    attestation = attest(root, api)
    target = root / "runs" / run_id
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,90}", run_id):
        raise ValueError("Invalid run id")
    target.mkdir(parents=True, exist_ok=False)
    cases = [c for c in design["cases"] if c["family_id"] in selected or c["case_id"] in selected]
    if not cases or any(
        x not in {c["family_id"] for c in cases} | {c["case_id"] for c in cases} for x in selected
    ):
        raise ValueError("Unknown or empty case selection")
    write(
        target / "manifest.json",
        {
            "protocol": PROTOCOL,
            "run_id": run_id,
            "cases": cases,
            "paths": paths,
            "api": api,
            "instrument_hash": digest(__file__),
            "instrument": INSTRUMENT,
            "plan": plan,
            "attestation": attestation,
            "rubrics": rubrics,
            "catalog_hash": digest(catalog_path or root / "catalog.json"),
            "rubrics_hash": digest(rubrics_path or root / "rubrics.json"),
            "package": read(root / "executed-package.json"),
        },
    )
    for case in cases:
        for path in paths:
            if path not in case["paths"] or path not in {"A", "C"}:
                continue
            for attempt in range(1, case["budget"].get("repetitions", 1) + 1):
                key = f"{run_id}-{case['case_id']}-{path}-{attempt}"
                user, session = "qa-" + key, "episode"
                write(
                    root / "active.json",
                    {
                        "run_id": run_id,
                        "case_id": case["case_id"],
                        "path": path,
                        "attempt": attempt,
                    },
                )
                entry = {
                    "run_id": run_id,
                    "case_id": case["case_id"],
                    "family_id": case["family_id"],
                    "split": case["split"],
                    "attempt": attempt,
                    "path": path,
                    "user_id": user,
                    "execution": "completed",
                    "quality": "not_evaluable",
                    "validity": "valid",
                    "diagnostic_override": False,
                    "turns": [],
                    "state_initial": "fresh unique identity and project",
                    "inference_policy": case["inference_policy"][path],
                    "fault_injected": False,
                }
                start = time.perf_counter()
                project = None
                try:
                    if path == "C":
                        _, profile = request(api + "/profile/" + user)
                        entry["profile_before"] = profile
                        if case["fixtures"]:
                            status, p = request(api + "/projects/" + user, {"name": key})
                            if status != 200:
                                raise ValueError(str(p))
                            project = p["id"]
                            entry["documents"] = []
                            for fixture in case["fixtures"]:
                                status, doc = request(
                                    api + f"/projects/{user}/{project}/documents", fixture
                                )
                                if status != 200:
                                    raise ValueError(str(doc))
                                entry["documents"].append(doc)
                    for turn, message in enumerate(case["messages"]):
                        label = {
                            "run_id": run_id,
                            "case_id": case["case_id"],
                            "path": path,
                            "attempt": attempt,
                            "turn": turn,
                        }
                        write(root / "active.json", label)
                        before = len(records(root / "transport.jsonl"))
                        if path == "C":
                            sent = {
                                "user_id": user,
                                "session_id": session,
                                "payload": message,
                                "project_id": project,
                                "run_id": str(uuid.uuid4()),
                            }
                            status, response = request(api + "/run", sent, timeout=520)
                            text = (
                                response.get("response", "") if isinstance(response, dict) else ""
                            )
                        else:
                            s = read(root / "isolation.json")["settings"]
                            sent = {
                                "model": s["model"],
                                "prompt": message,
                                "system": "Responda ao pedido do usuário.",
                                "stream": False,
                                "think": s["think"],
                                "options": {
                                    k: s[k]
                                    for k in ("temperature", "seed", "num_ctx", "num_predict")
                                },
                            }
                            status, response = request("http://127.0.0.1:11436/api/generate", sent)
                            text = response.get("response", "")
                        calls = [
                            x
                            for x in records(root / "transport.jsonl")[before:]
                            if x["path"] == "/api/generate" and x.get("case") == label
                        ]
                        dispatch = [
                            x
                            for x in records(root / "dispatch.jsonl")
                            if x["path"] == "/api/generate" and x.get("case") == label
                        ]
                        observed_calls = observed_generation_count(calls, dispatch)
                        backend_responses = []
                        for call in calls:
                            try:
                                backend_responses.append(
                                    json.loads(base64.b64decode(call["response_base64"]))
                                )
                            except ValueError:
                                pass
                        truncated = any(
                            x.get("done_reason") in {"length", "max_tokens"}
                            for x in backend_responses
                        )
                        if truncated:
                            entry["truncated"] = True
                        answer_origin = (
                            origin(response, calls)
                            if path == "C"
                            else "llm_text"
                            if status == 200
                            else "unknown"
                        )
                        entry["turns"].append(
                            {
                                "input": sent,
                                "status": status,
                                "response": response,
                                "text": text,
                                "calls": calls,
                                "dispatch": dispatch,
                                "llm_call_count": observed_calls,
                                "incomplete_observation": observed_calls is None,
                                "truncated": truncated,
                                "answer_origin": answer_origin,
                            }
                        )
                        if status != 200:
                            entry["execution"] = "operational_error"
                            break
                        if response.get("done_reason") in {"length", "max_tokens"}:
                            entry["execution"] = "operational_error"
                            entry["truncated"] = True
                            break
                    if entry["execution"] == "completed":
                        entry.update(evaluate(entry["turns"][-1]["text"], rubrics[case["case_id"]]))
                except Exception as e:
                    entry.update(execution="operational_error", error=f"{type(e).__name__}: {e}")
                entry["seconds"] = time.perf_counter() - start
                append(target / "attempts.jsonl", entry)
                report(root, target)
                print(
                    case["case_id"], path, attempt, entry["execution"], entry["quality"], flush=True
                )
    report(root, target)


def report(root, target):
    design = read(Path(root) / "catalog.json")
    manifest = read(Path(target) / "manifest.json")
    # The run may use a separately frozen confirmation catalogue. Report its
    # actual cases instead of silently substituting the root's original cases.
    run_cases = manifest.get("cases", [])
    active_families = {x["family_id"] for x in run_cases}
    design["cases"] = [
        x for x in design["cases"] if x["family_id"] not in active_families
    ] + run_cases
    attempts = records(Path(target) / "attempts.jsonl")
    matrix = []
    for f in FAMILIES:
        cases = [x for x in design["cases"] if x["family_id"] == f]
        rows = [x for x in attempts if x["family_id"] == f]
        matrix.append(
            {
                "family": f,
                "implemented_cases": [x["case_id"] for x in cases],
                "attempts": len(rows),
                "execution": dict(Counter(x["execution"] for x in rows)),
                "quality": dict(Counter(x["quality"] for x in rows)),
                "state": "attempted" if rows else "not_executed",
                "reason": None
                if rows
                else "not in this declared round"
                if cases
                else "not in this runtime catalogue; consult separate control adapters",
            }
        )
    metrics = {
        "families_planned": 36,
        "families_attempted": sum(x["attempts"] > 0 for x in matrix),
        "attempts": len(attempts),
        "execution": dict(Counter(x["execution"] for x in attempts)),
        "quality": dict(Counter(x["quality"] for x in attempts)),
        "llm_calls_observed": sum(t["llm_call_count"] or 0 for x in attempts for t in x["turns"]),
        "turns_with_unknown_call_count": sum(
            t["llm_call_count"] is None for x in attempts for t in x["turns"]
        ),
        "semantic_review": "separate manual artifact required; no automatic semantic certification",
    }
    write(Path(target) / "coverage.json", matrix)
    write(Path(target) / "metrics.json", metrics)
    lines = [
        "# CAIN evaluation v2",
        "",
        "Technical execution and semantic quality are separate.",
        "",
        "|Family|Cases implemented|Attempts|Execution|Quality|",
        "|---|---|---:|---|---|",
    ]
    lines += [
        f"|{x['family']}|{len(x['implemented_cases'])}|{x['attempts']}|{x['execution'] or x['state']}|{x['quality']}|"
        for x in matrix
    ]
    (Path(target) / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--root", type=Path, required=True)
    prep.add_argument("--config", type=Path, required=True)
    prep.add_argument("--catalog", type=Path, required=True)
    prep.add_argument("--rubrics", type=Path, required=True)
    srv = sub.add_parser("serve")
    srv.add_argument("--root", type=Path, required=True)
    srv.add_argument("--port", type=int, default=8896)
    srv.add_argument("--backend", default="http://127.0.0.1:11435")
    runp = sub.add_parser("run")
    runp.add_argument("--root", type=Path, required=True)
    runp.add_argument("--run-id", required=True)
    runp.add_argument("--cases", required=True)
    runp.add_argument("--paths", default="C")
    runp.add_argument("--api", default="http://127.0.0.1:8896")
    runp.add_argument("--catalog", type=Path)
    runp.add_argument("--rubrics", type=Path)
    a = p.parse_args(argv)
    if a.command == "prepare":
        prepare(a.root, a.config, a.catalog, a.rubrics)
    elif a.command == "serve":
        serve(a.root, a.port, a.backend)
    else:
        run(a.root, a.run_id, a.cases.split(","), a.paths.split(","), a.api, a.catalog, a.rubrics)


if __name__ == "__main__":
    main()
