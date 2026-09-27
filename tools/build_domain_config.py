"""Build the DecisionPolicy configuration of one domain (src/cain/orchestration/data/<domain>.json).

The configuration says what exists in the domain; the generic DecisionPolicy (cain.orchestration.policy) is the
same for every domain. Values come only from:
  * the domain repository at a pinned commit, read with ``git show <full sha>:<path>`` (crypto:
    341d270e4d709150c581c3cd93f4518d483009eb), with the blob hash and sha256 of every file read;
  * the domain contract (DOMAIN_RESEARCH_CONTRACT.json) from the main of predictor-qualification;
  * the frozen mission parameters (FROZEN_PARAMETERS.json → decision_policy.<domain>_config).
Nothing from later commits of the domain enters the configuration.

Usage:
  python tools/build_domain_config.py crypto --repo <cripto-predictor clone> \
      --qualification <predictor-qualification clone> --contract-commit <sha on main> \n      --frozen-commit <sha of the mission's frozen parameters> --out <json>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

SOURCES = {
    "crypto": {
        "repository": "leonardosovienski/cripto-predictor",
        "commit": "341d270e4d709150c581c3cd93f4518d483009eb",
        "files": ["charters/scientific_state.json", "GarimpoInvestimentos/v3/costs.py"],
        "contract": "qualification/crypto/DOMAIN_RESEARCH_CONTRACT.json",
        "frozen": "qualification/integration-crypto/FROZEN_PARAMETERS.json",
    }
}


def git(repo: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True).stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("domain", choices=sorted(SOURCES))
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--qualification", type=Path, required=True)
    ap.add_argument("--contract-commit", required=True)
    ap.add_argument("--frozen-commit", required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    spec = SOURCES[a.domain]
    if not all(re.fullmatch(r"[0-9a-f]{40}", c) for c in (spec["commit"], a.contract_commit, a.frozen_commit)):
        raise SystemExit("commits must be full 40-hex SHAs")
    files, raw_files = [], {}
    for path in spec["files"]:
        raw = git(a.repo, "show", f"{spec['commit']}:{path}")
        raw_files[path] = raw
        files.append({"path": path, "git_blob": git(a.repo, "rev-parse", f"{spec['commit']}:{path}").decode().strip(),
                      "sha256": hashlib.sha256(raw).hexdigest()})
    contract_raw = git(a.qualification, "show", f"{a.contract_commit}:{spec['contract']}")
    frozen_raw = git(a.qualification, "show", f"{a.frozen_commit}:{spec['frozen']}")
    contract, frozen = json.loads(contract_raw), json.loads(frozen_raw)
    frozen_config = frozen["decision_policy"][f"{a.domain}_config"]
    state = json.loads(raw_files["charters/scientific_state.json"])
    closed = {f"{a.domain}:{h}": s for h, s in sorted(state["hypotheses"].items())}
    if closed != frozen_config["closed_hypotheses"] or state["frozen_families"] != frozen_config["frozen_families"]:
        raise SystemExit("scientific state at the pinned commit differs from the frozen parameters")
    costs_src = raw_files["GarimpoInvestimentos/v3/costs.py"].decode("utf-8")
    fee = float(re.search(r"taker_fee_bps: float = ([0-9.]+)", costs_src).group(1))
    slippage = float(re.search(r"slippage_bps: float = ([0-9.]+)", costs_src).group(1))
    if (fee, slippage) != (frozen_config["costs"]["fee_bps"], frozen_config["costs"]["slippage_bps"]):
        raise SystemExit("frozen costs differ from v3/costs.py at the pinned commit")
    allowed_types = sorted(contract["handler_allowlist"])
    if allowed_types != sorted(frozen_config["allowed_request_types"]):
        raise SystemExit("allowed request types differ from the contract handler_allowlist")
    config = {
        "schema": "cain-domain-config/1",
        "domain": a.domain,
        "config_version": 1,
        "source": {"repository": spec["repository"], "commit": spec["commit"], "files": files},
        "contract": {"repository": "leonardosovienski/predictor-qualification", "commit": a.contract_commit,
                     "path": spec["contract"], "sha256": hashlib.sha256(contract_raw).hexdigest(),
                     "request_schema_id": contract["request_schema"]["$id"],
                     "result_schema_id": contract["result_schema"]["id"]},
        "frozen_parameters": {"repository": "leonardosovienski/predictor-qualification",
                              "commit": a.frozen_commit, "path": spec["frozen"],
                              "sha256": hashlib.sha256(frozen_raw).hexdigest()},
        "allowed_request_types": allowed_types,
        "closed_hypotheses": closed,
        "frozen_families": state["frozen_families"],
        "proposable_hypotheses": sorted(frozen_config["proposable_hypotheses"]),
        "allowed_symbols": frozen_config["allowed_symbols"],
        "costs": {"fee_bps": int(fee), "slippage_bps": int(slippage)},
        "allowed_references": {k: sorted(v) for k, v in frozen_config["allowed_references"].items()},
        "max_priority_hint": frozen_config["max_priority_hint"],
        "budget": frozen_config["budget"],
        "cooldown": {"after_consecutive_negative": frozen_config["cooldown"]["after_consecutive_negative"],
                     "episodes": frozen_config["cooldown"]["episodes"]},
        "negative_result_states": frozen_config["cooldown"]["negative_result_states"],
        "contradiction_pairs": [["REFUTED", "SUPPORTED"]],
    }
    a.out.write_text(json.dumps(config, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(a.out, hashlib.sha256(a.out.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
