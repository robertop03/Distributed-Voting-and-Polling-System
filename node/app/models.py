from typing import Dict, Annotated
from pydantic import BaseModel, Field, StringConstraints


class VoteIn(BaseModel):
    poll_id: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=64)
    ] = Field(..., examples=["poll1"])

    option: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=32)
    ] = Field(..., examples=["A"])


class CounterUpdate(BaseModel):
    """
    Idempotent update: carries the new value of one component of the G-Counter.
    Receiver merges with max().
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


class ClusterCRDTState(BaseModel):
    """
    Full CRDT state for all polls:
    polls[poll_id] = PollCRDTState
    """
    polls: Dict[str, PollCRDTState]