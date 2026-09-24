"""`cain inference`: call manifests, determinism check, replay and the small-model harness."""

from dataclasses import replace
import json
import os
from pathlib import Path
import sys

DEFAULT_PROMPT = ("Passage: The Riverside library opened in 1987 and holds about 42,000 books.\n"
                  "In one sentence, when did the library open and how many books does it hold?")


def register(sub):
    inference = sub.add_parser("inference", help="Inference manifests, record/replay and the local model harness")
    inference.add_argument("--db", type=Path, default=os.getenv("CAIN_INFERENCE_DB"),
                           help="inference store (default: inference.db next to storage.path)")
    inference.add_argument("--config", type=Path)
    commands = inference.add_subparsers(dest="inference_command", required=True)
    calls = commands.add_parser("calls", help="Most recent calls with their manifests")
    calls.add_argument("--limit", type=int, default=10)
    commands.add_parser("audit", help="Check every stored manifest for the required fields")
    show = commands.add_parser("show", help="One call: manifest, request and response bytes")
    show.add_argument("call_id")
    repeat = commands.add_parser("repeat", help="Same call N times in record mode; count distinct outputs")
    repeat.add_argument("--n", type=int, default=20)
    repeat.add_argument("--prompt", default=DEFAULT_PROMPT)
    repeat.add_argument("--model")
    replay = commands.add_parser("replay", help="Same call in replay mode: the model is never called")
    replay.add_argument("--prompt", default=DEFAULT_PROMPT)
    replay.add_argument("--model")
    harness = commands.add_parser("harness", help="Run the frozen 96-task harness against local models")
    harness.add_argument("--model", action="append", required=True)
    harness.add_argument("--mode", choices=["manifest", "record", "cache", "replay"], default="record")
    harness.add_argument("--attempts", type=int, default=2)
    harness.add_argument("--limit", type=int)
    harness.add_argument("--output", type=Path)


def _provider(args, model=None):
    from cain.llm import OllamaLLM
    from cain.providers import make_llm
    from cain.settings import load_settings

    settings = load_settings(args.config)
    provider = make_llm(settings.provider, settings.model, settings.base_url, settings.temperature, settings.seed,
                        timeout=settings.timeout, num_ctx=settings.num_ctx, num_predict=settings.num_predict,
                        max_input_bytes=settings.max_input_bytes, think=settings.think,
                        num_batch=settings.num_batch)
    if not isinstance(provider, OllamaLLM):
        raise ValueError("inference commands need a local model provider (ollama)")
    if model and model != provider.model:
        # think is a per-model capability; only the configured model keeps the configured value.
        provider = replace(provider, model=model, think=None)
    db = args.db or settings.inference_db
    return provider, db


def execute(args):
    from cain.inference.recorder import InferenceStore, Recorder

    cmd = args.inference_command
    if cmd in {"calls", "show", "audit"}:
        db = args.db
        if db is None:
            from cain.settings import load_settings

            db = load_settings(args.config).inference_db
        store = InferenceStore(db)
        if cmd == "calls":
            return {"store": str(db), "calls": store.calls(args.limit)}
        if cmd == "audit":
            return {"store": str(db), **store.audit()}
        found = store.call(args.call_id)
        if found is None:
            raise ValueError(f"unknown call {args.call_id}")
        for key in ("request", "response"):
            if found[key] is not None:
                found[key] = found[key].decode("utf-8", errors="replace")
        return found
    if cmd in {"repeat", "replay"}:
        provider, db = _provider(args, args.model)
        store = InferenceStore(db)
        if cmd == "repeat":
            if args.n < 1:
                raise ValueError("--n must be at least 1")
            recorder = Recorder(store, mode="record")
            provider = replace(provider, transport=recorder)
            texts, keys = [], set()
            for index in range(args.n):
                texts.append(provider.generate(args.prompt))
                keys.add(store.call(recorder.last_call_id)["cache_key"])
                print(f"[{index + 1}/{args.n}] {len(set(texts))} distinct so far", file=sys.stderr)
            key_count = len(keys)
            key = next(iter(keys)) if key_count == 1 else None
            outputs = store.outputs(key) if key else []
            return {"store": str(db), "model": provider.model, "calls": args.n, "cache_keys": key_count,
                    "cache_key": key, "distinct_outputs": len(set(texts)),
                    "distinct_text_sha256_recorded": len({o["text_sha256"] for o in outputs[-args.n:]}),
                    "manifests_recorded": len(outputs), "sample": texts[0]}
        recorder = Recorder(store, mode="replay")
        provider = replace(provider, transport=recorder)
        text = provider.generate(args.prompt)
        call = store.call(recorder.last_call_id)
        recorded = store.outputs(call["cache_key"])
        return {"store": str(db), "model": provider.model, "cache_hit": bool(call["cache_hit"]),
                "cache_key": call["cache_key"], "runtime_verified": call["manifest"]["runtime_verified"],
                "text_sha256": call["manifest"]["output"]["text_sha256"],
                "first_recorded_text_sha256": recorded[0]["text_sha256"] if recorded else None,
                "identical_to_first_recording": bool(recorded)
                and call["manifest"]["output"]["text_sha256"] == recorded[0]["text_sha256"],
                "text": text}
    if cmd == "harness":
        from cain.inference.harness import run_model

        results = []
        for model in args.model:
            provider, db = _provider(args, model)
            store = InferenceStore(db)

            def progress(done, total, row, model=model):
                print(f"[{model} {done}/{total}] {row['id']} correct={row['correct']} "
                      f"wall={row['wall_s']}s", file=sys.stderr)

            results.append(run_model(provider, store, mode=args.mode, attempts=args.attempts, limit=args.limit,
                                     progress=progress))
        summary = {"store": str(db), "models": [{k: v for k, v in r.items() if k != "rows"} for r in results]}
        if args.output is not None:
            args.output.write_text(json.dumps({"summary": summary, "results": results}, indent=2,
                                              ensure_ascii=False) + "\n", encoding="utf-8")
        return summary
    raise ValueError(f"unknown inference command {cmd!r}")
