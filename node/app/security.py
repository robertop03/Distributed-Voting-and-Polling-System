from fastapi import Header, HTTPException
from .config import INTERNAL_TOKEN


def verify_internal_token(x_internal_token: str | None = Header(default=None)) -> None:
    if not INTERNAL_TOKEN:
        raise HTTPException(status_code=500, detail="INTERNAL_TOKEN not configured on this node")


    if x_internal_token != INTERNAL_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")