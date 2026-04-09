# Test Suite (PowerShell)

This folder contains a set of **PowerShell scripts** designed to test the main functionalities of the Distributed Voting and Polling System.

The tests simulate realistic distributed scenarios, including failures, recovery, and asynchronous replication.

---

## Covered Features

The test suite validates the following system properties:

- vote submission via REST API
- asynchronous replication across nodes
- strong eventual consistency
- behavior under temporary node failures
- failure detection (heartbeat mechanism)
- crash recovery using WAL and checkpointing
- persistence across node restarts
- idempotent handling of duplicated internal updates
- convergence under concurrent writes
- divergence and healing after temporary disconnection

---

## Prerequisites

Before running the tests, make sure the environment is correctly prepared.

### 1. Reset the system state

To ensure reproducibility, remove all containers and persistent data:
Required Tools

- Docker
- Docker compose
- Python 3
- Powershell
- On Windows, Docker Desktop MUST be running

Useful checks:

```powershell
docker info
docker compose version
python --version
pwsh --version
```

---

### 2. Enable PowerShell script execution

PowerShell blocks unsigned scripts by default.

Run the following command (temporary for the current session):

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

---

## Running the Tests

### Run all tests

```powershell
.\test\run_all.ps1
```

---

## Test Descriptions

### 01 — Basic Replication

- Submits votes to different nodes
- Verifies that all nodes converge to the same result

Validates:

- replication
- CRDT merge correctness

---

### 02 — Eventual Consistency After Rejoin

- Stops a node (`node3`)
- Submits votes while it is offline
- Restarts the node
- Waits until all nodes converge

Validates:

- anti-entropy synchronization
- strong eventual consistency
- recovery after temporary partition

---

### 03 — Failure Detection

- Stops a node
- Observes its state transition (ALIVE → SUSPECT/DEAD)
- Restarts the node
- Verifies recovery

Validates:

- heartbeat mechanism
- failure detection logic

---

### 04 — Crash Recovery (Persistence)

- Submits votes
- Ensures state is replicated to a node
- Stops other nodes
- Restarts the isolated node
- Verifies that state is preserved

Validates:

- WAL (Write-Ahead Logging)
- checkpointing
- local crash recovery without peers

---

### 05 — Idempotent Duplicated Internal Update

Replays the same internal replicated update more than once and checks that the final state is not corrupted.

Validates:

- duplicate delivery tolerance
- idempotent update handling
- correctness of replicated merge behaviour

---

### 06 — Concurrent Updates Convergence

Submits concurrent votes to multiple nodes and verifies that all replicas eventually converge to the expected counts.

Validates:

- concurrent request handling
- distributed merge correctness
- convergence after parallel writes

---

### 07 — Temporary Disconnection and Healing

Temporarily disconnects one node from the others, submits updates while it is isolated, observes replica divergence, and then restores connectivity so that anti-entropy can reconcile the state.

Validates:

- continued availability of reachable nodes
- temporary divergence during disconnection
- eventual convergence after healing

---

## Notes

- Tests rely on **asynchronous behavior**, so convergence is verified using polling with timeouts.
- Due to anti-entropy, convergence is **eventual**, not immediate.
- Docker volumes are used for persistence; therefore:
  - `docker compose restart` → keeps data
  - `docker compose down -v` → resets everything

## Platform Note

The current test suite is implemented in PowerShell and has been developed and verified on Windows.
