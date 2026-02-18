# env vars + constants
import os

NODE_ID = os.getenv("NODE_ID", "nodeX")
PORT = int(os.getenv("PORT", "8000"))
PEERS = [p.strip() for p in os.getenv("PEERS", "").split(",") if p.strip()]

HEARTBEAT_INTERVAL = float(os.getenv("HEARTBEAT_INTERVAL", "1.0"))
SUSPECT_TIMEOUT = float(os.getenv("SUSPECT_TIMEOUT", "3.0"))
DEAD_TIMEOUT = float(os.getenv("DEAD_TIMEOUT", "6.0"))
ANTI_ENTROPY_INTERVAL = float(os.getenv("ANTI_ENTROPY_INTERVAL", "5.0"))