from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChecklistItemResult(BaseModel):
    item_key: str = Field(..., min_length=1, max_length=120)
    status: Literal['compliant', 'non_compliant', 'not_applicable', 'unchecked']
    actual: str = Field(default='', max_length=1000)
    note: str = Field(default='', max_length=2000)


class ChecklistInspectionCreate(BaseModel):
    template_key: str = Field(..., min_length=1, max_length=120)
    responsible: str = Field(..., min_length=2, max_length=200)
    performed_at: datetime
    overall_note: str = Field(default='', max_length=5000)
    items: list[ChecklistItemResult] = Field(..., min_length=1, max_length=100)


class ChecklistInspectionResponse(BaseModel):
    id: int
    template_key: str
    template_title: str
    responsible: str
    performed_at: datetime
    overall_note: str | None
    items: list[ChecklistItemResult]
