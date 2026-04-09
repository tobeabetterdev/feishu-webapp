from __future__ import annotations

from datetime import datetime
import re
from typing import Dict

import pandas as pd


OUTPUT_COLUMNS = ["日期", "单号", "工厂", "型号", "公司", "数量"]
SUMMARY_KEYWORDS = ("合计", "汇总", "总计", "合并", "小计")
MODEL_KEYWORDS = ("POY", "FDY")


def _normalize_column_name(value: str) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


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
    if value is None or pd.isna(value):
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).strip()
    return text or None


def _format_model(value) -> str | None:
    text = _format_string(value)
    if text is None:
        return None

    upper_text = text.upper()
    for keyword in MODEL_KEYWORDS:
        if keyword in upper_text:
            return keyword
    return None


def _format_quantity(value) -> int:
    if value is None or pd.isna(value):
        return 0

    if isinstance(value, str):
        normalized = value.replace(",", "").strip()
        if not normalized:
            return 0
        try:
            return int(float(normalized))
        except ValueError:
            return 0

    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _is_summary_like_text(value: object) -> bool:
    if value is None or pd.isna(value):
        return False
    text = str(value).strip()
    if not text:
        return False
    return any(keyword in text for keyword in SUMMARY_KEYWORDS)


def _optional_series(
    df: pd.DataFrame,
    plan: Dict[str, str],
    field_name: str,
    formatter,
) -> pd.Series:
    column_name = plan.get(field_name)
    if column_name and column_name in df.columns:
        return df[column_name].map(formatter)
    return pd.Series([None] * len(df), index=df.index)


def _require_columns(df: pd.DataFrame, plan: Dict[str, str]) -> None:
    missing = [
        plan[field_name]
        for field_name in ("order_no", "quantity")
        if field_name in plan and plan[field_name] not in df.columns
    ]
    if missing:
        raise ValueError(f"Extraction plan references missing columns: {', '.join(missing)}")


def _should_drop_row(row: pd.Series) -> bool:
    order_no = row.get("单号")
    quantity = row.get("数量")
    optional_values = [row.get("日期"), row.get("工厂"), row.get("型号"), row.get("公司")]

    order_blank = order_no is None or str(order_no).strip() == ""
    optional_blank = all(value is None or str(value).strip() == "" for value in optional_values)
    quantity_blank = quantity == 0

    if order_blank and optional_blank and quantity_blank:
        return True

    summary_candidates = [order_no, *optional_values]
    if order_blank and optional_blank:
        return True
    if order_blank and any(_is_summary_like_text(value) for value in summary_candidates):
        return True

    return False


def normalize_records(df: pd.DataFrame, plan: Dict[str, str]) -> pd.DataFrame:
    working_df = df.copy()
    working_df.columns = [_normalize_column_name(column) for column in working_df.columns]
    normalized_plan = {
        field_name: _normalize_column_name(column_name)
        for field_name, column_name in plan.items()
    }

    _require_columns(working_df, normalized_plan)

    normalized = pd.DataFrame(
        {
            "日期": _optional_series(working_df, normalized_plan, "date", _format_date),
            "单号": working_df[normalized_plan["order_no"]].map(_format_string),
            "工厂": _optional_series(working_df, normalized_plan, "factory", _format_string),
            "型号": _optional_series(working_df, normalized_plan, "model", _format_model),
            "公司": _optional_series(working_df, normalized_plan, "company", _format_string),
            "数量": working_df[normalized_plan["quantity"]].map(_format_quantity),
        }
    )

    normalized = normalized[~normalized.apply(_should_drop_row, axis=1)]
    normalized = normalized.dropna(subset=["单号"]).reset_index(drop=True)
    return normalized[OUTPUT_COLUMNS]


def attach_record_context(df: pd.DataFrame, *, source_filename: str, source_hint: str | None = None) -> pd.DataFrame:
    working = df.copy()
    working["来源文件"] = source_filename
    if source_hint is not None:
        working["来源工厂线索"] = source_hint
    elif "工厂" not in working.columns:
        working["来源工厂线索"] = None
    else:
        working["来源工厂线索"] = working["工厂"]
    return working
