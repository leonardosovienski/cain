"""Verify installed inspection against the three real archives, then reopen offline."""

import argparse
import json
from pathlib import Path

from cain.research import ResearchService
from cain.research.inspection import inspect
from research_snapshot import canonical, digest


def verify(db, policy, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    service = ResearchService(db, policy)
    service.backup(output / "offline.db")
    configuration = json.loads(Path(policy).read_bytes())
    for binding in configuration["imports"]:
        binding["root"] = str((output / "absent" / binding["collection"]).absolute())
        assert not Path(binding["root"]).exists()
    offline_policy = output / "offline-policy.json"
    offline_policy.write_bytes(canonical(configuration))
    results = {}
    for domain, count in (("crypto", 15), ("stocks", 1), ("brasileirao", 3)):
        offline = ResearchService(output / "offline.db", offline_policy)
        scope = offline.scope(collection=domain)
        baseline = offline.query(scope, limit=50)
        dossier = inspect(offline, scope)
        assert dossier["metrics"]["record_revisions"] == count
        assert {r["id"] for r in dossier["records"]} == {r["id"] for r in baseline["records"]}
        assert {r["namespace"][0] for r in dossier["records"]} == {domain}
        assert {r["id"]: r["source_status"] for r in dossier["records"]} == {
            r["id"]: r["source_status"] for r in baseline["records"]}
        assert all(digest(e["text"].encode()) == e["sha256"] for e in dossier["evidence"])
        assert inspect(offline, offline.scope(user="unadmitted", collection=domain))["records"] == []
        results[domain] = {"metrics": dossier["metrics"], "findings": len(dossier["findings"]),
                           "graph_nodes": len(dossier["graph"]["nodes"]),
                           "graph_edges": len(dossier["graph"]["edges"]),
                           "baseline_ids_and_states_equal": True, "offline_reopened": True}
    report = {"results": results, "model_calls": 0, "economic_validation": False,
              "utility_comparison": "structural_equivalence_not_semantic_superiority"}
    (output / "report.json").write_bytes(canonical(report))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("db", "policy", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    print(json.dumps(verify(**vars(parser.parse_args())), ensure_ascii=False, indent=2))
