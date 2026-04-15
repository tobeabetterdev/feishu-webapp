from __future__ import annotations

import io
from typing import Any

import pandas as pd

from services.data_comparator import DataComparator

FACTORY_REQUIRED_COLUMNS = ["交货创建日期", "交货单号", "销售组织描述", "客户名称", "件数"]
JIUDING_REQUIRED_COLUMNS = ["订单日期", "出库单号", "客户名称", "会员名称", "实际出库数量"]

FACTORY_PLAN_FIELDS = ["交货创建日期", "交货单号", "销售组织描述", "客户名称", "物料组描述", "件数"]
JIUDING_PLAN_FIELDS = ["订单日期", "出库单号", "客户名称", "会员名称", "产品类型", "实际出库数量"]

OUTPUT_COLUMNS = ["日期", "单号", "工厂", "型号", "公司", "数量"]
SUMMARY_KEYWORDS = ("合计", "汇总", "总计", "合并", "小计")
MODEL_KEYWORDS = ("POY", "FDY")
FACTORY_DETAIL_COLUMNS = [
    "交货单号",
    "交货创建日期",
    "销售组织描述",
    "客户名称",
    "业务员",
    "车牌号",
    "物料组描述",
    "件数",
    "交货单类型",
    "包装批号",
]
JIUDING_DETAIL_COLUMNS = [
    "出库单号",
    "订单日期",
    "客户名称",
    "会员名称",
    "产品类型",
    "实际出库数量",
    "子公司名称",
    "订单状态",
    "送货方式",
]


def _normalize_text(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _normalize_date(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    timestamp = pd.to_datetime(value, errors="coerce")
    if pd.isna(timestamp):
        return None
    return f"{timestamp.year}/{timestamp.month}/{timestamp.day}"


def _normalize_model(value: object) -> str | None:
    text = _normalize_text(value)
    if text is None:
        return None
    upper_text = text.upper()
    for keyword in MODEL_KEYWORDS:
        if keyword in upper_text:
            return keyword
    return None


def _normalize_quantity(value: object) -> int:
    if value is None or pd.isna(value):
        return 0
    text = str(value).strip().replace(",", "")
    if not text:
        return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def _is_summary_like_text(value: object) -> bool:
    text = _normalize_text(value)
    if text is None:
        return False
    return any(keyword in text for keyword in SUMMARY_KEYWORDS)


def _require_columns(df: pd.DataFrame, required_columns: list[str]) -> None:
    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise ValueError(f"缺少必需列: {', '.join(missing)}")


def _first_non_empty(series: pd.Series) -> Any:
    for value in series:
        if value is None or pd.isna(value):
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _should_drop_row(row: dict[str, Any]) -> bool:
    order_no = row.get("单号")
    quantity = row.get("数量", 0)
    factory = row.get("工厂")
    company = row.get("公司")
    model = row.get("型号")
    date = row.get("日期")

    order_blank = order_no is None
    optional_blank = all(value is None for value in (factory, company, model, date))
    if order_blank and optional_blank and quantity == 0:
        return True

    summary_candidates = [order_no, factory, company, model]
    if order_blank and any(_is_summary_like_text(value) for value in summary_candidates):
        return True

    return False


def _attach_context(df: pd.DataFrame, *, source_filename: str, source_hint: str | None) -> pd.DataFrame:
    working = df.copy()
    working["来源文件"] = source_filename
    working["来源工厂线索"] = source_hint
    return working


def _build_plan_artifact(fields: list[str]) -> dict[str, Any]:
    return {"mode": "fixed_columns", "fields": fields}


def _build_factory_detail_row(row: pd.Series) -> dict[str, Any]:
    return {
        "交货单号": _normalize_text(row.get("交货单号")),
        "交货创建日期": _normalize_date(row.get("交货创建日期")),
        "销售组织描述": _normalize_text(row.get("销售组织描述")),
        "客户名称": _normalize_text(row.get("客户名称")),
        "业务员": _normalize_text(row.get("业务员")),
        "车牌号": _normalize_text(row.get("车牌号")),
        "物料组描述": _normalize_text(row.get("物料组描述")),
        "件数": _normalize_quantity(row.get("件数")),
        "交货单类型": _normalize_text(row.get("交货单类型")),
        "包装批号": _normalize_text(row.get("包装批号")),
    }


def _build_jiuding_detail_row(row: pd.Series) -> dict[str, Any]:
    return {
        "出库单号": _normalize_text(row.get("出库单号")),
        "订单日期": _normalize_date(row.get("订单日期")),
        "客户名称": _normalize_text(row.get("客户名称")),
        "会员名称": _normalize_text(row.get("会员名称")),
        "产品类型": _normalize_text(row.get("产品类型")),
        "实际出库数量": _normalize_quantity(row.get("实际出库数量")),
        "子公司名称": _normalize_text(row.get("子公司名称")),
        "订单状态": _normalize_text(row.get("订单状态")),
        "送货方式": _normalize_text(row.get("送货方式")),
    }


def parse_xinfengming_factory_data(source_df: pd.DataFrame, *, source_filename: str) -> pd.DataFrame:
    working = source_df.copy()
    working.columns = [str(column).strip() for column in working.columns]
    _require_columns(working, FACTORY_REQUIRED_COLUMNS)

    model_column = "物料组描述" if "物料组描述" in working.columns else None
    parsed_rows: list[dict[str, Any]] = []
    for _, row in working.iterrows():
        parsed_row = {
            "日期": _normalize_date(row.get("交货创建日期")),
            "单号": _normalize_text(row.get("交货单号")),
            "工厂": _normalize_text(row.get("销售组织描述")),
            "型号": _normalize_model(row.get(model_column)) if model_column else None,
            "公司": _normalize_text(row.get("客户名称")),
            "数量": _normalize_quantity(row.get("件数")),
            **_build_factory_detail_row(row),
        }
        if _should_drop_row(parsed_row):
            continue
        parsed_rows.append(parsed_row)

    parsed = pd.DataFrame(parsed_rows)
    if parsed.empty:
        parsed = pd.DataFrame(columns=[*OUTPUT_COLUMNS, *FACTORY_DETAIL_COLUMNS])
    else:
        parsed["单号"] = parsed["单号"].map(_normalize_text)
        parsed = parsed.dropna(subset=["单号"])
        parsed = (
            parsed.groupby("单号", as_index=False)
            .agg(
                {
                    "日期": _first_non_empty,
                    "工厂": _first_non_empty,
                    "型号": _first_non_empty,
                    "公司": _first_non_empty,
                    "数量": "sum",
                    "交货单号": _first_non_empty,
                    "交货创建日期": _first_non_empty,
                    "销售组织描述": _first_non_empty,
                    "客户名称": _first_non_empty,
                    "业务员": _first_non_empty,
                    "车牌号": _first_non_empty,
                    "物料组描述": _first_non_empty,
                    "件数": "sum",
                    "交货单类型": _first_non_empty,
                    "包装批号": _first_non_empty,
                }
            )
            .reset_index(drop=True)
        )
    source_hint = None
    if not parsed.empty and "工厂" in parsed.columns:
        source_hint = _normalize_text(parsed["工厂"].iloc[0])
    return _attach_context(parsed, source_filename=source_filename, source_hint=source_hint)


def parse_xinfengming_jiuding_data(source_df: pd.DataFrame, *, source_filename: str) -> pd.DataFrame:
    working = source_df.copy()
    working.columns = [str(column).strip() for column in working.columns]
    _require_columns(working, JIUDING_REQUIRED_COLUMNS)

    model_column = "产品类型" if "产品类型" in working.columns else None
    parsed_rows: list[dict[str, Any]] = []
    for _, row in working.iterrows():
        parsed_row = {
            "日期": _normalize_date(row.get("订单日期")),
            "单号": _normalize_text(row.get("出库单号")),
            "工厂": _normalize_text(row.get("客户名称")),
            "型号": _normalize_model(row.get(model_column)) if model_column else None,
            "公司": _normalize_text(row.get("会员名称")),
            "数量": _normalize_quantity(row.get("实际出库数量")),
            "筛选公司": _normalize_text(row.get("客户名称")),
            **_build_jiuding_detail_row(row),
        }
        if _should_drop_row(parsed_row):
            continue
        parsed_rows.append(parsed_row)

    parsed = pd.DataFrame(parsed_rows)
    if parsed.empty:
        parsed = pd.DataFrame(columns=[*OUTPUT_COLUMNS, "筛选公司", *JIUDING_DETAIL_COLUMNS])
    return _attach_context(parsed, source_filename=source_filename, source_hint=None)


def _merge_frames(frames: list[pd.DataFrame], *, include_filter_company: bool = False) -> pd.DataFrame:
    if not frames:
        columns = [*OUTPUT_COLUMNS, "来源文件", "来源工厂线索"]
        if include_filter_company:
            columns.insert(6, "筛选公司")
        return pd.DataFrame(columns=columns)
    return pd.concat(frames, ignore_index=True).reset_index(drop=True)


def compare_xinfengming_data(
    *,
    factory_files: list[dict[str, Any]],
    jiuding_files: list[dict[str, Any]],
    factory_type: str,
) -> dict[str, Any]:
    factory_processed = []
    for file_item in factory_files:
        source_df = pd.read_excel(io.BytesIO(file_item["content"]), dtype=str)
        parsed_df = parse_xinfengming_factory_data(source_df, source_filename=file_item["filename"])
        factory_processed.append(
            {
                "filename": file_item["filename"],
                "parsed_df": parsed_df,
                "plan": _build_plan_artifact(FACTORY_PLAN_FIELDS),
                "preview": "",
            }
        )

    jiuding_processed = []
    for file_item in jiuding_files:
        source_df = pd.read_excel(io.BytesIO(file_item["content"]), dtype=str)
        parsed_df = parse_xinfengming_jiuding_data(source_df, source_filename=file_item["filename"])
        jiuding_processed.append(
            {
                "filename": file_item["filename"],
                "parsed_df": parsed_df,
                "plan": _build_plan_artifact(JIUDING_PLAN_FIELDS),
                "preview": "",
            }
        )

    factory_df = _merge_frames([item["parsed_df"] for item in factory_processed])
    jiuding_df = _merge_frames(
        [item["parsed_df"] for item in jiuding_processed],
        include_filter_company=True,
    )
    result_df = DataComparator(factory_df, jiuding_df, factory_type).compare()

    return {
        "result_df": result_df,
        "artifacts": {
            "factory_type": factory_type,
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
            "factory_records": factory_df.to_dict(orient="records"),
            "jiuding_records": jiuding_df.to_dict(orient="records"),
        },
    }
