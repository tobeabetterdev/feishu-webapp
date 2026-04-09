from io import BytesIO

import pandas as pd

from config.settings import LLMSettings
from services.field_mapping_service import _normalize_plan_payload, build_extraction_plan


def test_normalize_plan_payload_accepts_string_field_payloads():
    payload = {
        "source_sheet": "Sheet1",
        "header_row_index": 0,
        "data_start_row_index": 1,
        "skip_keywords": [],
        "fields": {
            "order_no": "交货单号",
            "company": "售达方",
            "model": "物料组",
            "quantity": "Unnamed: 5",
            "date": "过账日期",
        },
        "confidence": 0.95,
        "notes": "string payload fields",
    }

    normalized = _normalize_plan_payload(payload)

    assert normalized["fields"]["order_no"]["column"] == "交货单号"
    assert normalized["fields"]["company"]["column"] == "售达方"
    assert normalized["fields"]["model"]["column"] == "物料组"
    assert normalized["fields"]["quantity"]["column"] == "Unnamed: 5"
    assert normalized["fields"]["quantity"]["type"] == "integer"
    assert normalized["fields"]["date"]["column"] == "过账日期"


def test_build_extraction_plan_keeps_string_quantity_mapping_from_llm(monkeypatch):
    source_df = pd.DataFrame(
        [
            {
                "交货单号": "A-002",
                "售达方": "海宁恒逸新材料有限公司",
                "物料组": "FDY",
                "过账日期": "2026/4/10",
                "Unnamed: 5": 16,
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
                "header_row_index": 0,
                "data_start_row_index": 1,
                "skip_keywords": [],
                "fields": {
                    "order_no": "交货单号",
                    "company": "售达方",
                    "model": "物料组",
                    "quantity": "Unnamed: 5",
                    "date": "过账日期",
                },
                "confidence": 0.95,
                "notes": "string payload fields",
            }

    monkeypatch.setattr("services.field_mapping_service.LLMClient", FakeLLMClient)

    plan = build_extraction_plan(
        file_content=buffer.getvalue(),
        filename="factory-haining.xlsx",
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
        jiuding_reference_rows=[{"产品类型": "FDY"}],
    )

    assert plan.fields["quantity"].column == "Unnamed: 5"
    assert plan.fields["quantity"].type == "integer"
    assert plan.fields["company"].column == "售达方"
