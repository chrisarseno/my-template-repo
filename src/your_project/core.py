"""
Example core logic module.

- `hello` is free (no license gating).
- `pro_feature` is gated to the "pro" plan.
- `enterprise_feature` is gated to the "enterprise" plan.
"""

from __future__ import annotations

from your_project.license_check import require_license


def hello() -> str:
    """A free, always-available function."""
    return "Hello from core logic!"


@require_license("pro")
def pro_feature(x: int, y: int) -> str:
    """A feature available only to 'pro' plan licenses."""
    result = x * y
    return f"[PRO] Computed product of {x} * {y} = {result}"


@require_license("enterprise")
def enterprise_feature(name: str) -> str:
    """A feature available only to 'enterprise' plan licenses."""
    return f"[ENTERPRISE] Running advanced feature set for project '{name}'"
