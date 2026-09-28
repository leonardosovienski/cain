"""Build the DecisionPolicy configuration of one domain (src/cain/orchestration/data/<domain>.json).

The configuration says what exists in the domain; the generic DecisionPolicy (cain.orchestration.policy) is the
same for every domain. Values come only from:
  * the domain repository at a pinned commit, read with ``git show <full sha>:<path>`` (crypto:
    341d270e4d709150c581c3cd93f4518d483009eb; stocks: 61fc017256ffea815ae96bbe02b847dccdb395cc; brasileirao:
    25cdf4d9bb309d33f066fbc6a379f5d98c69f08a), with the blob hash and sha256 of every file read;
  * brasileirao only: CAIN's own research-loop ledger of PR #50 (docs/evidence/2026-09-24-prompt6/ledger-events.jsonl),
    read with ``git show`` at the pinned CAIN commit deccaaa0a0e2cb2b5f292614659eb4bf2e943e50;
  * the domain contract (DOMAIN_RESEARCH_CONTRACT.json) from the main of predictor-qualification;
  * the frozen mission parameters (FROZEN_PARAMETERS.json → decision_policy.<domain>_config);
  * stocks only, by the owner's decision D-26: the ``frozen_families`` list of one later file of the domain, named in
    the frozen parameters (``additional_frozen_families``: repository, full commit, path, blob, sha256 and the families
    it adds). The families are added to the base's, never removed, and nothing else of that file is read.
Nothing else from later commits of the domain enters the configuration.

Usage:
  python tools/build_domain_config.py {crypto,stocks,brasileirao} --repo <domain repository clone> \
      --qualification <predictor-qualification clone> --contract-commit <sha on main> \n      --frozen-commit <sha of the mission's frozen parameters> --out <json>
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

SOURCES = {
    "crypto": {
        "repository": "leonardosovienski/cripto-predictor",
        "commit": "341d270e4d709150c581c3cd93f4518d483009eb",
        "files": ["charters/scientific_state.json", "GarimpoInvestimentos/v3/costs.py"],
        "contract": "qualification/crypto/DOMAIN_RESEARCH_CONTRACT.json",
        "frozen": "qualification/integration-crypto/FROZEN_PARAMETERS.json",
    },
    "stocks": {
        "repository": "leonardosovienski/stocks-predictor",
        "commit": "61fc017256ffea815ae96bbe02b847dccdb395cc",
        "files": ["stocks_predictor/research_admission.py", "trials_v2.json", "trials.json", "config.yaml",
                  "EXTERNAL_INTELLIGENCE_TRIAL_READINESS_MATRIX.json"],
        "contract": "qualification/stocks/DOMAIN_RESEARCH_CONTRACT.json",
        "frozen": "qualification/integration-stocks/FROZEN_PARAMETERS.json",
    },
    "brasileirao": {
        "repository": "leonardosovienski/brasileirao-predictor",
        "commit": "25cdf4d9bb309d33f066fbc6a379f5d98c69f08a",
        "files": ["data/trials.json"],
        "contract": "qualification/brasileirao/DOMAIN_RESEARCH_CONTRACT.json",
        "frozen": "qualification/integration-brasileirao/FROZEN_PARAMETERS.json",
    },
}
CAIN_ROOT = Path(__file__).resolve().parents[1]
BRASILEIRAO_LOOP = ("deccaaa0a0e2cb2b5f292614659eb4bf2e943e50", "docs/evidence/2026-09-24-prompt6/ledger-events.jsonl")


def git(repo: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True).stdout


def read_crypto(domain: str, raw_files: dict[str, bytes]) -> tuple[dict, list, float, float]:
    """charters/scientific_state.json (hypotheses, frozen families) and v3/costs.py (taker fee, slippage)."""
    state = json.loads(raw_files["charters/scientific_state.json"])
    closed = {f"{domain}:{h}": s for h, s in sorted(state["hypotheses"].items())}
    costs_src = raw_files["GarimpoInvestimentos/v3/costs.py"].decode("utf-8")
    fee = float(re.search(r"taker_fee_bps: float = ([0-9.]+)", costs_src).group(1))
    slippage = float(re.search(r"slippage_bps: float = ([0-9.]+)", costs_src).group(1))
    return closed, state["frozen_families"], fee, slippage


def read_stocks(domain: str, raw_files: dict[str, bytes]) -> tuple[dict, list, float, float]:
    """research_admission.closed_hypotheses() (H1..H22, the compiled admission's own map), the families of the closed
    hypotheses (trials_v2.json hypothesis_family; trials.json <hn>_factor.name where trials_v2 says UNKNOWN) and the
    [H1-FROZEN] costs of config.yaml (b3_fee_pct, spread_slippage_pct, in basis points)."""
    tree = ast.parse(raw_files["stocks_predictor/research_admission.py"].decode("utf-8"))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "closed_hypotheses")
    namespace: dict = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), "research_admission.py", "exec"), namespace)  # noqa: S102
    status = namespace["closed_hypotheses"]()
    closed = dict(sorted(status.items(), key=lambda kv: int(kv[0].split(":H")[1])))
    families = set()
    for legacy, modern in zip(json.loads(raw_files["trials.json"]), json.loads(raw_files["trials_v2.json"]),
                              strict=True):
        family = modern["hypothesis_family"]
        if family == "UNKNOWN":
            family = legacy["params"][f"{modern['hypothesis_id'].lower()}_factor.name"]
        if f"{domain}:{modern['hypothesis_id']}" not in closed:
            raise SystemExit(f"trial of a hypothesis that is not closed: {modern['hypothesis_id']}")
        families.add(family)
    config_yaml = raw_files["config.yaml"].decode("utf-8")
    fee = float(re.search(r"^\s*b3_fee_pct:\s*([0-9.]+)\s*# \[H1-FROZEN\]", config_yaml, re.M).group(1)) * 10000
    slippage = float(re.search(r"^\s*spread_slippage_pct:\s*([0-9.]+)\s*# \[H1-FROZEN\]", config_yaml, re.M).group(1))
    return closed, sorted(families), round(fee, 6), round(slippage * 10000, 6)


def read_brasileirao(domain: str, raw_files: dict[str, bytes], contract: dict) -> tuple[dict, list, dict]:
    """Closed hypotheses of the Brasileirão (D-25): the trials with status ``refutada`` of data/trials.json at the base
    (negative per cain.findings.ingest.STATUS_KIND), the hypotheses the contract protects (the admission refuses them)
    and the hypothesis of CAIN's research loop (PR #50) that stopped without improvement, with its world as a frozen
    family. The request has no parameters, so there are no costs to compare (the cost model is an operator reference)."""
    closed = {}
    for row in json.loads(raw_files["data/trials.json"]):
        if row.get("status") == "refutada":
            identity = row.get("trial_id") or row.get("name")
            closed[f"{domain}:{identity}"] = "REFUTED (data/trials.json status refutada em 25cdf4d; PR #51: negativo)"
    for hypothesis in contract["admission_policy"]["protected_hypotheses_required"]:
        closed[hypothesis] = "PROTECTED_BY_ADMISSION (contrato: protected_hypotheses_required)"
    loops: dict[str, dict] = {}
    for line in git(CAIN_ROOT, "show", ":".join(BRASILEIRAO_LOOP)).decode("utf-8").splitlines():
        event = json.loads(line)
        body, loop = event.get("body") or {}, event.get("loop_id") or event.get("stream")
        if event["kind"] == "loop.started" and body["world_id"].startswith(f"{domain}-"):
            loops[loop] = {"hypothesis": body["hypothesis"], "world_id": body["world_id"], "improved": False}
        elif loop in loops and event["kind"] == "experiment.finished":
            loops[loop]["improved"] |= bool(body.get("improved")) and body.get("step_kind") != "baseline"
        elif loop in loops and event["kind"] == "loop.stopped":
            loops[loop]["stop"] = body["reason"]
    families = set()
    for loop in loops.values():
        if loop.get("stop") and not loop["improved"]:
            name = f"{domain}:" + loop["hypothesis"].replace(":", ".")
            closed[name] = ("NO_IMPROVEMENT_OVER_BASELINE (loop do PR #50: 2 ciclos, estagnação; hipótese "
                            f"{loop['hypothesis']} do ledger, com ':' trocado por '.' para o padrão brasileirao:<id>)")
            families.add(loop["world_id"])
    return dict(sorted(closed.items())), sorted(families), {}


READERS = {"crypto": read_crypto, "stocks": read_stocks}
ADDITIONAL_KEYS = {"decision", "repository", "commit", "path", "git_blob", "sha256", "key", "added"}


def additional_families(domain: str, repo: Path, frozen_config: dict, base: list) -> tuple[list, dict | None]:
    """Base families plus the frozen families of a later domain file (D-26, stocks): the file named in the frozen
    parameters, read with ``git show <full sha>:<path>``, its blob and sha256 checked; only its ``frozen_families``
    list is read. A family is added, never removed; the families it adds must be the ones the frozen parameters
    list. Without ``additional_frozen_families``: the base families, no source."""
    extra = frozen_config.get("additional_frozen_families")
    if extra is None:
        return list(base), None
    if domain != "stocks" or set(extra) != ADDITIONAL_KEYS or extra["key"] != "frozen_families":
        raise SystemExit("additional_frozen_families: stocks only, with " + ", ".join(sorted(ADDITIONAL_KEYS)))
    if extra["repository"] != SOURCES[domain]["repository"] or not re.fullmatch(r"[0-9a-f]{40}", extra["commit"]):
        raise SystemExit("additional_frozen_families: the domain repository at a full 40-hex SHA")
    raw = git(repo, "show", f"{extra['commit']}:{extra['path']}")
    blob = git(repo, "rev-parse", f"{extra['commit']}:{extra['path']}").decode().strip()
    if (blob, hashlib.sha256(raw).hexdigest()) != (extra["git_blob"], extra["sha256"]):
        raise SystemExit("additional_frozen_families: blob or sha256 differs from the frozen parameters")
    families = json.loads(raw)[extra["key"]]
    if not isinstance(families, list) or not all(isinstance(f, str) and f for f in families):
        raise SystemExit("additional_frozen_families: the file's frozen_families is not a list of names")
    added = sorted(set(families) - set(base))
    if added != sorted(extra["added"]):
        raise SystemExit(f"additional_frozen_families: the later file adds {added}, not the frozen parameters' list")
    source = {k: extra[k] for k in ("decision", "repository", "commit", "path", "git_blob", "sha256", "key")}
    return sorted(set(base) | set(families)), {**source, "added": added}


def sealed_scopes(frozen_config: dict) -> list:
    """Lacres da R16. Lista = formato de máquina; objeto só é aceito quando declara que ainda não foi materializado."""
    value = frozen_config.get("sealed_scopes", [])
    if isinstance(value, list):
        return value
    if isinstance(value, dict) and value.get("materialized_in_cain_config") is False:
        print("sealed_scopes ainda não materializado no FROZEN_PARAMETERS: configuração sem lacre", file=sys.stderr)
        return []
    raise SystemExit("sealed_scopes do FROZEN_PARAMETERS não está em formato de máquina (lista)")


def request_types(allowed_types: list, proposable: list, qualification: Path, frozen_commit: str, frozen: str) -> dict:
    """Request type of each proposable hypothesis: the LLM request template and R04 bind a hypothesis to it (the
    utility round showed a collection hypothesis sent as a backtest). With one allowed type every proposable
    hypothesis has it. With several (stocks), the mission's frozen proposal fixtures at the frozen commit decide
    (``git show``); each proposable hypothesis must appear there with exactly one allowed type."""
    if len(allowed_types) == 1:
        return {h: allowed_types[0] for h in proposable}
    folder = frozen.rsplit("/", 1)[0] + "/fixtures/proposals/"
    seen: dict[str, set] = {}
    for name in git(qualification, "ls-tree", "-r", "--name-only", frozen_commit, folder).decode().split():
        if name.endswith(".json"):
            request = json.loads(git(qualification, "show", f"{frozen_commit}:{name}"))["request"]
            seen.setdefault(request["hypothesis_id"], set()).add(request["request_type"])
    out = {}
    for hypothesis in proposable:
        types = seen.get(hypothesis, set())
        if len(types) != 1 or not types <= set(allowed_types):
            raise SystemExit(f"request type of {hypothesis} is not fixed by the frozen fixtures: {sorted(types)}")
        out[hypothesis] = next(iter(types))
    return out


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
    if a.domain == "brasileirao":
        closed, families, costs = read_brasileirao(a.domain, raw_files, contract)
        if costs != frozen_config["costs"]:
            raise SystemExit("frozen costs differ from the domain's request (no parameters, no costs)")
    else:
        closed, families, fee, slippage = READERS[a.domain](a.domain, raw_files)
        if (fee, slippage) != (frozen_config["costs"]["fee_bps"], frozen_config["costs"]["slippage_bps"]):
            raise SystemExit("frozen costs differ from the domain's cost source at the pinned commit")
        costs = {"fee_bps": int(fee), "slippage_bps": int(slippage)}
    families, later_source = additional_families(a.domain, a.repo, frozen_config, families)
    if closed != frozen_config["closed_hypotheses"] or families != frozen_config["frozen_families"]:
        raise SystemExit("scientific state at the pinned commit differs from the frozen parameters")
    allowed_types = sorted(contract["handler_allowlist"])
    if allowed_types != sorted(frozen_config["allowed_request_types"]):
        raise SystemExit("allowed request types differ from the contract handler_allowlist")
    config = {
        "schema": "cain-domain-config/1",
        "domain": a.domain,
        "config_version": 1,
        "source": {"repository": spec["repository"], "commit": spec["commit"], "files": files,
                   # D-26 (stocks): families added from a later file; key emitted only when present
                   **({"additional_frozen_families": later_source} if later_source else {})},
        "contract": {"repository": "leonardosovienski/predictor-qualification", "commit": a.contract_commit,
                     "path": spec["contract"], "sha256": hashlib.sha256(contract_raw).hexdigest(),
                     "request_schema_id": contract["request_schema"]["$id"],
                     "result_schema_id": contract["result_schema"]["id"]},
        "frozen_parameters": {"repository": "leonardosovienski/predictor-qualification",
                              "commit": a.frozen_commit, "path": spec["frozen"],
                              "sha256": hashlib.sha256(frozen_raw).hexdigest()},
        "allowed_request_types": allowed_types,
        "closed_hypotheses": closed,
        "frozen_families": families,
        "proposable_hypotheses": sorted(frozen_config["proposable_hypotheses"]),
        "allowed_symbols": frozen_config["allowed_symbols"],
        "costs": costs,
        "allowed_references": {k: sorted(v) for k, v in frozen_config["allowed_references"].items()},
        "max_priority_hint": frozen_config["max_priority_hint"],
        "budget": frozen_config["budget"],
        "cooldown": {"after_consecutive_negative": frozen_config["cooldown"]["after_consecutive_negative"],
                     "episodes": frozen_config["cooldown"]["episodes"]},
        "negative_result_states": frozen_config["cooldown"]["negative_result_states"],
        "contradiction_pairs": [["REFUTED", "SUPPORTED"]],
        # R16: escopos lacrados (ex.: holdout) em formato de máquina no FROZEN_PARAMETERS da integração; sem a
        # chave, nenhum lacre (cripto e stocks).
        "sealed_scopes": sealed_scopes(frozen_config),
        # tipo de pedido de cada hipótese proponível (molde do LLM e R04); um tipo só: todas; vários: fixtures congeladas
        "proposable_request_types": request_types(allowed_types, sorted(frozen_config["proposable_hypotheses"]),
                                                  a.qualification, a.frozen_commit, spec["frozen"]),
    }
    # sobreposição de parâmetros por hipótese no molde do LLM (ex.: controle negativo com semente própria no stocks);
    # chave opcional, emitida só quando não é vazia (crypto.json e brasileirao.json ficam com os mesmos bytes)
    overlays = frozen_config.get("proposal_overlays", {})
    if not set(overlays) <= set(frozen_config["proposable_hypotheses"]):
        raise SystemExit("proposal_overlays of hypotheses that are not proposable")
    if overlays:
        config["proposal_overlays"] = {h: overlays[h] for h in sorted(overlays)}
    # métricas do resultado que o CAIN guarda nos fatos e mostra ao modelo (nome -> caminho no payload); chave opcional,
    # emitida só quando não é vazia
    metrics = frozen_config.get("result_metrics", {})
    if metrics:
        config["result_metrics"] = {name: metrics[name] for name in sorted(metrics)}
    a.out.write_text(json.dumps(config, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(a.out, hashlib.sha256(a.out.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
