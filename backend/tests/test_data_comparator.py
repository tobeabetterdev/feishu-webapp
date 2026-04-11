import pandas as pd

from services.data_comparator import DataComparator


def test_compare_maps_factory_name_to_short_name_from_current_group():
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
                "公司": "新凤鸣江苏新拓新材有限公司",
                "数量": 14,
            }
        ]
    )

    result = DataComparator(factory_df, jiuding_df, "xinfengming").compare()

    assert result.iloc[0]["工厂"] == "新拓"


def test_compare_does_not_fill_factory_from_unmatched_jiuding_company():
    factory_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/5",
                "单号": "A-001",
                "工厂": None,
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
                "工厂": "未配置企业",
                "型号": "POY",
                "公司": "未配置企业",
                "数量": 8,
            }
        ]
    )

    result = DataComparator(factory_df, jiuding_df, "hengyi").compare()

    assert pd.isna(result.iloc[0]["工厂"])


def test_compare_filters_jiuding_full_dataset_by_factory_group_customers():
    factory_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/5",
                "单号": "H-001",
                "工厂": "浙江恒逸高新材料有限公司",
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
                "单号": "H-001",
                "工厂": "浙江恒逸高新材料有限公司",
                "型号": "POY",
                "公司": "浙江恒逸高新材料有限公司",
                "数量": 8,
            },
            {
                "日期": "2026/4/5",
                "单号": "X-001",
                "工厂": "新凤鸣集团股份有限公司",
                "型号": "FDY",
                "公司": "新凤鸣集团股份有限公司",
                "数量": 99,
            },
        ]
    )

    result = DataComparator(factory_df, jiuding_df, "hengyi").compare()

    assert len(result) == 1
    assert result.iloc[0]["单号"] == "H-001"
    assert result.iloc[0]["工厂"] == "恒逸高新"


def test_compare_prefers_company_mapping_for_factory_short_name():
    factory_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/8",
                "单号": "88396294",
                "工厂": None,
                "型号": None,
                "公司": "浙江恒逸高新材料有限公司",
                "数量": 36600,
            }
        ]
    )
    jiuding_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/8",
                "单号": "88396294",
                "工厂": None,
                "型号": None,
                "公司": "浙江恒逸高新材料有限公司",
                "数量": 0,
            }
        ]
    )

    result = DataComparator(factory_df, jiuding_df, "hengyi").compare()

    assert result.iloc[0]["工厂"] == "恒逸高新"


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
                "公司": "新凤鸣江苏新拓新材有限公司",
                "数量": 8,
            },
            {
                "日期": "2026/4/5",
                "单号": "DUP-001",
                "工厂": "新凤鸣江苏新拓新材有限公司",
                "型号": "POY",
                "公司": "新凤鸣江苏新拓新材有限公司",
                "数量": 4,
            },
        ]
    )

    result = DataComparator(factory_df, jiuding_df, "xinfengming").compare()

    assert len(result) == 1
    assert result.iloc[0]["单号"] == "DUP-001"
    assert result.iloc[0]["客户出库数"] == 15
    assert result.iloc[0]["久鼎出库数"] == 12
    assert result.iloc[0]["待处理数量"] == 3


def test_compare_prefers_jiuding_fields_and_backfills_from_factory():
    factory_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/8",
                "单号": "A-009",
                "工厂": None,
                "型号": "POY",
                "公司": "浙江恒逸高新材料有限公司",
                "数量": 20,
            }
        ]
    )
    jiuding_df = pd.DataFrame(
        [
            {
                "日期": None,
                "单号": "A-009",
                "工厂": None,
                "型号": None,
                "公司": None,
                "数量": 18,
            }
        ]
    )

    result = DataComparator(factory_df, jiuding_df, "hengyi").compare()

    assert result.iloc[0]["日期"] == "2026/4/8"
    assert result.iloc[0]["工厂"] == "恒逸高新"
    assert result.iloc[0]["型号"] == "POY"
    assert result.iloc[0]["公司"] == "浙江恒逸高新材料有限公司"


def test_compare_uses_jiuding_member_name_as_company_when_present():
    factory_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/8",
                "单号": "C-001",
                "工厂": None,
                "型号": None,
                "公司": "工厂侧企业名",
                "数量": 10,
            }
        ]
    )
    jiuding_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/8",
                "单号": "C-001",
                "工厂": None,
                "型号": None,
                "公司": "浙江恒逸高新材料有限公司",
                "数量": 8,
            }
        ]
    )

    result = DataComparator(factory_df, jiuding_df, "hengyi").compare()

    assert result.iloc[0]["公司"] == "浙江恒逸高新材料有限公司"


def test_compare_uses_factory_company_when_jiuding_company_missing():
    factory_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/8",
                "单号": "C-002",
                "工厂": None,
                "型号": None,
                "公司": "工厂侧企业名",
                "数量": 10,
            }
        ]
    )
    jiuding_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/8",
                "单号": "C-002",
                "工厂": None,
                "型号": None,
                "公司": None,
                "数量": 8,
            }
        ]
    )

    result = DataComparator(factory_df, jiuding_df, "hengyi").compare()

    assert result.iloc[0]["公司"] == "工厂侧企业名"


def test_compare_backfills_hengyi_factory_from_filename_when_jiuding_missing():
    factory_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/8",
                "单号": "H-900",
                "工厂": None,
                "型号": None,
                "公司": "杭州银瑞化纤有限公司",
                "数量": 10,
                "来源文件": "恒逸高新_出库明细.xlsx",
                "来源工厂线索": None,
            }
        ]
    )
    jiuding_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/8",
                "单号": "H-900",
                "工厂": None,
                "型号": None,
                "公司": "杭州银瑞化纤有限公司",
                "数量": 0,
            }
        ]
    )

    result = DataComparator(factory_df, jiuding_df, "hengyi").compare()

    assert result.iloc[0]["工厂"] == "恒逸高新"


def test_compare_backfills_xinfengming_factory_from_sales_org_hint():
    factory_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/8",
                "单号": "X-900",
                "工厂": None,
                "型号": None,
                "公司": "某客户",
                "数量": 10,
                "来源文件": "xinfengming.xlsx",
                "来源工厂线索": "中石销售组织",
            }
        ]
    )
    jiuding_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/8",
                "单号": "X-900",
                "工厂": None,
                "型号": None,
                "公司": "某客户",
                "数量": 0,
            }
        ]
    )

    result = DataComparator(factory_df, jiuding_df, "xinfengming").compare()

    assert result.iloc[0]["工厂"] == "中石"


def test_compare_filters_hengyi_jiuding_rows_by_matched_filename_short_names():
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
                "公司": "浙江双兔新材料有限公司",
                "数量": 8,
            },
            {
                "日期": "2026/4/8",
                "单号": "H-002",
                "工厂": None,
                "型号": None,
                "公司": "浙江恒逸高新材料有限公司",
                "数量": 99,
            },
        ]
    )

    result = DataComparator(factory_df, jiuding_df, "hengyi").compare()

    assert len(result) == 1
    assert result.iloc[0]["单号"] == "H-001"
    assert result.iloc[0]["工厂"] == "双兔"
