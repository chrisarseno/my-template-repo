import os
from dataclasses import dataclass

import requests


LICENSE_SERVER_URL = os.getenv("LICENSE_SERVER_URL", "https://your-license-server.example.com")
ENV_LICENSE_KEY = "MYAPP_LICENSE_KEY"  # what your users set


@dataclass
class LicenseStatus:
    valid: bool
    reason: str
    license_id: str | None = None
    plan: str | None = None
    seats: int | None = None
    customer_name: str | None = None


class LicenseValidationError(Exception):
    pass


def get_license_key_from_env() -> str:
    key = os.getenv(ENV_LICENSE_KEY, "").strip()
    if not key:
        raise LicenseValidationError(
            f"No license key found. Please set environment variable {ENV_LICENSE_KEY}."
        )
    return key


def verify_license_online(key: str) -> LicenseStatus:
    try:
        resp = requests.get(
            f"{LICENSE_SERVER_URL}/verify",
            params={"key": key},
            timeout=5,
        )
    except requests.RequestException as e:
        raise LicenseValidationError(f"Could not contact license server: {e}")

    if resp.status_code == 404:
        return LicenseStatus(valid=False, reason="License not found")
    if not resp.ok:
        raise LicenseValidationError(
            f"License server error ({resp.status_code}): {resp.text}"
        )

    data = resp.json()
    return LicenseStatus(
        valid=data.get("valid", False),
        reason=data.get("reason", "Unknown"),
        license_id=data.get("license_id"),
        plan=data.get("plan"),
        seats=data.get("seats"),
        customer_name=data.get("customer_name"),
    )


def enforce_license():
    """Call this early in your app startup to block unauthorized use."""
    key = get_license_key_from_env()
    status = verify_license_online(key)

    if not status.valid:
        # You can log, phone home, or just raise
        raise LicenseValidationError(f"Invalid license: {status.reason}")

    # Optionally, you can branch behavior based on plan
    return status

