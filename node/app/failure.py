# heartbeat loop + status computation
import time
import asyncio
import httpx
from fastapi import APIRouter
from .config import PEERS, NODE_ID, PORT, HEARTBEAT_INTERVAL, SUSPECT_TIMEOUT, DEAD_TIMEOUT

router = APIRouter()

# Manteniamo lo stato solo per i peer "ufficiali" (quelli in PEERS)
peer_last_seen = {peer: 0.0 for peer in PEERS}


def _normalize_sender(sender: str) -> str:
    """
    Normalizza sender in modo che includa sempre la porta, es:
    http://node2 -> http://node2:8002 (se è un peer noto)
    Se non è riconoscibile, lo lasciamo com'è.
    """
    sender = sender.strip()

    # Se arriva già con porta, ok
    if ":" in sender.replace("http://", "").replace("https://", ""):
        return sender

    # Se manca porta, proviamo a matchare con uno dei PEERS
    # es: sender="http://node2" e in PEERS c'è "http://node2:8002"
    for p in PEERS:
        if p.startswith(sender + ":"):
            return p

    return sender


@router.post("/internal/heartbeat")
def internal_heartbeat(sender: str):
    """
    Endpoint chiamato dai peer per segnalare che sono vivi.
    Aggiorna last_seen SOLO per peer noti, così evitiamo duplicati.
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

    async with httpx.AsyncClient(timeout=1.0) as client:
        while True:
            for peer in PEERS:
                try:
                    await client.post(
                        f"{peer}/internal/heartbeat",
                        params={"sender": my_sender},
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
