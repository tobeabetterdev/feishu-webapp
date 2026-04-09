import pandas as pd

from services.data_comparator import DataComparator


def test_compare_backfills_factory_from_jiuding_filter_company_when_factory_side_missing():
    factory_df = pd.DataFrame(
        columns=["日期", "单号", "工厂", "型号", "公司", "数量", "来源文件", "来源工厂线索"]
    )
    jiuding_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/8",
                "单号": "0088395730",
                "工厂": None,
                "型号": "FDY",
                "公司": "海宁锡铭经编有限公司",
                "筛选公司": "海宁恒逸新材料有限公司",
                "数量": 42,
            }
        ]
    )

    result = DataComparator(factory_df, jiuding_df, "hengyi").compare()

    assert len(result) == 1
    assert result.iloc[0]["单号"] == "0088395730"
    assert result.iloc[0]["工厂"] == "海宁恒逸"
    assert result.iloc[0]["客户出库数"] == 0
    assert result.iloc[0]["久鼎出库数"] == 42


def test_compare_keeps_jiuding_only_orders_for_all_matched_hengyi_factories():
    factory_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/8",
                "单号": "HX-001",
                "工厂": None,
                "型号": "FDY",
                "公司": "某客户A",
                "数量": 10,
                "来源文件": "恒逸高新_对账.xlsx",
                "来源工厂线索": None,
            }
        ]
    )
    jiuding_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/8",
                "单号": "HX-999",
                "工厂": None,
                "型号": "FDY",
                "公司": "某客户B",
                "筛选公司": "浙江恒逸高新材料有限公司",
                "数量": 21,
            }
        ]
    )

    result = DataComparator(factory_df, jiuding_df, "hengyi").compare()

    assert len(result) == 2
    jiuding_only_row = result[result["单号"] == "HX-999"].iloc[0]
    assert jiuding_only_row["工厂"] == "恒逸高新"
    assert jiuding_only_row["客户出库数"] == 0
    assert jiuding_only_row["久鼎出库数"] == 21
