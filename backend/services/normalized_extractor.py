from __future__ import annotations

from datetime import datetime
from typing import Dict
import re

import pandas as pd


OUTPUT_COLUMNS = ["日期", "单号", "工厂", "型号", "公司", "数量"]
REQUIRED_PLAN_FIELDS = ("order_no", "factory", "model", "company", "quantity")


def _normalize_column_name(value: str) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


def _optional_series(df: pd.DataFrame, plan: Dict[str, str], field_name: str, formatter) -> pd.Series:
    if field_name in plan and plan[field_name] in df.columns:
        return df[plan[field_name]].map(formatter)
    return pd.Series([None] * len(df), index=df.index)


def _require_columns(df: pd.DataFrame, plan: Dict[str, str]) -> None:
    missing = [
        plan[field_name]
        for field_name in ("order_no", "quantity")
        if field_name in plan and plan[field_name] not in df.columns
    ]
    if missing:
        raise ValueError(f"Extraction plan references missing columns: {', '.join(missing)}")


def _format_date(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None

    timestamp = pd.to_datetime(value, errors="coerce")
    if pd.isna(timestamp):
        return None
    if isinstance(timestamp, pd.Timestamp):
        return f"{timestamp.year}/{timestamp.month}/{timestamp.day}"
    if isinstance(timestamp, datetime):
        return f"{timestamp.year}/{timestamp.month}/{timestamp.day}"
    return None


def _format_string(value) -> str | None:
    if value is None:
        return None
    if pd.isna(value):
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip() or None


def _format_quantity(value) -> int:
    if value is None or pd.isna(value):
        return 0

    if isinstance(value, str):
        normalized = value.replace(",", "").strip()
        if not normalized:
            return 0
        return int(float(normalized))

    return int(float(value))


def normalize_records(df: pd.DataFrame, plan: Dict[str, str]) -> pd.DataFrame:
    working_df = df.copy()
    working_df.columns = [_normalize_column_name(column) for column in working_df.columns]
    normalized_plan = {
        field_name: _normalize_column_name(column_name)
        for field_name, column_name in plan.items()
    }

    _require_columns(working_df, normalized_plan)

    date_series = _optional_series(working_df, normalized_plan, "date", _format_date)

    normalized = pd.DataFrame(
        {
            "日期": date_series,
            "单号": working_df[normalized_plan["order_no"]].map(_format_string),
            "工厂": _optional_series(working_df, normalized_plan, "factory", _format_string),
            "型号": _optional_series(working_df, normalized_plan, "model", _format_string),
            "公司": _optional_series(working_df, normalized_plan, "company", _format_string),
            "数量": working_df[normalized_plan["quantity"]].map(_format_quantity),
        }
    )

    normalized = normalized.dropna(subset=["单号"]).reset_index(drop=True)
    return normalized[OUTPUT_COLUMNS]
