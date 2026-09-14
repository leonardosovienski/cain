"""Exact backend replay of observed requests; diagnostic, never normal routing approval."""

import argparse
import base64
import hashlib
import json
from pathlib import Path
import time
from urllib.request import Request, urlopen


def replay(source, output, backend, case_id):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    calls = [json.loads(x) for x in Path(source).read_text(encoding="utf-8").splitlines()]
    selected = [
        c
        for c in calls
        if c["path"] == "/api/generate"
        and (c.get("case") or {}).get("case_id") == case_id
        and (c.get("case") or {}).get("path") == "C"
    ]
    manifest = {
        "protocol": "cain-product-evaluation/2.0",
        "path": "B",
        "diagnostic_override": True,
        "source": str(source),
        "source_hash": hashlib.sha256(Path(source).read_bytes()).hexdigest(),
        "case_id": case_id,
        "calls_selected": len(selected),
        "repetitions": 1,
        "backend": backend,
        "schema_and_options": "unchanged captured bytes",
        "limits": "No runtime postprocessing/memory changes; playback is not routing approval",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    for i, c in enumerate(selected):
        body = base64.b64decode(c["request_base64"])
        assert hashlib.sha256(body).hexdigest() == c["request_sha256"]
        row = {
            "source_index": i,
            "source_case": c["case"],
            "request_base64": c["request_base64"],
            "request_sha256": c["request_sha256"],
            "original_response_base64": c["response_base64"],
            "inference_policy": "required",
        }
        start = time.perf_counter()
        try:
            with urlopen(
                Request(
                    backend + "/api/generate",
                    data=body,
                    headers={"Content-Type": "application/json"},
                ),
                timeout=245,
            ) as r:
                raw = r.read()
                row.update(
                    status=r.status,
                    response_base64=base64.b64encode(raw).decode(),
                    response=json.loads(raw),
                )
        except Exception as e:
            row["error"] = f"{type(e).__name__}: {e}"
        row["seconds"] = time.perf_counter() - start
        (output / f"{i + 1}.json").write_text(
            json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(i + 1, row.get("status"), row.get("error"), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--backend", default="http://127.0.0.1:11435")
    p.add_argument("--case-id", required=True)
    a = p.parse_args()
    replay(a.source, a.output, a.backend, a.case_id)
