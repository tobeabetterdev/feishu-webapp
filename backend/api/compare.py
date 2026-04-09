from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import traceback
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from config.settings import build_task_llm_settings, load_llm_settings
from services.data_comparator import DataComparator
from services.document_converter import convert_excel_to_markdown
from services.field_mapping_service import build_extraction_plan
from services.normalized_extractor import normalize_records

router = APIRouter()
tasks: Dict[str, Dict[str, Any]] = {}
FACTORY_GROUPS_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "factory_groups.json"
RUNTIME_DIR = Path(__file__).resolve().parent.parent / "runtime"
RUNTIME_DIR.mkdir(exist_ok=True)
LOGGER = logging.getLogger("compare_tasks")
if not LOGGER.handlers:
    file_handler = logging.FileHandler(RUNTIME_DIR / "backend.tasks.log", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    LOGGER.addHandler(file_handler)
    LOGGER.setLevel(logging.INFO)


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


def _build_result_filename(result_df) -> str:
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


def _run_comparison_sync(
    *,
    task_id: str,
    factory_content: bytes,
    jiuding_content: bytes,
    factory_filename: str,
    jiuding_filename: str,
    factory_type: str,
    llm_overrides: Dict[str, str],
) -> Dict[str, Any]:
    default_llm_settings = load_llm_settings()
    task_llm_settings = build_task_llm_settings(default_llm_settings, **llm_overrides)

    _update_task(task_id, status="parsing", progress=15, message="正在解析上传文件...")
    factory_doc = convert_excel_to_markdown(factory_content, factory_filename)
    jiuding_doc = convert_excel_to_markdown(jiuding_content, jiuding_filename)

    _update_task(task_id, progress=35, message="AI 正在识别有效字段...")
    factory_plan = build_extraction_plan(
        file_content=factory_content,
        filename=factory_filename,
        role="factory",
        factory_type=factory_type,
        markdown=factory_doc["markdown"],
        preview=factory_doc["preview"],
        llm_settings=task_llm_settings,
    )
    jiuding_plan = build_extraction_plan(
        file_content=jiuding_content,
        filename=jiuding_filename,
        role="jiuding",
        factory_type=factory_type,
        markdown=jiuding_doc["markdown"],
        preview=jiuding_doc["preview"],
        llm_settings=task_llm_settings,
    )

    import io
    import pandas as pd

    _update_task(task_id, progress=55, message="正在标准化订单数据...")
    factory_source_df = pd.read_excel(io.BytesIO(factory_content))
    jiuding_source_df = pd.read_excel(io.BytesIO(jiuding_content))
    factory_source_df.columns = [str(column).strip() for column in factory_source_df.columns]
    jiuding_source_df.columns = [str(column).strip() for column in jiuding_source_df.columns]

    factory_df = normalize_records(factory_source_df, factory_plan.to_column_mapping())
    jiuding_df = normalize_records(jiuding_source_df, jiuding_plan.to_column_mapping())

    _update_task(task_id, status="comparing", progress=75, message="正在汇总订单并核对差异...")
    result_df = DataComparator(factory_df, jiuding_df).compare()

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
            "factory_preview": factory_doc["preview"],
            "jiuding_preview": jiuding_doc["preview"],
            "factory_plan": factory_plan.model_dump(),
            "jiuding_plan": jiuding_plan.model_dump(),
        },
    }


async def process_comparison(
    *,
    task_id: str,
    factory_content: bytes,
    jiuding_content: bytes,
    factory_filename: str,
    jiuding_filename: str,
    factory_type: str,
    llm_overrides: Dict[str, str],
) -> Dict[str, Any]:
    return await asyncio.to_thread(
        _run_comparison_sync,
        task_id=task_id,
        factory_content=factory_content,
        jiuding_content=jiuding_content,
        factory_filename=factory_filename,
        jiuding_filename=jiuding_filename,
        factory_type=factory_type,
        llm_overrides=llm_overrides,
    )


async def _run_comparison_task(
    *,
    task_id: str,
    factory_content: bytes,
    jiuding_content: bytes,
    factory_filename: str,
    jiuding_filename: str,
    factory_type: str,
    llm_overrides: Dict[str, str],
) -> None:
    try:
        result = await process_comparison(
            task_id=task_id,
            factory_content=factory_content,
            jiuding_content=jiuding_content,
            factory_filename=factory_filename,
            jiuding_filename=jiuding_filename,
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
    factory_file: UploadFile = File(...),
    jiuding_file: UploadFile = File(...),
    factory_type: str = Form("hengyi"),
    llm_base_url: Optional[str] = Form(None),
    llm_api_key: Optional[str] = Form(None),
    llm_model: Optional[str] = Form(None),
    llm_transport: Optional[str] = Form(None),
):
    _ensure_excel(factory_file.filename, "工厂侧文件")
    _ensure_excel(jiuding_file.filename, "久鼎侧文件")

    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "progress": 5,
        "message": "任务已创建，等待处理...",
        "result": None,
    }

    factory_content = await factory_file.read()
    jiuding_content = await jiuding_file.read()

    asyncio.create_task(
        _run_comparison_task(
            task_id=task_id,
            factory_content=factory_content,
            jiuding_content=jiuding_content,
            factory_filename=factory_file.filename,
            jiuding_filename=jiuding_file.filename,
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
