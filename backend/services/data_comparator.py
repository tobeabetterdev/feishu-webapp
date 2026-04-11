from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


RESULT_COLUMNS = [
    "日期",
    "单号",
    "工厂",
    "型号",
    "公司",
    "客户出库数",
    "久鼎出库数",
    "待处理数量",
]

FACTORY_GROUPS_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "factory_groups.json"


def _load_factory_groups() -> dict[str, Any]:
    with FACTORY_GROUPS_CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


class DataComparator:
    def __init__(self, factory_df: pd.DataFrame, jiuding_df: pd.DataFrame, factory_type: str):
        self.factory_df = self._with_legacy_aliases(factory_df.copy())
        self.jiuding_df = self._with_legacy_aliases(jiuding_df.copy())
        self.factory_type = factory_type
        self.factory_groups = _load_factory_groups()
        current_group = self.factory_groups.get(factory_type, {})
        self.allowed_customers = set(current_group.get("customers", []))
        self.factory_short_names = dict(current_group.get("customer_short_names", {}))
        self.filename_aliases = dict(current_group.get("filename_aliases", {}))
        self.short_name_values = list(self.factory_short_names.values())
        self.short_name_to_customer = {
            short_name: customer_name
            for customer_name, short_name in self.factory_short_names.items()
        }

    @staticmethod
    def _with_legacy_aliases(df: pd.DataFrame) -> pd.DataFrame:
        rename_map = {}
        if "订单号" in df.columns and "单号" not in df.columns:
            rename_map["订单号"] = "单号"
        if "工厂量" in df.columns and "客户出库数" not in df.columns:
            rename_map["工厂量"] = "客户出库数"
        if "久鼎量" in df.columns and "久鼎出库数" not in df.columns:
            rename_map["久鼎量"] = "久鼎出库数"
        if "差量" in df.columns and "待处理数量" not in df.columns:
            rename_map["差量"] = "待处理数量"
        return df.rename(columns=rename_map)

    def _map_factory_short_name(self, value: object) -> str | None:
        if value is None or pd.isna(value):
            return None
        text = str(value).strip()
        if not text:
            return None

        direct_match = self.factory_short_names.get(text)
        if direct_match:
            return direct_match

        for enterprise_name, short_name in self.factory_short_names.items():
            if short_name in text or text in enterprise_name:
                return short_name
        return None

    def _resolve_factory_name(self, *values: object) -> str | None:
        for value in values:
            resolved = self._map_factory_short_name(value)
            if resolved:
                return resolved
        return None

    def _resolve_hengyi_from_filename(self, filename: object) -> str | None:
        if filename is None or pd.isna(filename):
            return None
        text = str(filename).strip()
        if not text:
            return None

        for short_name, aliases in self.filename_aliases.items():
            if any(alias in text for alias in aliases):
                return short_name
        return None

    def _resolve_hengyi_customers_from_filenames(self) -> set[str]:
        if self.factory_type != "hengyi" or "来源文件" not in self.factory_df.columns:
            return set()

        matched_short_names: set[str] = set()
        for filename in self.factory_df["来源文件"].dropna().tolist():
            short_name = self._resolve_hengyi_from_filename(filename)
            if short_name:
                matched_short_names.add(short_name)

        return {
            self.short_name_to_customer[short_name]
            for short_name in matched_short_names
            if short_name in self.short_name_to_customer
        }

    def _resolve_xinfengming_from_hint(self, hint: object) -> str | None:
        if hint is None or pd.isna(hint):
            return None
        text = str(hint).strip()
        if not text:
            return None
        for short_name in self.short_name_values:
            if short_name in text:
                return short_name
        return self._map_factory_short_name(text)

    def _resolve_factory_fallback(self, row: pd.Series) -> str | None:
        if self.factory_type == "hengyi":
            return self._resolve_hengyi_from_filename(
                row.get("来源文件_factory", row.get("来源文件"))
            )
        if self.factory_type == "xinfengming":
            return self._resolve_xinfengming_from_hint(
                row.get("来源工厂线索_factory", row.get("来源工厂线索"))
            )
        return None

    @staticmethod
    def _first_non_empty(series: pd.Series):
        for value in series:
            if value is None or pd.isna(value):
                continue
            text = str(value).strip() if isinstance(value, str) else value
            if text == "":
                continue
            return value
        return None

    def _filter_jiuding_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        if "公司" not in df.columns:
            return df

        working = df.copy()
        effective_customers = set(self.allowed_customers)
        if self.factory_type == "hengyi":
            narrowed_customers = self._resolve_hengyi_customers_from_filenames()
            if narrowed_customers:
                effective_customers = narrowed_customers

        if not effective_customers:
            return working

        if "筛选公司" in working.columns:
            filter_series = working["筛选公司"].combine_first(working["公司"])
        else:
            filter_series = working["公司"]

        company_series = filter_series.fillna("").map(lambda value: str(value).strip())
        return working[company_series.isin(effective_customers)].reset_index(drop=True)

    def _aggregate_rows(self, df: pd.DataFrame, quantity_column: str) -> pd.DataFrame:
        working = self._with_legacy_aliases(df.copy())
        working = working.dropna(subset=["单号"])
        working["单号"] = working["单号"].map(lambda value: str(value).strip())
        working = working[working["单号"] != ""]
        working[quantity_column] = working[quantity_column].fillna(0).astype(int)

        aggregate_map = {
            "日期": self._first_non_empty,
            "工厂": self._first_non_empty,
            "型号": self._first_non_empty,
            "公司": self._first_non_empty,
            quantity_column: "sum",
        }
        if "筛选公司" in working.columns:
            aggregate_map["筛选公司"] = self._first_non_empty
        if "来源文件" in working.columns:
            aggregate_map["来源文件"] = self._first_non_empty
        if "来源工厂线索" in working.columns:
            aggregate_map["来源工厂线索"] = self._first_non_empty

        return working.groupby("单号", as_index=False).agg(aggregate_map)

    def compare(self) -> pd.DataFrame:
        factory_rows = self._aggregate_rows(
            self.factory_df.rename(columns={"数量": "客户出库数"}),
            "客户出库数",
        )
        jiuding_rows = self._aggregate_rows(
            self._filter_jiuding_rows(self.jiuding_df).rename(columns={"数量": "久鼎出库数"}),
            "久鼎出库数",
        )

        merged = factory_rows.merge(
            jiuding_rows,
            on="单号",
            how="outer",
            suffixes=("_factory", "_jiuding"),
        )

        result = pd.DataFrame(
            {
                "日期": merged["日期_jiuding"].combine_first(merged["日期_factory"]),
                "单号": merged["单号"].astype(str),
                "工厂": merged.apply(
                    lambda row: self._resolve_factory_name(
                        row.get("筛选公司_jiuding", row.get("筛选公司")),
                        row.get("公司_jiuding"),
                        row.get("工厂_jiuding"),
                        row.get("公司_factory"),
                        row.get("工厂_factory"),
                    )
                    or self._resolve_factory_fallback(row),
                    axis=1,
                ),
                "型号": merged["型号_jiuding"].combine_first(merged["型号_factory"]),
                "公司": merged["公司_jiuding"].combine_first(merged["公司_factory"]),
                "客户出库数": merged["客户出库数"].fillna(0).astype(int),
                "久鼎出库数": merged["久鼎出库数"].fillna(0).astype(int),
            }
        )

        result["待处理数量"] = result["客户出库数"] - result["久鼎出库数"]
        result = result[result["待处理数量"] != 0].reset_index(drop=True)
        return result[RESULT_COLUMNS]
