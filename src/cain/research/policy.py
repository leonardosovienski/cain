"""Receiver policy: loading, validation, scope encoding and per-publication authorization."""

from pathlib import Path

from research_snapshot import canonical, keys, loads


def scope(user="leo", project=None, collection="crypto"):
    if any(type(v) is not str or not v.strip() or len(v) > 200 for v in (user, collection)):
        raise ValueError("Invalid research scope")
    if project is not None and (type(project) is not str or len(project) > 200):
        raise ValueError("Invalid project scope")
    return canonical([user, project or "", collection]).decode()


def load(policy_path):
    """Read and validate the policy file; every call re-reads it (revocation is immediate)."""
    policy = loads(Path(policy_path).read_bytes())
    if type(policy) is not dict:
        raise ValueError("Invalid receiver policy")
    version = policy.get("version")
    keys(policy, "version import_root grants" if version == 1 else
         "version imports grants bundle_grants" if version == 3 else "version imports grants")
    if type(version) is not int or version not in (1, 2, 3) or type(policy["grants"]) is not list:
        raise ValueError("Invalid receiver policy")
    if version == 3:
        from cain.research.bundles import validate_grants
        validate_grants(policy["bundle_grants"])
    if version == 1:
        roots = [policy["import_root"]]
    else:
        if type(policy["imports"]) is not list:
            raise ValueError("Invalid import bindings")
        scopes, roots = set(), []
        for binding in policy["imports"]:
            keys(binding, "user project collection root")
            bound = scope(binding["user"], binding["project"], binding["collection"])
            if bound in scopes:
                raise ValueError("Ambiguous import binding")
            scopes.add(bound)
            roots.append(binding["root"])
    if any(type(root) is not str or not Path(root).is_absolute() for root in roots):
        raise ValueError("Receiver import root must be absolute")
    for grant in policy["grants"]:
        keys(
            grant,
            "user project collection domain repository publisher stream sources policies generate",
        )
        if type(grant["generate"]) is not bool:
            raise ValueError("Invalid generation permission")
        for key in (
            "user",
            "project",
            "collection",
            "domain",
            "repository",
            "publisher",
            "stream",
        ):
            if type(grant[key]) is not str or len(grant[key]) > 500:
                raise ValueError("Invalid grant identity")
        for key in ("sources", "policies"):
            if type(grant[key]) is not list or not all(type(v) is str for v in grant[key]):
                raise ValueError("Invalid grant list")
    return policy


def import_root(policy, bound_scope):
    if policy["version"] == 1:
        return policy["import_root"]
    for binding in policy["imports"]:
        if scope(binding["user"], binding["project"], binding["collection"]) == bound_scope:
            return binding["root"]
    raise ValueError("No import root admitted for this scope")


def authorized(policy, bound_scope, origin, restrictions, generate=False):
    import json

    user, project, collection = json.loads(bound_scope)
    if restrictions.get("read") is not True or (
        generate and restrictions.get("generate") is not True
    ):
        return False
    for grant in policy["grants"]:
        if (
            [grant[k] for k in ("user", "project", "collection")] == [user, project, collection]
            and all(
                grant[k] == origin.get(k)
                for k in ("domain", "repository", "publisher", "stream")
            )
            and set(origin.get("inputs", {})) <= set(grant["sources"])
            and restrictions.get("policy") in grant["policies"]
            and (not generate or grant["generate"])
        ):
            return True
    return False
