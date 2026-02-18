from typing import Dict, List
from .config import NODE_ID
from .models import CounterUpdate, PollCRDTState, ClusterCRDTState

# g_counter[poll_id][option][node_id] = int
g_counter: Dict[str, Dict[str, Dict[str, int]]] = {}


def list_polls() -> List[str]:
    return list(g_counter.keys())


def ensure_poll(poll_id: str) -> None:
    if poll_id not in g_counter:
        g_counter[poll_id] = {}


def ensure_option(poll_id: str, option: str) -> None:
    ensure_poll(poll_id)
    if option not in g_counter[poll_id]:
        g_counter[poll_id][option] = {}


def local_increment(poll_id: str, option: str) -> CounterUpdate:
    ensure_option(poll_id, option)
    current = g_counter[poll_id][option].get(NODE_ID, 0) + 1
    g_counter[poll_id][option][NODE_ID] = current
    return CounterUpdate(poll_id=poll_id, option=option, node_id=NODE_ID, value=current)


def merge_update(upd: CounterUpdate) -> bool:
    ensure_option(upd.poll_id, upd.option)
    prev = g_counter[upd.poll_id][upd.option].get(upd.node_id, 0)
    newv = max(prev, upd.value)
    changed = newv != prev
    g_counter[upd.poll_id][upd.option][upd.node_id] = newv
    return changed


def export_poll_state(poll_id: str) -> PollCRDTState:
    ensure_poll(poll_id)
    counts = {opt: dict(nodes) for opt, nodes in g_counter[poll_id].items()}
    return PollCRDTState(counts=counts)


def merge_poll_state(poll_id: str, other: PollCRDTState) -> None:
    ensure_poll(poll_id)
    for opt, nodes in other.counts.items():
        ensure_option(poll_id, opt)
        for node_id, value in nodes.items():
            prev = g_counter[poll_id][opt].get(node_id, 0)
            g_counter[poll_id][opt][node_id] = max(prev, value)


def export_cluster_state() -> ClusterCRDTState:
    polls: Dict[str, PollCRDTState] = {}
    for poll_id in g_counter.keys():
        polls[poll_id] = export_poll_state(poll_id)
    return ClusterCRDTState(polls=polls)


def merge_cluster_state(other: ClusterCRDTState) -> None:
    for poll_id, poll_state in other.polls.items():
        merge_poll_state(poll_id, poll_state)


def query_poll_counts(poll_id: str) -> Dict[str, int]:
    ensure_poll(poll_id)
    result: Dict[str, int] = {}
    for opt, nodes in g_counter[poll_id].items():
        result[opt] = sum(nodes.values())
    return result