"""FastMCP variant that advertises and enforces closed tool input objects."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import AnyFunction, Icon, ToolAnnotations
from pydantic import ConfigDict


class ClosedInputFastMCP(FastMCP):
    """Close generated argument models until the SDK exposes this as a setting."""

    def add_tool(
        self,
        fn: AnyFunction,
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
        annotations: ToolAnnotations | None = None,
        icons: list[Icon] | None = None,
        meta: dict[str, Any] | None = None,
        structured_output: bool | None = None,
    ) -> None:
        super().add_tool(
            fn,
            name=name,
            title=title,
            description=description,
            annotations=annotations,
            icons=icons,
            meta=meta,
            structured_output=structured_output,
        )
        tool = self._tool_manager.get_tool(name or fn.__name__)
        if tool is None:  # pragma: no cover - protected by FastMCP registration
            raise RuntimeError("FastMCP did not retain the registered tool.")
        model = tool.fn_metadata.arg_model
        config = dict(model.model_config)
        config["extra"] = "forbid"
        model.model_config = ConfigDict(**config)
        model.model_rebuild(force=True)
        tool.parameters = model.model_json_schema(by_alias=True)
