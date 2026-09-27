"""Research orchestration of one domain over the V2 envelope (Stage B, D-22).

    proposal → DecisionPolicy (receipt) → ResearchTaskV2 → TaskOutbox → spool (transport)
    … domain adapter and circuit (outside the CAIN) …
    spool → ResultInbox → memory of the domain (bitemporal cube) → retrieval → next decision

The framework is generic; what exists in a domain is its configuration (``data/<domain>.json``). The CAIN only
proposes: it never chooses a handler, a final budget, a final priority or capital, never reads a domain database and
never runs domain evaluation code; the domain's admission decides and the consumer of the transport executes.
"""
