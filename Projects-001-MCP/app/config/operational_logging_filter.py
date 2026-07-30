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
_SERVICE_REGEX_PATTERN = re.compile(
    r'resource\.labels\.service_name\s*=~\s*"([^"]+)"',
    re.IGNORECASE,
)
_SEVERITY_PATTERN = re.compile(
    r"severity\s*(=|!=|>=|<=|>|<|:)\s*([A-Z]+)",
    re.IGNORECASE,
)


def _exact_anchored_regex_services(pattern: str) -> set[str] | None:
    """Return literal alternatives from ``^(service-a|service-b)$`` only."""

    match = re.fullmatch(r"\^\(([^()]+)\)\$", pattern)
    if match is None:
        return None

    alternatives = match.group(1).split("|")
    if any(re.fullmatch(r"[a-z0-9-]+", item) is None for item in alternatives):
        return None
    if len(alternatives) != len(set(alternatives)):
        return None
    return set(alternatives)


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
    equality_services = _SERVICE_PATTERN.findall(filter_text)
    service_regexes = _SERVICE_REGEX_PATTERN.findall(filter_text)
    service_reference_count = len(
        re.findall(r"resource\.labels\.service_name", filter_text, re.IGNORECASE)
    )
    severity_comparisons = [
        (operator, value.upper())
        for operator, value in _SEVERITY_PATTERN.findall(filter_text)
    ]

    if resource_types != {"cloud_run_revision"}:
        return False
    if regions != {expected_region}:
        return False

    if target == "sink":
        return (
            set(equality_services) == expected_services
            and len(equality_services) == len(expected_services)
            and not service_regexes
            and service_reference_count == len(expected_services)
            and severity_comparisons == [(">=", "WARNING")]
        )
    if target == "view":
        regex_services = (
            _exact_anchored_regex_services(service_regexes[0])
            if len(service_regexes) == 1
            else None
        )
        return (
            not equality_services
            and service_reference_count == 1
            and regex_services == expected_services
            and not severity_comparisons
        )
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
