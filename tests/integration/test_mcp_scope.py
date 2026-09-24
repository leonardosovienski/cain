"""MCP boundary: the process scope is fixed and no other scope's data is reachable.

Protected behaviour:
- ``tools/call`` with ``user``, ``project`` or ``collection`` in the arguments is
  rejected with JSON-RPC error -32602 before any query runs;
- every tool answers only from the scope bound at process start, even when another
  scope in the same database holds matching records;
- protocol errors carry the documented codes and the stdio loop enforces its limits.
"""
import io
import json
import sys

import pytest

from cain.mcp import PROTOCOL, TOOLS, Server, main
import test_research_l0 as cases

setup = cases.setup
SCOPE_KEYS = ("user", "project", "collection")


@pytest.fixture
def two_scopes(setup):
    """Records in the bound scope (leo / "" / crypto) and in a sibling scope (leo / project-a / crypto).

    The fixture policy grants both scopes, so the only thing keeping them apart is the
    scope bound to the MCP process.
    """
    service, scope, ingest, _, _ = setup
    ingest(cases.publication(("CRY-1",), text="Crypto report: liquidation cascade observed."))
    other = service.scope("leo", "project-a", "crypto")
    sibling = cases.publication(("STK-1",), text="Project report: dividend cut observed.")
    name = sibling["publication_id"] + ".json"
    (cases.Path(service.policy()["import_root"]) / name).write_bytes(cases.canonical(sibling))
    service.ingest(name, other)
    assert service.query(other, source_id="STK-1")["total_record_revisions"] == 1
    server = Server(service, scope)
    server.dispatch({"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}})
    server.dispatch({"jsonrpc": "2.0", "method": "notifications/initialized"})
    return service, scope, other, server


def call(server, name, arguments, identifier=1):
    return server.dispatch({"jsonrpc": "2.0", "id": identifier, "method": "tools/call",
                            "params": {"name": name, "arguments": arguments}})


def payload(response):
    assert response["result"]["isError"] is False, response
    return json.loads(response["result"]["content"][0]["text"])


@pytest.mark.parametrize("tool", sorted(TOOLS))
@pytest.mark.parametrize("key", SCOPE_KEYS)
def test_scope_arguments_are_rejected_with_invalid_params(two_scopes, tool, key, monkeypatch):
    service, _, _, server = two_scopes
    calls = []
    for attr in ("query", "evidence"):
        original = getattr(service, attr)
        monkeypatch.setattr(service, attr, lambda *a, _o=original, **k: calls.append(attr) or _o(*a, **k))
    valid = {"question": "report", "reference": "x"}  # satisfies every required field
    arguments = {k: v for k, v in valid.items() if k in TOOLS[tool]["properties"]}
    arguments[key] = "project-a" if key == "project" else "other"
    response = call(server, tool, arguments)
    assert response["error"]["code"] == -32602
    assert "scope" in response["error"]["message"]
    assert calls == [], "scope injection must be refused before touching the service"


def test_query_answers_only_from_the_bound_scope(two_scopes):
    _, _, _, server = two_scopes
    records = payload(call(server, "research_query", {}))["records"]
    assert {r["source_id"] for r in records} == {"CRY-1"}
    assert all(r["domain"] == "crypto" for r in records)
    # Asking for the sibling scope's record by id yields nothing, not the other scope's data.
    assert payload(call(server, "research_query", {"source_id": "STK-1"}))["records"] == []


def test_search_and_inspect_never_surface_sibling_scope(two_scopes):
    _, _, _, server = two_scopes
    result = payload(call(server, "research_search", {"question": "dividend cut"}))
    assert result["matches"] == 0
    hit = payload(call(server, "research_search", {"question": "liquidation cascade"}))
    assert hit["matches"] == 1
    assert "dividend" not in json.dumps(hit)
    inspected = payload(call(server, "research_inspect", {}))
    assert "STK-1" not in json.dumps(inspected) and "CRY-1" in json.dumps(inspected)


def test_evidence_reference_from_sibling_scope_is_not_readable(two_scopes):
    service, scope, other, server = two_scopes
    own_ref = service.query(scope, source_id="CRY-1")["records"][0]["evidence"][0]["reference_id"]
    foreign_ref = service.query(other, source_id="STK-1")["records"][0]["evidence"][0]["reference_id"]
    assert own_ref != foreign_ref
    own = payload(call(server, "research_evidence", {"reference": own_ref}))
    assert "liquidation cascade" in json.dumps(own)
    response = call(server, "research_evidence", {"reference": foreign_ref})
    assert response["result"]["isError"] is True
    assert "dividend" not in json.dumps(response)
    assert response["result"]["content"][0]["text"].startswith("Local tool failed: ")


@pytest.mark.parametrize("arguments, reason", [
    ({"question": ""}, "empty value"),
    ({"question": "x" * 1001}, "oversized value"),
    ({"question": 5}, "non-string value"),
    ({"question": "ok", "limit": "5"}, "argument outside the tool schema"),
    ({}, "missing required argument"),
    ([], "arguments not an object"),
])
def test_tool_argument_schema_is_enforced(two_scopes, arguments, reason):
    _, _, _, server = two_scopes
    assert call(server, "research_search", arguments)["error"]["code"] == -32602, reason


def test_protocol_error_codes(setup):
    service, scope, _, _, _ = setup
    server = Server(service, scope)

    def rpc(**req):
        return server.dispatch({"jsonrpc": "2.0", **req})

    assert rpc(id=1, method="ping")["result"] == {}  # allowed before initialize
    assert rpc(id=1, method="tools/list")["error"]["code"] == -32000
    assert rpc(id=1, method="tools/call", params=[])["error"]["code"] == -32602
    assert server.dispatch({"jsonrpc": "1.0", "id": 1, "method": "ping"})["error"]["code"] == -32600
    assert server.dispatch({"jsonrpc": "2.0", "id": 1.5, "method": "ping"})["error"]["code"] == -32600
    assert rpc(method="notifications/initialized") is None and server.ready is False
    init = rpc(id=2, method="initialize")["result"]
    assert init["protocolVersion"] == PROTOCOL and init["capabilities"]["tools"]["listChanged"] is False
    assert rpc(method="notifications/initialized") is None and server.ready is True
    assert rpc(id=3, method="resources/list")["error"]["code"] == -32601
    assert rpc(id=4, method="tools/call", params={"name": "shell", "arguments": {}})["error"]["code"] == -32602
    listed = rpc(id=5, method="tools/list")["result"]["tools"]
    assert all(t["inputSchema"]["additionalProperties"] is False for t in listed)
    assert all(not (set(t["inputSchema"]["properties"]) & set(SCOPE_KEYS)) for t in listed)
    assert all(t["annotations"]["readOnlyHint"] for t in listed)


def run_main(monkeypatch, setup, lines):
    service, _, _, _, policy = setup
    monkeypatch.setattr(sys, "argv", ["cain-mcp", "--db", str(service.path), "--policy", str(policy),
                                      "--collection", "crypto", "--trusted-local-client"])
    stdin = io.TextIOWrapper(io.BytesIO(b"".join(lines)))
    stdout = io.TextIOWrapper(io.BytesIO())
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(sys, "stdout", stdout)
    code = main()
    stdout.flush()
    out = stdout.buffer.getvalue().decode("utf-8")
    return code, [json.loads(line) for line in out.splitlines() if line]


def test_stdio_loop_answers_requests_and_reports_parse_errors(setup, monkeypatch):
    service, scope, ingest, _, _ = setup
    ingest(cases.publication())
    code, responses = run_main(monkeypatch, setup, [
        b'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n',
        b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n',
        b'not json\n',
        b'{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"research_query","arguments":{"source_id":"A"}}}\n',
    ])
    assert code == 0
    assert [r.get("id") for r in responses] == [1, None, 2]
    assert responses[1]["error"]["code"] == -32700
    assert json.loads(responses[2]["result"]["content"][0]["text"])["total_record_revisions"] == 1


def test_stdio_loop_stops_on_oversized_request(setup, monkeypatch):
    code, responses = run_main(monkeypatch, setup, [
        b'{"jsonrpc":"2.0","id":1,"method":"ping"}\n',
        b'{"jsonrpc":"2.0","id":2,"method":"ping","params":{"pad":"' + b"x" * 100_001 + b'"}}\n',
        b'{"jsonrpc":"2.0","id":3,"method":"ping"}\n',
    ])
    assert code == 1
    assert [r.get("id") for r in responses] == [1, None]
    assert responses[1]["error"]["code"] == -32600 and "100000" in responses[1]["error"]["message"]
