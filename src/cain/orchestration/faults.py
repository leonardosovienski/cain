"""Qualification fault injection at the CAIN edge (inactive without the variable).

``CAIN_ORCHESTRATION_FAULT=<point>`` makes the ``cain`` process die at that point with exit code 86 and no cleanup
(FAILURE_MATRIX F01–F05 of integration-crypto; same convention as the domains' ``research_faults``).
"""

from __future__ import annotations

import os

ENV = "CAIN_ORCHESTRATION_FAULT"
EXIT_CODE = 86
POINTS = frozenset(
    {
        "after_decision_before_episode_commit",
        "after_outbox_commit",
        "after_spool_write_before_ack",
        "after_inbox_commit_before_memory",
        "after_memory_commit",
    }
)


def fault(point: str) -> None:
    if point not in POINTS:
        raise ValueError(f"unknown fault point {point!r}")
    if os.environ.get(ENV) == point:
        os._exit(EXIT_CODE)
