from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field

class SOPBase(BaseModel):
    key: str = Field(..., min_length=1, max_length=120)
    number: Optional[str] = Field(default=None, max_length=40)
    title: str = Field(..., min_length=1, max_length=300)
    category: str = Field(..., min_length=1, max_length=100)
    normative_refs: Optional[str] = None
    scope: Optional[str] = None
    terms: Optional[str] = None
    responsibilities: Optional[str] = None
    procedure: Optional[str] = None
    quality_control: Optional[str] = None
    documentation: Optional[str] = None
    status: Literal['draft'] = 'draft'

class SOPCreate(SOPBase):
    pass

class SOPResponse(SOPBase):
    id: int
    status: Literal['draft', 'approved']
    approval_order: Optional[str] = None
    model_config = {'from_attributes': True}


class SOPApproval(BaseModel):
    order_number: str = Field(..., min_length=1, max_length=40)
    order_date: date
