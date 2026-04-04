# heartbeat loop + status computation
import time
import asyncio
import httpx
from fastapi import APIRouter, Depends
from urllib.parse import urlparse
from .config import PEERS, NODE_ID, PORT, HEARTBEAT_INTERVAL, SUSPECT_TIMEOUT, DEAD_TIMEOUT, INTERNAL_TOKEN
from .security import verify_internal_token

router = APIRouter()

# Manteniamo lo stato solo per i peer "ufficiali" (quelli in PEERS)
peer_last_seen = {peer: 0.0 for peer in PEERS}

def internal_auth_headers() -> dict[str, str]:
    if not INTERNAL_TOKEN:
        return {}
    return {"X-Internal-Token": INTERNAL_TOKEN}


def _normalize_sender(sender: str) -> str:
    """
    Normalize sender so that it matches one of the configured PEERS
    using structured URL parsing instead of string heuristics.

    Examples:
    - http://node2:8002 -> http://node2:8002
    - http://node2      -> http://node2:8002   (if uniquely identifiable in PEERS)
    - node2:8002        -> http://node2:8002
    """
    sender = sender.strip()
    if not sender:
        return sender

    parsed_sender = urlparse(sender if "://" in sender else f"http://{sender}")
    sender_host = parsed_sender.hostname
    sender_port = parsed_sender.port

    if sender_host is None:
        return sender

    # Exact host:port match against configured peers
    for peer in PEERS:
        parsed_peer = urlparse(peer if "://" in peer else f"http://{peer}")
        if parsed_peer.hostname == sender_host and parsed_peer.port == sender_port:
            return peer

    # Fallback: if sender has no port, try unique hostname match
    if sender_port is None:
        matches = []
        for peer in PEERS:
            parsed_peer = urlparse(peer if "://" in peer else f"http://{peer}")
            if parsed_peer.hostname == sender_host:
                matches.append(peer)

        if len(matches) == 1:
            return matches[0]

    return sender


@router.post("/internal/heartbeat")
def internal_heartbeat(sender: str, _: None = Depends(verify_internal_token)):
    """
    Endpoint used by peers to signal they are alive.
    Updates last_seen only for configured peers, avoiding duplicate identities.
    """
    now = time.monotonic()
    sender = _normalize_sender(sender)

    if sender in peer_last_seen:
        peer_last_seen[sender] = now

    return {"ok": True, "node": NODE_ID, "received_from": sender}


async def heartbeat_loop():
    """
    Loop in background: invia heartbeat a tutti i peer (best effort).
    """
    if not PEERS:
        return

    my_sender = f"http://{NODE_ID}:{PORT}"

    async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=1.0)) as client:
        while True:
            for peer in PEERS:
                try:
                    await client.post(
                        f"{peer}/internal/heartbeat",
                        params={"sender": my_sender},
                        headers=internal_auth_headers()
                    )
                except Exception:
                    # peer down/unreachable: ignora, verrà segnato SUSPECT/DEAD dai timeout
                    pass

            await asyncio.sleep(HEARTBEAT_INTERVAL)


@router.get("/status")
def status():
    """
    Restituisce lo stato dei peer in base a quanto tempo fa è arrivato l'ultimo heartbeat.
    """
    now = time.monotonic()
    result = {"node": NODE_ID, "peers": []}

    for peer, last in peer_last_seen.items():
        age = None if last == 0.0 else (now - last)

        if last == 0.0:
            state = "UNKNOWN"
        elif age <= SUSPECT_TIMEOUT:
            state = "ALIVE"
        elif age <= DEAD_TIMEOUT:
            state = "SUSPECT"
        else:
            state = "DEAD"

        result["peers"].append(
            {
                "peer": peer,
                "state": state,
                "last_seen_seconds_ago": None if age is None else round(age, 2),
            }
        )

    return result

def get_peer_states() -> dict[str, str]:
    now = time.monotonic()
    states: dict[str, str] = {}

    for peer, last in peer_last_seen.items():
        age = None if last == 0.0 else (now - last)

        if last == 0.0:
            state = "UNKNOWN"
        elif age <= SUSPECT_TIMEOUT:
            state = "ALIVE"
        elif age <= DEAD_TIMEOUT:
            state = "SUSPECT"
        else:
            state = "DEAD"

        states[peer] = state

    return states
