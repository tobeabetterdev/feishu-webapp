from datetime import datetime

import pandas as pd

from services.normalized_extractor import normalize_records


def test_normalize_records_enforces_string_integer_and_date_rules():
    source_df = pd.DataFrame(
        [
            {
                "交货日期": datetime(2026, 4, 5),
                "交货单号": 8006341007,
                "送达方": "江苏",
                "物料组描述": "POY",
                "客户名称": "安徽鸿强纺织科技有限公司",
                "交货数量": "15",
            },
            {
                "交货日期": "2026-04-05 00:00:00",
                "交货单号": "00123",
                "送达方": "中跃",
                "物料组描述": "FDY",
                "客户名称": "湖州某公司",
                "交货数量": 8.0,
            },
        ]
    )

    plan = {
        "date": "交货日期",
        "order_no": "交货单号",
        "factory": "送达方",
        "model": "物料组描述",
        "company": "客户名称",
        "quantity": "交货数量",
    }

    result = normalize_records(source_df, plan)

    assert list(result.columns) == ["日期", "单号", "工厂", "型号", "公司", "数量"]
    assert result.iloc[0]["日期"] == "2026/4/5"
    assert result.iloc[0]["单号"] == "8006341007"
    assert isinstance(result.iloc[0]["单号"], str)
    assert result.iloc[0]["数量"] == 15
    assert result.iloc[1]["单号"] == "00123"
    assert result.iloc[1]["日期"] == "2026/4/5"


def test_normalize_records_raises_when_required_field_is_missing():
    source_df = pd.DataFrame([{"交货数量": 10}])
    plan = {
        "date": "不存在的日期列",
        "order_no": "不存在的单号列",
        "factory": "送达方",
        "model": "物料组描述",
        "company": "客户名称",
        "quantity": "交货数量",
    }

    try:
        normalize_records(source_df, plan)
    except ValueError as exc:
        assert "不存在的单号列" in str(exc)
    else:
        raise AssertionError("normalize_records should reject missing plan columns")


def test_normalize_records_allows_missing_date_field_and_fills_blank_date():
    source_df = pd.DataFrame(
        [
            {
                "交货单号": "A-001",
                "送达方": "江苏",
                "物料组描述": "POY",
                "客户名称": "测试客户",
                "交货数量": 12,
            }
        ]
    )
    plan = {
        "order_no": "交货单号",
        "factory": "送达方",
        "model": "物料组描述",
        "company": "客户名称",
        "quantity": "交货数量",
    }

    result = normalize_records(source_df, plan)

    assert list(result.columns) == ["日期", "单号", "工厂", "型号", "公司", "数量"]
    assert result.iloc[0]["日期"] is None
    assert result.iloc[0]["单号"] == "A-001"
    assert result.iloc[0]["数量"] == 12


def test_normalize_records_allows_only_order_and_quantity_fields():
    source_df = pd.DataFrame(
        [
            {
                "交货单号": "A-001",
                "交货数量": 12,
            }
        ]
    )
    plan = {
        "order_no": "交货单号",
        "quantity": "交货数量",
    }

    result = normalize_records(source_df, plan)

    assert list(result.columns) == ["日期", "单号", "工厂", "型号", "公司", "数量"]
    assert result.iloc[0]["日期"] is None
    assert result.iloc[0]["工厂"] is None
    assert result.iloc[0]["型号"] is None
    assert result.iloc[0]["公司"] is None
    assert result.iloc[0]["单号"] == "A-001"
    assert result.iloc[0]["数量"] == 12


def test_normalize_records_matches_columns_after_whitespace_normalization():
    source_df = pd.DataFrame(
        [
            {
                "交货单号": "A-001",
                "送达方": "江苏",
                "托盘类型": "塑托",
                "久鼎托盘_x000D_\n数量": 12,
            }
        ]
    )
    plan = {
        "order_no": "交货单号",
        "factory": "送达方",
        "model": "托盘类型",
        "company": "送达方",
        "quantity": "久鼎托盘_x000D_ 数量",
    }

    result = normalize_records(source_df, plan)

    assert result.iloc[0]["单号"] == "A-001"
    assert result.iloc[0]["数量"] == 12


def test_normalize_records_drops_summary_rows_with_missing_business_fields():
    source_df = pd.DataFrame(
        [
            {
                "订单号": "A-001",
                "工厂出库数量": 10,
            },
            {
                "订单号": None,
                "工厂出库数量": "合计",
            },
        ]
    )
    plan = {
        "order_no": "订单号",
        "quantity": "工厂出库数量",
    }

    result = normalize_records(source_df, plan)

    assert len(result) == 1
    assert result.iloc[0]["单号"] == "A-001"


def test_normalize_records_only_keeps_clear_model_keywords():
    source_df = pd.DataFrame(
        [
            {
                "订单号": "A-001",
                "型号列": "350dtex/96f",
                "数量列": 10,
            },
            {
                "订单号": "A-002",
                "型号列": "超细旦 POY 用品",
                "数量列": 8,
            },
        ]
    )
    plan = {
        "order_no": "订单号",
        "model": "型号列",
        "quantity": "数量列",
    }

    result = normalize_records(source_df, plan)

    assert result.iloc[0]["型号"] is None
    assert result.iloc[1]["型号"] == "POY"


def test_normalize_records_preserves_leading_zero_order_numbers():
    source_df = pd.DataFrame(
        [
            {
                "订单号": "0088396406",
                "数量列": 10,
            }
        ]
    )
    plan = {
        "order_no": "订单号",
        "quantity": "数量列",
    }

    result = normalize_records(source_df, plan)

    assert result.iloc[0]["单号"] == "0088396406"
