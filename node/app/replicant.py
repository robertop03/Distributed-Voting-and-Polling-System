# replicate_to_peers + endpoints internal
import asyncio
import httpx
from fastapi import APIRouter, HTTPException
from .config import PEERS, NODE_ID
from .models import CounterUpdate, PollCRDTState
from .state import merge_update, export_poll_state, merge_poll_state

router = APIRouter()


async def replicate_update_to_peers(upd: CounterUpdate) -> None:
    """
    Best-effort, idempotent replication: send component value to peers.
    Safe with retries/duplicates because receivers do max().
    """
    if not PEERS:
        return

    async with httpx.AsyncClient(timeout=1.5) as client:
        tasks = []
        for peer in PEERS:
            tasks.append(
                client.post(f"{peer}/internal/counter/update", json=upd.model_dump())
            )
        await asyncio.gather(*tasks, return_exceptions=True)


@router.post("/internal/counter/update")
def internal_counter_update(upd: CounterUpdate):
    changed = merge_update(upd)
    return {"ok": True, "changed": changed, "node": NODE_ID}


@router.get("/internal/state/{poll_id}")
def internal_state(poll_id: str) -> PollCRDTState:
    return export_poll_state(poll_id)


@router.post("/internal/merge/{poll_id}")
def internal_merge(poll_id: str, other: PollCRDTState):
    merge_poll_state(poll_id, other)
    return {"ok": True, "node": NODE_ID}


@router.post("/internal/sync/{poll_id}")
async def internal_sync(poll_id: str):
    """
    Pull full state from first reachable peer and merge it.
    """
    if not PEERS:
        raise HTTPException(status_code=503, detail="No peers configured")

    async with httpx.AsyncClient(timeout=2.0) as client:
        for peer in PEERS:
            try:
                st = await client.get(f"{peer}/internal/state/{poll_id}")
                other = PollCRDTState(**st.json())
                merge_poll_state(poll_id, other)
                return {"ok": True, "synced_from": peer, "node": NODE_ID}
            except Exception:
                continue

    raise HTTPException(status_code=503, detail="No peer reachable for sync")

