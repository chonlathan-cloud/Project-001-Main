#!/usr/bin/env python3
"""Print or run bounded read-only GCP diagnostics for project001-489710."""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
from typing import Iterable


PROJECT = "project001-489710"
REGION = "asia-southeast1"
EXCLUDED_CLOUD_RUN = {"project-saas-001-be", "project-saas-001-fe"}
EXCLUDED_CLOUD_SQL = {"Project-001-saas"}


Command = list[str]


def gcloud(*args: str) -> Command:
    return ["gcloud", *args]


def bq(*args: str) -> Command:
    return ["bq", *args]


def quote_command(command: Command) -> str:
    return " ".join(shlex.quote(part) for part in command)


def cap_limit(value: int) -> str:
    return str(max(1, min(value, 200)))


def context_commands(_: argparse.Namespace) -> list[Command]:
    return [
        gcloud("config", "get-value", "project"),
        gcloud("auth", "list", "--filter=status:ACTIVE", "--format=table(account,status)"),
    ]


def inventory_commands(_: argparse.Namespace) -> list[Command]:
    return [
        gcloud("projects", "describe", PROJECT, "--format=json"),
        gcloud("services", "list", "--enabled", "--project", PROJECT, "--format=table(config.name,state)"),
        gcloud("run", "services", "list", "--project", PROJECT, "--platform", "managed", "--format=json"),
        gcloud("builds", "list", "--project", PROJECT, "--limit=20", "--format=json"),
        gcloud("artifacts", "repositories", "list", "--project", PROJECT, f"--location={REGION}", "--format=json"),
        gcloud("storage", "buckets", "list", "--project", PROJECT, "--format=json"),
        gcloud("firestore", "databases", "list", "--project", PROJECT, "--format=json"),
        bq("ls", f"--project_id={PROJECT}"),
        gcloud("secrets", "list", "--project", PROJECT, "--format=json"),
        gcloud("documentai", "processors", "list", "--project", PROJECT, f"--location={REGION}", "--format=json"),
        gcloud("ai", "models", "list", "--project", PROJECT, f"--region={REGION}", "--format=json"),
        gcloud("ai", "endpoints", "list", "--project", PROJECT, f"--region={REGION}", "--format=json"),
    ]


def cloud_run_commands(args: argparse.Namespace) -> list[Command]:
    if args.service in EXCLUDED_CLOUD_RUN:
        raise SystemExit(
            f"{args.service} is excluded SaaS context for another repository; "
            "do not inspect it with this skill unless the user explicitly redirects."
        )

    if not args.service:
        return [
            gcloud("run", "services", "list", "--project", PROJECT, "--platform", "managed", "--format=json"),
        ]

    region = args.region or REGION
    return [
        gcloud("run", "services", "describe", args.service, "--project", PROJECT, "--region", region, "--format=json"),
        gcloud("run", "revisions", "list", "--service", args.service, "--project", PROJECT, "--region", region, "--format=json"),
    ]


def log_commands(args: argparse.Namespace) -> list[Command]:
    filters = ['resource.type="cloud_run_revision"']
    if args.service:
        if args.service in EXCLUDED_CLOUD_RUN:
            raise SystemExit(
                f"{args.service} is excluded SaaS context for another repository; "
                "do not inspect it with this skill unless the user explicitly redirects."
            )
        filters.append(f'resource.labels.service_name="{args.service}"')
    if args.errors:
        filters.append("severity>=ERROR")

    return [
        gcloud(
            "logging",
            "read",
            " AND ".join(filters),
            "--project",
            PROJECT,
            f"--freshness={args.freshness}",
            f"--limit={cap_limit(args.limit)}",
            "--format=json",
        )
    ]


def bigquery_commands(args: argparse.Namespace) -> list[Command]:
    if args.query:
        return [
            bq(
                "query",
                f"--project_id={PROJECT}",
                "--nouse_legacy_sql",
                "--dry_run",
                args.query,
            )
        ]
    if args.table and args.dataset:
        return [bq("show", "--format=prettyjson", f"{PROJECT}:{args.dataset}.{args.table}")]
    if args.dataset:
        return [bq("ls", f"--project_id={PROJECT}", args.dataset)]
    return [bq("ls", f"--project_id={PROJECT}")]


def storage_commands(args: argparse.Namespace) -> list[Command]:
    if args.bucket:
        return [
            gcloud("storage", "buckets", "describe", f"gs://{args.bucket}", "--format=json"),
            gcloud("storage", "ls", f"gs://{args.bucket}/{args.prefix or ''}"),
        ]
    return [gcloud("storage", "buckets", "list", "--project", PROJECT, "--format=json")]


def secret_commands(args: argparse.Namespace) -> list[Command]:
    if args.secret:
        return [
            gcloud("secrets", "describe", args.secret, "--project", PROJECT, "--format=json"),
            gcloud("secrets", "versions", "list", args.secret, "--project", PROJECT, "--format=json"),
        ]
    return [gcloud("secrets", "list", "--project", PROJECT, "--format=json")]


def iam_commands(_: argparse.Namespace) -> list[Command]:
    return [gcloud("projects", "get-iam-policy", PROJECT, "--format=json")]


def document_ai_commands(args: argparse.Namespace) -> list[Command]:
    if args.processor:
        return [
            gcloud(
                "documentai",
                "processors",
                "describe",
                args.processor,
                "--project",
                PROJECT,
                f"--location={args.region or REGION}",
                "--format=json",
            )
        ]
    return [gcloud("documentai", "processors", "list", "--project", PROJECT, f"--location={args.region or REGION}", "--format=json")]


def vertex_ai_commands(args: argparse.Namespace) -> list[Command]:
    region = args.region or REGION
    return [
        gcloud("ai", "models", "list", "--project", PROJECT, f"--region={region}", "--format=json"),
        gcloud("ai", "endpoints", "list", "--project", PROJECT, f"--region={region}", "--format=json"),
        gcloud("ai", "indexes", "list", "--project", PROJECT, f"--region={region}", "--format=json"),
    ]


WORKFLOWS = {
    "context": context_commands,
    "inventory": inventory_commands,
    "cloud-run": cloud_run_commands,
    "logs": log_commands,
    "bigquery": bigquery_commands,
    "storage": storage_commands,
    "secrets": secret_commands,
    "iam": iam_commands,
    "document-ai": document_ai_commands,
    "vertex-ai": vertex_ai_commands,
}


def run_commands(commands: Iterable[Command], execute: bool) -> int:
    exit_code = 0
    for command in commands:
        print(quote_command(command))
        if not execute:
            continue

        executable = command[0]
        if shutil.which(executable) is None:
            print(f"missing executable: {executable}", file=sys.stderr)
            exit_code = 127
            continue

        result = subprocess.run(command, text=True)
        if result.returncode != 0:
            exit_code = result.returncode
    return exit_code


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workflow", choices=sorted(WORKFLOWS), help="Read-only diagnostic workflow to print or run.")
    parser.add_argument("--execute", action="store_true", help="Run commands instead of only printing them.")
    parser.add_argument("--service", help="Cloud Run service name for cloud-run/log workflows.")
    parser.add_argument("--region", default=REGION, help=f"GCP region. Default: {REGION}.")
    parser.add_argument("--freshness", default="1h", help="Cloud Logging freshness window. Default: 1h.")
    parser.add_argument("--limit", type=int, default=50, help="Cloud Logging result limit, capped at 200.")
    parser.add_argument("--errors", action="store_true", help="Filter Cloud Logging output to severity>=ERROR.")
    parser.add_argument("--dataset", help="BigQuery dataset for table listing.")
    parser.add_argument("--table", help="BigQuery table for schema metadata.")
    parser.add_argument("--query", help="BigQuery SQL to dry-run only.")
    parser.add_argument("--bucket", help="Cloud Storage bucket name without gs://.")
    parser.add_argument("--prefix", help="Cloud Storage prefix for object listing.")
    parser.add_argument("--secret", help="Secret Manager secret name for metadata only.")
    parser.add_argument("--processor", help="Document AI processor ID.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    commands = WORKFLOWS[args.workflow](args)
    return run_commands(commands, args.execute)


if __name__ == "__main__":
    raise SystemExit(main())
