import pandas as pd

from services.data_comparator import DataComparator
from services.xinfengming_order_comparison import parse_xinfengming_jiuding_data


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


def test_parse_xinfengming_jiuding_data_attaches_filter_company_from_customer_name():
    source_df = pd.DataFrame(
        [
            {
                "出库单号": "H-001",
                "客户名称": "浙江双兔新材料有限公司",
                "会员名称": "杭州银瑞化纤有限公司",
                "订单日期": "2026-04-08 08:00:00.0",
                "实际出库数量": 8,
            }
        ]
    )
    result = parse_xinfengming_jiuding_data(source_df, source_filename="jiuding.xlsx")

    assert result.iloc[0]["公司"] == "杭州银瑞化纤有限公司"
    assert result.iloc[0]["筛选公司"] == "浙江双兔新材料有限公司"
