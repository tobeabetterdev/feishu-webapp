import pandas as pd

from services.data_comparator import DataComparator


def test_compare_maps_factory_name_to_short_name_from_config():
    factory_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/5",
                "单号": "8006341007",
                "工厂": "新凤鸣江苏新拓新材有限公司",
                "型号": "POY",
                "公司": "安徽鸿强纺织科技有限公司",
                "数量": 15,
            }
        ]
    )
    jiuding_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/5",
                "单号": "8006341007",
                "工厂": "新凤鸣江苏新拓新材有限公司",
                "型号": "POY",
                "公司": "安徽鸿强纺织科技有限公司",
                "数量": 14,
            }
        ]
    )

    result = DataComparator(factory_df, jiuding_df).compare()

    assert result.iloc[0]["工厂"] == "江苏"


def test_compare_keeps_original_factory_name_when_no_mapping_exists():
    factory_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/5",
                "单号": "A-001",
                "工厂": "未配置简称的企业",
                "型号": "POY",
                "公司": "测试公司",
                "数量": 10,
            }
        ]
    )
    jiuding_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/5",
                "单号": "A-001",
                "工厂": "未配置简称的企业",
                "型号": "POY",
                "公司": "测试公司",
                "数量": 8,
            }
        ]
    )

    result = DataComparator(factory_df, jiuding_df).compare()

    assert result.iloc[0]["工厂"] == "未配置简称的企业"


def test_compare_aggregates_duplicate_order_rows_before_diff():
    factory_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/5",
                "单号": "DUP-001",
                "工厂": "新凤鸣江苏新拓新材有限公司",
                "型号": "POY",
                "公司": "测试公司",
                "数量": 10,
            },
            {
                "日期": "2026/4/5",
                "单号": "DUP-001",
                "工厂": "新凤鸣江苏新拓新材有限公司",
                "型号": "POY",
                "公司": "测试公司",
                "数量": 5,
            },
        ]
    )
    jiuding_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/5",
                "单号": "DUP-001",
                "工厂": "新凤鸣江苏新拓新材有限公司",
                "型号": "POY",
                "公司": "测试公司",
                "数量": 8,
            },
            {
                "日期": "2026/4/5",
                "单号": "DUP-001",
                "工厂": "新凤鸣江苏新拓新材有限公司",
                "型号": "POY",
                "公司": "测试公司",
                "数量": 4,
            },
        ]
    )

    result = DataComparator(factory_df, jiuding_df).compare()

    assert len(result) == 1
    assert result.iloc[0]["单号"] == "DUP-001"
    assert result.iloc[0]["客户出库数"] == 15
    assert result.iloc[0]["久鼎出库数"] == 12
    assert result.iloc[0]["待处理数量"] == 3
