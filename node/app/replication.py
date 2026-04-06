import asyncio
import logging

import httpx
from fastapi import APIRouter, HTTPException, Depends

from .config import PEERS, NODE_ID, ANTI_ENTROPY_INTERVAL, INTERNAL_TOKEN
from .models import CounterUpdate, PollCRDTState, ClusterCRDTState
from .state import (
    would_change_update,
    apply_update,
    export_poll_state,
    export_cluster_state,
    extract_new_updates_from_poll_state,
    extract_new_updates_from_cluster_state,
    g_counter,
)
from .storage import append_wal_update
from .locks import durability_lock
from .security import verify_internal_token
from .failure import get_peer_states

logger = logging.getLogger(__name__)
router = APIRouter()

_replication_client: httpx.AsyncClient | None = None
_anti_entropy_client: httpx.AsyncClient | None = None


def internal_auth_headers() -> dict[str, str]:
    if not INTERNAL_TOKEN:
        return {}
    return {"X-Internal-Token": INTERNAL_TOKEN}


def get_replication_client() -> httpx.AsyncClient:
    global _replication_client
    if _replication_client is None:
        _replication_client = httpx.AsyncClient(
            timeout=httpx.Timeout(1.5, connect=0.5),
        )
    return _replication_client


def get_anti_entropy_client() -> httpx.AsyncClient:
    global _anti_entropy_client
    if _anti_entropy_client is None:
        _anti_entropy_client = httpx.AsyncClient(
            timeout=httpx.Timeout(2.0, connect=0.5),
        )
    return _anti_entropy_client


async def close_replication_clients() -> None:
    global _replication_client, _anti_entropy_client

    if _replication_client is not None:
        await _replication_client.aclose()
        _replication_client = None

    if _anti_entropy_client is not None:
        await _anti_entropy_client.aclose()
        _anti_entropy_client = None


def replication_targets() -> list[str]:
    states = get_peer_states()
    return [peer for peer in PEERS if states.get(peer) != "DEAD"]


def anti_entropy_targets() -> list[str]:
    states = get_peer_states()
    return [peer for peer in PEERS if states.get(peer) != "DEAD"]


async def _replicate_update_to_peer(
    peer: str,
    payload: dict,
    headers: dict[str, str],
) -> None:
    client = get_replication_client()
    try:
        resp = await client.post(
            f"{peer}/internal/counter/update",
            json=payload,
            headers=headers,
        )
        logger.info(
            "Replication to %s -> status=%s body=%s",
            peer,
            resp.status_code,
            resp.text,
        )
        resp.raise_for_status()
    except Exception as e:
        logger.warning("Replication to %s failed: %r", peer, e)


async def replicate_update_to_peers(upd: CounterUpdate) -> None:
    targets = replication_targets()
    if not targets:
        return

    headers = internal_auth_headers()
    payload = upd.model_dump()

    logger.info(
        "Replicating update from %s headers=%s payload=%s targets=%s",
        NODE_ID,
        headers,
        payload,
        targets,
    )

    await asyncio.gather(
        *[
            _replicate_update_to_peer(peer, payload, headers)
            for peer in targets
        ],
        return_exceptions=True,
    )


@router.post("/internal/counter/update")
def internal_counter_update(
    upd: CounterUpdate,
    _: None = Depends(verify_internal_token),
):
    logger.info(
        "[%s] RECEIVED update: poll=%s option=%s node=%s value=%s",
        NODE_ID,
        upd.poll_id,
        upd.option,
        upd.node_id,
        upd.value,
    )

    with durability_lock:
        prev = g_counter.get(upd.poll_id, {}).get(upd.option, {}).get(upd.node_id, 0)
        changed = would_change_update(upd)

        logger.info(
            "[%s] BEFORE apply: prev=%s incoming=%s changed=%s",
            NODE_ID,
            prev,
            upd.value,
            changed,
        )

        if changed:
            append_wal_update(upd)
            apply_update(upd)
            logger.info("[%s] APPLIED update", NODE_ID)
        else:
            logger.warning("[%s] IGNORED update (not newer)", NODE_ID)

    return {"ok": True, "changed": changed, "node": NODE_ID}


@router.get("/internal/cluster-state")
def internal_cluster_state(_: None = Depends(verify_internal_token)) -> ClusterCRDTState:
    return export_cluster_state()


@router.post("/internal/cluster-merge")
def internal_cluster_merge(
    other: ClusterCRDTState,
    _: None = Depends(verify_internal_token),
):
    with durability_lock:
        updates = extract_new_updates_from_cluster_state(other)
        for upd in updates:
            append_wal_update(upd)
            apply_update(upd)

    return {"ok": True, "applied_updates": len(updates), "node": NODE_ID}


@router.get("/internal/state/{poll_id}")
def internal_state(
    poll_id: str,
    _: None = Depends(verify_internal_token),
) -> PollCRDTState:
    return export_poll_state(poll_id)


@router.post("/internal/merge/{poll_id}")
def internal_merge(
    poll_id: str,
    other: PollCRDTState,
    _: None = Depends(verify_internal_token),
):
    with durability_lock:
        updates = extract_new_updates_from_poll_state(poll_id, other)
        for upd in updates:
            append_wal_update(upd)
            apply_update(upd)

    return {"ok": True, "applied_updates": len(updates), "node": NODE_ID}


@router.post("/internal/sync/{poll_id}")
async def internal_sync(poll_id: str, _: None = Depends(verify_internal_token)):
    targets = replication_targets()
    if not targets:
        raise HTTPException(status_code=503, detail="No peer reachable for sync")

    client = get_replication_client()

    for peer in targets:
        try:
            st = await client.get(
                f"{peer}/internal/state/{poll_id}",
                headers=internal_auth_headers(),
            )
            st.raise_for_status()
            other = PollCRDTState(**st.json())

            with durability_lock:
                updates = extract_new_updates_from_poll_state(poll_id, other)
                for upd in updates:
                    append_wal_update(upd)
                    apply_update(upd)

            return {
                "ok": True,
                "synced_from": peer,
                "applied_updates": len(updates),
                "node": NODE_ID,
            }
        except Exception as e:
            logger.warning("Sync for poll %s from %s failed: %r", poll_id, peer, e)

    raise HTTPException(status_code=503, detail="No peer reachable for sync")


async def _pull_cluster_state_from_peer(peer: str) -> ClusterCRDTState | None:
    client = get_anti_entropy_client()
    try:
        resp = await client.get(
            f"{peer}/internal/cluster-state",
            headers=internal_auth_headers(),
        )
        resp.raise_for_status()
        return ClusterCRDTState(**resp.json())
    except Exception as e:
        logger.warning("Anti-entropy failed from %s: %r", peer, e)
        return None


async def anti_entropy_loop() -> None:
    if not PEERS:
        return

    # lascia assestare il cluster all'avvio
    await asyncio.sleep(2)

    while True:
        try:
            targets = anti_entropy_targets()

            if targets:
                states = await asyncio.gather(
                    *[_pull_cluster_state_from_peer(peer) for peer in targets],
                    return_exceptions=True,
                )

                with durability_lock:
                    for other in states:
                        if isinstance(other, Exception) or other is None:
                            continue

                        updates = extract_new_updates_from_cluster_state(other)
                        for upd in updates:
                            append_wal_update(upd)
                            apply_update(upd)
        except Exception as e:
            logger.warning("Anti-entropy loop error: %r", e)

        await asyncio.sleep(ANTI_ENTROPY_INTERVAL)