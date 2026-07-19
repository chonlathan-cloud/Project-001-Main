#!/usr/bin/env python3
"""Read-only MCP diagnostics for GCP project001-489710."""

from __future__ import annotations

import json
import os
import re
import subprocess
from typing import Any

from mcp.server.fastmcp import FastMCP

try:
    from google.cloud import firestore
except ImportError:  # pragma: no cover - dependency availability is environment-specific.
    firestore = None  # type: ignore[assignment]

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:  # pragma: no cover - dependency availability is environment-specific.
    psycopg2 = None  # type: ignore[assignment]
    RealDictCursor = None  # type: ignore[assignment]


mcp = FastMCP("GCP-Project001-Ops")

PROJECT = "project001-489710"
REGION = "asia-southeast1"
EXCLUDED_CLOUD_RUN = {"project-saas-001-be", "project-saas-001-fe"}
EXCLUDED_CLOUD_SQL = {"Project-001-saas"}

COMMAND_TIMEOUT_SECONDS = 30
MAX_LOG_LIMIT = 100
MAX_FIRESTORE_LIMIT = 20
MAX_SQL_ROWS = 100

CLOUD_RUN_SERVICE_RE = re.compile(r"^[a-z](?:[-a-z0-9]{0,61}[a-z0-9])?$")
REGION_RE = re.compile(r"^[a-z]+-[a-z]+[0-9]$")
SIMPLE_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")
FIRESTORE_SEGMENT_RE = re.compile(r"^[A-Za-z0-9_-]+$")
FRESHNESS_RE = re.compile(r"^[1-9][0-9]*(?:s|m|h|d)$")
BUCKET_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]$")

SENSITIVE_KEY_RE = re.compile(
    r"(password|passwd|secret|token|api[_-]?key|private[_-]?key|credential|"
    r"authorization|cookie|signed[_-]?url|connection[_-]?string|database[_-]?url)",
    re.IGNORECASE,
)
TEXT_REDACTIONS = (
    (
        re.compile(r"(?i)(authorization:\s*bearer\s+)[^\s\"']+"),
        r"\1[REDACTED]",
    ),
    (
        re.compile(r"(?i)((?:password|passwd|secret|token|api[_-]?key)=)[^&\s\"']+"),
        r"\1[REDACTED]",
    ),
    (re.compile(r"(?i)(X-Goog-Signature=)[^&\s\"']+"), r"\1[REDACTED]"),
)
MUTATING_SQL_RE = re.compile(
    r"\b(insert|update|delete|merge|drop|alter|create|truncate|grant|revoke|"
    r"copy|call|do|vacuum|refresh|listen|notify|execute|prepare|set|reset)\b",
    re.IGNORECASE,
)
DANGEROUS_SELECT_FUNCTION_RE = re.compile(
    r"\b(nextval|setval|pg_advisory_lock|pg_advisory_unlock|dblink_exec)\b",
    re.IGNORECASE,
)


def _bounded_int(value: int, default: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(1, min(parsed, maximum))


def _redact_text(text: str) -> str:
    redacted = text
    for pattern, replacement in TEXT_REDACTIONS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def _redact_json(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if SENSITIVE_KEY_RE.search(str(key)):
                redacted[str(key)] = "[REDACTED]"
            else:
                redacted[str(key)] = _redact_json(item)
        return redacted
    if isinstance(value, list):
        return [_redact_json(item) for item in value]
    if isinstance(value, str):
        return _redact_text(value)
    return value


def _json_dumps(value: Any) -> str:
    return json.dumps(_redact_json(value), indent=2, sort_keys=True, default=str)


def _run_command(command: list[str], timeout: int = COMMAND_TIMEOUT_SECONDS) -> tuple[str | None, str | None]:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return None, f"Missing executable: {command[0]}"
    except subprocess.TimeoutExpired:
        return None, f"Command timed out after {timeout}s: {' '.join(command[:3])}"

    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
        return None, _redact_text(message)

    return result.stdout, None


def _run_json_command(command: list[str], timeout: int = COMMAND_TIMEOUT_SECONDS) -> tuple[Any | None, str | None]:
    stdout, error = _run_command(command, timeout=timeout)
    if error:
        return None, error

    try:
        return json.loads(stdout or "[]"), None
    except json.JSONDecodeError as exc:
        return None, f"Failed to parse JSON from {command[0]} output: {exc}"


def _validate_region(region: str) -> str | None:
    if not REGION_RE.fullmatch(region):
        return f"Invalid region '{region}'."
    return None


def _validate_simple_id(name: str, label: str) -> str | None:
    if not name or not SIMPLE_ID_RE.fullmatch(name):
        return f"Invalid {label} '{name}'."
    return None


def _service_region(service: dict[str, Any]) -> str:
    metadata = service.get("metadata", {})
    labels = metadata.get("labels", {})
    return labels.get("cloud.googleapis.com/location") or REGION


def _service_summary(service: dict[str, Any]) -> dict[str, Any]:
    metadata = service.get("metadata", {})
    status = service.get("status", {})
    return {
        "name": metadata.get("name"),
        "region": _service_region(service),
        "url": status.get("url"),
        "latest_created_revision": status.get("latestCreatedRevisionName"),
        "latest_ready_revision": status.get("latestReadyRevisionName"),
    }


def _cloud_run_services() -> tuple[list[dict[str, Any]] | None, str | None]:
    services, error = _run_json_command(
        [
            "gcloud",
            "run",
            "services",
            "list",
            "--project",
            PROJECT,
            "--platform",
            "managed",
            "--format=json",
        ]
    )
    if error:
        return None, error
    return [
        service
        for service in services
        if service.get("metadata", {}).get("name") not in EXCLUDED_CLOUD_RUN
    ], None


def _validate_internal_cloud_run_service(service_name: str) -> tuple[dict[str, Any] | None, str | None]:
    if service_name in EXCLUDED_CLOUD_RUN:
        return None, f"Access denied: '{service_name}' belongs to an excluded SaaS environment."
    if not CLOUD_RUN_SERVICE_RE.fullmatch(service_name):
        return None, f"Invalid Cloud Run service name '{service_name}'."

    services, error = _cloud_run_services()
    if error:
        return None, error

    for service in services or []:
        if service.get("metadata", {}).get("name") == service_name:
            return service, None

    known = ", ".join(sorted(s.get("metadata", {}).get("name", "") for s in services or []))
    return None, f"Unknown in-scope Cloud Run service '{service_name}'. Known services: {known or 'none'}."


def _validate_firestore_collection_path(collection_path: str) -> str | None:
    if not collection_path or collection_path.strip("/") != collection_path:
        return "Firestore collection path must not be empty or start/end with '/'."

    segments = collection_path.split("/")
    if len(segments) % 2 == 0:
        return "Firestore collection path must point to a collection, not a document."

    for segment in segments:
        if not FIRESTORE_SEGMENT_RE.fullmatch(segment):
            return f"Unsafe Firestore path segment '{segment}'."
        if segment.startswith("__") and segment.endswith("__"):
            return f"Reserved Firestore path segment '{segment}' is not allowed."
    return None


def _field_type(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int) and not isinstance(value, bool):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    if value is None:
        return "null"
    return type(value).__name__


def _validate_readonly_sql(sql_query: str) -> tuple[str | None, str | None]:
    query = sql_query.strip().rstrip(";").strip()
    if not query:
        return None, "SQL query is empty."
    if ";" in query:
        return None, "Only one SQL statement is allowed."
    if not re.match(r"(?is)^(select|with)\b", query):
        return None, "Only SELECT or read-only WITH queries are allowed."
    if MUTATING_SQL_RE.search(query):
        return None, "Query contains a mutating or administrative SQL keyword."
    if DANGEROUS_SELECT_FUNCTION_RE.search(query):
        return None, "Query contains a function that is not allowed in diagnostics."
    return query, None


@mcp.tool()
def list_cloud_run_services() -> str:
    """List in-scope Cloud Run services, excluding known SaaS services."""
    services, error = _cloud_run_services()
    if error:
        return f"Error listing Cloud Run services: {error}"
    return _json_dumps([_service_summary(service) for service in services or []])


@mcp.tool()
def describe_cloud_run_service(service_name: str, region: str = REGION) -> str:
    """Describe one in-scope Cloud Run service without returning raw env values."""
    service, error = _validate_internal_cloud_run_service(service_name)
    if error:
        return error

    selected_region = region or _service_region(service or {})
    region_error = _validate_region(selected_region)
    if region_error:
        return region_error

    details, error = _run_json_command(
        [
            "gcloud",
            "run",
            "services",
            "describe",
            service_name,
            "--project",
            PROJECT,
            "--region",
            selected_region,
            "--format=json",
        ]
    )
    if error:
        return f"Error describing Cloud Run service: {error}"

    template = details.get("spec", {}).get("template", {}).get("spec", {})
    containers = []
    for container in template.get("containers", []):
        env = container.get("env", [])
        containers.append(
            {
                "image": container.get("image"),
                "ports": container.get("ports", []),
                "env_names": sorted(item.get("name") for item in env if item.get("name")),
                "env_names_from_value_sources": sorted(
                    item.get("name")
                    for item in env
                    if item.get("name") and item.get("valueFrom", {}).get("secretKeyRef")
                ),
            }
        )

    annotations = details.get("metadata", {}).get("annotations", {})
    safe_annotations = {
        key: annotations.get(key)
        for key in (
            "run.googleapis.com/ingress",
            "autoscaling.knative.dev/minScale",
            "autoscaling.knative.dev/maxScale",
        )
        if key in annotations
    }

    return _json_dumps(
        {
            **_service_summary(details),
            "service_account_name": template.get("serviceAccountName"),
            "traffic": details.get("status", {}).get("traffic", []),
            "containers": containers,
            "annotations": safe_annotations,
        }
    )


@mcp.tool()
def read_cloud_logs(
    service_name: str,
    limit: int = 30,
    freshness: str = "1h",
    errors_only: bool = False,
) -> str:
    """Read bounded, redacted Cloud Run logs for one in-scope service."""
    _, error = _validate_internal_cloud_run_service(service_name)
    if error:
        return error

    if not FRESHNESS_RE.fullmatch(freshness):
        return "Invalid freshness. Use values such as '30m', '1h', or '1d'."

    filters = [
        'resource.type="cloud_run_revision"',
        f'resource.labels.service_name="{service_name}"',
    ]
    if errors_only:
        filters.append("severity>=ERROR")

    logs, error = _run_json_command(
        [
            "gcloud",
            "logging",
            "read",
            " AND ".join(filters),
            "--project",
            PROJECT,
            f"--freshness={freshness}",
            f"--limit={_bounded_int(limit, 30, MAX_LOG_LIMIT)}",
            "--format=json",
        ]
    )
    if error:
        return f"Error retrieving logs: {error}"
    return _json_dumps(logs or [])


@mcp.tool()
def query_firestore_collection(
    collection_name: str,
    limit: int = 10,
    include_values: bool = False,
) -> str:
    """
    Inspect a Firestore collection.

    By default this returns document IDs and top-level field names/types only.
    Set include_values to true only when redacted sample values are needed.
    """
    if firestore is None:
        return "Firestore dependency is not installed."

    validation_error = _validate_firestore_collection_path(collection_name)
    if validation_error:
        return validation_error

    try:
        db = firestore.Client(project=PROJECT)
        docs = db.collection(collection_name).limit(_bounded_int(limit, 10, MAX_FIRESTORE_LIMIT)).stream(
            retry=None,
            timeout=5,
        )

        samples = []
        for doc in docs:
            data = _redact_json(doc.to_dict() or {})
            sample = {"id": doc.id}
            if include_values:
                sample["fields"] = data
            else:
                sample["field_names"] = sorted(data.keys())
                sample["field_types"] = {key: _field_type(value) for key, value in data.items()}
            samples.append(sample)

        if not samples:
            return f"Collection '{collection_name}' is empty or does not exist."

        return _json_dumps({"collection": collection_name, "sample_count": len(samples), "samples": samples})
    except Exception as exc:  # noqa: BLE001 - MCP tools should report errors as strings.
        return f"Firestore error: {_redact_text(str(exc))}"


@mcp.tool()
def diagnostic_postgres_query(
    instance_id: str,
    db_name: str,
    sql_query: str,
    max_rows: int = 20,
) -> str:
    """Execute a bounded read-only PostgreSQL diagnostic query through a local proxy."""
    if psycopg2 is None or RealDictCursor is None:
        return "psycopg2 dependency is not installed."
    if instance_id in EXCLUDED_CLOUD_SQL:
        return f"Access denied: instance '{instance_id}' is excluded from this repository's scope."
    instance_error = _validate_simple_id(instance_id, "Cloud SQL instance id")
    if instance_error:
        return instance_error
    db_error = _validate_simple_id(db_name, "database name")
    if db_error:
        return db_error

    query, sql_error = _validate_readonly_sql(sql_query)
    if sql_error:
        return sql_error

    row_limit = _bounded_int(max_rows, 20, MAX_SQL_ROWS)
    db_host = os.getenv("DB_HOST", "127.0.0.1")
    db_port = os.getenv("DB_PORT", "5432")
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "")

    try:
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password,
            connect_timeout=5,
            options="-c statement_timeout=5000 -c default_transaction_read_only=on",
        )
        conn.set_session(readonly=True, autocommit=True)
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(f"SELECT * FROM ({query}) AS codex_readonly_query LIMIT {row_limit}")
            rows = cursor.fetchall()
            return _json_dumps(rows)
    except Exception as exc:  # noqa: BLE001 - MCP tools should report errors as strings.
        return f"Database connection/query error: {_redact_text(str(exc))}"
    finally:
        if "conn" in locals() and conn:
            conn.close()


@mcp.tool()
def list_bigquery_datasets() -> str:
    """List BigQuery datasets for the project."""
    datasets, error = _run_json_command(["bq", "ls", "--format=json", f"--project_id={PROJECT}"])
    if error:
        return f"Error listing BigQuery datasets: {error}"
    return _json_dumps(datasets or [])


@mcp.tool()
def dry_run_bigquery_query(sql_query: str) -> str:
    """Dry-run a read-only BigQuery SQL query without returning row data."""
    query, sql_error = _validate_readonly_sql(sql_query)
    if sql_error:
        return sql_error

    stdout, error = _run_command(
        [
            "bq",
            "query",
            f"--project_id={PROJECT}",
            "--nouse_legacy_sql",
            "--dry_run",
            query or "",
        ]
    )
    if error:
        return f"BigQuery dry run error: {error}"
    return _redact_text(stdout.strip() or "BigQuery dry run completed.")


@mcp.tool()
def list_storage_buckets() -> str:
    """List Cloud Storage bucket metadata for the project."""
    buckets, error = _run_json_command(
        ["gcloud", "storage", "buckets", "list", "--project", PROJECT, "--format=json"]
    )
    if error:
        return f"Error listing storage buckets: {error}"
    return _json_dumps(buckets or [])


@mcp.tool()
def describe_storage_bucket(bucket_name: str) -> str:
    """Describe one Cloud Storage bucket without listing private object contents."""
    if not BUCKET_RE.fullmatch(bucket_name):
        return f"Invalid bucket name '{bucket_name}'."
    bucket, error = _run_json_command(
        ["gcloud", "storage", "buckets", "describe", f"gs://{bucket_name}", "--format=json"]
    )
    if error:
        return f"Error describing storage bucket: {error}"
    return _json_dumps(bucket or {})


@mcp.tool()
def list_secret_metadata() -> str:
    """List Secret Manager metadata only; never returns payloads."""
    secrets, error = _run_json_command(["gcloud", "secrets", "list", "--project", PROJECT, "--format=json"])
    if error:
        return f"Error listing secret metadata: {error}"
    return _json_dumps(secrets or [])


@mcp.tool()
def describe_secret_metadata(secret_name: str) -> str:
    """Describe one Secret Manager secret and version metadata without payload access."""
    validation_error = _validate_simple_id(secret_name, "secret name")
    if validation_error:
        return validation_error

    secret, secret_error = _run_json_command(
        ["gcloud", "secrets", "describe", secret_name, "--project", PROJECT, "--format=json"]
    )
    if secret_error:
        return f"Error describing secret metadata: {secret_error}"

    versions, version_error = _run_json_command(
        ["gcloud", "secrets", "versions", "list", secret_name, "--project", PROJECT, "--format=json"]
    )
    if version_error:
        return f"Error listing secret versions: {version_error}"

    return _json_dumps({"metadata": secret or {}, "versions": versions or []})


@mcp.tool()
def list_document_ai_processors(region: str = REGION) -> str:
    """List Document AI processors in a region."""
    region_error = _validate_region(region)
    if region_error:
        return region_error
    processors, error = _run_json_command(
        [
            "gcloud",
            "documentai",
            "processors",
            "list",
            "--project",
            PROJECT,
            f"--location={region}",
            "--format=json",
        ]
    )
    if error:
        return f"Error listing Document AI processors: {error}"
    return _json_dumps(processors or [])


@mcp.tool()
def list_vertex_ai_resources(region: str = REGION) -> str:
    """List Vertex AI models, endpoints, and indexes in a region."""
    region_error = _validate_region(region)
    if region_error:
        return region_error

    resources: dict[str, Any] = {}
    for resource_name, command in {
        "models": ["gcloud", "ai", "models", "list", "--project", PROJECT, f"--region={region}", "--format=json"],
        "endpoints": [
            "gcloud",
            "ai",
            "endpoints",
            "list",
            "--project",
            PROJECT,
            f"--region={region}",
            "--format=json",
        ],
        "indexes": ["gcloud", "ai", "indexes", "list", "--project", PROJECT, f"--region={region}", "--format=json"],
    }.items():
        result, error = _run_json_command(command)
        resources[resource_name] = {"error": error} if error else result or []

    return _json_dumps(resources)


if __name__ == "__main__":
    mcp.run()
