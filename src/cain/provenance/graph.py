"""Typed provenance: what influenced what, as events (never UPDATE), and cascading invalidation.

Relations: SUPPORTS, CONTRADICTS, DERIVED_FROM, INVALIDATES, USED, TRIGGERED, UPDATED.

Edges come from two places, both append-only:
* derived from records the memory already keeps (read ``as_of``): evidence DERIVED_FROM its
  document; evidence SUPPORTS the claim that cites it; a claim DERIVED_FROM its source document and,
  for EMPIRICAL_PROOF, from its run; an assessment UPDATED its claim and USED the evidence it scored;
  a finding DERIVED_FROM its source, USED its evaluation report and governance transition;
* explicit relations recorded with ``relate`` (cube ``provenance``, predicate ``prov:<RELATION>``).

Every relation has a dependency direction (who depends on whom), so ``trace`` walks ancestry,
``impact`` walks dependents, and ``invalidate`` flags (never deletes) every dependent: claims get an
assessment INCONCLUSIVE / ``needs_human_review``; other dependents get a ``prov:FLAGGED`` event.
"""

from __future__ import annotations

from collections import deque
import json
from uuid import uuid4

from cain.memory.store import MemoryStore, MemoryStoreError, instant

RELATIONS = ("SUPPORTS", "CONTRADICTS", "DERIVED_FROM", "INVALIDATES", "USED", "TRIGGERED", "UPDATED")
CUBE = "provenance"
RULE = "provenance-invalidation/1"


def dependency(src: str, relation: str, dst: str) -> tuple[str, str]:
    """(dependent, dependency) of an edge ``src --relation--> dst``."""
    if relation in ("SUPPORTS", "CONTRADICTS", "TRIGGERED", "UPDATED", "INVALIDATES"):
        return dst, src
    return src, dst  # DERIVED_FROM, USED: the source depends on the target


class ProvenanceGraph:
    def __init__(self, memory: MemoryStore):
        self.memory = memory

    # ------------------------------------------------------------------ recording
    def relate(self, src: str, relation: str, dst: str, *, by: str, note: str = "") -> dict:
        if relation not in RELATIONS:
            raise MemoryStoreError("INVALID_FIELD", f"relation must be one of {RELATIONS}")
        if not all(isinstance(v, str) and v.strip() for v in (src, dst, by)):
            raise MemoryStoreError("INVALID_FIELD", "relation needs source, target and who records it")
        return self.memory.assert_fact(CUBE, src, f"prov:{relation}", {"to": dst, "by": by, "note": note},
                                       status="DECLARED")

    # ------------------------------------------------------------------ edges
    def edges(self, *, as_of) -> list[dict]:
        at = instant(as_of)
        out: list[dict] = []

        def add(src, relation, dst, origin):
            out.append({"from": src, "relation": relation, "to": dst, "origin": origin})

        with self.memory.connection() as db:
            for row in db.execute("SELECT id, document_id FROM memory_evidence WHERE recorded_at <= ?", (at,)):
                add(row["id"], "DERIVED_FROM", row["document_id"], "evidence.recorded")
            for row in db.execute("SELECT id, source_document_id, evidence_ids, run_ref, kind FROM memory_claims "
                                  "WHERE recorded_at <= ?", (at,)):
                add(row["id"], "DERIVED_FROM", row["source_document_id"], "claim.recorded")
                for evidence in json.loads(row["evidence_ids"]):
                    add(evidence, "SUPPORTS", row["id"], "claim.recorded")
                run = json.loads(row["run_ref"])
                if row["kind"] == "EMPIRICAL_PROOF" and run:
                    add(row["id"], "DERIVED_FROM", f"run:{run['run_id']}@{run['report_sha256']}", "claim.recorded")
            for row in db.execute("SELECT event_id, claim_id, verifier_scores, assessed_by FROM "
                                  "memory_claim_assessments WHERE recorded_at <= ?", (at,)):
                add(row["event_id"], "UPDATED", row["claim_id"], "claim.assessed")
                add(row["event_id"], "USED", row["claim_id"], "claim.assessed")  # the decision rests on the claim
                for evidence in (json.loads(row["verifier_scores"]) or {}).get("evidence_ids", []):
                    add(row["event_id"], "USED", evidence, "claim.assessed")
        for fact in self._facts(at, predicate="finding"):
            obj = fact["object"]
            source = obj.get("source") or {}
            node = f"finding:{obj['finding_id']}"
            origin = "finding"
            if source.get("loop_id"):
                add(node, "DERIVED_FROM", f"loop:{source['loop_id']}", origin)
            elif source.get("path"):
                add(node, "DERIVED_FROM", f"source:{source.get('repo')}@{source.get('commit')}:{source['path']}",
                    origin)
            if obj.get("evaluation_report"):
                add(node, "USED", obj["evaluation_report"]["path"], origin)
            if obj.get("governance_transition"):
                add(node, "USED", obj["governance_transition"]["source"], origin)
        for fact in self._facts(at, predicate="review_item"):
            answered = fact["object"].get("answered_by") or {}
            if answered.get("ref"):
                add(answered["ref"], "SUPPORTS", f"review:{fact['object']['item_id']}", "review_item")
        for fact in self._facts(at, cube=CUBE):
            if fact["predicate"].startswith("prov:") and fact["predicate"] != "prov:FLAGGED":
                add(fact["subject"], fact["predicate"][5:], fact["object"]["to"], f"relate by {fact['object']['by']}")
        return out

    def _facts(self, at, *, predicate=None, cube=None):
        with self.memory.connection() as db:
            cubes = [cube] if cube else [r[0] for r in db.execute("SELECT DISTINCT cube FROM memory_facts")]
        if not cubes:
            return []
        return self.memory.facts(as_of=at, cubes=cubes, cross_cube=len(cubes) > 1, predicate=predicate)

    # ------------------------------------------------------------------ queries
    def _walk(self, start: str, *, as_of, upstream: bool) -> dict:
        edges = self.edges(as_of=as_of)
        index: dict[str, list] = {}
        for edge in edges:
            dependent, dep = dependency(edge["from"], edge["relation"], edge["to"])
            key, other = (dependent, dep) if upstream else (dep, dependent)
            index.setdefault(key, []).append((other, edge))
        seen, order, path = {start}, [], []
        queue = deque([(start, 0)])
        while queue:
            node, depth = queue.popleft()
            for other, edge in index.get(node, []):
                path.append({**edge, "depth": depth + 1})
                if other not in seen:
                    seen.add(other)
                    order.append({"node": other, "depth": depth + 1, "kind": node_kind(other)})
                    queue.append((other, depth + 1))
        return {"root": start, "nodes": order, "edges": path}

    def trace(self, node: str, *, as_of) -> dict:
        """Full ancestry: everything this object depends on."""
        return {**self._walk(node, as_of=as_of, upstream=True), "as_of": instant(as_of)}

    def impact(self, node: str, *, as_of) -> dict:
        """Everything that falls with this object if it is invalidated."""
        return {**self._walk(node, as_of=as_of, upstream=False), "as_of": instant(as_of)}

    def why(self, decision: str, *, as_of) -> dict:
        """Which evidence and runs led to a decision (and through which claims)."""
        chain = self.trace(decision, as_of=as_of)
        return {**chain, "evidence": [n["node"] for n in chain["nodes"] if n["kind"] == "evidence"],
                "runs": [n["node"] for n in chain["nodes"] if n["kind"] in ("run", "loop")],
                "claims": [n["node"] for n in chain["nodes"] if n["kind"] == "claim"],
                "documents": [n["node"] for n in chain["nodes"] if n["kind"] == "document"]}

    # ------------------------------------------------------------------ invalidation
    def invalidate(self, node: str, *, by: str, reason: str) -> dict:
        """Mark ``node`` invalid and flag every dependent for review (nothing is deleted)."""
        if not by.strip() or len(reason.strip()) < 5:
            raise MemoryStoreError("INVALID_FIELD", "an invalidation needs who and why")
        now = self.memory.now()
        dependents = self.impact(node, as_of=now)["nodes"]
        invalidation = f"invalidation:{uuid4().hex[:12]}"
        self.relate(invalidation, "INVALIDATES", node, by=by, note=reason)
        flagged = []
        for dependent in dependents:
            target = dependent["node"]
            if dependent["kind"] == "claim":
                assessment = self.memory.assess_claim(
                    target, "INCONCLUSIVE", rule=RULE, assessed_by=f"provenance:{invalidation}",
                    review_state="needs_human_review",
                    note=f"{node} was invalidated by {by}: {reason}")
                flagged.append({"node": target, "kind": "claim", "via": assessment["event_id"]})
            else:
                fact = self.memory.assert_fact(CUBE, invalidation, "prov:FLAGGED",
                                               {"to": target, "by": by, "note": f"depends on invalidated {node}"},
                                               status="DECLARED")
                flagged.append({"node": target, "kind": dependent["kind"], "via": fact["id"]})
        return {"invalidation": invalidation, "invalidated": node, "flagged": flagged}

    def flags(self, *, as_of) -> list[dict]:
        return [{"invalidation": f["subject"], **f["object"]} for f in self.memory.facts(
            as_of=as_of, cubes=[CUBE], predicate="prov:FLAGGED")]


def node_kind(node: str) -> str:
    prefix = node.split(":", 1)[0]
    return {"evidence": "evidence", "claim": "claim", "doc": "document", "event": "assessment",
            "run": "run", "loop": "loop", "finding": "finding", "review": "review_item",
            "invalidation": "invalidation", "source": "source", "inference": "model_call"}.get(prefix, "other")
