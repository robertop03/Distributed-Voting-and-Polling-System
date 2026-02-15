# replicate_to_peers + endpoints internal
import asyncio
import httpx
from fastapi import APIRouter, HTTPException
from .config import PEERS, NODE_ID
from .models import VoteEvent, PollState
from .state import apply_vote_event, ensure_poll, poll_counts, seen_votes, clock

router = APIRouter()

async def replicate_to_peers(ev: VoteEvent):
    if not PEERS:
        return

    async with httpx.AsyncClient(timeout=1.5) as client:
        tasks = []
        for peer in PEERS:
            tasks.append(
                client.post(f"{peer}/internal/replicate", json=ev.model_dump())
            )
        await asyncio.gather(*tasks, return_exceptions=True)

@router.post("/internal/replicate")
def internal_replicate(ev: VoteEvent):
    applied = apply_vote_event(ev)
    return {"ok": True, "applied": applied, "node": NODE_ID}

@router.get("/internal/state/{poll_id}")
def internal_state(poll_id: str):
    ensure_poll(poll_id)
    return PollState(
        counts=poll_counts[poll_id],
        seen_votes=list(seen_votes[poll_id]),
        clock=clock,
    )

@router.post("/internal/sync/{poll_id}")
async def internal_sync(poll_id: str):
    ensure_poll(poll_id)

    async with httpx.AsyncClient(timeout=2.0) as client:
        for peer in PEERS:
            try:
                st = await client.get(f"{peer}/internal/state/{poll_id}")
                other = PollState(**st.json())
                apply_vote_event(other)  # semplice merge MVP
                return {"ok": True, "synced_from": peer}
            except Exception:
                continue

    raise HTTPException(status_code=503, detail="No peer reachable")
