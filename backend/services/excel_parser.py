import pandas as pd
from typing import Dict, Any
import io

class ExcelParser:
    """Excel文件解析服务"""

    @staticmethod
    def parse_hengyi(file_content: bytes) -> pd.DataFrame:
        """解析恒逸格式Excel"""
        df = pd.read_excel(io.BytesIO(file_content))
        # 提取必要列
        required_columns = ['送达方', '交货单', '交货日期', '物料组', '交货数量']
        return df[required_columns].copy()

    @staticmethod
    def parse_xinfengming(file_content: bytes) -> pd.DataFrame:
        """解析新凤鸣格式Excel"""
        df = pd.read_excel(io.BytesIO(file_content))
        # 提取必要列
        required_columns = ['客户名称', '交货单号', '交货创建日期', '物料组描述', '件数']
        return df[required_columns].copy()

    @staticmethod
    def parse_jiuding(file_content: bytes) -> pd.DataFrame:
        """解析久鼎格式Excel"""
        df = pd.read_excel(io.BytesIO(file_content))
        # 提取必要列
        required_columns = ['出库单号', '会员名称', '产品类型', '订单日期', '实际出库数量']
        return df[required_columns].copy()

    @staticmethod
    def parse_factory(file_content: bytes, factory_type: str) -> pd.DataFrame:
        """根据工厂类型解析Excel"""
        if factory_type == "hengyi":
            return ExcelParser.parse_hengyi(file_content)
        elif factory_type == "xinfengming":
            return ExcelParser.parse_xinfengming(file_content)
        else:
            raise ValueError(f"未知的工厂类型: {factory_type}")
