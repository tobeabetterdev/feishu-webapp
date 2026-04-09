from io import BytesIO

import pandas as pd

from api import compare as compare_api
from config.settings import LLMSettings
from services.data_comparator import DataComparator


def test_compare_filters_hengyi_by_jiuding_filter_company_column_instead_of_member_name():
    factory_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/8",
                "单号": "H-001",
                "工厂": None,
                "型号": None,
                "公司": "杭州银瑞化纤有限公司",
                "数量": 10,
                "来源文件": "双兔_对账.xlsx",
                "来源工厂线索": None,
            }
        ]
    )
    jiuding_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/8",
                "单号": "H-001",
                "工厂": None,
                "型号": None,
                "公司": "杭州银瑞化纤有限公司",
                "筛选公司": "浙江双兔新材料有限公司",
                "数量": 8,
            }
        ]
    )

    result = DataComparator(factory_df, jiuding_df, "hengyi").compare()

    assert len(result) == 1
    assert result.iloc[0]["单号"] == "H-001"
    assert result.iloc[0]["久鼎出库数"] == 8


def test_process_single_excel_attaches_jiuding_filter_company_from_customer_name(monkeypatch):
    source_df = pd.DataFrame(
        [
            {
                "出库单号": "H-001",
                "客户名称": "浙江双兔新材料有限公司",
                "会员名称": "杭州银瑞化纤有限公司",
                "实际出库数量": 8,
            }
        ]
    )
    buffer = BytesIO()
    source_df.to_excel(buffer, index=False)

    class StubPlan:
        def to_column_mapping(self):
            return {"order_no": "出库单号", "company": "会员名称", "quantity": "实际出库数量"}

        def model_dump(self):
            return {"fields": {"order_no": "出库单号"}}

    monkeypatch.setattr(
        compare_api,
        "convert_excel_to_markdown",
        lambda content, filename: {"markdown": "", "preview": ""},
    )
    monkeypatch.setattr(compare_api, "build_extraction_plan", lambda **kwargs: StubPlan())

    result = compare_api._process_single_excel(
        content=buffer.getvalue(),
        filename="jiuding.xlsx",
        role="jiuding",
        factory_type="hengyi",
        llm_settings=LLMSettings(),
        jiuding_reference_rows=None,
    )

    normalized_df = result["normalized_df"]
    assert normalized_df.iloc[0]["公司"] == "杭州银瑞化纤有限公司"
    assert normalized_df.iloc[0]["筛选公司"] == "浙江双兔新材料有限公司"
