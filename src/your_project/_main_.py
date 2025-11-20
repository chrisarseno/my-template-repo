"""
Application entry point.

This is where we enforce the license once at startup.
"""

from __future__ import annotations

from your_project.license_check import enforce_license, LicenseValidationError
from your_project import core


def main() -> None:
    # 1. Enforce license
    try:
        status = enforce_license()
    except LicenseValidationError as exc:
        print(f"[LICENSE ERROR] {exc}")
        raise SystemExit(1)

    print(f"✔ License verified for {status.customer_name or 'Unknown Customer'} "
          f"(plan={status.plan or 'unassigned'})")

    # 2. Run your actual application logic
    #    For now, we just demonstrate calling some functions.
    print(core.hello())

    try:
        print(core.pro_feature(3, 4))
    except PermissionError as exc:
        print(f"[PRO FEATURE BLOCKED] {exc}")

    try:
        print(core.enterprise_feature("Sentinel"))
    except PermissionError as exc:
        print(f"[ENTERPRISE FEATURE BLOCKED] {exc}")


if __name__ == "__main__":
    main()
