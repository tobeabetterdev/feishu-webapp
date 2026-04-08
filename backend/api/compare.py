from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Any
import uuid
import os
import json
from datetime import datetime
import pandas as pd

from services.excel_parser import ExcelParser
from services.data_comparator import DataComparator

router = APIRouter()

# 任务存储（生产环境应使用数据库）
tasks: Dict[str, Dict[str, Any]] = {}

class TaskStatus(BaseModel):
    task_id: str
    status: str  # "pending", "parsing", "comparing", "completed", "failed"
    progress: int  # 0-100
    message: str

@router.post("/compare")
async def create_comparison(
    factory_file: UploadFile = File(...),
    jiuding_file: UploadFile = File(...),
    factory_type: str = Form("hengyi")
):
    """创建对比任务"""
    # 验证文件类型
    if not factory_file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="工厂侧文件必须是Excel格式")
    if not jiuding_file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="久鼎侧文件必须是Excel格式")

    # 创建任务ID
    task_id = str(uuid.uuid4())

    # 初始化任务状态
    tasks[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "progress": 0,
        "message": "任务已创建",
        "result": None
    }

    # 读取文件内容
    factory_content = await factory_file.read()
    jiuding_content = await jiuding_file.read()

    # 更新状态：解析中
    tasks[task_id]["status"] = "parsing"
    tasks[task_id]["progress"] = 20
    tasks[task_id]["message"] = "正在解析Excel文件..."

    try:
        # 解析Excel文件
        factory_df = ExcelParser.parse_factory(factory_content, factory_type)
        jiuding_df = ExcelParser.parse_jiuding(jiuding_content)

        # 更新状态：对比中
        tasks[task_id]["status"] = "comparing"
        tasks[task_id]["progress"] = 60
        tasks[task_id]["message"] = "正在对比数据..."

        # 执行对比
        comparator = DataComparator(factory_df, jiuding_df, factory_type)
        result_df = comparator.compare()

        # 生成结果文件
        output_dir = "outputs"
        os.makedirs(output_dir, exist_ok=True)

        # 获取久鼎侧日期作为文件名
        jiuding_date = result_df['日期'].iloc[0] if len(result_df) > 0 else datetime.now().strftime("%Y-%m-%d")
        if isinstance(jiuding_date, pd.Timestamp):
            jiuding_date = jiuding_date.strftime("%Y-%m-%d")

        unique_id = str(uuid.uuid4())[:8]
        filename = f"订单核对_{jiuding_date}_{unique_id}.xlsx"
        output_path = os.path.join(output_dir, filename)

        # 保存结果
        result_df.to_excel(output_path, index=False)

        # 更新状态：完成
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["progress"] = 100
        tasks[task_id]["message"] = "对比完成"
        tasks[task_id]["result"] = {
            "data": result_df.to_dict(orient="records"),
            "file_path": output_path,
            "filename": filename,
            "total_count": len(result_df)
        }

        return {"task_id": task_id, "status": "completed"}

    except Exception as e:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["message"] = f"处理失败: {str(e)}"
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/compare/{task_id}/status")
async def get_task_status(task_id: str):
    """获取任务状态"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = tasks[task_id]
    return TaskStatus(
        task_id=task["task_id"],
        status=task["status"],
        progress=task["progress"],
        message=task["message"]
    )

@router.get("/compare/{task_id}/result")
async def get_task_result(task_id: str):
    """获取对比结果"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = tasks[task_id]
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成")

    return task["result"]

@router.get("/compare/{task_id}/download")
async def download_result(task_id: str):
    """下载结果文件"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = tasks[task_id]
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成")

    file_path = task["result"]["file_path"]
    filename = task["result"]["filename"]

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="结果文件不存在")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@router.get("/factory-groups")
async def get_factory_groups() -> Dict[str, Any]:
    """获取工厂集团配置"""
    return {
        "hengyi": {
            "name": "恒逸",
            "customers": [
                "浙江恒逸高新材料有限公司",
                "浙江双兔新材料有限公司",
                "海宁恒逸新材料有限公司"
            ]
        },
        "xinfengming": {
            "name": "新凤鸣",
            "customers": [
                "桐乡市中鸿新材料有限公司",
                "湖州市中磊化纤有限公司",
                "湖州市中跃化纤有限公司",
                "桐乡市中益化纤有限公司",
                "新凤鸣集团湖州中石科技有限公司",
                "桐乡中欣化纤有限公司",
                "桐乡市中维化纤有限公司",
                "新凤鸣集团股份有限公司",
                "浙江独山能源有限公司",
                "新凤鸣江苏新拓新材有限公司"
            ]
        }
    }
