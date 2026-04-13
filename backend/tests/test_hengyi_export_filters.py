import base64
import io

import pandas as pd

from api import compare as compare_api
from services.hengyi_order_comparison import parse_hengyi_factory_data, parse_hengyi_jiuding_data


def test_parse_hengyi_factory_data_filters_9710_huifeng_rows():
    source_df = pd.DataFrame(
        [
            {
                "过账日期": "2026-04-08 00:00:00",
                "送达方": "杭州惠丰化纤有限公司",
                "交货单": "F001",
                "车牌号": "浙A12345",
                "托盘数": "10",
                "工厂": "9710",
                "物料组": "FDY",
            },
            {
                "过账日期": "2026-04-08 00:00:00",
                "送达方": "杭州银瑞化纤有限公司",
                "交货单": "F002",
                "车牌号": "浙A54321",
                "托盘数": "12",
                "工厂": "9710",
                "物料组": "POY",
            },
        ]
    )

    result = parse_hengyi_factory_data(source_df, source_filename="双兔_SAP.xlsx")

    assert result["订单号"].tolist() == ["F002"]
    assert result["工厂侧送达方"].tolist() == ["杭州银瑞化纤有限公司"]


def test_parse_hengyi_jiuding_data_filters_shuangtu_huifeng_rows():
    source_df = pd.DataFrame(
        [
            {
                "订单日期": "2026-04-08 21:36:04.0",
                "出库单号": "J001",
                "会员名称": "杭州惠丰化纤有限公司",
                "客户名称": "浙江双兔新材料有限公司",
                "产品类型": "FDY",
                "实际出库数量": "10",
            },
            {
                "订单日期": "2026-04-08 21:36:04.0",
                "出库单号": "J002",
                "会员名称": "杭州银瑞化纤有限公司",
                "客户名称": "浙江双兔新材料有限公司",
                "产品类型": "POY",
                "实际出库数量": "12",
            },
        ]
    )

    result = parse_hengyi_jiuding_data(source_df, selected_factory_short_names={"双兔"})

    assert result["订单号"].tolist() == ["J002"]
    assert result["久鼎侧会员名称"].tolist() == ["杭州银瑞化纤有限公司"]


def test_save_result_writes_hengyi_summary_and_detail_sheets():
    result_df = pd.DataFrame(
        [
            {
                "异常类型": "工厂缺单",
                "订单号": "J001",
                "工厂": "恒逸高新(3100)",
                "订单日期": "2026/4/8",
                "送达方": None,
                "会员名称": "杭州银瑞化纤有限公司",
                "交货单": None,
                "车牌号": None,
                "物料组": None,
                "交货数量": None,
                "托盘数": None,
                "业务员": None,
                "过账日期": None,
                "出库单号": "J001",
                "产品类型": "FDY",
                "客户名称": "恒逸高新",
                "子公司名称": "浙江恒逸高新材料有限公司",
                "出库数量": 18,
                "订单日期2": "2026/4/8",
                "出库数量差异": -18,
            },
            {
                "异常类型": "数量差异",
                "订单号": "F001",
                "工厂": "双兔(9710)",
                "订单日期": "2026/4/8",
                "送达方": "杭州银瑞化纤有限公司",
                "会员名称": "杭州银瑞化纤有限公司",
                "交货单": "F001",
                "车牌号": "浙A12345",
                "物料组": "POY",
                "交货数量": 20,
                "托盘数": 20,
                "业务员": "张三",
                "过账日期": "2026/4/8",
                "出库单号": "F001",
                "产品类型": "POY",
                "客户名称": "双兔",
                "子公司名称": "浙江双兔新材料有限公司",
                "出库数量": 15,
                "订单日期2": "2026/4/8",
                "出库数量差异": 5,
            },
        ]
    )

    saved = compare_api._save_result(result_df=result_df, artifacts={"factory_type": "hengyi"})

    workbook_bytes = base64.b64decode(saved["download_token"])
    workbook = pd.ExcelFile(io.BytesIO(workbook_bytes))

    assert workbook.sheet_names == ["异常汇总", "异常详情"]

    summary_df = pd.read_excel(io.BytesIO(workbook_bytes), sheet_name="异常汇总")
    assert summary_df["异常类型"].tolist() == ["工厂缺单", "数量差异"]
    assert summary_df["订单号"].tolist() == ["J001", "F001"]

    detail_df = pd.read_excel(io.BytesIO(workbook_bytes), sheet_name="异常详情", header=1)
    assert detail_df.columns.tolist() == [
        "异常类型",
        "交货单",
        "送达方",
        "车牌号",
        "物料组",
        "工厂",
        "交货数量",
        "托盘数",
        "业务员",
        "过账日期",
        "出库单号",
        "会员名称",
        "产品类型",
        "客户名称",
        "子公司名称",
        "出库数量",
        "订单日期2",
        "出库数量差异",
    ]
