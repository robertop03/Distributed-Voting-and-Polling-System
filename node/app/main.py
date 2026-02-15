# FastAPI app + routes
import uuid
from fastapi import FastAPI
from .config import NODE_ID
from .models import VoteIn, VoteEvent
from .state import ensure_poll, apply_vote_event, clock
from .replicant import replicate_to_peers, router as replication_router
from .failure import router as failure_router, heartbeat_loop

app = FastAPI(title=f"Distributed Voting Node ({NODE_ID})")

# include routers
app.include_router(replication_router)
app.include_router(failure_router)

@app.on_event("startup")
async def startup():
    import asyncio
    asyncio.create_task(heartbeat_loop())

@app.post("/vote")
async def vote(v: VoteIn):
    from .state import clock

    ensure_poll(v.poll_id)

    clock += 1
    ev = VoteEvent(
        vote_id=str(uuid.uuid4()),
        poll_id=v.poll_id,
        option=v.option,
        ts=clock,
        origin=NODE_ID,
    )

    apply_vote_event(ev)
    await replicate_to_peers(ev)

    return {"ok": True, "node": NODE_ID}

@app.get("/poll/{poll_id}")
def get_poll(poll_id: str):
    from .state import poll_counts
    ensure_poll(poll_id)
    return {"poll_id": poll_id, "counts": poll_counts[poll_id]}
