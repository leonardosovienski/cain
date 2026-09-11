"""Bounded, deterministic views of authorized evidence; no inferred facts or network."""

from collections import Counter, defaultdict
from datetime import datetime
from time import perf_counter

from research_snapshot import canonical, digest

NAMESPACE = ("domain", "repository", "publisher", "stream")
FIELDS = ("source_status", "status_axis", "reason", "event_at", "recorded_at",
          "available_at", "identity_basis", "supersedes", "evidence_ids")


def inspect(service, scope, *, source_id=None, domain=None, before=None, after=None):
    """Read one archive snapshot and build a local dossier, without writing history."""
    for value in (source_id, domain, before, after):
        if value is not None and (type(value) is not str or not value or len(value) > 500):
            raise ValueError("Invalid inspection filter")
    if (before is None) != (after is None):
        raise ValueError("Comparison requires both before and after revisions")
    if before is not None and not source_id:
        raise ValueError("Comparison requires an explicit source identity")
    started = perf_counter()
    policy_hash = digest(service.policy_path.read_bytes())
    with service.connection() as db:
        db.execute("BEGIN")
        archives = service._archive(db, scope)
        service._verify_projection(db, scope, archives)
        received = {row["id"]: row["received_at"] for row in db.execute(
            "SELECT id,received_at FROM publications WHERE scope=?", (scope,)
        ) if row["id"] in archives}
        result = _build(service, archives, received, source_id, domain, before, after)
    result["diagnostics"] = {
        "duration_seconds": perf_counter() - started,
        "model_calls": 0, "network_calls": 0, "policy_sha256": policy_hash,
        "snapshot_sha256": digest(canonical(sorted(archives))),
        "content_persisted": False,
    }
    if digest(service.policy_path.read_bytes()) != policy_hash:
        raise ValueError("Policy changed during inspection; retry under current permissions")
    if len(canonical(result)) > 1_000_000:
        raise ValueError("Inspection exceeds 1000000 bytes; filter source or domain")
    return result


def _build(service, archives, received, source_id, domain, before, after):
    records, evidence, packages = {}, {}, {}
    for pubid, package in sorted(archives.items()):
        if domain is not None and package["origin"]["domain"] != domain:
            continue
        lookup = {item["id"]: item for item in package["evidence"]}
        selected = [r for r in package["records"]
                    if source_id is None or r["source_id"] == source_id]
        if not selected:
            continue
        packages[pubid] = {
            "id": pubid, "origin": package["origin"], "coverage": package["coverage"],
            "exported_at": package["exported_at"], "received_at": received[pubid],
        }
        for record in selected:
            rid, _ = service.projection(package, record)
            if rid not in records:
                if len(records) >= 2000:
                    raise ValueError("Inspection exceeds 2000 revisions; filter source or domain")
                records[rid] = {
                    **record, "id": rid,
                    "namespace": [package["origin"][k] for k in NAMESPACE],
                    "publications": [], "references": [],
                }
            records[rid]["publications"].append(pubid)
            for eid in record["evidence_ids"]:
                ref = pubid + ":" + eid
                records[rid]["references"].append(ref)
                evidence[ref] = {**lookup[eid], "reference_id": ref}
    ordered = sorted(records.values(), key=lambda r: (*r["namespace"], r["source_id"], r["revision"]))
    identities = defaultdict(list)
    for record in ordered:
        identities[(*record["namespace"], record["source_id"])].append(record)

    nodes = [{"id": "record:" + r["id"], "type": "record", "label": r["source_id"],
              "revision": r["revision"]} for r in ordered]
    nodes += [{"id": "publication:" + p, "type": "publication", "label": p} for p in packages]
    nodes += [{"id": "evidence:" + e, "type": "evidence", "label": v["source"]}
              for e, v in evidence.items()]
    edges, findings, comparisons = [], [], []
    for record in ordered:
        for pubid in record["publications"]:
            edges.append({"from": "record:" + record["id"],
                          "to": "publication:" + pubid, "relation": "published_in"})
        for ref in record["references"]:
            edges.append({"from": "record:" + record["id"],
                          "to": "evidence:" + ref, "relation": "cites"})
        missing = [f for f in ("reason", "event_at", "recorded_at", "available_at")
                   if record[f] is None]
        if missing:
            findings.append({"code": "unknown_fields", "record": record["id"], "fields": missing})
        if record["identity_basis"] == "ambiguous_observation":
            findings.append({"code": "ambiguous_identity", "record": record["id"]})
        if not any(evidence[ref]["availability"] == "received" for ref in record["references"]):
            findings.append({"code": "no_received_evidence", "record": record["id"]})
    for identity, revisions in identities.items():
        by_revision = {r["revision"]: r for r in revisions}
        adjacency = {}
        for record in revisions:
            adjacency[record["revision"]] = []
            for previous in record["supersedes"]:
                if previous not in by_revision:
                    findings.append({"code": "superseded_revision_not_received",
                                     "record": record["id"], "revision": previous})
                else:
                    adjacency[record["revision"]].append(previous)
                    edges.append({"from": "record:" + record["id"],
                                  "to": "record:" + by_revision[previous]["id"],
                                  "relation": "source_declared_supersedes"})
        # Iterative topological elimination avoids recursion limits on long histories.
        pending = {key: set(values) for key, values in adjacency.items()}
        while pending:
            leaves = {key for key, values in pending.items() if not values}
            if not leaves:
                findings.append({"code": "supersession_cycle_or_dependency",
                                 "namespace_and_source": list(identity),
                                 "revisions": sorted(pending)})
                break
            pending = {key: values - leaves for key, values in pending.items() if key not in leaves}
        if len(revisions) > 1:
            findings.append({"code": "coexisting_revisions", "namespace_and_source": list(identity),
                             "revisions": sorted(by_revision), "resolution": "none_inferred"})
        if len({(r["status_axis"], r["source_status"]) for r in revisions}) > 1:
            findings.append({"code": "status_variation", "namespace_and_source": list(identity),
                             "interpretation": "difference_not_proven_contradiction"})
        if before is not None and before in by_revision and after in by_revision:
            left, right = by_revision[before], by_revision[after]
            changes = {f: {"before": left[f], "after": right[f]}
                       for f in FIELDS if left[f] != right[f]}
            left_support = sorted({canonical({k: evidence[ref][k] for k in
                                  ("source", "sha256", "hash_basis", "availability", "start", "end")}).decode()
                                   for ref in left["references"]})
            right_support = sorted({canonical({k: evidence[ref][k] for k in
                                   ("source", "sha256", "hash_basis", "availability", "start", "end")}).decode()
                                    for ref in right["references"]})
            if left_support != right_support:
                changes["evidence_support"] = {"before": left_support, "after": right_support}
            comparisons.append({"namespace_and_source": list(identity),
                                "before": left["id"], "after": right["id"],
                                "changes": changes,
                                "references_before": left["references"],
                                "references_after": right["references"]})
    if before is not None and len(comparisons) != 1:
        raise ValueError("Comparison unavailable or ambiguous in authorized scope; refine domain")
    timeline, undated = [], []
    for record in ordered:
        for field in ("event_at", "recorded_at", "available_at"):
            item = {"record": record["id"], "field": field, "at": record[field]}
            (timeline if record[field] else undated).append(item)
    for pubid, package in packages.items():
        for field in ("exported_at", "received_at"):
            timeline.append({"publication": pubid, "field": field, "at": package[field]})
    timeline.sort(key=lambda e: (datetime.fromisoformat(e["at"].replace("Z", "+00:00")),
                                  canonical(e)))
    statuses = Counter((r["namespace"][0], r["status_axis"], r["source_status"]) for r in ordered)
    return {
        "mode": "deterministic_inspection", "records": ordered,
        "publications": list(packages.values()), "evidence": list(evidence.values()),
        "graph": {"nodes": nodes, "edges": edges, "inferred_edges": 0},
        "timeline": {"dated": timeline, "unknown": undated,
                     "semantics": "source_times_and_receiver_times_are_distinct"},
        "comparisons": comparisons, "findings": findings,
        "metrics": {"record_revisions": len(records), "source_occurrences": len(identities),
                    "publications": len(packages), "evidence_references": len(evidence),
                    "received_content_hashes": len({e["sha256"] for e in evidence.values()
                                                     if e["availability"] == "received"}),
                    "statuses": [{"domain": d, "axis": a, "status": s, "count": n}
                                 for (d, a, s), n in sorted(statuses.items())]},
        "limitations": [
            "Only currently authorized received publications; absence is not nonexistence",
            "Dates and supersession are source declarations, not verified temporal truth",
            "Differences are not established contradictions; no latest revision selected",
            "Counts and identical hashes do not establish independent experiments",
            "Local inspection is not predictive, economic or semantic validation",
        ],
    }
