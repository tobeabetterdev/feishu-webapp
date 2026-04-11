from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


FACTORY_GROUPS_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "factory_groups.json"

FACTORY_REQUIRED_COLUMNS = ["过账日期", "送达方", "交货单", "车牌号", "托盘数", "工厂"]
JIUDING_REQUIRED_COLUMNS = ["订单日期", "出库单号", "会员名称", "客户名称", "产品类型", "实际出库数量"]

RESULT_COLUMNS = [
    "异常类型",
    "订单号",
    "工厂",
    "订单日期",
    "送达方",
    "工厂交货单",
    "工厂车牌号",
    "工厂物料组",
    "工厂交货数量",
    "工厂托盘数",
    "工厂业务员",
    "工厂过账日期",
    "会员名称",
    "久鼎出库单号",
    "久鼎产品类型",
    "久鼎客户名称",
    "久鼎子公司名称",
    "久鼎出库数量",
    "久鼎订单日期",
    "出库数量差异",
]

FACTORY_FILTER_CODE = "9710"
FACTORY_FILTER_COMPANY = "杭州惠丰化纤有限公司"
JIUDING_FILTER_CUSTOMER = "浙江双兔新材料有限公司"
JIUDING_FILTER_MEMBER = "杭州惠丰化纤有限公司"


class HengyiComparisonError(ValueError):
    pass


def _load_factory_groups() -> dict[str, Any]:
    with FACTORY_GROUPS_CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def _load_hengyi_config() -> dict[str, Any]:
    return _load_factory_groups().get("hengyi", {})


def _normalize_text(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _normalize_order_no(value: object) -> str | None:
    return _normalize_text(value)


def _normalize_date(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    timestamp = pd.to_datetime(value, errors="coerce")
    if pd.isna(timestamp):
        return None
    return (
        f"{timestamp.year}/{timestamp.month}/{timestamp.day} "
        f"{timestamp.hour:02d}:{timestamp.minute:02d}:{timestamp.second:02d}"
    )


def _normalize_date_key(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    timestamp = pd.to_datetime(value, errors="coerce")
    if pd.isna(timestamp):
        return None
    return f"{timestamp.year}/{timestamp.month}/{timestamp.day}"


def _normalize_quantity(value: object) -> int:
    if value is None or pd.isna(value):
        return 0
    text = str(value).strip().replace(",", "")
    if not text:
        return 0
    return int(float(text))


def _normalize_model(value: object) -> str | None:
    text = _normalize_text(value)
    if text is None:
        return None
    upper_text = text.upper()
    for keyword in ("POY", "FDY"):
        if keyword in upper_text:
            return keyword
    return None


def _first_non_empty(series: pd.Series) -> Any:
    for value in series:
        if value is None or pd.isna(value):
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _require_columns(df: pd.DataFrame, required_columns: list[str]) -> None:
    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise HengyiComparisonError(f"缺少必需列: {', '.join(missing)}")


def _build_code_mapping() -> tuple[dict[str, dict[str, str]], dict[str, str], dict[str, list[str]]]:
    hengyi_config = _load_hengyi_config()
    code_mapping = hengyi_config.get("factory_code_mapping", {})
    customer_short_names = hengyi_config.get("customer_short_names", {})
    filename_aliases = hengyi_config.get("filename_aliases", {})

    normalized_mapping: dict[str, dict[str, str]] = {}
    company_to_short_name: dict[str, str] = {}

    for code, payload in code_mapping.items():
        short_name = payload["short_name"]
        company_name = payload.get("company_name") or ""
        normalized_mapping[str(code).strip()] = {
            "short_name": short_name,
            "company_name": company_name,
        }
        if company_name:
            company_to_short_name[company_name] = short_name

    for company_name, short_name in customer_short_names.items():
        company_to_short_name.setdefault(company_name, short_name)

    return normalized_mapping, company_to_short_name, filename_aliases


def _resolve_factory_short_name_from_filename(source_filename: str) -> str | None:
    _, _, filename_aliases = _build_code_mapping()
    for short_name, aliases in filename_aliases.items():
        if any(alias in source_filename for alias in aliases):
            return short_name
    return None


def _resolve_factory_mapping(code: object, *, source_filename: str) -> dict[str, str]:
    code_mapping, company_to_short_name, _ = _build_code_mapping()
    normalized_code = _normalize_text(code)

    if normalized_code and normalized_code in code_mapping:
        return code_mapping[normalized_code]

    fallback_short_name = _resolve_factory_short_name_from_filename(source_filename)
    if fallback_short_name:
        fallback_company = next(
            (
                company
                for company, short_name in company_to_short_name.items()
                if short_name == fallback_short_name
            ),
            "",
        )
        return {"short_name": fallback_short_name, "company_name": fallback_company}

    return {"short_name": "", "company_name": ""}


def _format_factory_display(short_name: object, code: object) -> str | None:
    short_text = _normalize_text(short_name)
    code_text = _normalize_text(code)
    if short_text and code_text:
        return f"{short_text}({code_text})"
    if short_text:
        return short_text
    return None


def _short_name_from_company(company_name: object) -> str | None:
    _, company_to_short_name, _ = _build_code_mapping()
    company_text = _normalize_text(company_name)
    if not company_text:
        return None
    return company_to_short_name.get(company_text)


def _should_drop_factory_row(row: pd.Series) -> bool:
    return (
        row["订单号"] is None
        or row["工厂托盘数"] == 0
        or _normalize_text(row["工厂简称"]) is None
    )


def _should_filter_factory_business_row(row: dict[str, Any]) -> bool:
    return (
        _normalize_text(row.get("工厂编码")) == FACTORY_FILTER_CODE
        and _normalize_text(row.get("工厂侧送达方")) == FACTORY_FILTER_COMPANY
    )


def _should_filter_jiuding_business_row(row: dict[str, Any]) -> bool:
    return (
        _normalize_text(row.get("久鼎侧客户全称")) == JIUDING_FILTER_CUSTOMER
        and _normalize_text(row.get("久鼎侧会员名称")) == JIUDING_FILTER_MEMBER
    )


def parse_hengyi_factory_data(source_df: pd.DataFrame, *, source_filename: str) -> pd.DataFrame:
    working = source_df.copy()
    working.columns = [str(column).strip() for column in working.columns]
    _require_columns(working, FACTORY_REQUIRED_COLUMNS)

    parsed_rows: list[dict[str, Any]] = []
    for _, row in working.iterrows():
        factory_mapping = _resolve_factory_mapping(row.get("工厂"), source_filename=source_filename)
        parsed_row = {
            "日期": _normalize_date(row.get("过账日期")),
            "订单号": _normalize_order_no(row.get("交货单")),
            "工厂简称": factory_mapping["short_name"],
            "工厂全称": factory_mapping.get("company_name") or None,
            "工厂编码": _normalize_text(row.get("工厂")),
            "工厂侧送达方": _normalize_text(row.get("送达方")),
            "工厂侧物料组": _normalize_model(row.get("物料组"))
            or _normalize_model(row.get("物料描述"))
            or _normalize_model(row.get("物料组描述")),
            "工厂侧车牌号": _normalize_text(row.get("车牌号")),
            "工厂托盘数": _normalize_quantity(row.get("托盘数")),
            "工厂交货数量": _normalize_quantity(row.get("交货数量")) if "交货数量" in working.columns else 0,
            "工厂业务员": _normalize_text(row.get("业务员")),
            "来源文件": source_filename,
        }
        if _should_filter_factory_business_row(parsed_row):
            continue
        parsed_rows.append(parsed_row)

    parsed = pd.DataFrame(parsed_rows)
    if parsed.empty:
        return pd.DataFrame(
            columns=[
                "日期",
                "订单号",
                "工厂简称",
                "工厂全称",
                "工厂编码",
                "工厂侧送达方",
                "工厂侧物料组",
                "工厂侧车牌号",
                "工厂托盘数",
                "工厂交货数量",
                "工厂业务员",
                "来源文件",
            ]
        )

    parsed = parsed[~parsed.apply(_should_drop_factory_row, axis=1)].reset_index(drop=True)
    return parsed


def parse_hengyi_jiuding_data(
    source_df: pd.DataFrame,
    *,
    selected_factory_short_names: set[str] | None = None,
) -> pd.DataFrame:
    working = source_df.copy()
    working.columns = [str(column).strip() for column in working.columns]
    _require_columns(working, JIUDING_REQUIRED_COLUMNS)

    _, company_to_short_name, _ = _build_code_mapping()
    parsed_rows: list[dict[str, Any]] = []
    for _, row in working.iterrows():
        customer_name = _normalize_text(row.get("客户名称"))
        short_name = company_to_short_name.get(customer_name or "")
        if selected_factory_short_names and short_name not in selected_factory_short_names:
            continue

        parsed_row = {
            "日期": _normalize_date(row.get("订单日期")),
            "订单号": _normalize_order_no(row.get("出库单号")),
            "工厂简称": short_name,
            "久鼎侧客户全称": customer_name,
            "久鼎侧客户简称": short_name,
            "久鼎侧会员名称": _normalize_text(row.get("会员名称")),
            "久鼎侧产品类型": _normalize_model(row.get("产品类型")),
            "久鼎出库数量": _normalize_quantity(row.get("实际出库数量")),
            "久鼎侧子公司名称": customer_name,
        }
        if _should_filter_jiuding_business_row(parsed_row):
            continue
        parsed_rows.append(parsed_row)

    parsed = pd.DataFrame(parsed_rows)
    if parsed.empty:
        return pd.DataFrame(
            columns=[
                "日期",
                "订单号",
                "工厂简称",
                "久鼎侧客户全称",
                "久鼎侧客户简称",
                "久鼎侧会员名称",
                "久鼎侧产品类型",
                "久鼎出库数量",
                "久鼎侧子公司名称",
            ]
        )

    parsed = parsed.dropna(subset=["订单号"]).reset_index(drop=True)
    return parsed


def _collect_date_set(df: pd.DataFrame) -> set[str]:
    if df.empty or "日期" not in df.columns:
        return set()
    normalized_dates = {_normalize_date_key(value) for value in df["日期"].dropna().tolist()}
    return {value for value in normalized_dates if value}


def _validate_dates(factory_df: pd.DataFrame, jiuding_df: pd.DataFrame) -> None:
    factory_dates = _collect_date_set(factory_df)
    jiuding_dates = _collect_date_set(jiuding_df)
    if not factory_dates or not jiuding_dates:
        return
    if factory_dates != jiuding_dates:
        raise HengyiComparisonError(
            f"日期不一致，工厂侧={sorted(factory_dates)}，久鼎侧={sorted(jiuding_dates)}"
        )


def _aggregate_factory_rows(factory_df: pd.DataFrame) -> pd.DataFrame:
    if factory_df.empty:
        return pd.DataFrame(
            columns=[
                "日期",
                "订单号",
                "工厂简称",
                "工厂全称",
                "工厂编码",
                "工厂侧送达方",
                "工厂侧物料组",
                "工厂侧车牌号",
                "工厂托盘数",
                "工厂交货数量",
                "工厂业务员",
            ]
        )

    working = factory_df.copy()
    defaults: dict[str, Any] = {
        "工厂简称": None,
        "工厂全称": None,
        "工厂编码": None,
        "工厂侧送达方": None,
        "工厂侧物料组": None,
        "工厂侧车牌号": None,
        "工厂托盘数": 0,
        "工厂交货数量": 0,
        "工厂业务员": None,
    }
    for column_name, default_value in defaults.items():
        if column_name not in working.columns:
            working[column_name] = default_value
    working["订单号"] = working["订单号"].map(_normalize_order_no)
    working = working.dropna(subset=["订单号"])
    return working.groupby("订单号", as_index=False).agg(
        {
            "日期": _first_non_empty,
            "工厂简称": _first_non_empty,
            "工厂全称": _first_non_empty,
            "工厂编码": _first_non_empty,
            "工厂侧送达方": _first_non_empty,
            "工厂侧物料组": _first_non_empty,
            "工厂侧车牌号": _first_non_empty,
            "工厂托盘数": "sum",
            "工厂交货数量": "sum",
            "工厂业务员": _first_non_empty,
        }
    )


def _aggregate_jiuding_rows(jiuding_df: pd.DataFrame) -> pd.DataFrame:
    if jiuding_df.empty:
        return pd.DataFrame(
            columns=[
                "日期",
                "订单号",
                "工厂简称",
                "久鼎侧客户全称",
                "久鼎侧客户简称",
                "久鼎侧会员名称",
                "久鼎侧产品类型",
                "久鼎出库数量",
                "久鼎侧子公司名称",
            ]
        )

    working = jiuding_df.copy()
    defaults: dict[str, Any] = {
        "工厂简称": None,
        "久鼎侧客户全称": None,
        "久鼎侧客户简称": None,
        "久鼎侧会员名称": None,
        "久鼎侧产品类型": None,
        "久鼎出库数量": 0,
        "久鼎侧子公司名称": None,
    }
    for column_name, default_value in defaults.items():
        if column_name not in working.columns:
            working[column_name] = default_value
    working["订单号"] = working["订单号"].map(_normalize_order_no)
    working = working.dropna(subset=["订单号"])
    return working.groupby("订单号", as_index=False).agg(
        {
            "日期": _first_non_empty,
            "工厂简称": _first_non_empty,
            "久鼎侧客户全称": _first_non_empty,
            "久鼎侧客户简称": _first_non_empty,
            "久鼎侧会员名称": _first_non_empty,
            "久鼎侧产品类型": _first_non_empty,
            "久鼎出库数量": "sum",
            "久鼎侧子公司名称": _first_non_empty,
        }
    )


def _build_initial_result_rows(factory_df: pd.DataFrame, jiuding_df: pd.DataFrame) -> list[dict[str, Any]]:
    aggregated_factory = _aggregate_factory_rows(factory_df)
    aggregated_jiuding = _aggregate_jiuding_rows(jiuding_df)

    merged = aggregated_factory.merge(
        aggregated_jiuding,
        on="订单号",
        how="outer",
        suffixes=("_factory", "_jiuding"),
    )

    result_rows: list[dict[str, Any]] = []
    for _, row in merged.iterrows():
        factory_qty = _normalize_quantity(row.get("工厂托盘数"))
        jiuding_qty = _normalize_quantity(row.get("久鼎出库数量"))
        diff = factory_qty - jiuding_qty
        if diff == 0:
            continue

        order_no = _normalize_order_no(row.get("订单号"))
        factory_exists = factory_qty > 0
        jiuding_exists = jiuding_qty > 0

        if factory_exists and jiuding_exists:
            anomaly_type = "数量差异"
        elif factory_exists:
            anomaly_type = "久鼎缺单"
        else:
            anomaly_type = "工厂缺单"

        factory_short_name = row.get("工厂简称_factory")
        factory_code = row.get("工厂编码")
        factory_display = _format_factory_display(factory_short_name, factory_code)
        if not factory_display and jiuding_exists:
            factory_display = _normalize_text(row.get("久鼎侧客户简称")) or _short_name_from_company(row.get("久鼎侧客户全称"))

        result_rows.append(
            {
                "异常类型": anomaly_type,
                "订单号": order_no,
                "工厂": factory_display,
                "订单日期": row.get("日期_factory") or row.get("日期_jiuding"),
                "送达方": row.get("工厂侧送达方"),
                "会员名称": row.get("久鼎侧会员名称"),
                "工厂交货单": order_no if factory_exists else None,
                "工厂车牌号": row.get("工厂侧车牌号"),
                "工厂物料组": row.get("工厂侧物料组"),
                "工厂交货数量": factory_qty if factory_exists else None,
                "工厂托盘数": factory_qty if factory_exists else None,
                "工厂业务员": row.get("工厂业务员"),
                "工厂过账日期": row.get("日期_factory"),
                "久鼎出库单号": order_no if jiuding_exists else None,
                "久鼎产品类型": row.get("久鼎侧产品类型"),
                "久鼎客户名称": row.get("久鼎侧客户简称"),
                "久鼎子公司名称": row.get("久鼎侧子公司名称"),
                "久鼎出库数量": jiuding_qty if jiuding_exists else None,
                "久鼎订单日期": row.get("日期_jiuding"),
                "出库数量差异": diff,
                "_order_no": order_no,
                "_factory_total_qty": factory_qty,
                "_jiuding_total_qty": jiuding_qty,
                "_factory_order_no": order_no if factory_exists else None,
                "_jiuding_order_no": order_no if jiuding_exists else None,
                "_group_date": row.get("日期_factory") or row.get("日期_jiuding"),
                "_group_factory": row.get("工厂简称_factory") or row.get("工厂简称_jiuding"),
                "_factory_company": row.get("工厂侧送达方"),
                "_jiuding_company": row.get("久鼎侧会员名称"),
                "_plate_no": row.get("工厂侧车牌号"),
            }
        )

    return result_rows


def _find_subset_sum_indices(candidates: list[tuple[int, int]], target: int) -> list[int] | None:
    candidates = sorted(candidates, key=lambda item: item[1], reverse=True)

    def dfs(position: int, remaining: int, chosen: list[int]) -> list[int] | None:
        if remaining == 0:
            return chosen.copy()
        if remaining < 0 or position >= len(candidates):
            return None

        candidate_index, candidate_qty = candidates[position]
        with_current = dfs(position + 1, remaining - candidate_qty, chosen + [candidate_index])
        if with_current is not None:
            return with_current
        return dfs(position + 1, remaining, chosen)

    return dfs(0, target, [])


def _apply_split_order_reconciliation(result_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    remove_indexes: set[int] = set()
    used_factory_only_indexes: set[int] = set()

    for shortage_index, shortage_row in enumerate(result_rows):
        if shortage_index in remove_indexes:
            continue
        if shortage_row["出库数量差异"] >= 0:
            continue
        if not shortage_row["_factory_order_no"] or not shortage_row["_jiuding_order_no"]:
            continue

        plate_no = _normalize_text(shortage_row["_plate_no"])
        if plate_no is None:
            continue

        factory_company = _normalize_text(shortage_row["_factory_company"])
        jiuding_company = _normalize_text(shortage_row["_jiuding_company"])
        if factory_company is None or jiuding_company is None or factory_company != jiuding_company:
            continue

        target_qty = abs(int(shortage_row["出库数量差异"]))
        candidate_rows: list[tuple[int, int]] = []
        for candidate_index, candidate_row in enumerate(result_rows):
            if candidate_index == shortage_index or candidate_index in remove_indexes or candidate_index in used_factory_only_indexes:
                continue
            if candidate_row["出库数量差异"] <= 0:
                continue
            if candidate_row["_jiuding_order_no"] is not None:
                continue

            same_plate = _normalize_text(candidate_row["_plate_no"]) == plate_no
            same_company = _normalize_text(candidate_row["_factory_company"]) == factory_company
            same_date = candidate_row["_group_date"] == shortage_row["_group_date"]
            same_factory = candidate_row["_group_factory"] == shortage_row["_group_factory"]
            if same_plate and same_company and same_date and same_factory:
                candidate_rows.append((candidate_index, int(candidate_row["_factory_total_qty"])))

        matched_indexes = _find_subset_sum_indices(candidate_rows, target_qty)
        if matched_indexes:
            remove_indexes.add(shortage_index)
            remove_indexes.update(matched_indexes)
            used_factory_only_indexes.update(matched_indexes)

    return [row for index, row in enumerate(result_rows) if index not in remove_indexes]


def _build_factory_detail_map(factory_df: pd.DataFrame) -> dict[str, list[dict[str, Any]]]:
    if factory_df.empty:
        return {}

    detail_map: dict[str, list[dict[str, Any]]] = {}
    for _, row in factory_df.iterrows():
        order_no = _normalize_order_no(row.get("订单号"))
        if order_no is None:
            continue

        detail_map.setdefault(order_no, []).append(
            {
                "工厂交货单": order_no,
                "送达方": row.get("工厂侧送达方"),
                "工厂车牌号": row.get("工厂侧车牌号"),
                "工厂物料组": row.get("工厂侧物料组"),
                "工厂交货数量": _normalize_quantity(row.get("工厂交货数量")) or _normalize_quantity(row.get("工厂托盘数")),
                "工厂托盘数": _normalize_quantity(row.get("工厂托盘数")),
                "工厂业务员": row.get("工厂业务员"),
                "工厂过账日期": row.get("日期"),
                "工厂": _format_factory_display(row.get("工厂简称"), row.get("工厂编码")),
            }
        )

    return detail_map


def _strip_internal_keys(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if not key.startswith("_")}


def _expand_result_rows(result_rows: list[dict[str, Any]], factory_df: pd.DataFrame) -> list[dict[str, Any]]:
    factory_detail_map = _build_factory_detail_map(factory_df)
    sorted_rows = sorted(
        result_rows,
        key=lambda row: (
            _normalize_order_no(row.get("_order_no"))
            or _normalize_order_no(row.get("_factory_order_no"))
            or _normalize_order_no(row.get("_jiuding_order_no"))
            or ""
        ),
    )

    expanded_rows: list[dict[str, Any]] = []
    for row in sorted_rows:
        order_no = _normalize_order_no(row.get("_order_no"))
        factory_details = factory_detail_map.get(order_no or "", [])
        public_row = _strip_internal_keys(row)

        if not factory_details:
            expanded_rows.append(public_row)
            continue

        for index, detail in enumerate(factory_details):
            expanded_rows.append(
                {
                    "异常类型": public_row["异常类型"],
                    "订单号": public_row["订单号"],
                    "工厂": detail["工厂"] or public_row["工厂"],
                    "订单日期": public_row["订单日期"],
                    "送达方": detail["送达方"],
                    "会员名称": public_row["会员名称"] if index == 0 else None,
                    "工厂交货单": detail["工厂交货单"],
                    "工厂车牌号": detail["工厂车牌号"],
                    "工厂物料组": detail["工厂物料组"],
                    "工厂交货数量": detail["工厂交货数量"],
                    "工厂托盘数": detail["工厂托盘数"],
                    "工厂业务员": detail["工厂业务员"],
                    "工厂过账日期": detail["工厂过账日期"],
                    "久鼎出库单号": public_row["久鼎出库单号"] if index == 0 else None,
                    "久鼎产品类型": public_row["久鼎产品类型"] if index == 0 else None,
                    "久鼎客户名称": public_row["久鼎客户名称"] if index == 0 else None,
                    "久鼎子公司名称": public_row["久鼎子公司名称"] if index == 0 else None,
                    "久鼎出库数量": public_row["久鼎出库数量"] if index == 0 else None,
                    "久鼎订单日期": public_row["久鼎订单日期"] if index == 0 else None,
                    "出库数量差异": public_row["出库数量差异"] if index == 0 else None,
                }
            )

    return expanded_rows


def compare_hengyi_data(factory_df: pd.DataFrame, jiuding_df: pd.DataFrame) -> pd.DataFrame:
    _validate_dates(factory_df, jiuding_df)

    initial_result_rows = _build_initial_result_rows(factory_df, jiuding_df)
    reconciled_rows = _apply_split_order_reconciliation(initial_result_rows)
    final_rows = _expand_result_rows(reconciled_rows, factory_df)

    if not final_rows:
        return pd.DataFrame(columns=RESULT_COLUMNS)

    result_df = pd.DataFrame(final_rows)
    result_df = result_df[RESULT_COLUMNS].astype(object)
    result_df = result_df.where(pd.notna(result_df), None)
    return result_df
