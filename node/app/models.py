# Pydantic models
from typing import Dict
from pydantic import BaseModel, Field


class VoteIn(BaseModel):
    poll_id: str = Field(..., examples=["poll1"])
    option: str = Field(..., examples=["A"])


class CounterUpdate(BaseModel):
    """
    Idempotent update: it carries the new value of one component of the G-Counter.
    Receiving the same update multiple times is safe because we merge with max().
    """
    poll_id: str
    option: str
    node_id: str
    value: int


class PollCRDTState(BaseModel):
    """
    Full CRDT state for one poll:
    counts[option][node_id] = value
    """
    counts: Dict[str, Dict[str, int]]
