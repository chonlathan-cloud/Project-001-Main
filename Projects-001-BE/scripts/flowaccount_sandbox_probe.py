"""
Probe FlowAccount sandbox configuration without printing secrets.

Usage:
  cd Projects-001-BE
  source .venv/bin/activate
  python scripts/flowaccount_sandbox_probe.py

The script reads FlowAccount settings from the backend environment/.env,
checks token retrieval, then lists read-only bank channels and expense
categories needed for FLOWACCOUNT_DEFAULT_BANK_ACCOUNT_ID and
FLOWACCOUNT_EXPENSE_CATEGORY_MAPPING_JSON.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402
from app.services.flowaccount_service import FlowAccountError, FlowAccountService  # noqa: E402


READ_ONLY_ENDPOINTS = {
    "bank_accounts": "/bank-channel/bank-accounts",
    "expense_categories_business": "/expenses/categories/business",
    "expense_categories_accounting": "/expenses/categories/accounting",
}

SUMMARY_FIELDS = (
    "id",
    "recordId",
    "bankAccountId",
    "accountId",
    "categoryId",
    "systemCode",
    "name",
    "nameLocal",
    "nameForeign",
    "bankName",
    "accountName",
    "accountNumber",
    "creditId",
    "creditCategory",
    "debitId",
    "debitCategory",
    "unitName",
)


def _safe_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def _extract_items(payload: dict[str, Any]) -> list[Any]:
    data = payload.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in (
            "items",
            "list",
            "data",
            "bankAccounts",
            "bank_accounts",
            "categories",
            "expenseCategories",
        ):
            value = data.get(key)
            if isinstance(value, list):
                return value
        return [data]
    return []


def _summarize_item(item: Any) -> Any:
    if not isinstance(item, dict):
        return item
    summary = {
        field: item.get(field)
        for field in SUMMARY_FIELDS
        if field in item and item.get(field) not in (None, "")
    }
    return summary or {
        key: value
        for key, value in item.items()
        if not isinstance(value, (dict, list)) and value not in (None, "")
    }


def _print_section(title: str, payload: dict[str, Any], *, limit: int = 30) -> None:
    items = _extract_items(payload)
    print(f"\n== {title} ==")
    print(f"count: {len(items)}")
    for index, item in enumerate(items[:limit], start=1):
        print(f"{index}. {_safe_json(_summarize_item(item))}")
    if len(items) > limit:
        print(f"... {len(items) - limit} more items omitted")


def _print_preflight() -> None:
    settings = get_settings()
    print("== FlowAccount sandbox probe ==")
    print(f"enabled: {settings.flowaccount_enabled}")
    print(f"base_url: {settings.flowaccount_base_url}")
    print(f"scope: {settings.flowaccount_scope}")
    print(f"client_id configured: {bool(settings.flowaccount_client_id)}")
    print(f"client_secret configured: {bool(settings.flowaccount_client_secret)}")
    print(f"default payment method: {settings.flowaccount_default_payment_method}")
    print(f"default bank account id configured: {bool(settings.flowaccount_default_bank_account_id)}")


async def main() -> None:
    _print_preflight()
    service = FlowAccountService()

    try:
        await service.get_access_token()
    except FlowAccountError as exc:
        print(f"\nToken: FAILED - {exc}")
        raise SystemExit(1) from exc

    print("\nToken: OK")
    for title, path in READ_ONLY_ENDPOINTS.items():
        try:
            payload = await service._request("GET", path)
        except FlowAccountError as exc:
            print(f"\n== {title} ==")
            print(f"FAILED - {exc}")
            continue
        _print_section(title, payload)


if __name__ == "__main__":
    asyncio.run(main())
