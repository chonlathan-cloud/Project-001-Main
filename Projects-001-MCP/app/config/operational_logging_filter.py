"""Validate environment-locked Cloud Logging sink and view filters."""

from __future__ import annotations

import re
import sys
from collections.abc import Sequence
from typing import Literal

FilterTarget = Literal["sink", "view"]

_RESOURCE_TYPE_PATTERN = re.compile(
    r'resource\.type\s*=\s*"([^"]+)"',
    re.IGNORECASE,
)
_REGION_PATTERN = re.compile(
    r'resource\.labels\.location\s*=\s*"([^"]+)"',
    re.IGNORECASE,
)
_SERVICE_PATTERN = re.compile(
    r'resource\.labels\.service_name\s*=\s*"([^"]+)"',
    re.IGNORECASE,
)
_SEVERITY_PATTERN = re.compile(
    r"severity\s*(=|!=|>=|<=|>|<|:)\s*([A-Z]+)",
    re.IGNORECASE,
)


def is_valid_operational_filter(
    filter_text: str,
    *,
    target: FilterTarget,
    expected_region: str,
    expected_services: set[str],
) -> bool:
    """Return whether a sink or view filter enforces its exact boundary."""

    resource_types = set(_RESOURCE_TYPE_PATTERN.findall(filter_text))
    regions = set(_REGION_PATTERN.findall(filter_text))
    services = set(_SERVICE_PATTERN.findall(filter_text))
    severity_comparisons = [
        (operator, value.upper())
        for operator, value in _SEVERITY_PATTERN.findall(filter_text)
    ]

    if resource_types != {"cloud_run_revision"}:
        return False
    if regions != {expected_region}:
        return False
    if services != expected_services:
        return False

    if target == "sink":
        return severity_comparisons == [(">=", "WARNING")]
    if target == "view":
        return not severity_comparisons
    return False


def main(argv: Sequence[str] | None = None) -> int:
    """Read a filter from stdin and validate it for deploy preflight."""

    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 5:
        return 2

    target, expected_region, *expected_services = arguments
    if target not in {"sink", "view"}:
        return 2

    is_valid = is_valid_operational_filter(
        sys.stdin.read(),
        target=target,
        expected_region=expected_region,
        expected_services=set(expected_services),
    )
    return 0 if is_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
