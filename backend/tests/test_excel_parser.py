import pytest
from services.excel_parser import ExcelParser

def test_parse_hengyi():
    """测试恒逸格式解析"""
    # 使用实际文件测试
    with open(r'D:\Workspaces\Projects\code-cli\skillls\示例\工厂数据\SAP 导出数据.xlsx', 'rb') as f:
        content = f.read()

    df = ExcelParser.parse_hengyi(content)
    assert len(df) > 0
    assert '送达方' in df.columns
    assert '交货单' in df.columns

def test_parse_xinfengming():
    """测试新凤鸣格式解析"""
    with open(r'D:\Workspaces\Projects\code-cli\skillls\示例\工厂数据\新凤鸣工厂20260405.XLSX', 'rb') as f:
        content = f.read()

    df = ExcelParser.parse_xinfengming(content)
    assert len(df) > 0
    assert '客户名称' in df.columns
    assert '交货单号' in df.columns

def test_parse_jiuding():
    """测试久鼎格式解析"""
    with open(r'D:\Workspaces\Projects\code-cli\skillls\示例\久鼎数据\会员托盘租赁报表fd38e5f9bfe644f2861401342f00ac3d.xlsx', 'rb') as f:
        content = f.read()

    df = ExcelParser.parse_jiuding(content)
    assert len(df) > 0
    assert '出库单号' in df.columns
    assert '会员名称' in df.columns
