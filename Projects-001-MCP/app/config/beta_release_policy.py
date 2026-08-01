"""Fail-closed Demo/Beta deployment profile validation."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass

PROJECT_ID = "project001-489710"
REGION = "asia-southeast1"
ARTIFACT_REPOSITORY = "projects-001"
IMAGE_NAME = "projects-001-mcp"
IMAGE_DIGEST_RE = re.compile(
    rf"^{REGION}-docker\.pkg\.dev/{PROJECT_ID}/{ARTIFACT_REPOSITORY}/"
    rf"{IMAGE_NAME}@sha256:[0-9a-f]{{64}}$"
)


class ReleasePolicyError(ValueError):
    """Raised when a deployment selector violates the locked release profile."""


@dataclass(frozen=True, slots=True)
class ReleaseProfile:
    service_account: str
    audit_days: int


RELEASE_PROFILES = {
    "demo": ReleaseProfile(
        service_account=f"projects-001-mcp-demo@{PROJECT_ID}.iam.gserviceaccount.com",
        audit_days=90,
    ),
    "beta": ReleaseProfile(
        service_account=f"projects-001-mcp-beta@{PROJECT_ID}.iam.gserviceaccount.com",
        audit_days=365,
    ),
}


def validate_release_profile(
    *,
    environment: str,
    project_id: str,
    region: str,
    service_account: str,
    audit_read_max_days: int,
    promoted_image_uri: str = "",
) -> None:
    profile = RELEASE_PROFILES.get(environment)
    if profile is None:
        raise ReleasePolicyError("environment must be demo or beta")
    if project_id != PROJECT_ID or region != REGION:
        raise ReleasePolicyError("project or region does not match the locked release profile")
    if service_account != profile.service_account:
        raise ReleasePolicyError("service account does not match the environment identity")
    if audit_read_max_days != profile.audit_days:
        raise ReleasePolicyError("audit read window does not match environment retention")
    if environment == "beta" and IMAGE_DIGEST_RE.fullmatch(promoted_image_uri) is None:
        raise ReleasePolicyError("Beta must promote the exact approved Artifact Registry digest")


def validate_audit_bucket_retention(*, environment: str, retention_days: int) -> None:
    profile = RELEASE_PROFILES.get(environment)
    if profile is None:
        raise ReleasePolicyError("environment must be demo or beta")
    if retention_days != profile.audit_days:
        raise ReleasePolicyError("audit bucket retention does not match environment policy")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    profile = subparsers.add_parser("profile")
    profile.add_argument("environment")
    profile.add_argument("project_id")
    profile.add_argument("region")
    profile.add_argument("service_account")
    profile.add_argument("audit_read_max_days", type=int)
    profile.add_argument("promoted_image_uri", nargs="?", default="")

    retention = subparsers.add_parser("retention")
    retention.add_argument("environment")
    retention.add_argument("retention_days", type=int)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "profile":
            validate_release_profile(
                environment=args.environment,
                project_id=args.project_id,
                region=args.region,
                service_account=args.service_account,
                audit_read_max_days=args.audit_read_max_days,
                promoted_image_uri=args.promoted_image_uri,
            )
        else:
            validate_audit_bucket_retention(
                environment=args.environment,
                retention_days=args.retention_days,
            )
    except ReleasePolicyError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
