from app.config.audit_logging_filter import is_valid_audit_sink_filter

EXPECTED_SERVICE = "projects-001-mcp"
BASE_FILTER = """resource.type="cloud_run_revision"
AND resource.labels.service_name="projects-001-mcp"
AND (
  jsonPayload.log_type="product_audit"
  OR jsonPayload.message:"\\"log_type\\":\\"product_audit\\""
  OR textPayload:"\\"log_type\\":\\"product_audit\\""
)"""


def validate(filter_text: str) -> bool:
    return is_valid_audit_sink_filter(
        filter_text,
        expected_service=EXPECTED_SERVICE,
    )


def test_audit_sink_accepts_all_supported_product_audit_payload_shapes() -> None:
    assert validate(BASE_FILTER)


def test_audit_sink_rejects_missing_nested_json_message_selector() -> None:
    assert not validate(
        BASE_FILTER.replace(
            '  OR jsonPayload.message:"\\"log_type\\":\\"product_audit\\""\n',
            "",
        )
    )


def test_audit_sink_rejects_missing_direct_or_text_selectors() -> None:
    assert not validate(
        BASE_FILTER.replace('  jsonPayload.log_type="product_audit"\n', "")
    )
    assert not validate(
        BASE_FILTER.replace(
            '  OR textPayload:"\\"log_type\\":\\"product_audit\\""\n',
            "",
        )
    )


def test_audit_sink_rejects_wrong_or_additional_service_boundary() -> None:
    assert not validate(BASE_FILTER.replace(EXPECTED_SERVICE, "project-saas-001-be"))
    assert not validate(
        f'{BASE_FILTER}\nOR resource.labels.service_name="{EXPECTED_SERVICE}"'
    )


def test_audit_sink_rejects_wrong_resource_type() -> None:
    assert not validate(BASE_FILTER.replace("cloud_run_revision", "global"))
