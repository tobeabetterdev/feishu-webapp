from __future__ import annotations

import asyncio
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

import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from config.settings import build_task_llm_settings, load_llm_settings
from services.data_comparator import DataComparator
from services.document_converter import convert_excel_to_markdown
from services.field_mapping_service import build_extraction_plan, build_jiuding_reference_samples
from services.normalized_extractor import attach_record_context, normalize_records

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
    if not result_df.empty and "日期" in result_df.columns:
        first_date = result_df["日期"].iloc[0]
        if first_date is not None and str(first_date).strip():
            date_for_name = str(first_date).strip().replace("/", "-")

    filename_parts = ["订单核对"]
    if date_for_name:
        filename_parts.append(date_for_name)
    filename_parts.append(str(uuid.uuid4())[:8])
    return "_".join(filename_parts) + ".xlsx"


def _merge_normalized_frames(frames: List[pd.DataFrame]) -> pd.DataFrame:
    if not frames:
        return pd.DataFrame(columns=["日期", "订单号", "工厂", "型号", "公司", "数量"])
    merged = pd.concat(frames, ignore_index=True)
    return merged.reset_index(drop=True)


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
            "单号": source_df[order_column].map(_normalize_optional_text),
            "筛选公司": source_df[customer_column].map(_normalize_optional_text),
        }
    )
    filter_df = filter_df.dropna(subset=["单号", "筛选公司"])
    if filter_df.empty:
        return normalized_df

    filter_df = filter_df.groupby("单号", as_index=False).agg({"筛选公司": "first"})
    return normalized_df.merge(filter_df, on="单号", how="left")


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
        source_hint=source_df[source_hint].astype(str).str.strip().iloc[0] if source_hint and source_hint in source_df.columns and not source_df.empty else None,
    )

    LOGGER.info(
        "filename=%s role=%s extracted_columns=%s",
        filename,
        role,
        plan_mapping,
    )

    return {
        "normalized_df": normalized_df,
        "preview": document["preview"],
        "plan": plan.model_dump(),
        "filename": filename,
    }


def _run_comparison_sync(
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
    factory_processed = [
        _process_single_excel(
            content=file_item["content"],
            filename=file_item["filename"],
            role="factory",
            factory_type=factory_type,
            llm_settings=task_llm_settings,
            jiuding_reference_rows=jiuding_reference_rows,
        )
        for file_item in factory_files
    ]
    jiuding_processed = [
        _process_single_excel(
            content=file_item["content"],
            filename=file_item["filename"],
            role="jiuding",
            factory_type=factory_type,
            llm_settings=task_llm_settings,
            jiuding_reference_rows=None,
        )
        for file_item in jiuding_files
    ]

    _update_task(task_id, progress=55, message="正在标准化订单数据...")
    factory_df = _merge_normalized_frames([item["normalized_df"] for item in factory_processed])
    jiuding_df = _merge_normalized_frames([item["normalized_df"] for item in jiuding_processed])

    _update_task(task_id, status="comparing", progress=75, message="正在汇总订单并核对差异...")
    result_df = DataComparator(factory_df, jiuding_df, factory_type).compare()

    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)

    _update_task(task_id, progress=90, message="正在生成结果文件...")
    filename = _build_result_filename(result_df)
    file_path = os.path.join(output_dir, filename)
    result_df.to_excel(file_path, index=False)

    return {
        "data": result_df.to_dict(orient="records"),
        "file_path": file_path,
        "filename": filename,
        "total_count": len(result_df),
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

    file_path = tasks[task_id]["result"]["file_path"]
    filename = tasks[task_id]["result"]["filename"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="结果文件不存在")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.get("/factory-groups")
async def get_factory_groups() -> Dict[str, Any]:
    with FACTORY_GROUPS_CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)
