from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio

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
)
from .replication import (
    router as replication_router,
    replicate_update_to_peers,
    anti_entropy_loop,
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

    asyncio.create_task(heartbeat_loop())
    asyncio.create_task(anti_entropy_loop())
    asyncio.create_task(checkpoint_loop())

    yield


app = FastAPI(
    title=f"Distributed Voting Node ({NODE_ID})",
    lifespan=lifespan
)

app.include_router(replication_router)
app.include_router(failure_router)

app.mount("/ui", StaticFiles(directory="app/ui", html=True), name="ui")


@app.get("/")
def root():
    return RedirectResponse(url="/ui/")


@app.post("/vote")
async def vote(v: VoteIn):
    with durability_lock:
        upd = build_local_increment_update(v.poll_id, v.option)
        append_wal_update(upd)
        apply_update(upd)

    await replicate_update_to_peers(upd)
    return {"ok": True, "node": NODE_ID, "update": upd.model_dump()}


@app.get("/poll/{poll_id}")
def get_poll(poll_id: str):
    counts = query_poll_counts(poll_id)
    return {"poll_id": poll_id, "counts": counts, "node": NODE_ID}