"""Validate and bind the private Projects-001 plugin to a registered ChatGPT app."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

PLUGIN_NAME = "projects-001-product"
PLUGIN_VERSION = "0.6.0"
APP_ALIAS = "projects-001-product"
APP_ID_RE = re.compile(r"^plugin_asdk_app[0-9A-Za-z._-]{1,220}$")
APP_ID_PLACEHOLDER_MARKERS = ("replace_with", "replace-with", "placeholder", "example")


class PrivatePluginError(ValueError):
    """Raised when the private plugin package is incomplete or unsafe."""


def _registered_app_id(value: object) -> str:
    normalized = str(value or "").strip()
    lowered = normalized.lower()
    if APP_ID_RE.fullmatch(normalized) is None or any(
        marker in lowered for marker in APP_ID_PLACEHOLDER_MARKERS
    ):
        raise PrivatePluginError(
            "app ID must be the real plugin_asdk_app ID created by ChatGPT"
        )
    return normalized


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PrivatePluginError(f"invalid JSON file: {path.name}") from exc
    if not isinstance(value, dict):
        raise PrivatePluginError(f"{path.name} must contain a JSON object")
    return value


def validate_private_plugin(plugin_root: Path, *, require_bound: bool = False) -> dict[str, Any]:
    manifest = _read_object(plugin_root / ".codex-plugin" / "plugin.json")
    if manifest.get("name") != PLUGIN_NAME or manifest.get("version") != PLUGIN_VERSION:
        raise PrivatePluginError("plugin name/version does not match the Phase 6 package")
    if manifest.get("skills") != "./skills/" or manifest.get("apps") != "./.app.json":
        raise PrivatePluginError("plugin must include the bundled skill and registered app mapping")

    interface = manifest.get("interface")
    if not isinstance(interface, dict) or interface.get("capabilities") != ["Read"]:
        raise PrivatePluginError("plugin capabilities must be exactly read-only")
    prompts = interface.get("defaultPrompt")
    if not isinstance(prompts, list) or not 1 <= len(prompts) <= 3:
        raise PrivatePluginError("plugin must provide one to three bounded starter prompts")
    invalid_prompt = any(
        not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 128
        for prompt in prompts
    )
    if invalid_prompt:
        raise PrivatePluginError("plugin starter prompts must be non-empty and at most 128 chars")

    app_manifest = _read_object(plugin_root / ".app.json")
    apps = app_manifest.get("apps")
    if not isinstance(apps, dict):
        raise PrivatePluginError(".app.json apps must be an object")
    bound = apps.get(APP_ALIAS)
    if bound is not None:
        if not isinstance(bound, dict) or set(bound) != {"id", "category"}:
            raise PrivatePluginError("registered app mapping contains unsupported fields")
        _registered_app_id(bound.get("id"))
        if bound.get("category") != "Productivity":
            raise PrivatePluginError("registered app category must be Productivity")
    elif require_bound:
        raise PrivatePluginError("plugin is not bound to a registered ChatGPT MCP connection")

    skill_path = plugin_root / "skills" / "projects-001-workflows" / "SKILL.md"
    try:
        skill_text = skill_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PrivatePluginError("bundled workflow skill is missing") from exc
    if "name: projects-001-workflows" not in skill_text or "[TODO:" in skill_text:
        raise PrivatePluginError("bundled workflow skill is invalid or incomplete")

    return {"name": PLUGIN_NAME, "version": PLUGIN_VERSION, "bound": bound is not None}


def bind_registered_app(plugin_root: Path, app_id: str) -> Path:
    normalized_id = _registered_app_id(app_id)
    validate_private_plugin(plugin_root)
    app_path = plugin_root / ".app.json"
    payload = {
        "apps": {
            APP_ALIAS: {
                "id": normalized_id,
                "category": "Productivity",
            }
        }
    }
    temporary_path = app_path.with_suffix(".json.tmp")
    temporary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary_path.replace(app_path)
    validate_private_plugin(plugin_root, require_bound=True)
    return app_path


def prepare_private_plugin(
    source_root: Path,
    output_root: Path,
    app_id: str,
) -> Path:
    """Create a bound release copy without modifying the checked-in package."""

    source = source_root.resolve()
    output = output_root.resolve()
    source_result = validate_private_plugin(source)
    if source_result["bound"]:
        raise PrivatePluginError("source plugin must remain unbound")
    if output == source or source in output.parents:
        raise PrivatePluginError("release copy must be outside the source plugin")
    if output.exists():
        raise PrivatePluginError("release copy destination already exists")

    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, output)
        bind_registered_app(output, app_id)
    except (OSError, PrivatePluginError) as exc:
        shutil.rmtree(output, ignore_errors=True)
        if isinstance(exc, PrivatePluginError):
            raise
        raise PrivatePluginError("could not create private plugin release copy") from exc
    return output


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("plugin_root", type=Path)
    validate.add_argument("--require-bound", action="store_true")
    bind = subparsers.add_parser("bind")
    bind.add_argument("plugin_root", type=Path)
    bind.add_argument("app_id")
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("source_root", type=Path)
    prepare.add_argument("output_root", type=Path)
    prepare.add_argument("app_id")
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "prepare":
            path = prepare_private_plugin(
                args.source_root,
                args.output_root,
                args.app_id,
            )
            print(f"Prepared bound private plugin release copy in {path}")
        elif args.command == "bind":
            path = bind_registered_app(args.plugin_root, args.app_id)
            print(f"Bound registered ChatGPT app in {path}")
        else:
            result = validate_private_plugin(args.plugin_root, require_bound=args.require_bound)
            print(json.dumps(result, sort_keys=True))
    except PrivatePluginError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
