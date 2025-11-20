"""
License validation and feature gating for the commercial version.

This module is responsible for:
- Fetching the license key from the environment
- Verifying it against the license verification API
- Caching the result
- Providing decorators to gate features by plan/tier
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, TypeVar, Any, ParamSpec, Optional

import requests

# ---- Configuration ---------------------------------------------------------

# Where your license server lives (can be overridden via env var)
LICENSE_SERVER_URL = os.getenv(
    "LICENSE_SERVER_URL",
    "https://your-license-server.example.com",  # TODO: change this
)

# Environment variable that users must set with their license key
ENV_LICENSE_KEY = os.getenv("LICENSE_ENV_VAR_NAME", "MYAPP_LICENSE_KEY")

# Allow disabling license checks in development (NEVER in production)
DISABLE_LICENSE_CHECK = os.getenv("DISABLE_LICENSE_CHECK", "").lower() in {
    "1",
    "true",
    "yes",
}

# ---- Data models -----------------------------------------------------------

@dataclass
class LicenseStatus:
    valid: bool
    reason: str
    license_id: Optional[str] = None
    plan: Optional[str] = None   # e.g. "pro", "enterprise"
    seats: Optional[int] = None
    customer_name: Optional[str] = None


class LicenseValidationError(Exception):
    """Raised when license validation fails or a license is invalid."""


# cache so we only hit the server once per process
_cached_license: Optional[LicenseStatus] = None


# ---- Core validation functions --------------------------------------------

def _get_license_key_from_env() -> str:
    key = os.getenv(ENV_LICENSE_KEY, "").strip()
    if not key:
        raise LicenseValidationError(
            f"No license key found. Set environment variable {ENV_LICENSE_KEY}."
        )
    return key


def _verify_license_online(key: str) -> LicenseStatus:
    if DISABLE_LICENSE_CHECK:
        # Extremely useful during development, but DANGEROUS in prod.
        return LicenseStatus(
            valid=True,
            reason="License check disabled via DISABLE_LICENSE_CHECK",
            license_id="DEV-MODE",
            plan="dev",
            seats=1,
            customer_name="Development Mode",
        )

    if not LICENSE_SERVER_URL:
        raise LicenseValidationError("LICENSE_SERVER_URL is not configured.")

    url = LICENSE_SERVER_URL.rstrip("/") + "/verify"

    try:
        resp = requests.get(url, params={"key": key}, timeout=5)
    except requests.RequestException as exc:
        raise LicenseValidationError(f"Could not contact license server: {exc}") from exc

    if resp.status_code == 404:
        return LicenseStatus(valid=False, reason="License not found")

    if not resp.ok:
        raise LicenseValidationError(
            f"License server error ({resp.status_code}): {resp.text}"
        )

    data = resp.json()
    return LicenseStatus(
        valid=bool(data.get("valid", False)),
        reason=str(data.get("reason", "Unknown")),
        license_id=data.get("license_id"),
        plan=data.get("plan"),
        seats=data.get("seats"),
        customer_name=data.get("customer_name"),
    )


def enforce_license() -> LicenseStatus:
    """
    Perform license validation and cache the result.
    Call this early in application startup (e.g. __main__.py).
    Raises LicenseValidationError on failure.
    """
    global _cached_license

    if _cached_license is not None:
        # Already validated this process
        if not _cached_license.valid:
            raise LicenseValidationError(f"Invalid license: {_cached_license.reason}")
        return _cached_license

    key = _get_license_key_from_env()
    status = _verify_license_online(key)

    _cached_license = status

    if not status.valid:
        raise LicenseValidationError(f"Invalid license: {status.reason}")

    return status


def get_license_status() -> LicenseStatus:
    """
    Get (and lazily validate) the current license status.
    Useful inside feature gating decorators or specific functions.
    """
    global _cached_license

    if _cached_license is None:
        # This will raise if invalid
        return enforce_license()

    if not _cached_license.valid:
        raise LicenseValidationError(f"Invalid license: {_cached_license.reason}")

    return _cached_license


# ---- Feature gating decorators --------------------------------------------

P = ParamSpec("P")
R = TypeVar("R")


def require_license(plan: Optional[str] = None) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator to require a valid license, optionally for a specific plan/tier.
    Usage:
        @require_license()
        def some_feature(...):
            ...
        @require_license("enterprise")
        def enterprise_only(...):
            ...
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            status = get_license_status()

            if plan is not None:
                if status.plan is None:
                    raise PermissionError(
                        f"This feature requires plan '{plan}', but your license has no plan assigned."
                    )
                if status.plan != plan:
                    raise PermissionError(
                        f"This feature requires plan '{plan}', but your license plan is '{status.plan}'."
                    )

            return func(*args, **kwargs)

        # Preserve metadata (name, docstring) in a simple way
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        wrapper.__qualname__ = func.__qualname__
        return wrapper

    return decorator


def require_license_any(plans: list[str]) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator to allow multiple plans.
    Usage:
        @require_license_any(["pro", "enterprise"])
        def advanced_feature(...):
            ...
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            status = get_license_status()

            if not status.plan:
                raise PermissionError(
                    f"This feature requires one of plans {plans}, but your license has no plan assigned."
                )
            if status.plan not in plans:
                raise PermissionError(
                    f"This feature requires one of plans {plans}, but your license plan is '{status.plan}'."
                )

            return func(*args, **kwargs)

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        wrapper.__qualname__ = func.__qualname__
        return wrapper

    return decorator

