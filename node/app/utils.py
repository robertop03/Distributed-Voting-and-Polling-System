from .config import INTERNAL_TOKEN


def internal_auth_headers() -> dict[str, str]:
    if not INTERNAL_TOKEN:
        return {}
    return {"X-Internal-Token": INTERNAL_TOKEN}