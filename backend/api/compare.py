from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import math
import os
import traceback
import uuid
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from config.settings import build_task_llm_settings, load_llm_settings
from services.document_converter import convert_excel_to_markdown
from services.field_mapping_service import build_extraction_plan, build_jiuding_reference_samples
from services.hengyi_comparison import (
    HengyiComparisonError,
    compare_hengyi_data,
    parse_hengyi_factory_data,
    parse_hengyi_jiuding_data,
)
from services.normalized_extractor import attach_record_context, normalize_records
from services.xinfengming_comparison import compare_xinfengming_data

router = APIRouter()
tasks: Dict[str, Dict[str, Any]] = {}
FACTORY_GROUPS_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "factory_groups.json"
RUNTIME_DIR = Path(__file__).resolve().parent.parent / "runtime"
RUNTIME_DIR.mkdir(exist_ok=True)
LOGGER = logging.getLogger("compare_tasks")
if not LOGGER.handlers:
    file_handler = logging.FileHandler(RUNTIME_DIR / "backend.tasks.log", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    LOGGER.addHandler(file_handler)
    LOGGER.addHandler(stream_handler)
    LOGGER.setLevel(logging.INFO)

warnings.filterwarnings(
    "ignore",
    message="Workbook contains no default style, apply openpyxl's default",
    category=UserWarning,
)

HENGYI_ANOMALY_SHEET_NAMES = {
    "工厂侧待补录": "工厂侧待补录",
    "久鼎侧待补录": "久鼎侧待补录",
    "数量差异待核实": "数量差异待核实",
}


class TaskStatus(BaseModel):
    task_id: str
    status: str
    progress: int
    message: str


def _ensure_excel(filename: str, label: str) -> None:
    if not filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail=f"{label}必须是 Excel 文件")


def _clean_data(data):
    if isinstance(data, dict):
        return {key: _clean_data(value) for key, value in data.items()}
    if isinstance(data, list):
        return [_clean_data(item) for item in data]
    if isinstance(data, float) and not math.isfinite(data):
        return None
    return data


def _update_task(
    task_id: str,
    *,
    status: Optional[str] = None,
    progress: Optional[int] = None,
    message: Optional[str] = None,
) -> None:
    if status is not None:
        tasks[task_id]["status"] = status
    if progress is not None:
        tasks[task_id]["progress"] = progress
    if message is not None:
        tasks[task_id]["message"] = message

    LOGGER.info(
        "task=%s status=%s progress=%s message=%s",
        task_id,
        tasks[task_id].get("status"),
        tasks[task_id].get("progress"),
        tasks[task_id].get("message"),
    )


def _build_result_filename(result_df: pd.DataFrame) -> str:
    date_for_name = ""
    for column_name in ("日期", "过账日期(工厂)", "订单日期(久鼎)"):
        if not result_df.empty and column_name in result_df.columns:
            first_date = result_df[column_name].dropna().iloc[0] if not result_df[column_name].dropna().empty else None
            if first_date is not None and str(first_date).strip():
                date_for_name = str(first_date).strip().replace("/", "-")
                break

    filename_parts = ["订单核对"]
    if date_for_name:
        filename_parts.append(date_for_name)
    filename_parts.append(str(uuid.uuid4())[:8])
    return "_".join(filename_parts) + ".xlsx"


def _first_non_empty_value(series: pd.Series):
    for value in series:
        if value is None or pd.isna(value):
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _build_hengyi_order_key(row: pd.Series) -> str:
    for column_name in ("交货单(工厂)", "出库单号(久鼎)"):
        value = row.get(column_name)
        if value is not None and not pd.isna(value) and str(value).strip():
            return str(value).strip()
    return f"ROW-{row.name}"


def _build_hengyi_summary_sheet(result_df: pd.DataFrame) -> pd.DataFrame:
    working = result_df.copy()
    working["订单号"] = working.apply(_build_hengyi_order_key, axis=1)
    if "托盘数(工厂)" in working.columns:
        working["托盘数(工厂)"] = working["托盘数(工厂)"].fillna(0)

    summary_df = (
        working.groupby(["异常类型", "订单号"], as_index=False)
        .agg(
            {
                "工厂(工厂)": _first_non_empty_value,
                "会员名称(久鼎)": _first_non_empty_value,
                "送达方(工厂)": _first_non_empty_value,
                "托盘数(工厂)": "sum",
                "实际出库数量(久鼎)": _first_non_empty_value,
                "差量": _first_non_empty_value,
            }
        )
        .rename(
            columns={
                "工厂(工厂)": "工厂",
                "会员名称(久鼎)": "会员名称(久鼎)",
                "送达方(工厂)": "送达方(工厂)",
                "托盘数(工厂)": "工厂托盘合计",
                "实际出库数量(久鼎)": "久鼎数量",
            }
        )
    )
    summary_df["公司"] = summary_df["会员名称(久鼎)"].combine_first(summary_df["送达方(工厂)"])
    summary_df = summary_df[
        ["异常类型", "订单号", "工厂", "公司", "工厂托盘合计", "久鼎数量", "差量"]
    ]
    anomaly_order = {name: index for index, name in enumerate(HENGYI_ANOMALY_SHEET_NAMES.keys())}
    summary_df["__sort_order"] = summary_df["异常类型"].map(anomaly_order).fillna(len(anomaly_order))
    summary_df = summary_df.sort_values(["__sort_order", "订单号"], kind="stable").drop(columns="__sort_order")
    summary_df = summary_df.reset_index(drop=True)
    return summary_df


def _write_sheet(writer: pd.ExcelWriter, sheet_name: str, df: pd.DataFrame) -> None:
    export_df = df.copy().astype(object)
    export_df = export_df.where(pd.notna(export_df), None)
    export_df.to_excel(writer, sheet_name=sheet_name, index=False)


def _merge_hengyi_quantity_sheet(writer: pd.ExcelWriter, sheet_name: str, df: pd.DataFrame) -> None:
    if df.empty:
        return

    worksheet = writer.book[sheet_name]
    columns = list(df.columns)
    merge_columns = [
        "异常类型",
        "订单日期(久鼎)",
        "出库单号(久鼎)",
        "客户名称(久鼎)",
        "会员名称(久鼎)",
        "产品类型(久鼎)",
        "实际出库数量(久鼎)",
        "差量",
    ]
    column_index_map = {column_name: index + 1 for index, column_name in enumerate(columns)}

    order_keys = df.apply(_build_hengyi_order_key, axis=1).tolist()
    start = 0
    while start < len(order_keys):
        end = start
        while end + 1 < len(order_keys) and order_keys[end + 1] == order_keys[start]:
            end += 1

        if end > start:
            for column_name in merge_columns:
                if column_name not in column_index_map:
                    continue
                column_index = column_index_map[column_name]
                worksheet.merge_cells(
                    start_row=start + 2,
                    start_column=column_index,
                    end_row=end + 2,
                    end_column=column_index,
                )
        start = end + 1


def _save_hengyi_result_workbook(file_path: str, result_df: pd.DataFrame) -> None:
    summary_df = _build_hengyi_summary_sheet(result_df)

    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        _write_sheet(writer, "异常汇总", summary_df)

        for anomaly_type, sheet_name in HENGYI_ANOMALY_SHEET_NAMES.items():
            filtered_df = result_df[result_df["异常类型"] == anomaly_type].reset_index(drop=True)
            _write_sheet(writer, sheet_name, filtered_df)
            if anomaly_type == "数量差异待核实":
                _merge_hengyi_quantity_sheet(writer, sheet_name, filtered_df)


def _build_hengyi_result_bytes(result_df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    summary_df = _build_hengyi_summary_sheet(result_df)

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        _write_sheet(writer, "异常汇总", summary_df)

        for anomaly_type, sheet_name in HENGYI_ANOMALY_SHEET_NAMES.items():
            filtered_df = result_df[result_df["异常类型"] == anomaly_type].reset_index(drop=True)
            _write_sheet(writer, sheet_name, filtered_df)
            if anomaly_type == "数量差异待核实":
                _merge_hengyi_quantity_sheet(writer, sheet_name, filtered_df)

    return buffer.getvalue()


def _build_xinfengming_result_bytes(result_df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        result_df.to_excel(writer, index=False)
    return buffer.getvalue()


def _is_hengyi_result(result_df: pd.DataFrame, artifacts: Dict[str, Any]) -> bool:
    if artifacts.get("factory_type") == "hengyi":
        return True
    return "异常类型" in result_df.columns


def _save_result(
    *,
    result_df: pd.DataFrame,
    artifacts: Dict[str, Any],
) -> Dict[str, Any]:
    filename = _build_result_filename(result_df)
    if _is_hengyi_result(result_df, artifacts):
        download_bytes = _build_hengyi_result_bytes(result_df)
    else:
        download_bytes = _build_xinfengming_result_bytes(result_df)

    download_token = base64.b64encode(download_bytes).decode("ascii")

    return {
        "data": result_df.to_dict(orient="records"),
        "filename": filename,
        "total_count": len(result_df),
        "download_token": download_token,
        "artifacts": artifacts,
    }


def _normalize_optional_text(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _attach_jiuding_filter_company(
    normalized_df: pd.DataFrame,
    *,
    source_df: pd.DataFrame,
    plan_mapping: Dict[str, str],
) -> pd.DataFrame:
    normalized_order_column = "订单号" if "订单号" in normalized_df.columns else "单号" if "单号" in normalized_df.columns else None
    if normalized_order_column is None:
        return normalized_df

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
            normalized_order_column: source_df[order_column].map(_normalize_optional_text),
            "筛选公司": source_df[customer_column].map(_normalize_optional_text),
        }
    )
    filter_df = filter_df.dropna(subset=[normalized_order_column, "筛选公司"])
    if filter_df.empty:
        return normalized_df

    filter_df = filter_df.groupby(normalized_order_column, as_index=False).agg({"筛选公司": "first"})
    return normalized_df.merge(filter_df, on=normalized_order_column, how="left")


def _process_single_excel(
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
        normalized_df = _attach_jiuding_filter_company(
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


def _run_hengyi_comparison_sync(
    *,
    task_id: str,
    factory_files: List[Dict[str, Any]],
    jiuding_files: List[Dict[str, Any]],
) -> Dict[str, Any]:
    _update_task(task_id, status="parsing", progress=15, message="正在解析恒逸工厂数据...")

    parsed_factory_files = []
    selected_short_names: set[str] = set()
    for file_item in factory_files:
        source_df = pd.read_excel(io.BytesIO(file_item["content"]), dtype=str)
        parsed_df = parse_hengyi_factory_data(source_df, source_filename=file_item["filename"])
        selected_short_names.update(
            short_name
            for short_name in parsed_df["工厂"].dropna().tolist()
            if str(short_name).strip()
        )
        LOGGER.info(
            "hengyi_factory filename=%s columns=%s selected_factories=%s",
            file_item["filename"],
            ["过账日期", "送达方", "交货单", "车牌号", "托盘数", "工厂"],
            sorted(selected_short_names),
        )
        parsed_factory_files.append({"filename": file_item["filename"], "parsed_df": parsed_df})

    _update_task(task_id, progress=45, message="正在筛选久鼎数据...")
    parsed_jiuding_files = []
    for file_item in jiuding_files:
        source_df = pd.read_excel(io.BytesIO(file_item["content"]), dtype=str)
        parsed_df = parse_hengyi_jiuding_data(
            source_df,
            selected_factory_short_names=selected_short_names or None,
        )
        LOGGER.info(
            "hengyi_jiuding filename=%s columns=%s selected_factories=%s",
            file_item["filename"],
            ["订单日期", "出库单号", "会员名称", "客户名称", "产品类型", "实际出库数量"],
            sorted(selected_short_names),
        )
        parsed_jiuding_files.append({"filename": file_item["filename"], "parsed_df": parsed_df})

    factory_df = pd.concat(
        [item["parsed_df"] for item in parsed_factory_files],
        ignore_index=True,
    ) if parsed_factory_files else pd.DataFrame()
    jiuding_df = pd.concat(
        [item["parsed_df"] for item in parsed_jiuding_files],
        ignore_index=True,
    ) if parsed_jiuding_files else pd.DataFrame()

    _update_task(task_id, status="comparing", progress=75, message="正在汇总恒逸异常订单...")
    result_df = compare_hengyi_data(factory_df, jiuding_df)

    _update_task(task_id, progress=90, message="正在生成结果文件...")
    return _save_result(
        result_df=result_df,
        artifacts={
            "factory_type": "hengyi",
            "factory_files": [
                {
                    "filename": item["filename"],
                    "preview": "",
                    "plan": {
                        "mode": "fixed_columns",
                        "fields": ["过账日期", "送达方", "交货单", "车牌号", "托盘数", "工厂"],
                    },
                }
                for item in parsed_factory_files
            ],
            "jiuding_files": [
                {
                    "filename": item["filename"],
                    "preview": "",
                    "plan": {
                        "mode": "fixed_columns",
                        "fields": ["订单日期", "出库单号", "会员名称", "客户名称", "产品类型", "实际出库数量"],
                    },
                }
                for item in parsed_jiuding_files
            ],
        },
    )


def _run_xinfengming_comparison_sync(
    *,
    task_id: str,
    factory_files: List[Dict[str, Any]],
    jiuding_files: List[Dict[str, Any]],
    factory_type: str,
    llm_overrides: Dict[str, str],
) -> Dict[str, Any]:
    default_llm_settings = load_llm_settings()
    task_llm_settings = build_task_llm_settings(default_llm_settings, **llm_overrides)

    _update_task(task_id, status="parsing", progress=15, message="正在解析上传文件...")
    jiuding_reference_rows = build_jiuding_reference_samples([file_item["content"] for file_item in jiuding_files])

    _update_task(task_id, progress=35, message="AI 正在识别有效字段...")
    comparison_payload = compare_xinfengming_data(
        factory_files=factory_files,
        jiuding_files=jiuding_files,
        factory_type=factory_type,
        llm_settings=task_llm_settings,
        jiuding_reference_rows=jiuding_reference_rows,
    )

    _update_task(task_id, status="comparing", progress=75, message="正在汇总订单并核对差异...")
    result_df = comparison_payload["result_df"]

    _update_task(task_id, progress=90, message="正在生成结果文件...")
    return _save_result(
        result_df=result_df,
        artifacts=comparison_payload["artifacts"],
    )


def _run_comparison_sync(
    *,
    task_id: str,
    factory_files: List[Dict[str, Any]],
    jiuding_files: List[Dict[str, Any]],
    factory_type: str,
    llm_overrides: Dict[str, str],
) -> Dict[str, Any]:
    if factory_type == "hengyi":
        return _run_hengyi_comparison_sync(
            task_id=task_id,
            factory_files=factory_files,
            jiuding_files=jiuding_files,
        )

    return _run_xinfengming_comparison_sync(
        task_id=task_id,
        factory_files=factory_files,
        jiuding_files=jiuding_files,
        factory_type=factory_type,
        llm_overrides=llm_overrides,
    )


async def process_comparison(
    *,
    task_id: str,
    factory_files: List[Dict[str, Any]],
    jiuding_files: List[Dict[str, Any]],
    factory_type: str,
    llm_overrides: Dict[str, str],
) -> Dict[str, Any]:
    return await asyncio.to_thread(
        _run_comparison_sync,
        task_id=task_id,
        factory_files=factory_files,
        jiuding_files=jiuding_files,
        factory_type=factory_type,
        llm_overrides=llm_overrides,
    )


async def _run_comparison_task(
    *,
    task_id: str,
    factory_files: List[Dict[str, Any]],
    jiuding_files: List[Dict[str, Any]],
    factory_type: str,
    llm_overrides: Dict[str, str],
) -> None:
    try:
        result = await process_comparison(
            task_id=task_id,
            factory_files=factory_files,
            jiuding_files=jiuding_files,
            factory_type=factory_type,
            llm_overrides=llm_overrides,
        )
        tasks[task_id]["result"] = _clean_data(result)
        _update_task(task_id, status="completed", progress=100, message="比对完成")
    except HengyiComparisonError as exc:
        _update_task(task_id, status="failed", message=f"处理失败: {exc}")
        LOGGER.exception("task=%s failed", task_id)
    except Exception as exc:
        _update_task(task_id, status="failed", message=f"处理失败: {exc}")
        LOGGER.exception("task=%s failed", task_id)
        print(traceback.format_exc())


@router.post("/compare")
async def create_comparison(
    factory_files: List[UploadFile] = File(...),
    jiuding_files: List[UploadFile] = File(...),
    factory_type: str = Form("hengyi"),
    llm_base_url: Optional[str] = Form(None),
    llm_api_key: Optional[str] = Form(None),
    llm_model: Optional[str] = Form(None),
    llm_transport: Optional[str] = Form(None),
):
    if not factory_files:
        raise HTTPException(status_code=400, detail="工厂侧文件不能为空")
    if not jiuding_files:
        raise HTTPException(status_code=400, detail="久鼎侧文件不能为空")

    for file_item in factory_files:
        _ensure_excel(file_item.filename, "工厂侧文件")
    for file_item in jiuding_files:
        _ensure_excel(file_item.filename, "久鼎侧文件")

    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "progress": 5,
        "message": "任务已创建，等待处理...",
        "result": None,
    }

    factory_payloads = [
        {"filename": file_item.filename, "content": await file_item.read()}
        for file_item in factory_files
    ]
    jiuding_payloads = [
        {"filename": file_item.filename, "content": await file_item.read()}
        for file_item in jiuding_files
    ]

    asyncio.create_task(
        _run_comparison_task(
            task_id=task_id,
            factory_files=factory_payloads,
            jiuding_files=jiuding_payloads,
            factory_type=factory_type,
            llm_overrides={
                "base_url": llm_base_url or "",
                "api_key": llm_api_key or "",
                "model": llm_model or "",
                "transport": llm_transport or "",
            },
        )
    )

    return {"task_id": task_id, "status": "pending"}


@router.get("/compare/{task_id}/status")
async def get_task_status(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = tasks[task_id]
    return TaskStatus(
        task_id=task["task_id"],
        status=task["status"],
        progress=task["progress"],
        message=task["message"],
    )


@router.get("/compare/{task_id}/result")
async def get_task_result(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    if tasks[task_id]["status"] != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成")
    return JSONResponse(content=_clean_data(tasks[task_id]["result"]))


@router.get("/compare/{task_id}/download")
async def download_result(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    if tasks[task_id]["status"] != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成")

    filename = tasks[task_id]["result"]["filename"]
    download_token = tasks[task_id]["result"].get("download_token")
    if not download_token:
        raise HTTPException(status_code=404, detail="结果文件不存在")

    file_bytes = base64.b64decode(download_token)
    safe_ascii_filename = "download.xlsx"
    encoded_filename = quote(filename)
    content_disposition = (
        f"attachment; filename=\"{safe_ascii_filename}\"; "
        f"filename*=UTF-8''{encoded_filename}"
    )

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": content_disposition},
    )


@router.get("/factory-groups")
async def get_factory_groups() -> Dict[str, Any]:
    with FACTORY_GROUPS_CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)
