from __future__ import annotations

import io
from typing import Any, Dict, List

import pandas as pd

from services.data_comparator import DataComparator
from services.document_converter import convert_excel_to_markdown
from services.field_mapping_service import build_extraction_plan
from services.normalized_extractor import attach_record_context, normalize_records


def merge_normalized_frames(frames: List[pd.DataFrame]) -> pd.DataFrame:
    if not frames:
        return pd.DataFrame(columns=["日期", "订单号", "工厂", "型号", "公司", "数量"])
    return pd.concat(frames, ignore_index=True).reset_index(drop=True)


def normalize_optional_text(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def attach_jiuding_filter_company(
    normalized_df: pd.DataFrame,
    *,
    source_df: pd.DataFrame,
    plan_mapping: Dict[str, str],
) -> pd.DataFrame:
    order_column = plan_mapping.get("order_no")
    if not order_column or order_column not in source_df.columns:
        return normalized_df

    customer_column = None
    for column in source_df.columns:
        if "客户名称" in str(column).strip():
            customer_column = str(column).strip()
            break
    if customer_column is None:
        return normalized_df

    filter_df = pd.DataFrame(
        {
            "订单号": source_df[order_column].map(normalize_optional_text),
            "筛选公司": source_df[customer_column].map(normalize_optional_text),
        }
    )
    filter_df = filter_df.dropna(subset=["订单号", "筛选公司"])
    if filter_df.empty:
        return normalized_df

    filter_df = filter_df.groupby("订单号", as_index=False).agg({"筛选公司": "first"})
    return normalized_df.merge(filter_df, on="订单号", how="left")


def process_single_excel(
    *,
    content: bytes,
    filename: str,
    role: str,
    factory_type: str,
    llm_settings,
    jiuding_reference_rows: List[Dict[str, str]] | None = None,
) -> Dict[str, Any]:
    document = convert_excel_to_markdown(content, filename)
    plan = build_extraction_plan(
        file_content=content,
        filename=filename,
        role=role,
        factory_type=factory_type,
        markdown=document["markdown"],
        preview=document["preview"],
        llm_settings=llm_settings,
        jiuding_reference_rows=jiuding_reference_rows,
    )

    source_df = pd.read_excel(io.BytesIO(content), dtype=str)
    source_df.columns = [str(column).strip() for column in source_df.columns]
    plan_mapping = plan.to_column_mapping()
    normalized_df = normalize_records(source_df, plan_mapping)

    if role == "jiuding":
        normalized_df = attach_jiuding_filter_company(
            normalized_df,
            source_df=source_df,
            plan_mapping=plan_mapping,
        )

    source_hint = plan_mapping.get("factory")
    normalized_df = attach_record_context(
        normalized_df,
        source_filename=filename,
        source_hint=(
            source_df[source_hint].astype(str).str.strip().iloc[0]
            if source_hint and source_hint in source_df.columns and not source_df.empty
            else None
        ),
    )

    return {
        "normalized_df": normalized_df,
        "preview": document["preview"],
        "plan": plan.model_dump(),
        "filename": filename,
    }


def compare_xinfengming_data(
    *,
    factory_files: List[Dict[str, Any]],
    jiuding_files: List[Dict[str, Any]],
    factory_type: str,
    llm_settings,
    jiuding_reference_rows: List[Dict[str, str]],
) -> Dict[str, Any]:
    factory_processed = [
        process_single_excel(
            content=file_item["content"],
            filename=file_item["filename"],
            role="factory",
            factory_type=factory_type,
            llm_settings=llm_settings,
            jiuding_reference_rows=jiuding_reference_rows,
        )
        for file_item in factory_files
    ]
    jiuding_processed = [
        process_single_excel(
            content=file_item["content"],
            filename=file_item["filename"],
            role="jiuding",
            factory_type=factory_type,
            llm_settings=llm_settings,
            jiuding_reference_rows=None,
        )
        for file_item in jiuding_files
    ]

    factory_df = merge_normalized_frames([item["normalized_df"] for item in factory_processed])
    jiuding_df = merge_normalized_frames([item["normalized_df"] for item in jiuding_processed])
    result_df = DataComparator(factory_df, jiuding_df, factory_type).compare()

    return {
        "result_df": result_df,
        "artifacts": {
            "factory_files": [
                {
                    "filename": item["filename"],
                    "preview": item["preview"],
                    "plan": item["plan"],
                }
                for item in factory_processed
            ],
            "jiuding_files": [
                {
                    "filename": item["filename"],
                    "preview": item["preview"],
                    "plan": item["plan"],
                }
                for item in jiuding_processed
            ],
        },
    }
