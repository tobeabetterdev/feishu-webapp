from __future__ import annotations

import io
import json
from typing import Dict, List

import pandas as pd

from config.settings import LLMSettings
from services.llm_client import LLMClient
from services.schema_models import ExtractionField, ExtractionPlan


FIELD_KEYWORDS: Dict[str, Dict[str, List[str]]] = {
    "factory_hengyi": {
        "date": ["交货日期", "日期", "创建日期", "时间"],
        "order_no": ["交货单", "订单", "单号"],
        "factory": ["送达方", "客户名称", "客户"],
        "model": ["物料组描述", "物料", "产品", "品种"],
        "company": ["客户名称", "送达方", "客户"],
        "quantity": ["交货数量", "数量", "件数", "出库数"],
    },
    "factory_xinfengming": {
        "date": ["交货创建日期", "交货日期", "日期", "时间"],
        "order_no": ["交货单号", "交货单", "订单", "单号"],
        "factory": ["客户名称", "工厂", "送达方"],
        "model": ["物料组描述", "物料", "产品", "品种"],
        "company": ["客户名称", "公司", "会员"],
        "quantity": ["件数", "数量", "出库数", "交货数量"],
    },
    "jiuding": {
        "date": ["订单日期", "日期", "创建日期", "时间"],
        "order_no": ["出库单号", "订单", "单号"],
        "factory": ["工厂", "客户", "会员"],
        "model": ["产品类型", "产品", "物料", "品种"],
        "company": ["会员名称", "公司", "客户"],
        "quantity": ["实际出库数量", "出库数", "数量", "件数"],
    },
}

FIELD_DEFAULT_TYPES = {
    "date": "date",
    "order_no": "string",
    "factory": "string",
    "model": "string",
    "company": "string",
    "quantity": "integer",
}

REQUIRED_FIELDS_BY_ROLE = {
    "factory": ("order_no", "quantity"),
    "jiuding": ("order_no", "quantity"),
}


def _find_column(columns: List[str], keywords: List[str]) -> str:
    for column in columns:
        normalized = str(column).strip()
        for keyword in keywords:
            if keyword in normalized:
                return normalized
    raise ValueError(f"Could not identify column for keywords: {keywords}")


def _find_column_optional(columns: List[str], keywords: List[str]) -> str | None:
    try:
        return _find_column(columns, keywords)
    except ValueError:
        return None


def _heuristic_plan(df: pd.DataFrame, role: str, factory_type: str) -> ExtractionPlan:
    key = "jiuding" if role == "jiuding" else f"factory_{factory_type}"
    keywords = FIELD_KEYWORDS[key]
    columns = [str(column).strip() for column in df.columns]
    fields = {
        name: ExtractionField(
            column=_find_column(columns, field_keywords),
            type="integer" if name == "quantity" else ("date" if name == "date" else "string"),
            output_format="yyyy/m/d" if name == "date" else None,
        )
        for name, field_keywords in keywords.items()
    }
    return ExtractionPlan(
        source_sheet=None,
        header_row_index=1,
        data_start_row_index=2,
        skip_keywords=["合计", "汇总", "总计", "备注"],
        fields=fields,
        confidence=0.4,
        notes=["heuristic fallback plan"],
    )


def _build_prompt(*, role: str, factory_type: str, filename: str, markdown: str, preview: str) -> str:
    return (
        f"Document role: {role}\n"
        f"Factory type: {factory_type}\n"
        f"Filename: {filename}\n"
        "You must extract a JSON object that maps source columns to fields: "
        "date, order_no, factory, model, company, quantity.\n"
        "Hard rules: order_no must be string; quantity must be integer; date output_format must be yyyy/m/d; "
        "all other fields are strings.\n"
        "Return only JSON.\n\n"
        f"Markdown:\n{markdown[:12000]}\n\n"
        f"Table preview:\n{preview[:4000]}"
    )


def _normalize_plan_payload(payload: Dict) -> Dict:
    normalized = dict(payload)

    notes = normalized.get("notes")
    if isinstance(notes, str):
        normalized["notes"] = [notes]
    elif notes is None:
        normalized["notes"] = []

    fields = normalized.get("fields", {})
    normalized_fields = {}
    for field_name, field_payload in fields.items():
        if not isinstance(field_payload, dict):
            continue
        normalized_field = dict(field_payload)
        if "column" not in normalized_field and "source_column" in normalized_field:
            normalized_field["column"] = normalized_field["source_column"]
        column_value = normalized_field.get("column")
        if column_value is None or not str(column_value).strip():
            continue
        normalized_field["column"] = str(column_value).strip()
        if "type" not in normalized_field and "data_type" in normalized_field:
            normalized_field["type"] = normalized_field["data_type"]
        if "type" not in normalized_field:
            normalized_field["type"] = FIELD_DEFAULT_TYPES.get(field_name, "string")
        if field_name == "date" and "output_format" not in normalized_field:
            normalized_field["output_format"] = "yyyy/m/d"
        normalized_fields[field_name] = normalized_field
    normalized["fields"] = normalized_fields
    return normalized


def _merge_missing_fields_with_heuristics(
    normalized_payload: Dict,
    *,
    df: pd.DataFrame,
    role: str,
    factory_type: str,
) -> Dict:
    merged = dict(normalized_payload)
    merged_fields = dict(merged.get("fields", {}))
    key = "jiuding" if role == "jiuding" else f"factory_{factory_type}"
    keywords = FIELD_KEYWORDS[key]
    columns = [str(column).strip() for column in df.columns]

    missing_fields = []
    for field_name, field_keywords in keywords.items():
        if field_name in merged_fields:
            continue

        inferred_column = _find_column_optional(columns, field_keywords)
        if inferred_column is None:
            continue

        merged_fields[field_name] = {
            "column": inferred_column,
            "type": FIELD_DEFAULT_TYPES.get(field_name, "string"),
            **({"output_format": "yyyy/m/d"} if field_name == "date" else {}),
        }
        missing_fields.append(field_name)

    merged["fields"] = merged_fields
    if missing_fields:
        merged["notes"] = [
            *merged.get("notes", []),
            f"Filled missing fields from heuristic detection: {', '.join(missing_fields)}",
        ]

    return merged


def _validate_required_fields(normalized_payload: Dict, *, role: str) -> None:
    fields = normalized_payload.get("fields", {})
    required_fields = REQUIRED_FIELDS_BY_ROLE.get(role, ("order_no", "quantity"))
    missing_required = [field_name for field_name in required_fields if field_name not in fields]
    if missing_required:
        raise ValueError(f"Missing required fields for {role}: {', '.join(missing_required)}")


def build_extraction_plan(
    *,
    file_content: bytes,
    filename: str,
    role: str,
    factory_type: str,
    markdown: str,
    preview: str,
    llm_settings: LLMSettings,
) -> ExtractionPlan:
    df = pd.read_excel(io.BytesIO(file_content))
    df.columns = [str(column).strip() for column in df.columns]

    if not llm_settings.is_configured:
        return _heuristic_plan(df, role, factory_type)

    system_prompt = (
        "You are an extraction planner for Excel comparison tasks. "
        "Return strict JSON only. "
        "The JSON must include source_sheet, header_row_index, data_start_row_index, skip_keywords, "
        "fields, confidence, and notes."
    )
    user_prompt = _build_prompt(
        role=role,
        factory_type=factory_type,
        filename=filename,
        markdown=markdown,
        preview=preview,
    )
    payload = LLMClient(llm_settings).generate_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )
    normalized_payload = _normalize_plan_payload(payload)
    merged_payload = _merge_missing_fields_with_heuristics(
        normalized_payload,
        df=df,
        role=role,
        factory_type=factory_type,
    )
    _validate_required_fields(merged_payload, role=role)
    return ExtractionPlan.model_validate(merged_payload)
