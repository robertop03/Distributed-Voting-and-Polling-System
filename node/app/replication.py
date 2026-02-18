import asyncio
import random
import httpx
from fastapi import APIRouter, HTTPException
from .config import PEERS, NODE_ID, ANTI_ENTROPY_INTERVAL
from .models import CounterUpdate, PollCRDTState, ClusterCRDTState
from .state import (
    merge_update,
    export_poll_state,
    merge_poll_state,
    export_cluster_state,
    merge_cluster_state,
)

router = APIRouter()


async def replicate_update_to_peers(upd: CounterUpdate) -> None:
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


# ----------- per-poll sync (rimane utile) -----------

@router.get("/internal/state/{poll_id}")
def internal_state(poll_id: str) -> PollCRDTState:
    return export_poll_state(poll_id)


@router.post("/internal/merge/{poll_id}")
def internal_merge(poll_id: str, other: PollCRDTState):
    merge_poll_state(poll_id, other)
    return {"ok": True, "node": NODE_ID}


@router.post("/internal/sync/{poll_id}")
async def internal_sync(poll_id: str):
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

@router.get("/internal/state/all")
def internal_state_all() -> ClusterCRDTState:
    return export_cluster_state()

@router.post("/internal/merge/all")
def internal_merge_all(other: ClusterCRDTState):
    merge_cluster_state(other)
    return {"ok": True, "node": NODE_ID}

async def anti_entropy_loop() -> None:
    """
    Periodically pull full CRDT state from a random peer and merge it.
    This guarantees automatic convergence after crashes/partitions.
    """
    if not PEERS:
        return

    async with httpx.AsyncClient(timeout=2.0) as client:
        while True:
            peer = random.choice(PEERS)
            try:
                resp = await client.get(f"{peer}/internal/state/all")
                other = ClusterCRDTState(**resp.json())
                merge_cluster_state(other)
            except Exception:
                pass

            await asyncio.sleep(ANTI_ENTROPY_INTERVAL)