from io import BytesIO

import pandas as pd

from services.xinfengming_order_comparison import (
    compare_xinfengming_data,
    parse_xinfengming_factory_data,
    parse_xinfengming_jiuding_data,
)


def _to_excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    return buffer.getvalue()


def test_parse_xinfengming_factory_data_uses_fixed_columns_and_drops_summary_rows():
    source_df = pd.DataFrame(
        [
            {
                "交货单号": "008001",
                "交货创建日期": "2026-04-09 00:00:00",
                "销售组织描述": "中跃化纤",
                "客户名称": "绍兴柯桥炯炯纺织有限公司",
                "物料组描述": "POY",
                "件数": "33",
            },
            {
                "交货单号": None,
                "交货创建日期": None,
                "销售组织描述": "合计",
                "客户名称": None,
                "物料组描述": None,
                "件数": "33",
            },
        ]
    )

    result = parse_xinfengming_factory_data(source_df, source_filename="factory.xlsx")

    assert result.to_dict(orient="records") == [
        {
            "日期": "2026/4/9",
            "单号": "008001",
            "工厂": "中跃化纤",
            "型号": "POY",
            "公司": "绍兴柯桥炯炯纺织有限公司",
            "数量": 33,
            "交货单号": "008001",
            "交货创建日期": "2026/4/9",
            "销售组织描述": "中跃化纤",
            "客户名称": "绍兴柯桥炯炯纺织有限公司",
            "业务员": None,
            "车牌号": None,
            "物料组描述": "POY",
            "件数": 33,
            "交货单类型": None,
            "包装批号": None,
            "来源文件": "factory.xlsx",
            "来源工厂线索": "中跃化纤",
        }
    ]


def test_parse_xinfengming_jiuding_data_uses_fixed_columns_and_attaches_filter_company():
    source_df = pd.DataFrame(
        [
            {
                "出库单号": "008001",
                "客户名称": "湖州市中跃化纤有限公司",
                "会员名称": "绍兴柯桥炯炯纺织有限公司",
                "产品类型": "POY",
                "订单日期": "2026-04-09 08:00:00.0",
                "实际出库数量": "30",
            }
        ]
    )

    result = parse_xinfengming_jiuding_data(source_df, source_filename="jiuding.xlsx")

    assert result.to_dict(orient="records") == [
        {
            "日期": "2026/4/9",
            "单号": "008001",
            "工厂": "湖州市中跃化纤有限公司",
            "型号": "POY",
            "公司": "绍兴柯桥炯炯纺织有限公司",
            "数量": 30,
            "筛选公司": "湖州市中跃化纤有限公司",
            "出库单号": "008001",
            "订单日期": "2026/4/9",
            "客户名称": "湖州市中跃化纤有限公司",
            "会员名称": "绍兴柯桥炯炯纺织有限公司",
            "产品类型": "POY",
            "实际出库数量": 30,
            "子公司名称": None,
            "订单状态": None,
            "送货方式": None,
            "来源文件": "jiuding.xlsx",
            "来源工厂线索": None,
        }
    ]


def test_compare_xinfengming_data_uses_fixed_parser_and_preserves_current_result_shape():
    factory_df = pd.DataFrame(
        [
            {
                "交货单号": "008001",
                "交货创建日期": "2026-04-09 00:00:00",
                "销售组织描述": "中跃化纤",
                "客户名称": "绍兴柯桥炯炯纺织有限公司",
                "物料组描述": "POY",
                "件数": "33",
            }
        ]
    )
    jiuding_df = pd.DataFrame(
        [
            {
                "出库单号": "008001",
                "客户名称": "湖州市中跃化纤有限公司",
                "会员名称": "绍兴柯桥炯炯纺织有限公司",
                "产品类型": "POY",
                "订单日期": "2026-04-09 08:00:00.0",
                "实际出库数量": "30",
            }
        ]
    )

    payload = compare_xinfengming_data(
        factory_files=[{"filename": "factory.xlsx", "content": _to_excel_bytes(factory_df)}],
        jiuding_files=[{"filename": "jiuding.xlsx", "content": _to_excel_bytes(jiuding_df)}],
        factory_type="xinfengming",
    )

    assert payload["result_df"].to_dict(orient="records") == [
        {
            "日期": "2026/4/9",
            "单号": "008001",
            "工厂": "中跃",
            "型号": "POY",
            "公司": "绍兴柯桥炯炯纺织有限公司",
            "客户出库数": 33,
            "久鼎出库数": 30,
            "待处理数量": 3,
        }
    ]
    assert payload["artifacts"]["factory_files"][0]["plan"] == {
        "mode": "fixed_columns",
        "fields": ["交货创建日期", "交货单号", "销售组织描述", "客户名称", "物料组描述", "件数"],
    }
    assert payload["artifacts"]["jiuding_files"][0]["plan"] == {
        "mode": "fixed_columns",
        "fields": ["订单日期", "出库单号", "客户名称", "会员名称", "产品类型", "实际出库数量"],
    }
