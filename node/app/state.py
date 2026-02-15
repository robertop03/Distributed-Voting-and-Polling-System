# in-memory state + helpers
from typing import Dict, Set
from .models import VoteEvent

clock: int = 0
poll_counts: Dict[str, Dict[str, int]] = {}
seen_votes: Dict[str, Set[str]] = {}

def ensure_poll(poll_id: str) -> None:
    if poll_id not in poll_counts:
        poll_counts[poll_id] = {}
    if poll_id not in seen_votes:
        seen_votes[poll_id] = set()

def apply_vote_event(ev: VoteEvent) -> bool:
    global clock
    ensure_poll(ev.poll_id)

    clock = max(clock, ev.ts) + 1

    if ev.vote_id in seen_votes[ev.poll_id]:
        return False

    seen_votes[ev.poll_id].add(ev.vote_id)
    poll_counts[ev.poll_id][ev.option] = poll_counts[ev.poll_id].get(ev.option, 0) + 1
    return True
