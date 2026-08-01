"""Deterministic Phase 6 private-plugin and Beta release-boundary evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config.beta_release_policy import validate_release_profile
from app.config.private_plugin import validate_private_plugin
from tests.evals.phase2_evaluator import evaluate_phase2
from tests.evals.phase3_evaluator import evaluate_phase3
from tests.evals.phase4_evaluator import evaluate_phase4
from tests.evals.phase5_evaluator import evaluate_phase5

MCP_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = MCP_ROOT.parent
PLUGIN_ROOT = MCP_ROOT / "plugins" / "projects-001-product"
PHASE5_EVIDENCE = REPOSITORY_ROOT / "docs/implementation/mcp/phase5-demo-release-evidence.md"
REQUIRED_PHASE6_DOCS = (
    REPOSITORY_ROOT / "docs/User_Manual_MCP_Private_Plugin.md",
    REPOSITORY_ROOT / "docs/implementation/mcp/phase6-privacy-notice.md",
    REPOSITORY_ROOT / "docs/implementation/mcp/phase6-beta-runbook.md",
    REPOSITORY_ROOT / "docs/implementation/mcp/phase6-beta-release-evidence.md",
)
TEST_DIGEST = (
    "asia-southeast1-docker.pkg.dev/project001-489710/projects-001/"
    "projects-001-mcp@sha256:" + "a" * 64
)


def evaluate_phase6() -> dict[str, Any]:
    previous_reports = {
        "phase2": evaluate_phase2(),
        "phase3": evaluate_phase3(),
        "phase4": evaluate_phase4(),
        "phase5": evaluate_phase5(),
    }
    previous_repository_gates = {
        name: bool(report["gate_passed"]) for name, report in previous_reports.items()
    }

    plugin = validate_private_plugin(PLUGIN_ROOT)
    validate_release_profile(
        environment="beta",
        project_id="project001-489710",
        region="asia-southeast1",
        service_account="projects-001-mcp-beta@project001-489710.iam.gserviceaccount.com",
        audit_read_max_days=365,
        promoted_image_uri=TEST_DIGEST,
    )

    beta_env = (REPOSITORY_ROOT / "cloudrun-mcp-beta.env.yaml.example").read_text(
        encoding="utf-8"
    )
    beta_deploy = (REPOSITORY_ROOT / "mcp.deploy.beta.example").read_text(
        encoding="utf-8"
    )
    deploy_script = (REPOSITORY_ROOT / "deploy_mcp.sh").read_text(encoding="utf-8")
    beta_profile_ready = all(
        marker in beta_env
        for marker in (
            'MCP_ENVIRONMENT: "beta"',
            'MCP_AUDIT_READ_MAX_DAYS: "365"',
            'MCP_OPERATIONAL_LOG_READ_MAX_DAYS: "30"',
        )
    ) and all(
        marker in beta_deploy
        for marker in (
            "MCP_SERVICE_NAME=projects-001-mcp-beta",
            "MCP_SERVICE_ACCOUNT=projects-001-mcp-beta@project001-489710.iam.gserviceaccount.com",
            "MCP_PROMOTED_IMAGE_URI=",
        )
    )
    deployment_policy_ready = all(
        marker in deploy_script
        for marker in (
            "beta_release_policy.py",
            "EXPECTED_AUDIT_RETENTION_DAYS=\"365\"",
            "Promoting tested image",
        )
    )
    documentation_ready = all(
        path.is_file() and path.stat().st_size > 0 for path in REQUIRED_PHASE6_DOCS
    )

    phase5_text = PHASE5_EVIDENCE.read_text(encoding="utf-8")
    phase5_pending_rows = phase5_text.count("| Pending |")
    repository_gate_passed = (
        all(previous_repository_gates.values())
        and plugin["name"] == "projects-001-product"
        and plugin["version"] == "0.6.0"
        and beta_profile_ready
        and deployment_policy_ready
        and documentation_ready
    )

    return {
        "schema_version": "1.0",
        "previous_repository_gates": previous_repository_gates,
        "plugin_repository_ready": True,
        "plugin_connection_bound": plugin["bound"],
        "beta_profile_ready": beta_profile_ready,
        "deployment_policy_ready": deployment_policy_ready,
        "documentation_ready": documentation_ready,
        "phase5_evidence_pending_rows": phase5_pending_rows,
        "repository_gate_passed": repository_gate_passed,
        "live_release_gate_passed": None,
        "live_release_status": "not_evaluated",
        "remaining_live_gates": [
            "close the seven remaining Phase 5 Demo evidence rows",
            "provision and preflight Beta MCP identity/service/logging resources",
            "build and approve a Phase 6 Demo image digest",
            "register and bind the ChatGPT MCP connection",
            "run Owner, revoke, selected-Admin, performance and rollback evidence",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(evaluate_phase6(), ensure_ascii=False, indent=2))
