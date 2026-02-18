from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio

from .config import NODE_ID
from .models import VoteIn
from .state import local_increment, query_poll_counts
from .replication import (
    router as replication_router,
    replicate_update_to_peers,
    anti_entropy_loop,
)
from .failure import router as failure_router, heartbeat_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: background tasks
    asyncio.create_task(heartbeat_loop())
    asyncio.create_task(anti_entropy_loop())
    yield
    # Shutdown: nothing to clean up for MVP


app = FastAPI(
    title=f"Distributed Voting Node ({NODE_ID})",
    lifespan=lifespan
)

app.include_router(replication_router)
app.include_router(failure_router)


@app.post("/vote")
async def vote(v: VoteIn):
    upd = local_increment(v.poll_id, v.option)
    await replicate_update_to_peers(upd)
    return {"ok": True, "node": NODE_ID, "update": upd.model_dump()}


@app.get("/poll/{poll_id}")
def get_poll(poll_id: str):
    counts = query_poll_counts(poll_id)
    return {"poll_id": poll_id, "counts": counts, "node": NODE_ID}