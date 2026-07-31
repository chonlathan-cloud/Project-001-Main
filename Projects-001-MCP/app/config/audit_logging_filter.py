"""Validate the environment-locked Product Audit Cloud Logging sink filter."""

from __future__ import annotations

import re
import sys
from collections.abc import Sequence

_RESOURCE_TYPE_PATTERN = re.compile(
    r'resource\.type\s*=\s*"([^"]+)"',
    re.IGNORECASE,
)
_SERVICE_PATTERN = re.compile(
    r'resource\.labels\.service_name\s*=\s*"([^"]+)"',
    re.IGNORECASE,
)
_REQUIRED_PRODUCT_AUDIT_SELECTORS = (
    'jsonPayload.log_type="product_audit"',
    'jsonPayload.message:"\\"log_type\\":\\"product_audit\\""',
    'textPayload:"\\"log_type\\":\\"product_audit\\""',
)


def is_valid_audit_sink_filter(
    filter_text: str,
    *,
    expected_service: str,
) -> bool:
    """Return whether the sink captures every supported Product Audit payload shape."""

    resource_types = set(_RESOURCE_TYPE_PATTERN.findall(filter_text))
    services = _SERVICE_PATTERN.findall(filter_text)
    service_reference_count = len(
        re.findall(r"resource\.labels\.service_name", filter_text, re.IGNORECASE)
    )
    compact_filter = re.sub(r"\s+", "", filter_text)

    return (
        resource_types == {"cloud_run_revision"}
        and services == [expected_service]
        and service_reference_count == 1
        and all(
            selector in compact_filter
            for selector in _REQUIRED_PRODUCT_AUDIT_SELECTORS
        )
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Read a filter from stdin and validate it for deploy preflight."""

    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 1:
        return 2

    return (
        0
        if is_valid_audit_sink_filter(
            sys.stdin.read(),
            expected_service=arguments[0],
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
