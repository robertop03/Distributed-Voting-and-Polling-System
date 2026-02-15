# Pydantic models
from typing import Dict, List
from pydantic import BaseModel, Field

class VoteIn(BaseModel):
    poll_id: str = Field(..., examples=["poll1"])
    option: str = Field(..., examples=["A"])

class VoteEvent(BaseModel):
    vote_id: str
    poll_id: str
    option: str
    ts: int
    origin: str

class PollState(BaseModel):
    counts: Dict[str, int]
    seen_votes: List[str]
    clock: int
