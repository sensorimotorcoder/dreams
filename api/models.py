"""Pydantic models describing API inputs and outputs."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class InRow(BaseModel):
    row: int
    new_id: Optional[str] = None
    text: str


class CodePayload(BaseModel):
    rows: List[InRow]
    preset: Optional[str] = None


class CodeResult(BaseModel):
    row: int
    code_version: str
    preset_version: str
    coded: Dict[str, Any]


class ExtendPayload(BaseModel):
    base_preset: Optional[str] = None
    categories: List[str]
    keywords: Dict[str, List[str]] = Field(default_factory=dict)
    exceptions: Dict[str, List[str]] = Field(default_factory=dict)
    policy: Dict[str, Any] = Field(default_factory=dict)


class ExtendResult(BaseModel):
    proposed: Dict[str, List[Dict[str, Any]]]
    conflicts: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
