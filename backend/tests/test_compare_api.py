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


def test_download_result_supports_unicode_filename():
    task_id = "unicode-download-task"
    compare_api.tasks[task_id] = {
        "task_id": task_id,
        "status": "completed",
        "progress": 100,
        "message": "比对完成",
        "result": {
            "data": [],
            "filename": "订单核对_2026-4-11.xlsx",
            "total_count": 0,
            "download_token": base64.b64encode(b"mock-binary").decode("ascii"),
        },
    }

    response = client.get(f"/api/compare/{task_id}/download")

    assert response.status_code == 200
    assert response.content == b"mock-binary"
    assert "attachment;" in response.headers["content-disposition"]
    assert "filename*=UTF-8''" in response.headers["content-disposition"]


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


def test_save_result_writes_hengyi_summary_and_detail_workbook(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    result_df = pd.DataFrame(
        [
            {
                "异常类型": "久鼎缺单",
                "订单号": "F001",
                "工厂": "恒逸高新(3100)",
                "订单日期": "2026/4/8",
                "送达方": "杭州银瑞化纤有限公司",
                "工厂交货单": "F001",
                "工厂车牌号": "浙A12345",
                "工厂物料组": "FDY",
                "工厂交货数量": 12,
                "工厂托盘数": 12,
                "工厂业务员": None,
                "工厂过账日期": "2026/4/8",
                "会员名称": None,
                "久鼎出库单号": None,
                "久鼎产品类型": None,
                "久鼎客户名称": None,
                "久鼎子公司名称": None,
                "久鼎出库数量": None,
                "久鼎订单日期": None,
                "出库数量差异": 12,
            },
            {
                "异常类型": "工厂缺单",
                "订单号": "J001",
                "工厂": "恒逸高新",
                "订单日期": "2026/4/8",
                "送达方": None,
                "工厂交货单": None,
                "工厂车牌号": None,
                "工厂物料组": None,
                "工厂交货数量": None,
                "工厂托盘数": None,
                "工厂业务员": None,
                "工厂过账日期": None,
                "会员名称": "杭州银瑞化纤有限公司",
                "久鼎出库单号": "J001",
                "久鼎产品类型": "FDY",
                "久鼎客户名称": "恒逸高新",
                "久鼎子公司名称": "浙江恒逸高新材料有限公司",
                "久鼎出库数量": 9,
                "久鼎订单日期": "2026/4/8",
                "出库数量差异": -9,
            },
            {
                "异常类型": "数量差异",
                "订单号": "M001",
                "工厂": "恒逸高新(3100)",
                "订单日期": "2026/4/8",
                "送达方": "杭州银瑞化纤有限公司",
                "工厂交货单": "M001",
                "工厂车牌号": "浙A99999",
                "工厂物料组": "FDY",
                "工厂交货数量": 10,
                "工厂托盘数": 10,
                "工厂业务员": None,
                "工厂过账日期": "2026/4/8",
                "会员名称": "杭州银瑞化纤有限公司",
                "久鼎出库单号": "M001",
                "久鼎产品类型": "FDY",
                "久鼎客户名称": "恒逸高新",
                "久鼎子公司名称": "浙江恒逸高新材料有限公司",
                "久鼎出库数量": 15,
                "久鼎订单日期": "2026/4/8",
                "出库数量差异": -5,
            },
        ]
    )

    saved = compare_api._save_result(result_df=result_df, artifacts={"factory_type": "hengyi"})

    workbook = pd.ExcelFile(io.BytesIO(base64.b64decode(saved["download_token"])))

    assert workbook.sheet_names == ["异常汇总", "异常详情"]

    summary_df = pd.read_excel(io.BytesIO(base64.b64decode(saved["download_token"])), sheet_name="异常汇总")
    assert "异常类型" in summary_df.columns
    assert summary_df["异常类型"].tolist() == ["工厂缺单", "久鼎缺单", "数量差异"]

    detail_df = pd.read_excel(io.BytesIO(base64.b64decode(saved["download_token"])), sheet_name="异常详情", header=1)
    assert "工厂交货单" in detail_df.columns
    assert "久鼎出库单号" in detail_df.columns
