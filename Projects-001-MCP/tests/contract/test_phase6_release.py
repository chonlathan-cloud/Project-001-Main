from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from app.config.beta_release_policy import (
    ReleasePolicyError,
    validate_audit_bucket_retention,
    validate_release_profile,
)
from app.config.private_plugin import (
    PrivatePluginError,
    bind_registered_app,
    prepare_private_plugin,
    validate_private_plugin,
)

MCP_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = MCP_ROOT / "plugins" / "projects-001-product"
BETA_DIGEST = (
    "asia-southeast1-docker.pkg.dev/project001-489710/projects-001/"
    "projects-001-mcp@sha256:" + "a" * 64
)


def test_private_plugin_repository_package_is_valid_and_unbound() -> None:
    result = validate_private_plugin(PLUGIN_ROOT)
    assert result == {
        "name": "projects-001-product",
        "version": "0.6.0",
        "bound": False,
    }
    with pytest.raises(PrivatePluginError, match="not bound"):
        validate_private_plugin(PLUGIN_ROOT, require_bound=True)


def test_private_plugin_binding_accepts_only_registered_chatgpt_id(tmp_path: Path) -> None:
    plugin_copy = tmp_path / "projects-001-product"
    shutil.copytree(PLUGIN_ROOT, plugin_copy)
    bind_registered_app(plugin_copy, "plugin_asdk_app_phase6test")
    assert validate_private_plugin(plugin_copy, require_bound=True)["bound"] is True
    app_manifest = json.loads((plugin_copy / ".app.json").read_text(encoding="utf-8"))
    assert app_manifest["apps"]["projects-001-product"]["category"] == "Productivity"


def test_private_plugin_binding_rejects_placeholder_or_untrusted_id(tmp_path: Path) -> None:
    plugin_copy = tmp_path / "projects-001-product"
    shutil.copytree(PLUGIN_ROOT, plugin_copy)
    with pytest.raises(PrivatePluginError, match="plugin_asdk_app"):
        bind_registered_app(plugin_copy, "replace-with-app-id")
    with pytest.raises(PrivatePluginError, match="real plugin_asdk_app"):
        bind_registered_app(
            plugin_copy,
            "plugin_asdk_app_REPLACE_WITH_REGISTERED_ID",
        )
    assert json.loads((plugin_copy / ".app.json").read_text(encoding="utf-8")) == {
        "apps": {}
    }


def test_private_plugin_prepare_creates_bound_copy_and_preserves_source(
    tmp_path: Path,
) -> None:
    release_copy = tmp_path / "release" / "projects-001-product-demo"
    prepared = prepare_private_plugin(
        PLUGIN_ROOT,
        release_copy,
        "plugin_asdk_app_phase6demo",
    )

    assert prepared == release_copy
    assert validate_private_plugin(prepared, require_bound=True)["bound"] is True
    assert validate_private_plugin(PLUGIN_ROOT)["bound"] is False


def test_private_plugin_prepare_refuses_existing_or_nested_destination(
    tmp_path: Path,
) -> None:
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(PrivatePluginError, match="already exists"):
        prepare_private_plugin(
            PLUGIN_ROOT,
            existing,
            "plugin_asdk_app_phase6demo",
        )
    with pytest.raises(PrivatePluginError, match="outside the source"):
        prepare_private_plugin(
            PLUGIN_ROOT,
            PLUGIN_ROOT / "release-copy",
            "plugin_asdk_app_phase6demo",
        )
    invalid_copy = tmp_path / "invalid-app-id"
    with pytest.raises(PrivatePluginError, match="real plugin_asdk_app"):
        prepare_private_plugin(
            PLUGIN_ROOT,
            invalid_copy,
            "plugin_asdk_app_PLACEHOLDER",
        )
    assert not invalid_copy.exists()


def test_beta_release_profile_requires_exact_identity_digest_and_retention() -> None:
    validate_release_profile(
        environment="beta",
        project_id="project001-489710",
        region="asia-southeast1",
        service_account=(
            "projects-001-mcp-beta@project001-489710.iam.gserviceaccount.com"
        ),
        audit_read_max_days=365,
        promoted_image_uri=BETA_DIGEST,
    )
    validate_audit_bucket_retention(environment="beta", retention_days=365)


@pytest.mark.parametrize(
    ("service_account", "audit_days", "image_uri"),
    [
        (
            "projects-001-mcp-demo@project001-489710.iam.gserviceaccount.com",
            365,
            BETA_DIGEST,
        ),
        (
            "projects-001-mcp-beta@project001-489710.iam.gserviceaccount.com",
            90,
            BETA_DIGEST,
        ),
        (
            "projects-001-mcp-beta@project001-489710.iam.gserviceaccount.com",
            365,
            "asia-southeast1-docker.pkg.dev/project001-489710/projects-001/"
            "projects-001-mcp:latest",
        ),
    ],
)
def test_beta_release_profile_fails_closed(
    service_account: str,
    audit_days: int,
    image_uri: str,
) -> None:
    with pytest.raises(ReleasePolicyError):
        validate_release_profile(
            environment="beta",
            project_id="project001-489710",
            region="asia-southeast1",
            service_account=service_account,
            audit_read_max_days=audit_days,
            promoted_image_uri=image_uri,
        )


def test_beta_audit_bucket_retention_cannot_reuse_demo_policy() -> None:
    with pytest.raises(ReleasePolicyError):
        validate_audit_bucket_retention(environment="beta", retention_days=90)
