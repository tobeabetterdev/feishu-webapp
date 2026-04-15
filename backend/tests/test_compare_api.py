import asyncio
import base64
import io
import math
from types import SimpleNamespace

import pandas as pd
from openpyxl import Workbook
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


def test_read_excel_with_fallback_handles_openpyxl_filter_error(monkeypatch):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["交货单", "托盘数"])
    sheet.append(["A100", 8])
    buffer = io.BytesIO()
    workbook.save(buffer)

    real_read_excel = compare_api.pd.read_excel

    def fake_read_excel(*args, **kwargs):
        raise ValueError("Value must be either numerical or a string containing a wildcard")

    monkeypatch.setattr(compare_api.pd, "read_excel", fake_read_excel)

    result = compare_api._read_excel_with_fallback(buffer.getvalue())

    monkeypatch.setattr(compare_api.pd, "read_excel", real_read_excel)

    assert result.columns.tolist() == ["交货单", "托盘数"]
    assert result.iloc[0]["交货单"] == "A100"
    assert str(result.iloc[0]["托盘数"]) == "8"


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
            "filename": "新凤鸣订单核对_2026-4-11.xlsx",
            "total_count": 0,
            "download_token": base64.b64encode(b"mock-binary").decode("ascii"),
        },
    }

    response = client.get(f"/api/compare/{task_id}/download")

    assert response.status_code == 200
    assert response.content == b"mock-binary"
    assert "attachment;" in response.headers["content-disposition"]
    assert "filename*=UTF-8''" in response.headers["content-disposition"]


def test_build_result_filename_uses_date_only_when_source_contains_time():
    result_df = pd.DataFrame([{"日期": "2026/4/8 21:36:04"}])

    filename = compare_api._build_result_filename(result_df, factory_type="hengyi")

    assert filename.startswith("恒逸订单核对_2026-4-8_")
    assert ":" not in filename


def test_run_comparison_sync_uses_xinfengming_service_and_omits_missing_date(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    compare_api.tasks["missing-date-task"] = {
        "task_id": "missing-date-task",
        "status": "pending",
        "progress": 0,
        "message": "",
        "result": None,
    }
    assert not hasattr(compare_api, "load_llm_settings")
    assert not hasattr(compare_api, "build_task_llm_settings")
    assert not hasattr(compare_api, "build_jiuding_reference_samples")

    observed = {}

    def fake_compare_xinfengming_data(**kwargs):
        observed["kwargs"] = kwargs
        return {
            "result_df": pd.DataFrame([{"日期": None, "订单号": "A-001", "工厂": "江苏", "差量": 1}]),
            "artifacts": {
                "factory_type": "xinfengming",
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

    assert result["filename"].startswith("新凤鸣订单核对_")
    assert result["filename"].count("_") == 1
    assert observed["kwargs"]["factory_type"] == "xinfengming"
    assert "llm_settings" not in observed["kwargs"]
    assert "jiuding_reference_rows" not in observed["kwargs"]
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
                "交货单": "F001",
                "车牌号": "浙A12345",
                "物料组": "FDY",
                "交货数量": 12,
                "托盘数": 12,
                "业务员": None,
                "过账日期": "2026/4/8",
                "会员名称": None,
                "出库单号": None,
                "产品类型": None,
                "客户名称": None,
                "子公司名称": None,
                "出库数量": None,
                "订单日期2": None,
                "出库数量差异": 12,
            },
            {
                "异常类型": "工厂缺单",
                "订单号": "J001",
                "工厂": "恒逸高新",
                "订单日期": "2026/4/8",
                "送达方": None,
                "交货单": None,
                "车牌号": None,
                "物料组": None,
                "交货数量": None,
                "托盘数": None,
                "业务员": None,
                "过账日期": None,
                "会员名称": "杭州银瑞化纤有限公司",
                "出库单号": "J001",
                "产品类型": "FDY",
                "客户名称": "恒逸高新",
                "子公司名称": "浙江恒逸高新材料有限公司",
                "出库数量": 9,
                "订单日期2": "2026/4/8",
                "出库数量差异": -9,
            },
            {
                "异常类型": "数量差异",
                "订单号": "M001",
                "工厂": "恒逸高新(3100)",
                "订单日期": "2026/4/8",
                "送达方": "杭州银瑞化纤有限公司",
                "交货单": "M001",
                "车牌号": "浙A99999",
                "物料组": "FDY",
                "交货数量": 10,
                "托盘数": 10,
                "业务员": None,
                "过账日期": "2026/4/8",
                "会员名称": "杭州银瑞化纤有限公司",
                "出库单号": "M001",
                "产品类型": "FDY",
                "客户名称": "恒逸高新",
                "子公司名称": "浙江恒逸高新材料有限公司",
                "出库数量": 15,
                "订单日期2": "2026/4/8",
                "出库数量差异": -5,
            },
        ]
    )

    saved = compare_api._save_result(result_df=result_df, artifacts={"factory_type": "hengyi"})

    assert saved["filename"].startswith("恒逸订单核对_")

    workbook = pd.ExcelFile(io.BytesIO(base64.b64decode(saved["download_token"])))

    assert workbook.sheet_names == ["异常汇总", "异常详情"]

    summary_df = pd.read_excel(io.BytesIO(base64.b64decode(saved["download_token"])), sheet_name="异常汇总")
    assert "异常类型" in summary_df.columns
    assert summary_df["异常类型"].tolist() == ["工厂缺单", "久鼎缺单", "数量差异"]

    detail_df = pd.read_excel(io.BytesIO(base64.b64decode(saved["download_token"])), sheet_name="异常详情", header=1)
    assert "交货单" in detail_df.columns
    assert "出库单号" in detail_df.columns


def test_save_result_writes_xinfengming_summary_and_detail_workbook(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    result_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/9",
                "单号": "8006349234",
                "工厂": "中跃",
                "型号": "POY",
                "公司": "绍兴柯桥炯炯纺织有限公司",
                "客户出库数": 33,
                "久鼎出库数": 30,
                "待处理数量": 3,
            }
        ]
    )
    artifacts = {
        "factory_type": "xinfengming",
        "factory_records": [
            {
                "单号": "8006349234",
                "交货单号": "8006349234",
                "交货创建日期": "2026/4/9",
                "销售组织描述": "中跃化纤",
                "客户名称": "绍兴柯桥炯炯纺织有限公司",
                "业务员": "沈祥强",
                "车牌号": "赣CDL713",
                "物料组描述": "POY",
                "件数": 33,
                "交货单类型": "标准交货单",
                "包装批号": "NXP0720",
            }
        ],
        "jiuding_records": [
            {
                "单号": "8006349234",
                "出库单号": "8006349234",
                "订单日期": "2026/4/9",
                "客户名称": "湖州市中跃化纤有限公司",
                "会员名称": "绍兴柯桥炯炯纺织有限公司",
                "产品类型": "POY",
                "实际出库数量": 30,
                "子公司名称": None,
                "订单状态": "订单完成",
                "送货方式": "自提",
            }
        ],
    }

    saved = compare_api._save_result(result_df=result_df, artifacts=artifacts)

    assert saved["filename"].startswith("新凤鸣订单核对_")

    workbook = pd.ExcelFile(io.BytesIO(base64.b64decode(saved["download_token"])))
    assert workbook.sheet_names == ["异常汇总", "异常详情"]

    summary_df = pd.read_excel(io.BytesIO(base64.b64decode(saved["download_token"])), sheet_name="异常汇总")
    assert summary_df.columns.tolist() == ["日期", "单号", "工厂", "型号", "公司", "客户出库数", "久鼎出库数", "待处理数量"]

    detail_df = pd.read_excel(io.BytesIO(base64.b64decode(saved["download_token"])), sheet_name="异常详情", header=1)
    assert detail_df.columns.tolist()[0] == "异常类型"
    assert "交货单号" in detail_df.columns
    assert "汇总单号" in detail_df.columns
    assert "工厂" in detail_df.columns
    assert "销售组织描述" in detail_df.columns
    assert "出库单号" in detail_df.columns
    assert "客户名称2" in detail_df.columns
    assert "会员名称" in detail_df.columns
    assert detail_df.columns.tolist()[-1] == "差异数量"
    assert detail_df.iloc[0]["异常类型"] == "数量差异"
    assert str(detail_df.iloc[0]["汇总单号"]) == "8006349234"
