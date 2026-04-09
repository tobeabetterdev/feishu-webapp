import asyncio
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
            "file_path": "outputs/mock.xlsx",
            "filename": "mock.xlsx",
            "total_count": 0,
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
                    "单号": "A-001",
                    "工厂": None,
                    "型号": None,
                    "公司": None,
                    "客户出库数": 1,
                    "久鼎出库数": 2,
                    "待处理数量": math.nan,
                }
            ],
            "file_path": "outputs/mock.xlsx",
            "filename": "mock.xlsx",
            "total_count": 1,
        },
    }

    response = client.get(f"/api/compare/{task_id}/result")

    assert response.status_code == 200
    assert response.json()["data"][0]["待处理数量"] is None


def test_run_comparison_sync_omits_filename_date_when_missing(monkeypatch, tmp_path):
    class StubPlan:
        def to_column_mapping(self):
            return {"order_no": "单号", "company": "公司", "quantity": "数量"}

        def model_dump(self):
            return {"fields": [{"name": "order_no"}, {"name": "company"}, {"name": "quantity"}]}

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
    monkeypatch.setattr(
        compare_api,
        "build_jiuding_reference_samples",
        lambda file_contents: [
            {
                "出库单号": "A-001",
                "会员名称": "浙江恒逸高新材料有限公司",
                "实际出库数量": "1",
                "产品类型": "POY",
            }
        ],
    )
    monkeypatch.setattr(
        compare_api,
        "convert_excel_to_markdown",
        lambda content, filename: {"markdown": "mock", "preview": "mock"},
    )
    observed = {}

    def fake_build_extraction_plan(**kwargs):
        observed.setdefault("calls", []).append(kwargs)
        return StubPlan()

    monkeypatch.setattr(compare_api, "build_extraction_plan", fake_build_extraction_plan)
    monkeypatch.setattr(compare_api, "normalize_records", lambda df, mapping: df)
    monkeypatch.setattr(
        pd,
        "read_excel",
        lambda *args, **kwargs: pd.DataFrame([{"单号": "A-001", "公司": "浙江恒逸高新材料有限公司", "数量": 1}]),
    )
    monkeypatch.setattr(
        compare_api.DataComparator,
        "compare",
        lambda self: pd.DataFrame([{"日期": None, "单号": "A-001", "工厂": "恒逸高新", "待处理数量": 1}]),
    )

    result = compare_api._run_comparison_sync(
        task_id="missing-date-task",
        factory_files=[{"filename": "factory.xlsx", "content": b"factory"}],
        jiuding_files=[{"filename": "jiuding.xlsx", "content": b"jiuding"}],
        factory_type="hengyi",
        llm_overrides={},
    )

    assert result["filename"].startswith("订单核对_")
    assert "2026-" not in result["filename"]
    assert result["filename"].count("_") == 1
    assert observed["calls"][0]["role"] == "factory"
    assert observed["calls"][0]["jiuding_reference_rows"][0]["会员名称"] == "浙江恒逸高新材料有限公司"
    assert result["artifacts"]["factory_files"][0]["plan"]["fields"][1]["name"] == "company"
