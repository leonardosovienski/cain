"""Bundle grants: validation, per-bundle grant selection, resource visibility and admission."""

import json

from research_bundle import MAX_BYTES, MAX_OBJECT, MAX_RECEIVED, keys


def validate_grants(grants):
    if type(grants) is not list or len(grants) > 200:
        raise ValueError("Invalid bundle grants")
    for grant in grants:
        keys(
            grant,
            "user project collection domain repository publisher stream sources policies generate roles reference_only max_manifest_bytes max_object_bytes max_received_bytes",
        )
        for key in ("user", "project", "collection", "domain", "repository", "publisher", "stream"):
            if type(grant[key]) is not str or len(grant[key]) > 500:
                raise ValueError("Invalid bundle grant identity")
        for key in ("sources", "policies", "roles"):
            if (
                type(grant[key]) is not list
                or len(grant[key]) > 200
                or any(type(v) is not str for v in grant[key])
            ):
                raise ValueError("Invalid bundle grant list")
        for key in ("generate", "reference_only"):
            if type(grant[key]) is not bool:
                raise ValueError("Invalid bundle permission")
        for key, cap in (
            ("max_manifest_bytes", MAX_BYTES),
            ("max_object_bytes", MAX_OBJECT),
            ("max_received_bytes", MAX_RECEIVED),
        ):
            if type(grant[key]) is not int or not 0 <= grant[key] <= cap:
                raise ValueError("Invalid bundle cap")


def grants_for(policy, scope, origin, restrictions, generate=False):
    """Grants of ``policy`` (already loaded) that admit this origin/restrictions in ``scope``."""
    if not restrictions["read"] or (generate and not restrictions["generate"]):
        return []
    if policy["version"] != 3:
        return []
    identity = json.loads(scope)
    return [
        g
        for g in policy["bundle_grants"]
        if [g[k] for k in ("user", "project", "collection")] == identity
        and all(g[k] == origin[k] for k in ("domain", "repository", "publisher", "stream"))
        and set(origin["inputs"]) <= set(g["sources"])
        and restrictions["policy"] in g["policies"]
        and (not generate or g["generate"])
    ]


def resource_allowed(artifact, grants):
    return any(
        artifact["role"] in g["roles"]
        and (artifact["availability"] == "received" or g["reference_only"])
        for g in grants
    )


def admit(grants, package, size):
    """One complete grant must admit the whole manifest; partial grants do not compose caps."""
    total = sum(a["size"] for a in package["artifacts"] if a["availability"] == "received")
    for grant in grants:
        if (
            size <= grant["max_manifest_bytes"]
            and total <= grant["max_received_bytes"]
            and all(
                resource_allowed(a, [grant])
                and (a["availability"] != "received" or a["size"] <= grant["max_object_bytes"])
                for a in package["artifacts"]
            )
        ):
            return
    raise PermissionError("NOT_AUTHORIZED")
