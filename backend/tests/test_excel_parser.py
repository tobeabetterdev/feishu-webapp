from io import BytesIO

import pandas as pd

from services.excel_parser import ExcelParser


def _to_excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    return buffer.getvalue()


def test_parse_hengyi():
    source_df = pd.DataFrame([{"送达方": "测试客户", "交货单": "0088395730"}])
    content = _to_excel_bytes(source_df)

    df = ExcelParser.parse_hengyi(content)
    assert len(df) == 1
    assert "送达方" in df.columns
    assert "交货单" in df.columns


def test_parse_xinfengming():
    source_df = pd.DataFrame([{"客户名称": "测试客户", "交货单号": "A-001"}])
    content = _to_excel_bytes(source_df)

    df = ExcelParser.parse_xinfengming(content)
    assert len(df) == 1
    assert "客户名称" in df.columns
    assert "交货单号" in df.columns


def test_parse_jiuding():
    source_df = pd.DataFrame([{"出库单号": "H-001", "会员名称": "测试会员"}])
    content = _to_excel_bytes(source_df)

    df = ExcelParser.parse_jiuding(content)
    assert len(df) == 1
    assert "出库单号" in df.columns
    assert "会员名称" in df.columns
