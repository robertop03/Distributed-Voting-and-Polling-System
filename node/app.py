import os
import uuid
import asyncio
from typing import Dict, Set, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import httpx


# Config
NODE_ID = os.getenv("NODE_ID", "nodeX")
PORT = int(os.getenv("PORT", "8000"))
PEERS = [p.strip() for p in os.getenv("PEERS", "").split(",") if p.strip()]

app = FastAPI(title=f"Distributed Voting Node ({NODE_ID})")


# Models
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


# In-memory state (MVP)
clock: int = 0
poll_counts: Dict[str, Dict[str, int]] = {}          # poll_id -> option -> count
seen_votes: Dict[str, Set[str]] = {}                # poll_id -> set(vote_id)

def _ensure_poll(poll_id: str) -> None:
    if poll_id not in poll_counts:
        poll_counts[poll_id] = {}
    if poll_id not in seen_votes:
        seen_votes[poll_id] = set()

def _apply_vote_event(ev: VoteEvent) -> bool:
    """
    Returns True if applied, False if duplicate.
    """
    global clock
    _ensure_poll(ev.poll_id)

    # Lamport receive rule
    clock = max(clock, ev.ts) + 1

    if ev.vote_id in seen_votes[ev.poll_id]:
        return False  # idempotent

    seen_votes[ev.poll_id].add(ev.vote_id)
    poll_counts[ev.poll_id][ev.option] = poll_counts[ev.poll_id].get(ev.option, 0) + 1
    return True

async def _replicate_to_peers(ev: VoteEvent) -> None:
    """
    Best effort replication: do not fail the client vote if some peer is down.
    """
    if not PEERS:
        return

    async with httpx.AsyncClient(timeout=1.5) as client:
        tasks = []
        for peer in PEERS:
            url = f"{peer}/internal/replicate"
            tasks.append(client.post(url, json=ev.model_dump()))
        # Fire and gather (ignore errors)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # Optional: you could log results/exceptions here


# Client-facing APIs
@app.post("/vote")
async def vote(v: VoteIn):
    global clock
    _ensure_poll(v.poll_id)

    # Lamport send rule
    clock += 1
    ev = VoteEvent(
        vote_id=str(uuid.uuid4()),
        poll_id=v.poll_id,
        option=v.option,
        ts=clock,
        origin=NODE_ID,
    )

    # Apply locally
    _apply_vote_event(ev)

    # Replicate asynchronously (best effort)
    await _replicate_to_peers(ev)

    return {"ok": True, "node": NODE_ID, "vote_id": ev.vote_id, "ts": ev.ts}

@app.get("/poll/{poll_id}")
def get_poll(poll_id: str):
    _ensure_poll(poll_id)
    return {
        "poll_id": poll_id,
        "counts": poll_counts[poll_id],
        "node": NODE_ID,
        "clock": clock,
        "seen_votes": len(seen_votes[poll_id]),
    }


# Internal APIs (node-to-node)
@app.post("/internal/replicate")
def internal_replicate(ev: VoteEvent):
    applied = _apply_vote_event(ev)
    return {"ok": True, "applied": applied, "node": NODE_ID, "clock": clock}

@app.get("/internal/state/{poll_id}")
def internal_state(poll_id: str) -> PollState:
    _ensure_poll(poll_id)
    return PollState(
        counts=poll_counts[poll_id],
        seen_votes=list(seen_votes[poll_id]),
        clock=clock,
    )

@app.post("/internal/merge/{poll_id}")
def internal_merge(poll_id: str, other: PollState):
    """
    Merge strategy (MVP):
    - Use seen_votes to avoid double count.
    - Reconstruct counts from 'other' votes by comparing vote ids is expensive without full log.
      For MVP we do a conservative merge:
        * union seen_votes
        * take max per option count (works if nodes are eventually consistent + idempotent replication).
    This is not perfect in all cases, but is fine for the first milestone.
    """
    global clock
    _ensure_poll(poll_id)

    # merge clock
    clock = max(clock, other.clock) + 1

    # merge seen votes
    local_seen = seen_votes[poll_id]
    local_seen.update(other.seen_votes)

    # merge counts (MVP heuristic: max counts per option)
    for opt, cnt in other.counts.items():
        poll_counts[poll_id][opt] = max(poll_counts[poll_id].get(opt, 0), cnt)

    return {"ok": True, "node": NODE_ID, "clock": clock, "seen_votes": len(local_seen)}

@app.post("/internal/sync/{poll_id}")
async def internal_sync(poll_id: str):
    """
    Pull state from the first reachable peer and merge it.
    Useful after restart.
    """
    _ensure_poll(poll_id)

    async with httpx.AsyncClient(timeout=2.0) as client:
        for peer in PEERS:
            try:
                st = await client.get(f"{peer}/internal/state/{poll_id}")
                other = PollState(**st.json())
                # merge locally via function
                internal_merge(poll_id, other)
                return {"ok": True, "synced_from": peer, "node": NODE_ID}
            except Exception:
                continue

    raise HTTPException(status_code=503, detail="No peer reachable for sync")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, log_level="info")
