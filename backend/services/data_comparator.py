from __future__ import annotations

import json
from pathlib import Path

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


def _load_factory_short_names() -> dict[str, str]:
    with FACTORY_GROUPS_CONFIG_PATH.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    short_names: dict[str, str] = {}
    for group in payload.values():
        short_names.update(group.get("customer_short_names", {}))
    return short_names


class DataComparator:
    def __init__(self, factory_df: pd.DataFrame, jiuding_df: pd.DataFrame):
        self.factory_df = factory_df.copy()
        self.jiuding_df = jiuding_df.copy()
        self.factory_short_names = _load_factory_short_names()

    def _map_factory_short_name(self, value):
        if value is None or pd.isna(value):
            return value
        text = str(value).strip()
        return self.factory_short_names.get(text, text)

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

    def _aggregate_rows(self, df: pd.DataFrame, quantity_column: str) -> pd.DataFrame:
        working = df.copy()
        working[quantity_column] = working[quantity_column].fillna(0).astype(int)

        aggregated = (
            working.groupby("单号", as_index=False)
            .agg(
                {
                    "日期": self._first_non_empty,
                    "工厂": self._first_non_empty,
                    "型号": self._first_non_empty,
                    "公司": self._first_non_empty,
                    quantity_column: "sum",
                }
            )
        )
        return aggregated

    def compare(self) -> pd.DataFrame:
        factory_rows = self._aggregate_rows(
            self.factory_df.rename(columns={"数量": "客户出库数"}),
            "客户出库数",
        )
        jiuding_rows = self._aggregate_rows(
            self.jiuding_df.rename(columns={"数量": "久鼎出库数"}),
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
                "日期": merged["日期_factory"].combine_first(merged["日期_jiuding"]),
                "单号": merged["单号"].astype(str),
                "工厂": merged["工厂_factory"].combine_first(merged["工厂_jiuding"]).map(self._map_factory_short_name),
                "型号": merged["型号_factory"].combine_first(merged["型号_jiuding"]),
                "公司": merged["公司_factory"].combine_first(merged["公司_jiuding"]),
                "客户出库数": merged["客户出库数"].fillna(0).astype(int),
                "久鼎出库数": merged["久鼎出库数"].fillna(0).astype(int),
            }
        )

        result["待处理数量"] = result["客户出库数"] - result["久鼎出库数"]
        result = result[result["待处理数量"] != 0].reset_index(drop=True)
        return result[RESULT_COLUMNS]
