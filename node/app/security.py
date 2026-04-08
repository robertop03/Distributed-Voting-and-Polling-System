from fastapi import Header, HTTPException
from .config import INTERNAL_TOKEN


def verify_internal_token(x_internal_token: str | None = Header(default=None)) -> None:
    if not INTERNAL_TOKEN:
        raise RuntimeError("INTERNAL_TOKEN is required for internal cluster communication")

    if x_internal_token != INTERNAL_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")