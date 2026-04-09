from __future__ import annotations

import io
from typing import Dict

import pandas as pd


def convert_excel_to_markdown(file_content: bytes, filename: str) -> Dict[str, str]:
    markdown = ""
    error = None

    try:
        from markitdown import MarkItDown

        converter = MarkItDown()
        result = converter.convert_stream(io.BytesIO(file_content), file_extension=filename.split(".")[-1])
        markdown = getattr(result, "text_content", "") or getattr(result, "markdown", "") or str(result)
    except Exception as exc:
        error = str(exc)

    preview_df = pd.read_excel(io.BytesIO(file_content), nrows=10)
    preview = preview_df.fillna("").astype(str).to_markdown(index=False)

    return {
        "markdown": markdown,
        "preview": preview,
        "conversion_error": error or "",
    }
