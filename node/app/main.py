from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
import logging
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from .locks import durability_lock
from .config import NODE_ID, CHECKPOINT_INTERVAL
from .models import VoteIn

from .state import (
    build_local_increment_update,
    apply_update,
    query_poll_counts,
    replace_cluster_state,
    list_polls
)
from .replication import (
    router as replication_router,
    replicate_update_to_peers,
    anti_entropy_loop,
    close_replication_clients,
)
from .failure import router as failure_router, heartbeat_loop
from .storage import (
    ensure_storage,
    load_checkpoint,
    load_wal_updates,
    write_checkpoint,
    truncate_wal,
    append_wal_update,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent
UI_DIR = BASE_DIR / "ui"

async def checkpoint_loop():
    while True:
        await asyncio.sleep(CHECKPOINT_INTERVAL)
        from .state import export_cluster_state

        with durability_lock:
            state = export_cluster_state()
            write_checkpoint(state)
            truncate_wal()


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_storage()

    # Recovery: checkpoint + WAL replay
    snapshot = load_checkpoint()
    replace_cluster_state(snapshot)

    wal_updates = load_wal_updates()
    for upd in wal_updates:
        apply_update(upd)

    tasks = [
        asyncio.create_task(heartbeat_loop(), name="heartbeat_loop"),
        asyncio.create_task(anti_entropy_loop(), name="anti_entropy_loop"),
        asyncio.create_task(checkpoint_loop(), name="checkpoint_loop"),
    ]
    try:
        yield
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await close_replication_clients()


app = FastAPI(
    title=f"Distributed Voting Node ({NODE_ID})",
    lifespan=lifespan
)

app.include_router(replication_router)
app.include_router(failure_router)

app.mount("/ui", StaticFiles(directory=str(UI_DIR), html=True), name="ui")


@app.get("/")
def root():
    return RedirectResponse(url="/ui/")


@app.get("/polls")
def get_polls():
    poll_ids = sorted(list_polls())
    return {"poll_ids": poll_ids, "node": NODE_ID}


@app.post("/vote")
async def vote(v: VoteIn):
    with durability_lock:
        upd = build_local_increment_update(v.poll_id, v.option)
        append_wal_update(upd)
        apply_update(upd)

    asyncio.create_task(replicate_update_to_peers(upd))
    return {"ok": True, "node": NODE_ID, "update": upd.model_dump()}


@app.get("/poll/{poll_id}")
def get_poll(poll_id: str):
    counts = query_poll_counts(poll_id)
    return {"poll_id": poll_id, "counts": counts, "node": NODE_ID}