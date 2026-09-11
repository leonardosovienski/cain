"""Verify installed research delivery; writes only receiver receipts and new backup files."""
import argparse
import json
from pathlib import Path
from time import perf_counter

from cain.research import ResearchService
from research_snapshot import canonical, digest


def verify(db, policy, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    service = ResearchService(db, policy)
    results = {}
    for domain, expected in (("crypto", 15), ("stocks", 1), ("brasileirao", 3)):
        scope = service.scope(collection=domain)
        start = perf_counter()
        result = service.query(scope, limit=50)
        assert result["total_record_revisions"] == expected
        assert {r["domain"] for r in result["records"]} == {domain}
        refs = {e["reference_id"] for r in result["records"] for e in r["evidence"]}
        for ref in refs:
            item = service.evidence(scope, ref)
            assert digest(item["text"].encode("utf-8")) == item["sha256"]
        assert not service.query(service.scope(user="unadmitted", collection=domain))["records"]
        service.verify(scope)
        service.verify(scope, rebuild=True)
        results[domain] = dict(records=expected, references=len(refs),
                               query_evidence_verify_rebuild_seconds=perf_counter() - start)
    backup = output / "research-backup.db"
    service.backup(backup)
    restored = output / "research-restored.db"
    ResearchService.restore(backup, restored)
    offline_policy = json.loads(Path(policy).read_bytes())
    assert offline_policy["version"] == 2
    for binding in offline_policy["imports"]:
        binding["root"] = str((output / "unavailable-producers" / binding["collection"]).absolute())
        assert not Path(binding["root"]).exists()
    offline_path = output / "offline-policy.json"
    offline_path.write_bytes(canonical(offline_policy))
    reopened = ResearchService(restored, offline_path)
    for domain, observed in results.items():
        assert reopened.query(reopened.scope(collection=domain))["total_record_revisions"] == observed["records"]
        observed["restored_with_all_producer_roots_absent"] = True
    report = dict(results=results, model_calls=0, economic_validation=False,
                  scope="Installed local receiver; public report snapshots only")
    (output / "report.json").write_bytes(canonical(report))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("db", "policy", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    print(json.dumps(verify(**vars(parser.parse_args())), indent=2))
