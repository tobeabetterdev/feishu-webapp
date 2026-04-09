from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, AliasChoices


class ExtractionField(BaseModel):
    column: str = Field(validation_alias=AliasChoices("column", "source_column"))
    type: str = Field(validation_alias=AliasChoices("type", "data_type"))
    output_format: Optional[str] = None


class ExtractionPlan(BaseModel):
    source_sheet: Optional[str] = None
    header_row_index: int = 1
    data_start_row_index: int = 2
    skip_keywords: List[str] = Field(default_factory=list)
    fields: Dict[str, ExtractionField]
    confidence: float = 0.0
    notes: List[str] = Field(default_factory=list)

    def to_column_mapping(self) -> Dict[str, str]:
        return {name: field.column for name, field in self.fields.items()}
