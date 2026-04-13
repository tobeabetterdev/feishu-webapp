import pandas as pd
import pytest

from services.hengyi_order_comparison import (
    HengyiComparisonError,
    compare_hengyi_data,
    parse_hengyi_factory_data,
    parse_hengyi_jiuding_data,
)


def test_parse_hengyi_factory_data_maps_code_to_short_name_and_keeps_order_as_string():
    source_df = pd.DataFrame(
        [
            {
                "过账日期": "2026-04-08 00:00:00",
                "送达方": "杭州银瑞化纤有限公司",
                "交货单": "0088395730",
                "车牌号": "浙A12345",
                "托盘数": "42",
                "工厂": "3100",
                "物料描述": "POY 切片",
            }
        ]
    )

    result = parse_hengyi_factory_data(source_df, source_filename="高新_SAP.xlsx")

    assert result.iloc[0]["日期"] == "2026/4/8"
    assert result.iloc[0]["订单号"] == "0088395730"
    assert result.iloc[0]["工厂简称"] == "恒逸高新"
    assert result.iloc[0]["工厂侧物料组"] == "POY"
    assert result.iloc[0]["工厂侧送达方"] == "杭州银瑞化纤有限公司"
    assert result.iloc[0]["工厂侧车牌号"] == "浙A12345"
    assert result.iloc[0]["工厂托盘数"] == 42


def test_parse_hengyi_factory_data_falls_back_to_filename_alias_when_code_is_unknown():
    source_df = pd.DataFrame(
        [
            {
                "过账日期": "2026-04-08 00:00:00",
                "送达方": "杭州银瑞化纤有限公司",
                "交货单": "0088395730",
                "车牌号": "浙A12345",
                "托盘数": "42",
                "工厂": "1600",
                "物料描述": "FDY 切片",
            }
        ]
    )

    result = parse_hengyi_factory_data(source_df, source_filename="恒逸高新_SAP.xlsx")

    assert result.iloc[0]["工厂简称"] == "恒逸高新"
    assert result.iloc[0]["工厂侧物料组"] == "FDY"


def test_parse_hengyi_factory_data_deduplicates_same_display_rows():
    source_df = pd.DataFrame(
        [
            {
                "过账日期": "2026-04-12 00:00:00",
                "送达方": "浙江物产经编供应链有限公司",
                "交货单": "0088405489",
                "车牌号": "ZT-浙A33H55",
                "托盘数": "8",
                "工厂": "9710",
                "物料组": "130",
                "物料描述": "POY-220dtex/***f-XA161001SS-AA",
                "交货数量": "5760",
                "业务员": "杨俊先",
            },
            {
                "过账日期": "2026-04-12 00:00:00",
                "送达方": "浙江物产经编供应链有限公司",
                "交货单": "0088405489",
                "车牌号": "ZT-浙A33H55",
                "托盘数": "8",
                "工厂": "9710",
                "物料组": "130",
                "物料描述": "POY-222dtex/144f-XA051009-AA",
                "交货数量": "5760",
                "业务员": "杨俊先",
            },
        ]
    )

    result = parse_hengyi_factory_data(source_df, source_filename="4.12.xlsx")

    assert len(result) == 1
    assert result.iloc[0]["订单号"] == "0088405489"
    assert result.iloc[0]["工厂托盘数"] == 8
    assert result.iloc[0]["工厂交货数量"] == 5760


def test_parse_hengyi_jiuding_data_filters_to_selected_factories():
    source_df = pd.DataFrame(
        [
            {
                "订单日期": "2026-04-08 21:36:04.0",
                "出库单号": "0088395730",
                "会员名称": "杭州银瑞化纤有限公司",
                "客户名称": "浙江恒逸高新材料有限公司",
                "产品类型": "FDY",
                "实际出库数量": "42",
            },
            {
                "订单日期": "2026-04-08 21:36:04.0",
                "出库单号": "0088395999",
                "会员名称": "其他客户",
                "客户名称": "浙江双兔新材料有限公司",
                "产品类型": "FDY",
                "实际出库数量": "10",
            },
        ]
    )

    result = parse_hengyi_jiuding_data(source_df, selected_factory_short_names={"恒逸高新"})

    assert result["订单号"].tolist() == ["0088395730"]
    assert result.iloc[0]["工厂简称"] == "恒逸高新"
    assert result.iloc[0]["久鼎出库数量"] == 42


def test_parse_hengyi_jiuding_data_keeps_time_in_date():
    source_df = pd.DataFrame(
        [
            {
                "订单日期": "2026-04-08 21:36:04.0",
                "出库单号": "0088395730",
                "会员名称": "杭州银瑞化纤有限公司",
                "客户名称": "浙江恒逸高新材料有限公司",
                "产品类型": "FDY",
                "实际出库数量": "42",
            }
        ]
    )

    result = parse_hengyi_jiuding_data(source_df, selected_factory_short_names={"恒逸高新"})

    assert result.iloc[0]["日期"] == "2026/4/8 21:36:04"


def test_compare_hengyi_data_stops_when_dates_do_not_match():
    factory_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/9",
                "订单号": "0088395730",
                "工厂简称": "恒逸高新",
                "工厂侧送达方": "杭州银瑞化纤有限公司",
                "工厂侧车牌号": "浙A12345",
                "工厂托盘数": 42,
                "工厂交货数量": 42,
            }
        ]
    )
    jiuding_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/8",
                "订单号": "0088395730",
                "工厂简称": "恒逸高新",
                "久鼎侧会员名称": "杭州银瑞化纤有限公司",
                "久鼎侧产品类型": "FDY",
                "久鼎出库数量": 42,
            }
        ]
    )

    with pytest.raises(HengyiComparisonError, match="日期"):
        compare_hengyi_data(factory_df, jiuding_df)


def test_compare_hengyi_data_treats_same_day_different_time_as_same_date():
    factory_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/8 00:00:00",
                "订单号": "0088395730",
                "工厂简称": "恒逸高新",
                "工厂侧送达方": "杭州银瑞化纤有限公司",
                "工厂侧车牌号": "浙A12345",
                "工厂托盘数": 42,
                "工厂交货数量": 42,
            }
        ]
    )
    jiuding_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/8 21:36:04",
                "订单号": "0088395730",
                "工厂简称": "恒逸高新",
                "久鼎侧会员名称": "杭州银瑞化纤有限公司",
                "久鼎侧产品类型": "FDY",
                "久鼎出库数量": 42,
            }
        ]
    )

    result = compare_hengyi_data(factory_df, jiuding_df)

    assert result.empty


def test_compare_hengyi_data_suppresses_split_delivery_in_second_pass():
    factory_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/8",
                "订单号": "A",
                "工厂简称": "恒逸高新",
                "工厂侧送达方": "客户甲",
                "工厂侧车牌号": "浙A12345",
                "工厂托盘数": 20,
                "工厂交货数量": 20,
            },
            {
                "日期": "2026/4/8",
                "订单号": "B",
                "工厂简称": "恒逸高新",
                "工厂侧送达方": "客户甲",
                "工厂侧车牌号": "浙A12345",
                "工厂托盘数": 22,
                "工厂交货数量": 22,
            },
        ]
    )
    jiuding_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/8",
                "订单号": "A",
                "工厂简称": "恒逸高新",
                "久鼎侧会员名称": "客户甲",
                "久鼎侧产品类型": "FDY",
                "久鼎出库数量": 42,
            }
        ]
    )

    result = compare_hengyi_data(factory_df, jiuding_df)

    assert result.empty


def test_compare_hengyi_data_keeps_factory_only_missing_order_as_exception():
    factory_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/8",
                "订单号": "B",
                "工厂简称": "恒逸高新",
                "工厂编码": "3100",
                "工厂侧送达方": "客户甲",
                "工厂侧车牌号": "浙A12345",
                "工厂托盘数": 22,
                "工厂交货数量": 22,
            }
        ]
    )
    jiuding_df = pd.DataFrame(
        columns=["日期", "订单号", "工厂简称", "久鼎侧会员名称", "久鼎侧产品类型", "久鼎出库数量"]
    )

    result = compare_hengyi_data(factory_df, jiuding_df)

    assert len(result) == 1
    assert result.iloc[0]["交货单"] == "B"
    assert result.iloc[0]["出库单号"] is None
    assert result.iloc[0]["异常类型"] == "久鼎缺单"
    assert result.iloc[0]["出库数量差异"] == 22


def test_compare_hengyi_data_outputs_new_business_fields():
    factory_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/8",
                "订单号": "0088395730",
                "工厂简称": "恒逸高新",
                "工厂编码": "3100",
                "工厂侧送达方": "杭州银瑞化纤有限公司",
                "工厂侧物料组": "FDY",
                "工厂侧车牌号": "浙A12345",
                "工厂托盘数": 36,
                "工厂交货数量": 36,
                "工厂业务员": "张三",
            }
        ]
    )
    jiuding_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/8",
                "订单号": "0088395730",
                "工厂简称": "恒逸高新",
                "久鼎侧客户全称": "浙江恒逸高新材料有限公司",
                "久鼎侧客户简称": "恒逸高新",
                "久鼎侧会员名称": "杭州银瑞化纤有限公司",
                "久鼎侧产品类型": "FDY",
                "久鼎出库数量": 42,
                "久鼎侧子公司名称": "浙江恒逸高新材料有限公司",
            },
            {
                "日期": "2026/4/8",
                "订单号": "0088396000",
                "工厂简称": "恒逸高新",
                "久鼎侧客户全称": "浙江恒逸高新材料有限公司",
                "久鼎侧客户简称": "恒逸高新",
                "久鼎侧会员名称": "海宁锡铭经编有限公司",
                "久鼎侧产品类型": "FDY",
                "久鼎出库数量": 10,
                "久鼎侧子公司名称": "浙江恒逸高新材料有限公司",
            },
        ]
    )

    result = compare_hengyi_data(factory_df, jiuding_df)

    assert list(result.columns) == [
        "异常类型",
        "订单号",
        "工厂",
        "订单日期",
        "送达方",
        "交货单",
        "车牌号",
        "物料组",
        "交货数量",
        "托盘数",
        "业务员",
        "过账日期",
        "会员名称",
        "出库单号",
        "产品类型",
        "客户名称",
        "子公司名称",
        "出库数量",
        "订单日期2",
        "出库数量差异",
    ]
    assert result.iloc[0]["异常类型"] == "数量差异"
    assert result.iloc[1]["异常类型"] == "工厂缺单"
    assert result["交货单"].tolist() == ["0088395730", None]
    assert result["出库单号"].tolist() == ["0088395730", "0088396000"]
    assert result.iloc[0]["工厂"] == "恒逸高新(3100)"
    assert result.iloc[0]["托盘数"] == 36
    assert result.iloc[0]["出库数量"] == 42
    assert result.iloc[0]["出库数量差异"] == -6
    assert result.iloc[1]["工厂"] == "恒逸高新"
    assert result.iloc[1]["会员名称"] == "海宁锡铭经编有限公司"


def test_compare_hengyi_data_expands_factory_rows_and_keeps_jiuding_once_per_order():
    factory_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/8",
                "订单号": "B200",
                "工厂简称": "恒逸高新",
                "工厂编码": "3100",
                "工厂侧送达方": "杭州银瑞化纤有限公司",
                "工厂侧物料组": "FDY",
                "工厂侧车牌号": "浙A12345",
                "工厂托盘数": 10,
                "工厂交货数量": 10,
            },
            {
                "日期": "2026/4/8",
                "订单号": "A100",
                "工厂简称": "恒逸高新",
                "工厂编码": "3100",
                "工厂侧送达方": "杭州银瑞化纤有限公司",
                "工厂侧物料组": "FDY",
                "工厂侧车牌号": "浙A12345",
                "工厂托盘数": 20,
                "工厂交货数量": 20,
            },
            {
                "日期": "2026/4/8",
                "订单号": "A100",
                "工厂简称": "恒逸高新",
                "工厂编码": "3100",
                "工厂侧送达方": "杭州银瑞化纤有限公司",
                "工厂侧物料组": "FDY",
                "工厂侧车牌号": "浙A12345",
                "工厂托盘数": 16,
                "工厂交货数量": 16,
            },
        ]
    )
    jiuding_df = pd.DataFrame(
        [
            {
                "日期": "2026/4/8",
                "订单号": "A100",
                "工厂简称": "恒逸高新",
                "久鼎侧客户全称": "浙江恒逸高新材料有限公司",
                "久鼎侧客户简称": "恒逸高新",
                "久鼎侧会员名称": "杭州银瑞化纤有限公司",
                "久鼎侧产品类型": "FDY",
                "久鼎出库数量": 42,
                "久鼎侧子公司名称": "浙江恒逸高新材料有限公司",
            },
            {
                "日期": "2026/4/8",
                "订单号": "B200",
                "工厂简称": "恒逸高新",
                "久鼎侧客户全称": "浙江恒逸高新材料有限公司",
                "久鼎侧客户简称": "恒逸高新",
                "久鼎侧会员名称": "杭州银瑞化纤有限公司",
                "久鼎侧产品类型": "FDY",
                "久鼎出库数量": 9,
                "久鼎侧子公司名称": "浙江恒逸高新材料有限公司",
            },
        ]
    )

    result = compare_hengyi_data(factory_df, jiuding_df)

    assert result["异常类型"].tolist() == ["数量差异", "数量差异", "数量差异"]
    assert result["交货单"].tolist() == ["A100", "A100", "B200"]
    assert result["出库单号"].tolist() == ["A100", None, "B200"]
    assert result["托盘数"].tolist() == [20, 16, 10]
    assert result["出库数量"].tolist() == [42, None, 9]
    assert result["出库数量差异"].tolist() == [-6, None, 1]
