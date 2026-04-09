import pandas as pd

from services.data_comparator import DataComparator


def test_hengyi_filename_alias_highxin_narrows_jiuding_to_gaoxin_customer():
    factory_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/8",
                "单号": "GX-001",
                "工厂": None,
                "型号": "FDY",
                "公司": "某客户A",
                "数量": 10,
                "来源文件": "高新.xlsx",
                "来源工厂线索": None,
            }
        ]
    )
    jiuding_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/8",
                "单号": "GX-999",
                "工厂": None,
                "型号": "FDY",
                "公司": "某客户B",
                "筛选公司": "浙江恒逸高新材料有限公司",
                "数量": 21,
            },
            {
                "日期": "2026/4/8",
                "单号": "HT-999",
                "工厂": None,
                "型号": "FDY",
                "公司": "某客户C",
                "筛选公司": "海宁恒逸新材料有限公司",
                "数量": 22,
            },
            {
                "日期": "2026/4/8",
                "单号": "ST-999",
                "工厂": None,
                "型号": "FDY",
                "公司": "某客户D",
                "筛选公司": "浙江双兔新材料有限公司",
                "数量": 23,
            },
        ]
    )

    result = DataComparator(factory_df, jiuding_df, "hengyi").compare()

    assert "GX-999" in set(result["单号"].tolist())
    assert "HT-999" not in set(result["单号"].tolist())
    assert "ST-999" not in set(result["单号"].tolist())


def test_hengyi_filename_alias_highxin_backfills_factory_for_factory_only_rows():
    factory_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/8",
                "单号": "GX-001",
                "工厂": None,
                "型号": "FDY",
                "公司": "某客户A",
                "数量": 10,
                "来源文件": "高新.xlsx",
                "来源工厂线索": None,
            }
        ]
    )
    jiuding_df = pd.DataFrame(columns=["日期", "单号", "工厂", "型号", "公司", "筛选公司", "数量"])

    result = DataComparator(factory_df, jiuding_df, "hengyi").compare()

    assert len(result) == 1
    assert result.iloc[0]["单号"] == "GX-001"
    assert result.iloc[0]["工厂"] == "恒逸高新"
