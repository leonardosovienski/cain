"""OpenTelemetry spans for model and tool calls (optional extra ``observability``).

Off unless configured: ``configure()`` is called explicitly, or ``CAIN_OTEL_ENDPOINT`` names an OTLP/HTTP
traces endpoint (for a local MLflow server: ``http://127.0.0.1:5000/v1/traces`` with
``CAIN_OTEL_HEADERS=x-mlflow-experiment-id=<id>``). Without the SDK installed nothing happens; a
tracing failure never breaks a model or tool call.

Spans are recorded when the call ends, with its measured start and end instants, inside the current
context (so a model call made during a loop attempt is a child of that attempt's span).
"""

from __future__ import annotations

from contextlib import contextmanager
import os
import time

_STATE: dict = {"tracer": None, "provider": None, "configured": False}


def configure(*, exporter=None, endpoint: str | None = None, headers: dict | None = None,
              service: str = "cain", simple: bool = False):
    """Install a tracer provider exporting to ``exporter`` (tests) or to an OTLP/HTTP ``endpoint``."""
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor

    if exporter is None:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        exporter = OTLPSpanExporter(endpoint=endpoint, headers=headers or {})
    provider = TracerProvider(resource=Resource.create({"service.name": service}))
    provider.add_span_processor(SimpleSpanProcessor(exporter) if simple else BatchSpanProcessor(exporter))
    _STATE.update(tracer=provider.get_tracer("cain"), provider=provider, configured=True)
    return _STATE["tracer"]


def _from_env():
    endpoint = os.getenv("CAIN_OTEL_ENDPOINT")
    if not endpoint:
        _STATE["configured"] = True
        return None
    headers = dict(pair.split("=", 1) for pair in os.getenv("CAIN_OTEL_HEADERS", "").split(",") if "=" in pair)
    try:
        return configure(endpoint=endpoint, headers=headers)
    except ImportError:
        _STATE["configured"] = True
        return None


def tracer():
    if not _STATE["configured"]:
        _from_env()
    return _STATE["tracer"]


def shutdown():
    provider = _STATE.get("provider")
    if provider is not None:
        provider.force_flush()
        provider.shutdown()
    _STATE.update(tracer=None, provider=None, configured=False)


def record_span(name: str, start_ns: int, attributes: dict, *, error: str | None = None,
                end_ns: int | None = None, kind: str = "client") -> None:
    """Record a finished span (no-op without a tracer)."""
    active = tracer()
    if active is None:
        return
    try:
        from opentelemetry.trace import SpanKind, Status, StatusCode

        span = active.start_span(name, start_time=start_ns,
                                 kind=SpanKind.CLIENT if kind == "client" else SpanKind.INTERNAL,
                                 attributes={k: v for k, v in attributes.items() if v is not None})
        if error:
            span.set_status(Status(StatusCode.ERROR, error[:500]))
        span.end(end_time=end_ns or time.time_ns())
    except Exception:  # noqa: BLE001 - observability never breaks the traced call
        return


@contextmanager
def active_span(name: str, attributes: dict, *, kind: str = "internal"):
    """A span around a block (children created inside it get it as parent); no-op without a tracer."""
    active = tracer()
    if active is None:
        yield None
        return
    from opentelemetry.trace import SpanKind

    with active.start_as_current_span(name, kind=SpanKind.CLIENT if kind == "client" else SpanKind.INTERNAL,
                                      attributes={k: v for k, v in attributes.items() if v is not None}) as span:
        yield span
