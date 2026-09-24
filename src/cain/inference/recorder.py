"""Inference manifest, record mode and replay cache for local model calls.

The recorder sits on the HTTP transport of the local providers (Ollama ``/api/generate`` and
``/api/chat``, llama.cpp ``/completion``), so it sees the exact request and response bytes. Every
generation call gets a manifest (model, runtime, parameters, input, output, context) stored in
SQLite with those bytes.

Modes:
* ``manifest`` call the model; store the manifest (the default: every call is documented);
* ``record`` like ``manifest`` but one request at a time (process and file lock), temperature 0 or an
             explicit seed required, and the response becomes the cached answer for its key;
* ``cache``  cached answer when the key exists, otherwise ``record``;
* ``replay`` cached answer only; a miss fails closed without calling the model.

Cache key: sha256 over (model blob sha256 or digest, runtime build, endpoint, request body sha256).
The request body already carries the prompt, the system text, every option and the schema; the
server renders it with the chat template whose sha256 is in the manifest.

Reproducible here means: same hardware, same runtime build, same parameters. Bit-for-bit equality
across machines is not promised. Replaying the recorded output is what makes a past run repeatable.
"""

from __future__ import annotations

from contextlib import contextmanager
import contextvars
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import re
import sqlite3
import subprocess
import threading
import time
from urllib.parse import urlsplit
from urllib.request import Request
from uuid import uuid4

from cain.memory.jcs import canonicalize

MANIFEST_SCHEMA = "cain-inference-manifest/1"
MODES = ("manifest", "record", "cache", "replay")
GENERATION_PATHS = {"/api/generate", "/api/chat", "/completion"}
MAX_BODY = 4 * 1024 * 1024 + 1
_CONTEXT = contextvars.ContextVar("cain_inference_context", default=None)
_PROCESS_LOCK = threading.Lock()
_GGUF_SHA256: dict = {}


def _hash(data: bytes | str | None) -> str | None:
    if data is None:
        return None
    return sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


@contextmanager
def inference_context(**values):
    """Attach caller context (evidence hashes, tool versions, attempt group) to calls in this block."""
    token = _CONTEXT.set({**(_CONTEXT.get() or {}), **values})
    try:
        yield
    finally:
        _CONTEXT.reset(token)


class _Response:
    """Minimal response object for providers that read the body inside ``with``."""

    def __init__(self, raw: bytes):
        self._raw = raw

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit: int = -1) -> bytes:
        return self._raw if limit is None or limit < 0 else self._raw[:limit]


class ReplayMiss(OSError):
    """Replay requested and no recorded answer exists for this exact call (the model is not called)."""


class InferenceStore:
    def __init__(self, path: str | Path):
        # Nothing touches the disk until a call is recorded or read.
        self.path = Path(path)
        self._ready = False

    def _create(self, db):
        db.executescript("""
            CREATE TABLE IF NOT EXISTS inference_calls(
              id TEXT PRIMARY KEY, recorded_at TEXT NOT NULL, mode TEXT NOT NULL, endpoint TEXT NOT NULL,
              cache_key TEXT NOT NULL, cache_hit INTEGER NOT NULL, status TEXT NOT NULL,
              request_sha256 TEXT NOT NULL, request BLOB NOT NULL, response_sha256 TEXT, response BLOB,
              manifest TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS inference_calls_key ON inference_calls(cache_key);
            CREATE TABLE IF NOT EXISTS inference_cache(
              cache_key TEXT PRIMARY KEY, request_key TEXT NOT NULL, call_id TEXT NOT NULL,
              response_sha256 TEXT NOT NULL, response BLOB NOT NULL);
            CREATE INDEX IF NOT EXISTS inference_cache_request ON inference_cache(request_key);
            CREATE TABLE IF NOT EXISTS inference_validations(
              call_id TEXT NOT NULL, attempt_group TEXT NOT NULL, attempt INTEGER NOT NULL,
              valid INTEGER NOT NULL, error TEXT, recorded_at TEXT NOT NULL,
              PRIMARY KEY(attempt_group, attempt));
        """)
        for table in ("inference_calls", "inference_cache", "inference_validations"):
            for action in ("UPDATE", "DELETE"):
                db.execute(f"CREATE TRIGGER IF NOT EXISTS {table}_no_{action.lower()} BEFORE {action} ON {table} "
                           "BEGIN SELECT RAISE(ABORT, 'inference records are append-only'); END")

    @contextmanager
    def connection(self):
        if not self._ready:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                if not self._ready:
                    self._create(db)
                    self._ready = True
                yield db
        finally:
            db.close()

    def cached(self, key: str, *, request_key: str | None = None) -> tuple[bytes, str, str] | None:
        """Recorded answer for the full key; with ``request_key``, the latest answer for the same request
        bytes (used only when the runtime cannot be asked for the model identity: offline replay)."""
        with self.connection() as db:
            if request_key is None:
                row = db.execute("SELECT response, response_sha256, cache_key, call_id FROM inference_cache "
                                 "WHERE cache_key=?", (key,)).fetchone()
            else:
                row = db.execute("SELECT c.response, c.response_sha256, c.cache_key, c.call_id "
                                 "FROM inference_cache c "
                                 "JOIN inference_calls k ON k.id = c.call_id WHERE c.request_key=? "
                                 "ORDER BY k.recorded_at DESC LIMIT 1", (request_key,)).fetchone()
        if row is None:
            return None
        if _hash(row["response"]) != row["response_sha256"]:
            raise ReplayMiss("cached response bytes do not match their sha256")
        return row["response"], row["cache_key"], row["call_id"]

    def save(self, call: dict, *, cache: bool) -> None:
        with self.connection() as db:
            db.execute("INSERT INTO inference_calls VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                       (call["id"], call["recorded_at"], call["mode"], call["endpoint"], call["cache_key"],
                        int(call["cache_hit"]), call["status"], call["request_sha256"], call["request"],
                        call["response_sha256"], call["response"],
                        canonicalize(call["manifest"]).decode("utf-8")))
            if cache and call["response"] is not None:
                db.execute("INSERT OR IGNORE INTO inference_cache VALUES (?,?,?,?,?)",
                           (call["cache_key"], call["request_key"], call["id"], call["response_sha256"],
                            call["response"]))

    def validation(self, call_id: str, attempt_group: str, attempt: int, valid: bool,
                   error: str | None = None) -> None:
        """Outcome of validating one structured-output attempt; invalid attempts are kept."""
        with self.connection() as db:
            db.execute("INSERT INTO inference_validations VALUES (?,?,?,?,?,?)",
                       (call_id, attempt_group, attempt, int(valid), error, _now()))

    def validations(self, attempt_group: str) -> list[dict]:
        with self.connection() as db:
            rows = db.execute("SELECT * FROM inference_validations WHERE attempt_group=? ORDER BY attempt",
                              (attempt_group,)).fetchall()
        return [dict(r) for r in rows]

    def outputs(self, cache_key: str, *, statuses=("called",)) -> list[dict]:
        """Output identity of each recorded call for one cache key, oldest first.

        The raw response carries timings, so equality of answers is judged on ``text_sha256``
        (the generated text) rather than on the response bytes."""
        marks = ",".join("?" * len(statuses))
        with self.connection() as db:
            rows = db.execute(f"SELECT id, status, response_sha256, manifest FROM inference_calls "
                              f"WHERE cache_key=? AND status IN ({marks}) ORDER BY recorded_at",
                              (cache_key, *statuses)).fetchall()
        return [{"call_id": r["id"], "status": r["status"], "response_sha256": r["response_sha256"],
                 "text_sha256": (json.loads(r["manifest"]).get("output") or {}).get("text_sha256")} for r in rows]

    def call(self, call_id: str) -> dict | None:
        with self.connection() as db:
            row = db.execute("SELECT * FROM inference_calls WHERE id=?", (call_id,)).fetchone()
        if row is None:
            return None
        found = dict(row)
        found["manifest"] = json.loads(found["manifest"])
        return found

    def calls(self, limit: int = 20) -> list[dict]:
        with self.connection() as db:
            rows = db.execute("SELECT id, recorded_at, mode, endpoint, cache_key, cache_hit, status, "
                              "request_sha256, response_sha256, manifest FROM inference_calls "
                              "ORDER BY recorded_at DESC LIMIT ?", (limit,)).fetchall()
        return [{**{k: r[k] for k in r.keys() if k != "manifest"}, "manifest": json.loads(r["manifest"])}
                for r in rows]

    def audit(self) -> dict:
        """Every stored manifest checked against ``required_fields``, grouped by call status."""
        with self.connection() as db:
            rows = db.execute("SELECT status, endpoint, manifest FROM inference_calls ORDER BY recorded_at").fetchall()
        report: dict = {"calls": len(rows), "by_status": {}, "missing": {}}
        for row in rows:
            status = report["by_status"].setdefault(row["status"], {"calls": 0, "complete": 0})
            status["calls"] += 1
            missing = missing_fields(json.loads(row["manifest"]), row["endpoint"])
            if not missing:
                status["complete"] += 1
            for name in missing:
                report["missing"][name] = report["missing"].get(name, 0) + 1
        return report


REQUIRED_FIELDS = (
    "model.gguf_sha256", "runtime.name", "runtime.version", "hardware.os", "hardware.cpu", "hardware.ram_bytes",
    "parameters.requested", "input.request_sha256", "input.prompt_sha256", "output.response_sha256",
    "output.text_sha256", "output.output_tokens", "context.cain", "cache.key",
)
OLLAMA_FIELDS = ("model.ollama_digest", "model.quantization", "model.template_sha256", "model.default_parameters",
                 "runtime.backend")


def missing_fields(manifest: dict, endpoint: str) -> list[str]:
    """Manifest fields that are absent or empty for a call that returned an answer. A replay did not
    run the model, so where it would have run (``runtime.backend``) is not asked of it."""
    required = REQUIRED_FIELDS + (OLLAMA_FIELDS if endpoint != "/completion" else ())
    if manifest.get("status") == "replayed":
        required = tuple(name for name in required if name != "runtime.backend")
    missing = []
    for name in required:
        section, key = name.split(".")
        value = (manifest.get(section) or {}).get(key)
        # A model that declares no default parameters has an empty set, which is a recorded fact.
        empty = (None, "") if name == "model.default_parameters" else (None, "", {}, [])
        if value in empty:
            missing.append(name)
    return missing


def _cain_identity() -> dict:
    root = Path(__file__).resolve().parents[1]
    identity = {"package": "cain-research", "version": None, "git_commit": None, "git_dirty": None,
                "uv_lock_sha256": None}
    try:
        from importlib import metadata

        identity["version"] = metadata.version("cain-research")
    except Exception:  # noqa: BLE001 - identity is best effort, recorded as null
        pass
    checkout = root.parents[1]
    if (checkout / ".git").exists():
        try:
            identity["git_commit"] = subprocess.run(["git", "-C", str(checkout), "rev-parse", "HEAD"],
                                                    capture_output=True, text=True, timeout=5).stdout.strip() or None
            status = subprocess.run(["git", "-C", str(checkout), "status", "--porcelain", "--untracked-files=no"],
                                    capture_output=True, text=True, timeout=5).stdout
            identity["git_dirty"] = bool(status.strip())
        except (OSError, subprocess.SubprocessError):
            pass
    lock = checkout / "uv.lock"
    if lock.is_file():
        identity["uv_lock_sha256"] = _hash(lock.read_bytes())
    return identity


def _hardware() -> dict:
    cpu = None
    try:
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    except OSError:
        cpu = platform.processor() or None
    return {"os": platform.platform(), "machine": platform.machine(), "cpu": cpu or platform.machine() or None,
            "cpu_count": os.cpu_count(), "ram_bytes": _ram_bytes(), "python": platform.python_version()}


def _ram_bytes() -> int | None:
    """Physical memory: sysconf on Linux/macOS, GlobalMemoryStatusEx on Windows (None if unknown)."""
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (AttributeError, ValueError, OSError):
        pass
    try:
        import ctypes

        class _MemoryStatus(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

        status = _MemoryStatus()
        status.dwLength = ctypes.sizeof(_MemoryStatus)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return int(status.ullTotalPhys)
    except (AttributeError, OSError):
        pass
    return None


def _parse_parameters(text: str | None) -> dict:
    parsed: dict = {}
    for line in (text or "").splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            parsed.setdefault(parts[0], []).append(parts[1].strip().strip('"'))
    return {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}


class Recorder:
    """Transport wrapper: ``Recorder(store, mode=...)(request, timeout)`` behaves like ``urlopen``."""

    def __init__(self, store: InferenceStore, *, mode: str = "manifest", base=None, server_parallel=None):
        if mode not in MODES:
            raise ValueError(f"inference mode must be one of {MODES}")
        from cain.llm import urlopen

        self.store, self.mode, self.base = store, mode, base or urlopen
        self.server_parallel = server_parallel
        self._facts: dict = {}
        self._cain = None
        self.last_call_id: str | None = None
        self.last_manifest: dict | None = None

    # -------------------------------------------------------------- facts
    def _get_json(self, url: str, body: dict | None = None):
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = Request(url, data=data, headers={"Content-Type": "application/json"},
                          method="POST" if data else "GET")
        with self.base(request, timeout=15) as response:
            raw = response.read(MAX_BODY)
        return json.loads(raw.decode("utf-8")), raw

    def facts(self, base_url: str, endpoint: str, model: str | None) -> dict:
        key = (base_url, endpoint, model)
        if key in self._facts:
            return self._facts[key]
        facts: dict = {"model": {"name": model}, "runtime": {}}
        try:
            if endpoint == "/completion":
                props, raw = self._get_json(base_url + "/props")
                path = str(props.get("model_path", ""))
                facts["runtime"] = {"name": "llama.cpp", "version": props.get("build_info"),
                                    "props_sha256": _hash(raw), "total_slots": props.get("total_slots"),
                                    "n_ctx": (props.get("default_generation_settings") or {}).get("n_ctx")}
                facts["model"].update(model_path=path, gguf_sha256=None,
                                      chat_template_sha256=_hash(props.get("chat_template")))
                if path and Path(path).is_file():
                    stat = Path(path).stat()
                    marker = (path, stat.st_size, stat.st_mtime_ns)
                    if marker not in _GGUF_SHA256:
                        digest = sha256()
                        with Path(path).open("rb") as handle:
                            for block in iter(lambda: handle.read(1 << 20), b""):
                                digest.update(block)
                        _GGUF_SHA256[marker] = digest.hexdigest()
                    facts["model"]["gguf_sha256"] = _GGUF_SHA256[marker]
            else:
                version, _ = self._get_json(base_url + "/api/version")
                tags, _ = self._get_json(base_url + "/api/tags")
                found = next((m for m in tags.get("models", []) if m.get("name") == model), {})
                show, _ = self._get_json(base_url + "/api/show", {"model": model})
                modelfile = show.get("modelfile") or ""
                blob = re.search(r"^FROM\s+\S*sha256[-:]([0-9a-f]{64})", modelfile, re.M)
                details = show.get("details") or {}
                facts["runtime"] = {"name": "ollama", "version": version.get("version")}
                facts["model"].update(
                    ollama_digest=found.get("digest"), size_bytes=found.get("size"),
                    gguf_sha256=blob.group(1) if blob else None, format=details.get("format"),
                    family=details.get("family"), parameter_size=details.get("parameter_size"),
                    quantization=details.get("quantization_level"),
                    template_sha256=_hash(show.get("template")), modelfile_sha256=_hash(modelfile),
                    license_sha256=_hash(show.get("license")) if show.get("license") else None,
                    default_parameters=_parse_parameters(show.get("parameters")),
                    tokenizer="embedded in the GGUF (covered by gguf_sha256)",
                    hf_repo_revision=None)
        except Exception as exc:  # noqa: BLE001 - recorded in the manifest, never hidden
            facts["error"] = f"{type(exc).__name__}: {exc}"[:300]
        facts["runtime"]["server_parallel_declared"] = self.server_parallel
        facts["hardware"] = _hardware()
        self._facts[key] = facts
        return facts

    def _backend(self, base_url: str, model: str | None) -> dict:
        """Where the model ran for this call (Ollama /api/ps after the call; best effort)."""
        try:
            running, _ = self._get_json(base_url + "/api/ps")
            loaded = next((m for m in running.get("models", []) if m.get("name") == model), None)
        except Exception:  # noqa: BLE001 - backend detection is best effort
            return {}
        if loaded is None:
            return {}
        return {"backend": "gpu" if loaded.get("size_vram") else "cpu",
                "loaded_size_bytes": loaded.get("size"), "size_vram": loaded.get("size_vram"),
                "context_length": loaded.get("context_length")}

    # -------------------------------------------------------------- transport
    def __call__(self, request, timeout=None):
        url = request.full_url if isinstance(request, Request) else str(request)
        parts = urlsplit(url)
        if parts.path not in GENERATION_PATHS or not isinstance(request, Request) or request.data is None:
            return self.base(request, timeout=timeout)
        started = time.time_ns()
        self.last_manifest = None
        try:
            response = self._generation(request, timeout, parts)
        except Exception as exc:
            self._span(started, error=f"{type(exc).__name__}: {exc}")
            raise
        self._span(started)
        return response

    def _span(self, started: int, error: str | None = None) -> None:
        """OpenTelemetry span with gen_ai.* attributes from the manifest (no-op when tracing is off)."""
        from cain.observability import semconv as sc
        from cain.observability.tracing import record_span

        manifest = self.last_manifest
        if manifest is None:
            return
        requested = (manifest.get("parameters") or {}).get("requested") or {}
        model = (manifest.get("model") or {}).get("name") or (manifest.get("model") or {}).get("model_path")
        output = manifest.get("output") or {}
        operation = sc.OPERATION_CHAT if manifest["input"]["endpoint"] == "/api/chat" else sc.OPERATION_TEXT_COMPLETION
        record_span(f"{operation} {model}", started, {
            sc.OPERATION_NAME: operation, sc.PROVIDER_NAME: (manifest.get("runtime") or {}).get("name"),
            sc.REQUEST_MODEL: model, sc.REQUEST_TEMPERATURE: requested.get("temperature"),
            sc.REQUEST_SEED: requested.get("seed"),
            sc.REQUEST_MAX_TOKENS: requested.get("num_predict", requested.get("n_predict")),
            sc.RESPONSE_FINISH_REASONS: [output["done_reason"]] if output.get("done_reason") else None,
            sc.USAGE_INPUT_TOKENS: output.get("prompt_tokens"), sc.USAGE_OUTPUT_TOKENS: output.get("output_tokens"),
            sc.CAIN_CALL_ID: manifest["call_id"], sc.CAIN_CACHE_KEY: manifest["cache"]["key"],
            sc.CAIN_CACHE_HIT: manifest["cache"]["hit"], sc.CAIN_INFERENCE_MODE: manifest["mode"],
            sc.CAIN_MODEL_SHA256: (manifest.get("model") or {}).get("gguf_sha256")}, error=error)

    def _generation(self, request, timeout, parts):
        body_bytes = bytes(request.data)
        body = json.loads(body_bytes.decode("utf-8"))
        base_url = f"{parts.scheme}://{parts.netloc}"
        facts = self.facts(base_url, parts.path, body.get("model"))
        model_identity = facts["model"].get("gguf_sha256") or facts["model"].get("ollama_digest") or             facts["model"].get("model_path") or body.get("model")
        request_sha = _hash(body_bytes)
        key = _hash(canonicalize({"model": model_identity, "runtime": facts["runtime"].get("version"),
                                  "endpoint": parts.path, "request_sha256": request_sha}))
        request_key = _hash(canonicalize({"endpoint": parts.path, "request_sha256": request_sha}))
        options = body.get("options") or {}
        if self.mode == "record" and not (options.get("temperature", body.get("temperature")) == 0
                                          or "seed" in options or "seed" in body):
            raise ValueError("record mode requires temperature 0 or an explicit seed")
        call = {"id": "inference:" + uuid4().hex, "recorded_at": _now(), "mode": self.mode, "endpoint": parts.path,
                "cache_key": key, "request_key": request_key, "cache_hit": False, "status": "pending",
                "request_sha256": request_sha, "request": body_bytes, "response_sha256": None, "response": None,
                "runtime_verified": "error" not in facts}
        self.last_call_id = call["id"]
        found = None
        if self.mode in ("cache", "replay"):
            found = self.store.cached(key)
            if found is None and self.mode == "replay" and "error" in facts:
                # Runtime unreachable: the model identity cannot be re-checked, so serve the latest
                # recording of these exact request bytes and say so in the manifest.
                found = self.store.cached(key, request_key=request_key)
        if found is not None:
            cached, recorded_key, recorded_call = found
            call.update(cache_hit=True, status="replayed", response=cached, response_sha256=_hash(cached),
                        cache_key=recorded_key, identity_from_call=recorded_call)
            if "error" in facts:
                # The runtime could not be asked; the identity is the one recorded with the answer.
                original = self.store.call(recorded_call)["manifest"]
                facts = {**{k: original.get(k) for k in ("model", "runtime", "hardware")}, "error": facts["error"]}
            call["manifest"] = self.last_manifest = self._manifest(call, facts, body, cached)
            self.store.save(call, cache=False)
            return _Response(cached)
        if self.mode == "replay":
            call.update(status="replay_miss")
            call["manifest"] = self.last_manifest = self._manifest(call, facts, body, None)
            self.store.save(call, cache=False)
            raise ReplayMiss(f"no recorded answer for cache key {key}; the model was not called")
        serialize = self.mode in ("record", "cache")
        lock = _FileLock(self.store.path.with_suffix(".lock")) if serialize else None
        if serialize:
            _PROCESS_LOCK.acquire()
            lock.acquire()
        try:
            try:
                with self.base(request, timeout=timeout) as response:
                    raw = response.read(MAX_BODY)
            except Exception as exc:
                call.update(status=f"error:{type(exc).__name__}")
                call["manifest"] = self.last_manifest = self._manifest(call, facts, body, None)
                self.store.save(call, cache=False)
                raise
            if parts.path != "/completion":
                call["backend"] = self._backend(base_url, body.get("model"))
            call.update(status="called", response=raw, response_sha256=_hash(raw))
            call["manifest"] = self.last_manifest = self._manifest(call, facts, body, raw)
            self.store.save(call, cache=serialize)
        finally:
            if serialize:
                lock.release()
                _PROCESS_LOCK.release()
        return _Response(raw)

    def _manifest(self, call: dict, facts: dict, body: dict, raw: bytes | None) -> dict:
        if self._cain is None:
            self._cain = _cain_identity()
        options = dict(body.get("options") or {})
        for key in ("temperature", "seed", "n_predict", "top_p", "top_k", "min_p", "repeat_penalty"):
            if key in body:
                options.setdefault(key, body[key])
        parsed = None
        if raw is not None:
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except ValueError:
                parsed = None
        text = None
        if isinstance(parsed, dict):
            text = parsed.get("response") if "response" in parsed else parsed.get("content")
        output = None if raw is None else {
            "response_sha256": _hash(raw), "text_sha256": _hash(text) if isinstance(text, str) else None,
            "prompt_tokens": (parsed or {}).get("prompt_eval_count", (parsed or {}).get("tokens_evaluated")),
            "output_tokens": (parsed or {}).get("eval_count", (parsed or {}).get("tokens_predicted")),
            "done_reason": (parsed or {}).get("done_reason", (parsed or {}).get("stop_type")),
            "durations_ns": {k: (parsed or {}).get(k) for k in ("total_duration", "load_duration",
                                                                 "prompt_eval_duration", "eval_duration")},
        }
        context = _CONTEXT.get() or {}
        return {
            "schema": MANIFEST_SCHEMA, "call_id": call["id"], "recorded_at": call["recorded_at"], "mode": call["mode"],
            "status": call["status"], "cache": {"key": call["cache_key"], "hit": call["cache_hit"]},
            "model": facts.get("model"), "runtime": {**facts.get("runtime", {}), **call.get("backend", {})},
            "hardware": facts.get("hardware"), "facts_error": facts.get("error"),
            "runtime_verified": call["runtime_verified"],
            "identity_from_call": call.get("identity_from_call"),
            "parameters": {
                "requested": options, "stream": body.get("stream"), "think": body.get("think"),
                "keep_alive": body.get("keep_alive"), "cache_prompt": body.get("cache_prompt"),
                "sampler_order": body.get("samplers") or "runtime default (not exposed by this API)",
                "record_mode_single_request": self.mode in ("record", "cache"),
            },
            "input": {
                "endpoint": call["endpoint"], "request_sha256": call["request_sha256"],
                "prompt_sha256": _hash(body.get("prompt")), "system_sha256": _hash(body.get("system")),
                "messages_sha256": _hash(canonicalize(body["messages"])) if "messages" in body else None,
                "schema_sha256": _hash(canonicalize(body.get("format") or body.get("json_schema")))
                if (body.get("format") or body.get("json_schema")) is not None else None,
                "rendering": "server-side template (template_sha256) over system/prompt, or client-rendered "
                             "prompt for llama.cpp",
            },
            "output": output,
            "context": {"cain": self._cain, **context},
        }


class _FileLock:
    def __init__(self, path: Path):
        self.path, self.handle = path, None

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)  # the store itself is created lazily
        self.handle = self.path.open("a+")
        try:
            import fcntl

            fcntl.flock(self.handle, fcntl.LOCK_EX)
        except ImportError:  # Windows: process lock only; documented limitation
            pass

    def release(self):
        try:
            import fcntl

            fcntl.flock(self.handle, fcntl.LOCK_UN)
        except ImportError:
            pass
        self.handle.close()


def attach(provider, store: InferenceStore, *, mode: str = "manifest", server_parallel=None):
    """Route a local provider's model calls through a recorder (no-op for providers without transport)."""
    if hasattr(provider, "transport"):
        provider.transport = Recorder(store, mode=mode, server_parallel=server_parallel)
    return provider
