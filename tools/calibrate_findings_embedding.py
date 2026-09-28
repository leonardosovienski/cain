"""Calibrate the findings embedding on the sealed stocks set (docs/evidence/2026-09-28-findings-calibration).

Decision of the owner (integration-stocks, 2026-09-28, "Calibrar embedding"): enrich the statements of the closed
hypotheses, measure the local embedding on a labelled set, show the separation and a threshold; the owner approves the
number by merging findings-policy v3, and only then the embedding decides.

Procedure, fixed before the measurement (this file is committed before it runs):
  1. The closed stocks findings are ingested from stocks-predictor at a pinned commit, with the CAIN code
     (``read_source`` + ``ingest_scientific_state``), in three statement variants:
       state      the scientific state alone (as in the utility rounds);
       registry   plus the trial registry (trials_v2.json), identity + params + notes;
       described  ``--describe``: plain words, the parameters that tell each trial apart and the RESEARCH_FREEZE
                  manifest's result and note.
  2. Each text of the set goes through ``equivalent_closed`` first (identity, name and lexical routes of the policy in
     force). A text those routes already match is reported and left out of the embedding numbers.
  3. Score of a text = the highest embedding cosine (``similarity_function("embedding")``, the model and digest pinned
     in the config) between the text and the statement of each closed finding of the domain: the same pairs
     ``equivalent_closed`` visits.
  4. The variant is the one with the highest AUC (closed vs new) on the calibration split.
  5. Threshold t* = the smallest multiple of 0.001 above the highest score of a new text of the calibration split:
     no calibration new idea is blocked. Reported on both splits: closed texts caught, new texts blocked (hard or
     not). For comparison only: t_J, the calibration threshold with the largest TPR - FPR (ties: the higher one).
  6. Recommendation, fixed here: propose t* in findings-policy v3 only if, on the validation split, it catches at
     least half of the closed texts and blocks no new text. Otherwise the report says the measure does not separate
     well enough and the embedding stays review-only; the owner decides either way.

Usage: python tools/calibrate_findings_embedding.py --stocks-repo <clone> --commit <full sha> \\
           --set docs/evidence/2026-09-28-findings-calibration/calibration-set.json --config <cain.toml> --out <dir>
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import tempfile

from cain import policy as policies
from cain.findings.archive import FindingsArchive, equivalence_policy
from cain.findings.ingest import freeze_manifest, ingest_scientific_state, read_source
from cain.loop.similarity import similarity_function
from cain.memory.store import MemoryStore

STATE, REGISTRY, MANIFEST = "research/scientific_state.json", "trials_v2.json", "RESEARCH_FREEZE.md"
VARIANTS = ("state", "registry", "described")


def closed_findings(repo: Path, commit: str, variant: str, db: Path) -> tuple[FindingsArchive, list[dict], list]:
    archive = FindingsArchive(MemoryStore(db))
    raw, source = read_source(repo, commit, STATE)
    rows, sources = None, [source]
    if variant in ("registry", "described"):
        registry_raw, registry_source = read_source(repo, commit, REGISTRY)
        rows, sources = json.loads(registry_raw), [*sources, registry_source]
    describe = None
    if variant == "described":
        manifest_raw, manifest_source = read_source(repo, commit, MANIFEST)
        describe, sources = {"manifest": freeze_manifest(manifest_raw), "manifest_source": manifest_source}, \
            [*sources, manifest_source]
    ingest_scientific_state(archive, "stocks", raw, source, rows, describe)
    return archive, archive.closed("stocks", as_of=archive.memory.now()), sources


def auc(closed: list[float], new: list[float]) -> float:
    """Probability that a closed text scores above a new one (ties count half)."""
    if not closed or not new:
        return float("nan")
    wins = sum((c > n) + 0.5 * (c == n) for c in closed for n in new)
    return wins / (len(closed) * len(new))


def at(threshold: float, rows: list[dict]) -> dict:
    closed = [r for r in rows if r["label"] == "closed"]
    new = [r for r in rows if r["label"] == "new"]
    caught = [r["id"] for r in closed if r["score"] >= threshold]
    blocked = [r["id"] for r in new if r["score"] >= threshold]
    return {"threshold": threshold, "closed": len(closed), "closed_caught": len(caught),
            "closed_recall": round(len(caught) / len(closed), 4) if closed else None,
            "closed_missed": sorted(r["id"] for r in closed if r["score"] < threshold),
            "new": len(new), "new_blocked": len(blocked), "new_blocked_ids": sorted(blocked),
            "new_blocked_hard": sum(bool(r.get("hard")) for r in new if r["score"] >= threshold)}


def youden(rows: list[dict]) -> float:
    closed = [r["score"] for r in rows if r["label"] == "closed"]
    new = [r["score"] for r in rows if r["label"] == "new"]
    best = None
    for t in sorted({r["score"] for r in rows}):
        j = sum(c >= t for c in closed) / len(closed) - sum(n >= t for n in new) / len(new)
        if best is None or j >= best[0]:
            best = (j, t)
    return round(best[1], 4)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stocks-repo", type=Path, required=True)
    ap.add_argument("--commit", required=True)
    ap.add_argument("--set", type=Path, required=True)
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", a.commit):
        raise SystemExit("--commit must be a full 40-hex SHA")
    a.out.mkdir(parents=True, exist_ok=False)
    set_raw = a.set.read_bytes()
    labelled = json.loads(set_raw)
    rank = similarity_function("embedding", a.config)
    rules = equivalence_policy()
    report = {"schema": "cain-findings-calibration/1", "started_at": datetime.now(timezone.utc).isoformat(),
              "set": {"path": a.set.as_posix(), "sha256": hashlib.sha256(set_raw).hexdigest(),
                      "items": len(labelled["items"])},
              "stocks": {"commit": a.commit}, "policy_in_force": policies.ref(rules),
              "cain_commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                                            check=True).stdout.strip(),
              "config": {"path": a.config.as_posix(), "sha256": hashlib.sha256(a.config.read_bytes()).hexdigest()},
              "variants": {}}
    with tempfile.TemporaryDirectory() as tmp:
        for variant in VARIANTS:
            archive, closed, sources = closed_findings(a.stocks_repo, a.commit, variant, Path(tmp) / f"{variant}.db")
            now = archive.memory.now()
            rows = []
            for item in labelled["items"]:
                matches = archive.equivalent_closed("stocks", item["text"], as_of=now, identity={})
                scored = sorted(((rank(item["text"], f["statement"]), f["finding_id"]) for f in closed), reverse=True)
                target = item.get("target")
                rows.append({**{k: item[k] for k in ("id", "split", "label", "lang") if k in item},
                             **({"target": target} if target else {}),
                             **({"hard": True} if item.get("hard") else {}),
                             **({"kind": item["kind"]} if item.get("kind") else {}),
                             "policy_match": [m["finding_id"] for m in matches],
                             "score": round(scored[0][0], 4), "top": [[fid, round(s, 4)] for s, fid in scored[:3]],
                             "top_is_target": bool(target) and scored[0][1] == f"stocks:hypothesis:{target}"})
            measured = [r for r in rows if not r["policy_match"]]
            calibration = [r for r in measured if r["split"] == "calibration"]
            validation = [r for r in measured if r["split"] == "validation"]
            new_calibration = [r["score"] for r in calibration if r["label"] == "new"]
            t_star = math.floor(max(new_calibration) * 1000 + 1) / 1000
            t_j = youden(calibration)
            report["variants"][variant] = {
                "sources": sources, "closed_findings": len(closed),
                "closed_statement_sample": {f["finding_id"]: f["statement"][:400] for f in closed[:4]},
                "decided_by_policy": [{"id": r["id"], "label": r["label"], "match": r["policy_match"]}
                                      for r in rows if r["policy_match"]],
                "auc": {"calibration": round(auc([r["score"] for r in calibration if r["label"] == "closed"],
                                                 new_calibration), 4),
                        "validation": round(auc([r["score"] for r in validation if r["label"] == "closed"],
                                                [r["score"] for r in validation if r["label"] == "new"]), 4)},
                "top_is_target": {split: f"{sum(r['top_is_target'] for r in part)}/"
                                         f"{sum(r['label'] == 'closed' for r in part)}"
                                  for split, part in (("calibration", calibration), ("validation", validation))},
                "t_star": {"calibration": at(t_star, calibration), "validation": at(t_star, validation)},
                "t_youden_for_comparison": {"calibration": at(t_j, calibration), "validation": at(t_j, validation)},
                "rows": rows,
            }
    chosen = max(VARIANTS, key=lambda v: report["variants"][v]["auc"]["calibration"])
    validation = report["variants"][chosen]["t_star"]["validation"]
    report["chosen_variant"] = chosen
    report["threshold"] = report["variants"][chosen]["t_star"]["calibration"]["threshold"]
    report["recommendation"] = (
        "PROPOSE_THRESHOLD" if validation["closed_recall"] >= 0.5 and validation["new_blocked"] == 0
        else "KEEP_REVIEW_ONLY")
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    out = a.out / "calibration-result.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"chosen_variant": chosen, "threshold": report["threshold"],
                      "recommendation": report["recommendation"],
                      "auc": {v: report["variants"][v]["auc"] for v in VARIANTS},
                      "validation_at_t_star": {k: validation[k] for k in ("closed_recall", "new_blocked")}},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
