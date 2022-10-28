from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class Input(BaseModel):
    indexed: Optional[bool] = None
    internalType: str
    name: str
    type: str


class Output(BaseModel):
    internalType: str
    name: str
    type: str


class GlpModel(BaseModel):
    inputs: List[Input]
    stateMutability: Optional[str] = None
    type: str
    anonymous: Optional[bool] = None
    name: Optional[str] = None
    outputs: Optional[List[Output]] = None
