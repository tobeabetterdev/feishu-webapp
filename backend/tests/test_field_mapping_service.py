from io import BytesIO

import pandas as pd

from config.settings import LLMSettings
from services.field_mapping_service import _normalize_plan_payload, build_extraction_plan


def test_normalize_plan_payload_accepts_model_variant_field_names():
    payload = {
        "source_sheet": "Sheet1",
        "header_row_index": 1,
        "data_start_row_index": 2,
        "skip_keywords": ["合计"],
        "fields": {
            "date": {"source_column": "交货创建日期", "output_format": "yyyy/m/d"},
            "order_no": {"source_column": "交货单号", "data_type": "string"},
            "factory": {"source_column": "销售组织描述"},
            "model": {"source_column": "物料组描述"},
            "company": {"source_column": "客户名称"},
            "quantity": {"source_column": "件数", "data_type": "integer"},
        },
        "confidence": 0.91,
        "notes": "Mapped all required fields.",
    }

    normalized = _normalize_plan_payload(payload)

    assert normalized["notes"] == ["Mapped all required fields."]
    assert normalized["fields"]["date"]["column"] == "交货创建日期"
    assert normalized["fields"]["date"]["type"] == "date"
    assert normalized["fields"]["factory"]["type"] == "string"
    assert normalized["fields"]["quantity"]["type"] == "integer"


def test_build_extraction_plan_fills_missing_required_fields_from_heuristics(monkeypatch):
    source_df = pd.DataFrame(
        [
            {
                "交货日期": "2026-04-05",
                "交货单号": "A-001",
                "送达方": "江苏",
                "物料组描述": "POY",
                "客户名称": "测试客户",
                "交货数量": 12,
            }
        ]
    )
    buffer = BytesIO()
    source_df.to_excel(buffer, index=False)

    class FakeLLMClient:
        def __init__(self, settings):
            self.settings = settings

        def generate_json(self, system_prompt, user_prompt):
            return {
                "source_sheet": "Sheet1",
                "header_row_index": 1,
                "data_start_row_index": 2,
                "skip_keywords": [],
                "fields": {
                    "order_no": {"column": "交货单号", "type": "string"},
                    "factory": {"column": "送达方", "type": "string"},
                    "model": {"column": "物料组描述", "type": "string"},
                    "company": {"column": "客户名称", "type": "string"},
                    "quantity": {"column": "交货数量", "type": "integer"},
                },
                "confidence": 0.72,
                "notes": ["date omitted by model"],
            }

    monkeypatch.setattr("services.field_mapping_service.LLMClient", FakeLLMClient)

    plan = build_extraction_plan(
        file_content=buffer.getvalue(),
        filename="factory.xlsx",
        role="factory",
        factory_type="hengyi",
        markdown="",
        preview="",
        llm_settings=LLMSettings(
            api_key="test-key",
            base_url="https://example.com/v1",
            model="test-model",
            transport="responses",
        ),
    )

    assert plan.fields["date"].column == "交货日期"
    assert plan.fields["date"].type == "date"
    assert plan.fields["date"].output_format == "yyyy/m/d"


def test_build_extraction_plan_allows_factory_plan_with_only_order_and_quantity(monkeypatch):
    source_df = pd.DataFrame(
        [
            {
                "交货单号": "A-001",
                "售达方": "江苏",
                "托盘类型": "塑托",
                "久鼎托盘_x000D_\n数量": 12,
            }
        ]
    )
    buffer = BytesIO()
    source_df.to_excel(buffer, index=False)

    class FakeLLMClient:
        def __init__(self, settings):
            self.settings = settings

        def generate_json(self, system_prompt, user_prompt):
            return {
                "source_sheet": "Sheet1",
                "header_row_index": 1,
                "data_start_row_index": 2,
                "skip_keywords": [],
                "fields": {
                    "order_no": {"column": "交货单号", "type": "string"},
                    "quantity": {"column": "久鼎托盘_x000D_\n数量", "type": "integer"},
                },
                "confidence": 0.81,
                "notes": ["factory file only contains order and quantity"],
            }

    monkeypatch.setattr("services.field_mapping_service.LLMClient", FakeLLMClient)

    plan = build_extraction_plan(
        file_content=buffer.getvalue(),
        filename="factory.xlsx",
        role="factory",
        factory_type="hengyi",
        markdown="",
        preview="",
        llm_settings=LLMSettings(
            api_key="test-key",
            base_url="https://example.com/v1",
            model="test-model",
            transport="responses",
        ),
    )

    assert set(plan.fields.keys()) == {"order_no", "quantity"}
