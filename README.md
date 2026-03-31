# Distributed Voting System (CRDT-based)

## Overview

This project implements a **Distributed Voting and Polling System** composed of multiple nodes that collaboratively collect, replicate, and aggregate votes.

Each node:

- accepts votes independently through a REST API
- maintains a local replica of the voting state
- propagates updates to other nodes on a best-effort basis

Updates are disseminated without coordination or quorum requirements.
If some replicas miss an update due to failures or partitions, periodic anti-entropy synchronization guarantees eventual convergence.

The system is designed to tolerate:

- node failures
- network partitions

and ensures **Strong Eventual Consistency (SEC)** using a **CRDT-based approach**.

---

## Architecture

The system is composed of multiple identical nodes running as Docker containers.

Each node includes:

- REST API (FastAPI)
- CRDT-based state (G-Counter per poll/option/node)
- Write-Ahead Log (WAL) for durability
- Periodic checkpointing
- Anti-entropy synchronization
- Failure detection via heartbeat

### High-level workflow

1. A client submits a vote to any node
2. The node appends the update to the WAL and applies it to its local CRDT state
3. The node attempts to propagate the update to its peers on a best-effort basis
4. Missed updates may temporarily create replica divergence
5. Nodes periodically reconcile state via anti-entropy

---

## Consistency Model

The system provides:

### Strong Eventual Consistency (SEC)

This is achieved through:

- CRDT G-Counter (per poll/option/node)
- Commutative, associative and idempotent merge
- Anti-entropy synchronization

### Guarantees

- No conflicts under concurrent updates
- Deterministic convergence across all nodes
- Monotonic growth of counters
- No data loss after crash (with WAL + checkpoint fix)

Write propagation is best-effort and does not require immediate acknowledgement from all peers.
Therefore, replicas may temporarily diverge, but the combination of CRDT merge semantics and anti-entropy ensures Strong Eventual Consistency.

### Non-goals

The system does **not** guarantee:

- Linearizability
- Strong consistency
- Global ordering of operations

---

## Data Model

Votes are represented using a **G-Counter CRDT**:

```
g_counter[poll_id][option][node_id] = count
```

Each node only increments its own counter.

### Merge rule

When merging replicas:

```
value = max(local_value, remote_value)
```

This ensures:

- idempotency
- convergence without coordination

---

## Durability Model

Each node uses:

- **Write-Ahead Log (WAL)** for every update
- **Periodic checkpoints** to persist full state

### Crash safety

A global durability lock ensures that:

- `WAL append + state apply`
- `checkpoint + WAL truncation`

are serialized.

This guarantees that every update is either:

- included in the checkpoint, or
- preserved in the WAL

→ preventing data loss on restart.

---

## Technologies

- Python
- FastAPI
- Asyncio
- Docker & Docker Compose
- JSON (data exchange)

---

## Running the system

### 1. Start the cluster

```bash
docker compose up --build
```

The system will start multiple nodes (e.g. node1, node2, node3).

---

### 2. Submit a vote

```bash
curl -X POST http://localhost:8001/vote \
  -H "Content-Type: application/json" \
  -d '{"poll_id":"poll1","option":"A"}'
```

---

### 3. Get poll results

```bash
curl http://localhost:8001/poll/poll1
```

---

### 4. Node status

```bash
curl http://localhost:8001/status
```

---

## Network Partition Simulation

The system supports simulation of network partitions using Docker networks.

### Networks

- `progetto_ds_default`: main cluster network
- `ds_isolated`: isolated network

### Isolate a node

```bash
docker network disconnect progetto_ds_default ds_node3
docker network connect ds_isolated ds_node3
```

Now `node3` is running but cannot communicate with other nodes.

---

### Reconnect the node

```bash
docker network disconnect ds_isolated ds_node3
docker network connect progetto_ds_default ds_node3
```

After reconnection, anti-entropy will synchronize the state.

---

## Failure Handling

### Node crash

Simulate:

```bash
docker compose stop node2
docker compose start node2
```

On restart:

- state is recovered from checkpoint + WAL
- node resynchronizes via anti-entropy

---

### Failure detection

Nodes exchange periodic heartbeats.

Each peer can be in one of the following states:

- ALIVE: the peer is responding to heartbeats
- SUSPECT: the peer missed some heartbeats and may be unreachable
- DEAD: the peer is considered unreachable
- UNKNOWN: the peer has not been observed yet or no recent information is available

A peer typically transitions from UNKNOWN to ALIVE after the first successful heartbeat.

This mechanism is **timeout-based** and may produce false positives under network delay.

---

## Anti-Entropy Synchronization

Nodes periodically:

1. select a random peer
2. fetch its full state
3. merge missing updates

This ensures convergence after:

- network partitions
- temporary inconsistencies
- node recovery

---

## Limitations

- Votes are modeled as **increments only**
- No support for:
  - vote changes
  - vote removal
  - "one user = one vote"

- `/vote` is not idempotent (duplicate requests may increase counts)
- Anti-entropy is simple and not bandwidth-optimized
- Failure detector is basic (timeout-based)

---

## Testing

Basic scenarios included:

- Vote propagation across nodes
- Node failure and recovery
- Network partition and reconciliation

---
