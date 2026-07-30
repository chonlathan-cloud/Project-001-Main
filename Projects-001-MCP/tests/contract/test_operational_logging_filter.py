import pytest

from app.config.operational_logging_filter import is_valid_operational_filter

EXPECTED_REGION = "asia-southeast1"
EXPECTED_SERVICES = {
    "projects-001-fe",
    "projects-001-be",
    "projects-001-mcp",
}
BASE_FILTER = """resource.type="cloud_run_revision"
AND resource.labels.location="asia-southeast1"
AND (
  resource.labels.service_name="projects-001-fe"
  OR resource.labels.service_name="projects-001-be"
  OR resource.labels.service_name="projects-001-mcp"
)"""


def validate(filter_text: str, *, target: str) -> bool:
    return is_valid_operational_filter(
        filter_text,
        target=target,
        expected_region=EXPECTED_REGION,
        expected_services=EXPECTED_SERVICES,
    )


def test_view_accepts_exact_resource_boundary_without_severity() -> None:
    assert validate(BASE_FILTER, target="view")


def test_view_rejects_severity_filter_that_cloud_logging_views_do_not_support() -> None:
    assert not validate(f"{BASE_FILTER}\nAND severity>=WARNING", target="view")


def test_sink_requires_warning_severity_boundary() -> None:
    assert validate(f"{BASE_FILTER}\nAND severity >= warning", target="sink")
    assert not validate(BASE_FILTER, target="sink")
    assert not validate(f"{BASE_FILTER}\nAND severity>=ERROR", target="sink")


@pytest.mark.parametrize(
    "filter_text",
    [
        BASE_FILTER.replace('resource.type="cloud_run_revision"\nAND ', ""),
        BASE_FILTER.replace(EXPECTED_REGION, "us-central1"),
        BASE_FILTER.replace(
            '  OR resource.labels.service_name="projects-001-mcp"\n',
            "",
        ),
        BASE_FILTER.replace(
            'resource.labels.service_name="projects-001-mcp"',
            'resource.labels.service_name="project-saas-001-be"',
        ),
    ],
)
def test_sink_and_view_reject_inexact_resource_boundaries(filter_text: str) -> None:
    assert not validate(filter_text, target="view")
    assert not validate(f"{filter_text}\nAND severity>=WARNING", target="sink")
