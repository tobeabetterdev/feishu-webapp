import asyncio
import base64
import io
import math
from types import SimpleNamespace

import pandas as pd
from fastapi.testclient import TestClient

from api import compare as compare_api
from main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "API" in response.json()["message"]


def test_get_factory_groups():
    response = client.get("/api/factory-groups")
    assert response.status_code == 200
    data = response.json()
    assert "hengyi" in data
    assert "xinfengming" in data


def test_compare_returns_task_id_immediately_and_runs_in_background(monkeypatch):
    observed = {"started": False, "finished": False, "factory_count": 0, "jiuding_count": 0}

    async def fake_process_comparison(
        *,
        task_id,
        factory_files,
        jiuding_files,
        factory_type,
        llm_overrides,
    ):
        observed["started"] = True
        observed["factory_count"] = len(factory_files)
        observed["jiuding_count"] = len(jiuding_files)
        await asyncio.sleep(0.05)
        observed["finished"] = True
        return {
            "data": [],
            "filename": "mock.xlsx",
            "total_count": 0,
            "download_token": "bW9jaw==",
            "artifacts": {},
        }

    monkeypatch.setattr(compare_api, "process_comparison", fake_process_comparison)

    response = client.post(
        "/api/compare",
        data={
            "factory_type": "hengyi",
            "llm_base_url": "https://example.com/v1",
            "llm_api_key": "test-key",
            "llm_model": "test-model",
            "llm_transport": "responses",
        },
        files=[
            (
                "factory_files",
                (
                    "factory-1.xlsx",
                    b"factory-bytes-1",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            ),
            (
                "factory_files",
                (
                    "factory-2.xlsx",
                    b"factory-bytes-2",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            ),
            (
                "jiuding_files",
                (
                    "jiuding-1.xlsx",
                    b"jiuding-bytes-1",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            ),
        ],
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "pending"
    assert "task_id" in payload
    assert observed["started"] is True
    assert observed["factory_count"] == 2
    assert observed["jiuding_count"] == 1

    status_response = client.get(f"/api/compare/{payload['task_id']}/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] in {"pending", "parsing", "completed"}


def test_get_task_result_replaces_nan_with_null():
    task_id = "nan-result-task"
    compare_api.tasks[task_id] = {
        "task_id": task_id,
        "status": "completed",
        "progress": 100,
        "message": "比对完成",
        "result": {
            "data": [
                {
                    "日期": "2026/4/9",
                    "订单号": "A-001",
                    "工厂": None,
                    "型号": None,
                    "公司": None,
                    "工厂量": 1,
                    "久鼎量": 2,
                    "差量": math.nan,
                }
            ],
            "filename": "mock.xlsx",
            "total_count": 1,
            "download_token": "bW9jaw==",
        },
    }

    response = client.get(f"/api/compare/{task_id}/result")

    assert response.status_code == 200
    assert response.json()["data"][0]["差量"] is None


def test_run_comparison_sync_uses_xinfengming_service_and_omits_missing_date(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    compare_api.tasks["missing-date-task"] = {
        "task_id": "missing-date-task",
        "status": "pending",
        "progress": 0,
        "message": "",
        "result": None,
    }
    monkeypatch.setattr(compare_api, "load_llm_settings", lambda: SimpleNamespace())
    monkeypatch.setattr(compare_api, "build_task_llm_settings", lambda settings, **kwargs: settings)
    monkeypatch.setattr(compare_api, "build_jiuding_reference_samples", lambda file_contents: [{"订单号": "A-001"}])

    observed = {}

    def fake_compare_xinfengming_data(**kwargs):
        observed["kwargs"] = kwargs
        return {
            "result_df": pd.DataFrame([{"日期": None, "订单号": "A-001", "工厂": "江苏", "差量": 1}]),
            "artifacts": {
                "factory_files": [
                    {
                        "filename": "factory.xlsx",
                        "preview": "mock",
                        "plan": {"fields": [{"name": "order_no"}, {"name": "company"}]},
                    }
                ],
                "jiuding_files": [],
            },
        }

    monkeypatch.setattr(compare_api, "compare_xinfengming_data", fake_compare_xinfengming_data)

    result = compare_api._run_comparison_sync(
        task_id="missing-date-task",
        factory_files=[{"filename": "factory.xlsx", "content": b"factory"}],
        jiuding_files=[{"filename": "jiuding.xlsx", "content": b"jiuding"}],
        factory_type="xinfengming",
        llm_overrides={},
    )

    assert result["filename"].startswith("订单核对_")
    assert result["filename"].count("_") == 1
    assert observed["kwargs"]["factory_type"] == "xinfengming"
    assert observed["kwargs"]["jiuding_reference_rows"][0]["订单号"] == "A-001"
    assert result["artifacts"]["factory_files"][0]["plan"]["fields"][1]["name"] == "company"


def test_save_result_writes_hengyi_multi_sheet_workbook(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    result_df = pd.DataFrame(
        [
            {
                "异常类型": "工厂侧待补录",
                "过账日期(工厂)": "2026/4/8",
                "交货单(工厂)": "F001",
                "工厂(工厂)": "恒逸高新(3100)",
                "送达方(工厂)": "杭州银瑞化纤有限公司",
                "车牌号(工厂)": "浙A12345",
                "型号(工厂)": "FDY",
                "托盘数(工厂)": 12,
                "订单日期(久鼎)": None,
                "出库单号(久鼎)": None,
                "客户名称(久鼎)": None,
                "会员名称(久鼎)": None,
                "产品类型(久鼎)": None,
                "实际出库数量(久鼎)": None,
                "差量": 12,
            },
            {
                "异常类型": "久鼎侧待补录",
                "过账日期(工厂)": None,
                "交货单(工厂)": None,
                "工厂(工厂)": None,
                "送达方(工厂)": None,
                "车牌号(工厂)": None,
                "型号(工厂)": None,
                "托盘数(工厂)": None,
                "订单日期(久鼎)": "2026/4/8",
                "出库单号(久鼎)": "J001",
                "客户名称(久鼎)": "浙江恒逸高新材料有限公司",
                "会员名称(久鼎)": "杭州银瑞化纤有限公司",
                "产品类型(久鼎)": "FDY",
                "实际出库数量(久鼎)": 9,
                "差量": -9,
            },
            {
                "异常类型": "数量差异待核实",
                "过账日期(工厂)": "2026/4/8",
                "交货单(工厂)": "M001",
                "工厂(工厂)": "恒逸高新(3100)",
                "送达方(工厂)": "杭州银瑞化纤有限公司",
                "车牌号(工厂)": "浙A99999",
                "型号(工厂)": "FDY",
                "托盘数(工厂)": 10,
                "订单日期(久鼎)": "2026/4/8",
                "出库单号(久鼎)": "M001",
                "客户名称(久鼎)": "浙江恒逸高新材料有限公司",
                "会员名称(久鼎)": "杭州银瑞化纤有限公司",
                "产品类型(久鼎)": "FDY",
                "实际出库数量(久鼎)": 15,
                "差量": -5,
            },
        ]
    )

    saved = compare_api._save_result(result_df=result_df, artifacts={"factory_type": "hengyi"})

    workbook = pd.ExcelFile(io.BytesIO(base64.b64decode(saved["download_token"])))

    assert workbook.sheet_names == ["异常汇总", "工厂侧待补录", "久鼎侧待补录", "数量差异待核实"]

    summary_df = pd.read_excel(io.BytesIO(base64.b64decode(saved["download_token"])), sheet_name="异常汇总")
    assert "异常类型" in summary_df.columns
    assert summary_df["异常类型"].tolist() == ["工厂侧待补录", "久鼎侧待补录", "数量差异待核实"]
