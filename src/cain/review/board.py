"""Adversarial review before pre-registration (STORM-style perspectives; the human is the moderator).

A draft hypothesis is reviewed from configurable perspectives (``data/perspectives-v1.toml``). A local
model asks each perspective's questions with structured output (every call has an inference
manifest, Prompt 5); each question becomes a checklist item with a proposed test, or is marked not
testable with a reason. The closed-hypothesis archive (Prompt 7) adds its own mandatory item.

The question map (question → test / evidence / run → status) lives in the bitemporal memory as facts
of the domain's cube: it survives restarts, every change supersedes (nothing is overwritten), and it
can be read ``as_of``. Statuses: OPEN, TEST_DEFINED, ANSWERED, NOT_TESTABLE, WAIVED.

Pre-registration is refused while any mandatory item is OPEN or NOT_TESTABLE: each needs a defined
test, an answer with evidence, or a waiver recorded by a named human with a reason.
"""

from __future__ import annotations

from hashlib import sha256
from importlib.resources import files
import tomllib

from cain.memory.jcs import canonicalize
from cain.memory.store import MemoryStore, MemoryStoreError

EXTRACTOR = "cain-review/1"
RESOLVED = ("TEST_DEFINED", "ANSWERED", "WAIVED")
STATUSES = ("OPEN", "TEST_DEFINED", "ANSWERED", "NOT_TESTABLE", "WAIVED")
TEST_KINDS = ("backtest", "statistical", "data_check", "prospective", "manual")
QUESTION_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["questions"],
    "properties": {"questions": {"type": "array", "minItems": 1, "maxItems": 3, "items": {
        "type": "object", "additionalProperties": False,
        "required": ["question", "why", "testable", "test_kind", "test", "pass_criterion", "not_testable_reason"],
        "properties": {
            "question": {"type": "string", "minLength": 10, "maxLength": 400},
            "why": {"type": "string", "minLength": 3, "maxLength": 400},
            "testable": {"type": "boolean"},
            "test_kind": {"type": "string", "enum": list(TEST_KINDS)},
            "test": {"type": "string", "maxLength": 600},
            "pass_criterion": {"type": "string", "maxLength": 300},
            "not_testable_reason": {"type": "string", "maxLength": 400}}}}},
}


def perspectives_bytes() -> bytes:
    return files("cain.review").joinpath("data/perspectives-v1.toml").read_bytes()


def load_perspectives(raw: bytes | None = None) -> dict:
    raw = raw if raw is not None else perspectives_bytes()
    spec = tomllib.loads(raw.decode("utf-8"))
    ids = [p["id"] for p in spec["perspective"]]
    if len(ids) != len(set(ids)) or not all(p.get("focus") for p in spec["perspective"]):
        raise ValueError("perspectives need unique ids and a focus")
    return {"version": spec["version"], "sha256": sha256(raw).hexdigest(), "perspectives": spec["perspective"]}


def _sha_of(value) -> str:
    return sha256(canonicalize(value)).hexdigest()


class ReviewBoard:
    def __init__(self, memory: MemoryStore, archive=None):
        self.memory, self.archive = memory, archive

    # ------------------------------------------------------------------ storage
    def _current(self, domain, subject, predicate):
        found = self.memory.facts(as_of=self.memory.now(), cubes=[domain], subject=subject, predicate=predicate)
        return found[-1] if found else None

    def _put(self, domain, subject, predicate, obj):
        current = self._current(domain, subject, predicate)
        return self.memory.assert_fact(domain, subject, predicate, obj, status="DECLARED",
                                       source_hash=_sha_of(obj), extractor_version=EXTRACTOR,
                                       supersedes=None if current is None else current["id"])

    def draft(self, domain: str, hypothesis_id: str) -> dict:
        found = self._current(domain, hypothesis_id, "review_draft")
        if found is None:
            raise MemoryStoreError("DRAFT_UNKNOWN", f"no review draft {hypothesis_id!r} in {domain!r}")
        return found["object"]

    # ------------------------------------------------------------------ draft and questions
    def open(self, domain: str, draft: dict) -> dict:
        required = ("hypothesis_id", "statement", "metric", "data", "design", "author")
        missing = [k for k in required if not str(draft.get(k, "")).strip()]
        if missing:
            raise MemoryStoreError("INVALID_FIELD", f"draft needs {missing}")
        obj = {**draft, "domain": domain, "state": "UNDER_REVIEW"}
        self._put(domain, draft["hypothesis_id"], "review_draft", obj)
        return obj

    def generate(self, domain: str, hypothesis_id: str, provider, *, perspectives: dict | None = None,
                 closed_threshold: float = 0.6, similarity=None) -> dict:
        from cain.inference.structured import StructuredOutputError, generate_structured

        draft = self.draft(domain, hypothesis_id)
        perspectives = perspectives or load_perspectives()
        created, failures = [], []
        for perspective in perspectives["perspectives"]:
            if "*" not in perspective["domains"] and domain not in perspective["domains"]:
                continue
            prompt = canonicalize({
                "hypothesis": {k: draft[k] for k in ("hypothesis_id", "statement", "metric", "data", "design")},
                "perspective": {"name": perspective["name"], "focus": perspective["focus"]},
                "instruction": ("Ask up to three sharp questions a skeptical reviewer with this perspective would "
                                "ask before this hypothesis is frozen. For each, propose a concrete test and its "
                                "pass criterion; if it cannot be tested with data, set testable=false and explain "
                                "why. Use only the information given."),
            }).decode("utf-8")
            system = ("You are an adversarial scientific reviewer. You do not decide; you ask questions that must "
                      "be answered by tests. Answer with the JSON object requested and nothing else.")
            try:
                value, attempts = generate_structured(provider, prompt, system, QUESTION_SCHEMA, attempts=2,
                                                      review_hypothesis=hypothesis_id,
                                                      review_perspective=perspective["id"])
            except StructuredOutputError as exc:
                failures.append({"perspective": perspective["id"], "attempts": exc.attempts})
                continue
            for index, question in enumerate(value["questions"], start=1):
                test = None
                if question["testable"] and question["test"].strip():
                    test = {"kind": question["test_kind"], "description": question["test"].strip(),
                            "pass_criterion": question["pass_criterion"].strip(), "defined_by": "model:proposed"}
                status = "TEST_DEFINED" if test else ("NOT_TESTABLE" if not question["testable"] else "OPEN")
                item = {"item_id": f"{hypothesis_id}:{perspective['id']}:{index}", "hypothesis_id": hypothesis_id,
                        "perspective": perspective["id"], "perspective_name": perspective["name"],
                        "mandatory": bool(perspective.get("mandatory", True)), "question": question["question"],
                        "why": question["why"], "test": test,
                        "not_testable_reason": (question["not_testable_reason"].strip() or None)
                        if not question["testable"] else None,
                        "status": status, "answered_by": None, "waiver": None,
                        "generated_by": {"call_id": attempts[-1]["call_id"],
                                         "model": getattr(provider, "model", None),
                                         "perspectives_sha256": perspectives["sha256"]}}
                self._put(domain, item["item_id"], "review_item", item)
                created.append(item["item_id"])
        if self.archive is not None:
            created.append(self._closed_item(domain, draft, closed_threshold, similarity))
        return {"hypothesis_id": hypothesis_id, "items": created, "failures": failures,
                "perspectives_sha256": perspectives["sha256"]}

    def _closed_item(self, domain, draft, threshold, similarity) -> str:
        kwargs = {"threshold": threshold} if similarity is None else {"threshold": threshold, "similarity": similarity}
        # A draft that declares its lineage (derived_from a trial finding) is checked by that identity too.
        parent = str(draft.get("derived_from") or "")
        trial = draft.get("trial_id") or (parent.split(":trial:", 1)[1] if ":trial:" in parent else None)
        matches = self.archive.equivalent_closed(domain, draft["statement"], as_of=self.memory.now(),
                                                 identity={"hypothesis_family": draft.get("family"),
                                                           "trial_id": trial}, **kwargs)
        item = {"item_id": f"{draft['hypothesis_id']}:closed-archive:1", "hypothesis_id": draft["hypothesis_id"],
                "perspective": "closed-archive", "perspective_name": "Already closed? (findings archive)",
                "mandatory": True,
                "question": "Is this hypothesis equivalent to one already refuted, closed or frozen in this domain?",
                "why": "A retest under another name is data snooping (Prompt 7).",
                "test": None, "not_testable_reason": None,
                "status": "OPEN" if matches else "ANSWERED",
                "answered_by": None if matches else {"ref": "findings-archive:no-equivalent", "by": "cain"},
                "matches": matches, "waiver": None, "generated_by": {"call_id": None, "model": None}}
        self._put(domain, item["item_id"], "review_item", item)
        return item["item_id"]

    # ------------------------------------------------------------------ moderation (human)
    def _item(self, domain, item_id):
        found = self._current(domain, item_id, "review_item")
        if found is None:
            raise MemoryStoreError("ITEM_UNKNOWN", f"no review item {item_id!r}")
        return found["object"]

    def define_test(self, domain, item_id, *, kind, description, pass_criterion, by) -> dict:
        if kind not in TEST_KINDS or not description.strip() or not pass_criterion.strip() or not by.strip():
            raise MemoryStoreError("INVALID_FIELD", f"a test needs a kind in {TEST_KINDS}, a description, a pass "
                                                    "criterion and who defines it")
        item = {**self._item(domain, item_id), "status": "TEST_DEFINED",
                "test": {"kind": kind, "description": description, "pass_criterion": pass_criterion, "defined_by": by}}
        self._put(domain, item_id, "review_item", item)
        return item

    def answer(self, domain, item_id, *, ref, by, note="") -> dict:
        if not ref.strip() or not by.strip():
            raise MemoryStoreError("INVALID_FIELD", "an answer needs the evidence/run reference and who answers")
        item = {**self._item(domain, item_id), "status": "ANSWERED", "answered_by": {"ref": ref, "by": by, "note": note}}
        self._put(domain, item_id, "review_item", item)
        return item

    def waive(self, domain, item_id, *, by, reason) -> dict:
        if not by.strip() or len(reason.strip()) < 10:
            raise MemoryStoreError("INVALID_FIELD", "a waiver needs a named human and a reason (10+ characters)")
        if by.startswith(("model:", "cain")):
            raise MemoryStoreError("WAIVER_IS_HUMAN", "only a human waives a checklist item")
        item = {**self._item(domain, item_id), "status": "WAIVED", "waiver": {"by": by, "reason": reason}}
        self._put(domain, item_id, "review_item", item)
        return item

    # ------------------------------------------------------------------ reads
    def items(self, domain, hypothesis_id, *, as_of) -> list[dict]:
        facts = self.memory.facts(as_of=as_of, cubes=[domain], predicate="review_item")
        return [f["object"] | {"recorded_at": f["recorded_at"]} for f in facts
                if f["object"]["hypothesis_id"] == hypothesis_id]

    def question_map(self, domain, hypothesis_id, *, as_of) -> dict:
        items = self.items(domain, hypothesis_id, as_of=as_of)
        blocking = [i["item_id"] for i in items if i["mandatory"] and i["status"] not in RESOLVED]
        draft = self.draft(domain, hypothesis_id)
        return {"hypothesis_id": hypothesis_id, "domain": domain, "state": draft["state"],
                "statement": draft["statement"], "as_of": as_of, "blocking": blocking,
                "ready_to_preregister": not blocking and bool(items),
                "questions": [{k: i.get(k) for k in ("item_id", "perspective_name", "mandatory", "question", "status",
                                                     "test", "answered_by", "waiver", "not_testable_reason",
                                                     "matches")} for i in items]}

    # ------------------------------------------------------------------ pre-registration
    def preregister(self, domain, hypothesis_id, *, by) -> dict:
        view = self.question_map(domain, hypothesis_id, as_of=self.memory.now())
        if not view["questions"]:
            raise MemoryStoreError("REVIEW_MISSING", "no adversarial review was generated for this hypothesis")
        if view["blocking"]:
            raise MemoryStoreError("CHECKLIST_UNRESOLVED",
                                   f"mandatory items without test, answer or human waiver: {view['blocking']}")
        checklist_sha = _sha_of(view["questions"])
        draft = {**self.draft(domain, hypothesis_id), "state": "PREREGISTERED", "checklist_sha256": checklist_sha,
                 "preregistered_by": by}
        self._put(domain, hypothesis_id, "review_draft", draft)
        if self.archive is not None:
            self.archive.preregister(domain, hypothesis_id, statement=draft["statement"],
                                     derived_from=draft.get("derived_from"), by=by, source_hash=checklist_sha)
        return {"hypothesis_id": hypothesis_id, "state": "PREREGISTERED", "checklist_sha256": checklist_sha,
                "items": len(view["questions"])}
