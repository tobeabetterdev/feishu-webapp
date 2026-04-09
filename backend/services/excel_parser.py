from __future__ import annotations

import io

import pandas as pd


class ExcelParser:
    """Legacy compatibility wrapper.

    The comparison flow now relies on LLM-assisted extraction planning and
    deterministic normalization. These helpers only expose raw DataFrames for
    fallback or debugging use.
    """

    @staticmethod
    def read_excel(file_content: bytes) -> pd.DataFrame:
        df = pd.read_excel(io.BytesIO(file_content))
        df.columns = [str(column).strip() for column in df.columns]
        return df

    @staticmethod
    def parse_factory(file_content: bytes, factory_type: str) -> pd.DataFrame:
        return ExcelParser.read_excel(file_content)

    @staticmethod
    def parse_jiuding(file_content: bytes) -> pd.DataFrame:
        return ExcelParser.read_excel(file_content)

    @staticmethod
    def parse_hengyi(file_content: bytes) -> pd.DataFrame:
        return ExcelParser.read_excel(file_content)

    @staticmethod
    def parse_xinfengming(file_content: bytes) -> pd.DataFrame:
        return ExcelParser.read_excel(file_content)
