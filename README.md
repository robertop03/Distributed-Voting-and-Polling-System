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

## Prerequisites

Make sure the following tools are installed:

- Git
- Docker
- Docker Compose
- Python 3

Verify installation:

```bash
git --version
docker --version
docker compose version
python --version
```

On Windows, you may need to use:

```bash
py --version
```

---

## Clone the Repository

```bash
git clone https://github.com/robertop03/Distributed-Voting-and-Polling-System
cd Distributed-Voting-and-Polling-System
```

---

## Running the System

### Start the cluster

The system can be started with a configurable number of nodes.

Example (3 nodes):

```bash
python run_cluster.py 3
```

You can choose any number of nodes:

```bash
python run_cluster.py 5
```

This will:

- generate a Docker Compose configuration dynamically
- start a cluster of N nodes
- assign ports `8001 ... 800N`

---

### Submit a vote

```bash
curl -X POST http://localhost:8001/vote \
  -H "Content-Type: application/json" \
  -d '{"poll_id":"poll1","option":"A"}'
```

---

### Get poll results

```bash
curl http://localhost:8001/poll/poll1
```

---

### Node status

```bash
curl http://localhost:8001/status
```

---

## Stop the Cluster

To stop and remove all containers and volumes:

```bash
python stop_cluster.py
```

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

### Strong Eventual Consistency (SEC)

Achieved through:

- CRDT G-Counter (per poll/option/node)
- Commutative, associative and idempotent merge
- Anti-entropy synchronization

### Guarantees

- No conflicts under concurrent updates
- Deterministic convergence across all nodes
- Monotonic growth of counters
- No data loss after crash (with WAL + checkpoint)

Write propagation is best-effort and does not require immediate acknowledgement from all peers.
Replicas may temporarily diverge, but eventually converge.

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

```
value = max(local_value, remote_value)
```

Ensures:

- idempotency
- convergence without coordination

---

## Durability Model

Each node uses:

- **Write-Ahead Log (WAL)** for every update
- **Periodic checkpoints** to persist full state

### Crash safety

A global durability lock ensures:

- WAL append + state apply
- checkpoint + WAL truncation

are serialized.

Every update is either:

- in the checkpoint, or
- in the WAL

→ preventing data loss.

---

## Network Partition Simulation

### Networks

- `progetto_ds_default`: main cluster network
- `ds_isolated`: isolated network

### Isolate a node

```bash
NODE3=$(docker compose ps -q node3)
docker network disconnect progetto_ds_default $NODE3
docker network connect ds_isolated $NODE3
```

### Reconnect the node

```bash
docker network disconnect ds_isolated $NODE3
docker network connect progetto_ds_default $NODE3
```

After reconnection, anti-entropy synchronizes the state.

---

## Failure Handling

### Node crash

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

Peer states:

- ALIVE
- SUSPECT
- DEAD
- UNKNOWN

Transitions are timeout-based and may produce false positives.

---

## Anti-Entropy Synchronization

Nodes periodically:

1. select a random peer
2. fetch its full state
3. merge updates

Ensures convergence after:

- partitions
- failures
- recovery

---

## Limitations

- Votes are **increments only**

- No support for:
  - vote changes
  - vote removal
  - "one user = one vote"

- `/vote` is not idempotent

- Anti-entropy is not bandwidth optimized

- Failure detector is basic

---

## Testing

Basic scenarios included:

- Vote propagation across nodes
- Node failure and recovery
- Network partition and reconciliation
