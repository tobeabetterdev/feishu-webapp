from io import BytesIO

import pandas as pd

from config.settings import LLMSettings
from services.field_mapping_service import (
    _normalize_plan_payload,
    build_extraction_plan,
    build_jiuding_reference_samples,
)


def test_normalize_plan_payload_accepts_variant_field_keys():
    payload = {
        "source_sheet": "Sheet1",
        "header_row_index": 1,
        "data_start_row_index": 2,
        "skip_keywords": ["合计"],
        "fields": {
            "date": {"source_column": "交货创建日期", "output_format": "yyyy/m/d"},
            "order_no": {"source_column": "交货单号", "data_type": "string"},
            "factory": {"source_column": "销售组织描述"},
            "model": {"source_column": "任意类型列"},
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


def test_build_jiuding_reference_samples_returns_all_columns_from_non_empty_rows():
    source_df = pd.DataFrame(
        [
            {"出库单号": None, "会员名称": "空", "实际出库数量": 1, "产品类型": "POY"},
            {"出库单号": "J-001", "会员名称": "浙江恒逸高新材料有限公司", "实际出库数量": 12, "产品类型": "POY"},
            {"出库单号": "J-002", "会员名称": "浙江双兔新材料有限公司", "实际出库数量": 8, "产品类型": "FDY"},
        ]
    )
    buffer = BytesIO()
    source_df.to_excel(buffer, index=False)

    rows = build_jiuding_reference_samples([buffer.getvalue()])

    assert len(rows) == 2
    assert rows[0]["出库单号"] == "J-001"
    assert rows[0]["会员名称"] == "浙江恒逸高新材料有限公司"
    assert rows[0]["产品类型"] == "POY"


def test_build_extraction_plan_prompt_requires_value_similarity_not_fixed_factory_headers(monkeypatch):
    source_df = pd.DataFrame(
        [
            {
                "单据编码": "A-001",
                "收货单位": "浙江恒逸高新材料有限公司",
                "数量字段": 12,
                "规格字段": "POY 细旦",
            }
        ]
    )
    buffer = BytesIO()
    source_df.to_excel(buffer, index=False)
    captured = {}

    class FakeLLMClient:
        def __init__(self, settings):
            self.settings = settings

        def generate_json(self, system_prompt, user_prompt):
            captured["user_prompt"] = user_prompt
            return {
                "source_sheet": "Sheet1",
                "header_row_index": 1,
                "data_start_row_index": 2,
                "skip_keywords": [],
                "fields": {
                    "order_no": {"column": "单据编码", "type": "string"},
                    "company": {"column": "收货单位", "type": "string"},
                    "quantity": {"column": "数量字段", "type": "integer"},
                    "model": {"column": "规格字段", "type": "string"},
                },
                "confidence": 0.82,
                "notes": ["matched against jiuding reference rows"],
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
        jiuding_reference_rows=[
            {
                "出库单号": "J-001",
                "会员名称": "浙江恒逸高新材料有限公司",
                "实际出库数量": "12",
                "产品类型": "POY",
            }
        ],
    )

    assert plan.fields["order_no"].column == "单据编码"
    assert plan.fields["company"].column == "收货单位"
    assert plan.fields["model"].column == "规格字段"
    assert "久鼎参考样本" in captured["user_prompt"]
    assert "会员名称" in captured["user_prompt"]
    assert "产品类型" in captured["user_prompt"]
    assert "比较工厂侧每一列的样本值" in captured["user_prompt"]
    assert "不能依赖固定列名" in captured["user_prompt"]
    assert "物料组描述" not in captured["user_prompt"]


def test_build_extraction_plan_allows_factory_plan_with_only_order_company_and_quantity(monkeypatch):
    source_df = pd.DataFrame(
        [
            {
                "交货单号": "A-001",
                "售达方": "江苏",
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
        jiuding_reference_rows=[],
    )

    assert set(plan.fields.keys()) == {"order_no", "quantity", "company"}
    assert plan.fields["company"].column == "售达方"
    assert "factory" not in plan.fields


def test_build_extraction_plan_infers_model_from_value_similarity_even_with_generic_header(monkeypatch):
    source_df = pd.DataFrame(
        [
            {
                "交货单号": "A-001",
                "送达方": "浙江恒逸高新材料有限公司",
                "项目说明": "POY 细旦",
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
                    "company": {"column": "送达方", "type": "string"},
                    "quantity": {"column": "交货数量", "type": "integer"},
                },
                "confidence": 0.75,
                "notes": ["model omitted by llm"],
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
        jiuding_reference_rows=[{"产品类型": "POY"}],
    )

    assert plan.fields["model"].column == "项目说明"


def test_jiuding_company_prefers_member_name_column():
    source_df = pd.DataFrame(
        [
            {
                "出库单号": "J-001",
                "公司": "错误公司列",
                "会员名称": "正确会员名称",
                "实际出库数量": 12,
            }
        ]
    )
    buffer = BytesIO()
    source_df.to_excel(buffer, index=False)

    plan = build_extraction_plan(
        file_content=buffer.getvalue(),
        filename="jiuding.xlsx",
        role="jiuding",
        factory_type="hengyi",
        markdown="",
        preview="",
        llm_settings=LLMSettings(),
        jiuding_reference_rows=None,
    )

    assert plan.fields["company"].column == "会员名称"


def test_build_extraction_plan_corrects_missing_model_from_semantic_values(monkeypatch):
    source_df = pd.DataFrame(
        [
            {
                "交货单号": "A-001",
                "送达方": "浙江恒逸高新材料有限公司",
                "任意列A": "普通文本",
                "任意列B": "FDY 半光",
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
                    "company": {"column": "送达方", "type": "string"},
                    "quantity": {"column": "交货数量", "type": "integer"},
                },
                "confidence": 0.4,
                "notes": ["llm omitted model"],
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
        jiuding_reference_rows=[
            {
                "出库单号": "J-001",
                "会员名称": "浙江恒逸高新材料有限公司",
                "实际出库数量": "12",
                "产品类型": "FDY",
            }
        ],
    )

    assert plan.fields["company"].column == "送达方"
    assert plan.fields["model"].column == "任意列B"
