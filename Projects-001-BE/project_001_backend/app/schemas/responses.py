"""
Generic Standard Response wrapper.
All API endpoints return this structure: {"status": "success", "data": ...}
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class StandardResponse(BaseModel, Generic[T]):
    """Wraps every API response in a consistent envelope."""
    status: str = "success"
    data: T


class ErrorResponse(BaseModel):
    """Returned on handled errors."""
    status: str = "error"
    detail: str
