"""Frozen evaluator adapter: the CAIN loop's stage protocol over the Brasileirão research worker.

Runs with the Brasileirão predictor's own Python (its installed wheel). It only calls the worker's
``walkforward`` and ``evaluate`` (pure; they write nothing) over the immutable SQLite snapshot opened
read-only, and applies the loop's parameters to a copy of the serving-baseline model config.

Stages (stdin ``{"stage", "params", "data"}`` → stdout one JSON line):
* sanity        snapshot sha256 check, no information after the decision cutoff (engine audit),
                target count, and a cheap signal (p_home − p_away on the last 60 matches of 2021);
* in_sample     full monthly walk-forward on 2021 (1X2 vs climatology);
* walk_forward  full monthly walk-forward on 2022, the development season with a recorded reference;
* holdout       refused: 2025 is sealed by the Brasileirão policy; unsealing it is the predictor's
                governed process, not something this adapter may do.
"""

import copy
import datetime as dt
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import sys

from brasileirao_predictor.research_runtime import worker as w

PARAMETERS = {
    "elo_home_advantage": ("elo", "home_advantage"),
    "elo_form_half_life_years": ("elo", "form_half_life_years"),
    "elo_window_years": ("elo", "window_years"),
    "model_calibration_window_years": ("model", "calibration_window_years"),
    "model_max_goals": ("model", "max_goals"),
}
SEASONS = {"in_sample": "2021", "walk_forward": "2022"}
AS_OF = "2026-09-08T19:31:32Z"


def _data(request):
    by_role = {entry.get("role"): entry for entry in request["data"]}
    return Path(by_role["snapshot"]["path"]), by_role["snapshot"].get("sha256"), Path(by_role["objects"]["path"])


def _load(root: Path, name: str):
    return json.loads((root / name).read_text(encoding="utf-8"))


def _config(root: Path, params: dict) -> tuple[dict, dict]:
    model = _load(root, "model-serving-baseline.json")
    config = copy.deepcopy(model["config"])
    for name, value in params.items():
        section, key = PARAMETERS[name]
        config[section][key] = value
    return model, config


def _season(db, root: Path, season: str, config: dict, *, limit: int | None = None):
    request = _load(root, f"req/{season}-1X2-climatology.json")
    refs = {"model": {**_load(root, "model-serving-baseline.json"), "config": config},
            "features": _load(root, "features-elo-home-advantage.json"),
            "baseline": _load(root, "baseline-climatology.json"),
            "cost_model": _load(root, "cost_model-close-slippage-tax.json"),
            "odds": _load(root, "odds-sofascore-close.json")}
    cutoff = w.parse_instant(request["data_cutoff"], "data_cutoff")
    info = [r for r in w._information(db, w.parse_instant(AS_OF, "as_of")) if r["available_at"] < cutoff]
    targets, quality = w._targets(db, request, cutoff, dt.timedelta(minutes=request["decision_lead_minutes"]))
    if limit is not None:
        targets = targets[-limit:]  # the last matches: early-season ones are not predicted
    decisions, audit = w.walkforward(info, targets, config, w.GoalModelCache())
    return request, refs, info, targets, quality, decisions, audit


def main():
    request = json.load(sys.stdin)
    stage, params = request["stage"], request["params"]
    unknown = sorted(set(params) - set(PARAMETERS))
    if unknown:
        print(json.dumps({"stage": stage, "ok": False, "checks": {"unknown_parameters": unknown}}))
        return
    if stage == "holdout":
        print(json.dumps({"stage": stage, "ok": False, "checks": {
            "refused": "2025 is sealed by the Brasileirão policy; run it through brasileirao-research with a "
                       "human decision, not from the CAIN loop"}}))
        return
    snapshot, expected, root = _data(request)
    db = sqlite3.connect(f"file:{snapshot}?mode=ro&immutable=1", uri=True)
    _, config = _config(root, params)
    if stage == "sanity":
        digest = sha256(snapshot.read_bytes()).hexdigest()
        _, _, info, targets, _, decisions, audit = _season(db, root, "2021", config, limit=60)
        leaked = audit.get("max_used_minus_cutoff_seconds")
        checks = {"snapshot_sha256": digest, "snapshot_matches_world": digest == expected,
                  "information_rows": len(info), "targets": len(targets),
                  "max_used_minus_cutoff_seconds": leaked, "no_lookahead": leaked is not None and leaked <= 0,
                  "predicted": sum(d.get("status") == "PREDICTED" for d in decisions)}
        ok = checks["snapshot_matches_world"] and checks["no_lookahead"] and checks["predicted"] == len(targets)
        signal = [d["p_home"] - d["p_away"] for d in decisions if d.get("status") == "PREDICTED"]
        print(json.dumps({"stage": stage, "ok": ok, "metrics": {}, "checks": checks, "signal": signal}))
        return
    season = SEASONS[stage]
    req, refs, _, targets, quality, decisions, audit = _season(db, root, season, config)
    out = w.evaluate(req, refs, targets, decisions, quality)
    evaluation = out["evaluation"]
    leaked = audit.get("max_used_minus_cutoff_seconds")
    metrics = {"rps": evaluation["model"]["rps"], "baseline_rps": evaluation["baseline_scores"]["rps"],
               "mean_delta": evaluation["mean_delta"], "ci_delta": evaluation["ci_delta"],
               "log_loss": evaluation["model"]["log_loss"], "n": evaluation["n_evaluated"]}
    print(json.dumps({"stage": stage, "ok": leaked is not None and leaked <= 0, "metrics": metrics,
                      "checks": {"season": season, "result_state": out["result_state"],
                                 "max_used_minus_cutoff_seconds": leaked, "rule": evaluation.get("rule")}}))


if __name__ == "__main__":
    main()
