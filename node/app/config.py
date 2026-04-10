# env vars + constants
import os
import math

NODE_ID = os.getenv("NODE_ID", "nodeX")
PORT = int(os.getenv("PORT", "8000"))
PEERS = [p.strip() for p in os.getenv("PEERS", "").split(",") if p.strip()]
CLUSTER_SIZE = int(os.getenv("CLUSTER_SIZE", str(len(PEERS) + 1)))
BASE_STARTUP_DELAY = float(os.getenv("BASE_STARTUP_DELAY", "4"))

DATA_DIR = os.getenv("DATA_DIR", "/data")
CHECKPOINT_FILE = os.path.join(DATA_DIR, "checkpoint.json")
WAL_FILE = os.path.join(DATA_DIR, "wal.jsonl")
INTERNAL_TOKEN = os.getenv("INTERNAL_TOKEN", "")

def adaptive_fanout(n: int) -> int:
    return min(5, max(2, math.ceil(math.sqrt(n))))

def adaptive_heartbeat_interval(n: int) -> float:
    if n <= 10:
        return 2.0
    return 3.0 + n / 25.0

def adaptive_anti_entropy_interval(n: int) -> float:
    if n <= 10:
        return 5.0
    return 8.0 + n / 10.0

def adaptive_startup_delay(n: int) -> float:
    return BASE_STARTUP_DELAY + 0.25 * n

def adaptive_connect_timeout(n: int) -> float:
    return 0.8 if n <= 10 else 1.5

def adaptive_request_timeout(n: int) -> float:
    return 3.0 if n <= 10 else 5.0

FANOUT = adaptive_fanout(CLUSTER_SIZE)
HEARTBEAT_INTERVAL = adaptive_heartbeat_interval(CLUSTER_SIZE)
ANTI_ENTROPY_INTERVAL = adaptive_anti_entropy_interval(CLUSTER_SIZE)
STARTUP_DELAY = adaptive_startup_delay(CLUSTER_SIZE)
CONNECT_TIMEOUT = adaptive_connect_timeout(CLUSTER_SIZE)
REQUEST_TIMEOUT = adaptive_request_timeout(CLUSTER_SIZE)

SUSPECT_TIMEOUT = max(3 * HEARTBEAT_INTERVAL, 10.0)
DEAD_TIMEOUT = max(2 * SUSPECT_TIMEOUT, 20.0)
CHECKPOINT_INTERVAL = 10.0 if CLUSTER_SIZE <= 10 else 15.0