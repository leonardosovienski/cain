"""Explicit local text/image streaming CLI; no archive or memory writes."""
import argparse
import base64
from dataclasses import replace
import json
from pathlib import Path
import sys

from cain.providers import configured_llm
from cain.llm.streaming import stream
from cain.settings import load_settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--image", type=Path)
    parser.add_argument("--vision-model", default="qwen3.5:0.8b")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        provider = configured_llm(load_settings(args.config))
        images = []
        if args.image:
            with args.image.open("rb") as handle:
                raw = handle.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValueError("Image exceeds 2000000 bytes")
            images = [base64.b64encode(raw).decode()]
            provider = replace(provider, model=args.vision_model)
        for event in stream(provider, args.prompt, images=images):
            if args.json:
                print(json.dumps(event, ensure_ascii=False), flush=True)
            elif event["type"] == "token":
                print(event["text"], end="", flush=True)
        if not args.json:
            print()
        return 0
    except (ValueError, RuntimeError, OSError) as exc:
        print("Incomplete local generation: " + type(exc).__name__, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
