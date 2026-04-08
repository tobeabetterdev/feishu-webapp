import pytest
import pandas as pd
from services.data_comparator import DataComparator

def test_compare_both_sides():
    """测试两端都有数据的对比"""
    # 创建测试数据
    factory_df = pd.DataFrame({
        '送达方': ['公司A', '公司B'],
        '交货单': ['001', '002'],
        '交货日期': ['2026-04-05', '2026-04-05'],
        '物料组': ['POY', 'POY'],
        '交货数量': [100, 200]
    })

    jiuding_df = pd.DataFrame({
        '出库单号': ['001', '002'],
        '会员名称': ['公司A', '公司B'],
        '产品类型': ['POY', 'POY'],
        '订单日期': ['2026-04-05', '2026-04-05'],
        '实际出库数量': [95, 200]
    })

    comparator = DataComparator(factory_df, jiuding_df, "hengyi")
    result = comparator.compare()

    assert len(result) == 2
    assert result.iloc[0]['待处理数量'] == 5  # 100 - 95
    assert result.iloc[1]['待处理数量'] == 0  # 200 - 200


def test_compare_factory_only():
    """测试只在工厂侧存在的数据"""
    factory_df = pd.DataFrame({
        '送达方': ['公司A'],
        '交货单': ['001'],
        '交货日期': ['2026-04-05'],
        '物料组': ['POY'],
        '交货数量': [100]
    })

    jiuding_df = pd.DataFrame({
        '出库单号': [],
        '会员名称': [],
        '产品类型': [],
        '订单日期': [],
        '实际出库数量': []
    })

    comparator = DataComparator(factory_df, jiuding_df, "hengyi")
    result = comparator.compare()

    assert len(result) == 1
    assert result.iloc[0]['单号'] == '001'
    assert result.iloc[0]['客户出库数'] == 100
    assert result.iloc[0]['久鼎出库数'] is None
    assert result.iloc[0]['待处理数量'] is None


def test_compare_jiuding_only():
    """测试只在久鼎侧存在的数据"""
    factory_df = pd.DataFrame({
        '送达方': [],
        '交货单': [],
        '交货日期': [],
        '物料组': [],
        '交货数量': []
    })

    jiuding_df = pd.DataFrame({
        '出库单号': ['001'],
        '会员名称': ['公司A'],
        '产品类型': ['POY'],
        '订单日期': ['2026-04-05'],
        '实际出库数量': [95]
    })

    comparator = DataComparator(factory_df, jiuding_df, "hengyi")
    result = comparator.compare()

    assert len(result) == 1
    assert result.iloc[0]['单号'] == '001'
    assert result.iloc[0]['客户出库数'] is None
    assert result.iloc[0]['久鼎出库数'] == 95
    assert result.iloc[0]['待处理数量'] is None


def test_compare_xinfengming():
    """测试新凤明工厂类型"""
    factory_df = pd.DataFrame({
        '客户名称': ['公司A'],
        '交货单号': ['001'],
        '交货创建日期': ['2026-04-05'],
        '物料组描述': ['POY'],
        '件数': [100]
    })

    jiuding_df = pd.DataFrame({
        '出库单号': ['001'],
        '会员名称': ['公司A'],
        '产品类型': ['POY'],
        '订单日期': ['2026-04-05'],
        '实际出库数量': [95]
    })

    comparator = DataComparator(factory_df, jiuding_df, "xinfengming")
    result = comparator.compare()

    assert len(result) == 1
    assert result.iloc[0]['单号'] == '001'
    assert result.iloc[0]['客户出库数'] == 100
    assert result.iloc[0]['久鼎出库数'] == 95
    assert result.iloc[0]['待处理数量'] == 5
