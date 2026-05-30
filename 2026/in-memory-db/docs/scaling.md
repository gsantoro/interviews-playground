# Scaling in-memory-db to Production

This document outlines how the single-node `in-memory-db` would evolve into a
production-grade distributed system, and answers likely interview questions about
scalability, fault tolerance, and cloud deployment.

---

## Current limitations (single node)

| Constraint | Impact |
|-----------|--------|
| All data in one process | Limited by single machine RAM |
| No replication | Single point of failure |
| No persistence | Data lost on restart |
| Background TTL not swept | Expired slots occupy RAM until next read |

---

## 1. Background TTL sweep (near-term)

Add a daemon thread that periodically scans `_key_index` for expired entries and
frees their slots. Configurable sweep interval (e.g., every 1 second).

```python
import threading

class MemoryStore:
    def _start_ttl_sweep(self, interval: float = 1.0) -> None:
        def sweep():
            while True:
                self.keys()   # lazy expiry already cleans up expired keys
                time.sleep(interval)
        t = threading.Thread(target=sweep, daemon=True)
        t.start()
```

**Trade-off:** Adds CPU overhead on sweep thread. Configurable interval balances
freshness vs. CPU cost.

---

## 2. Persistence

Two strategies (mirrors Redis):

### AOF (Append-Only File)
Every write command is appended to a log file. On restart, replay the log to
rebuild state. Low data loss (lose at most the last `fsync` interval).

### RDB Snapshot
Periodically serialise the full `_key_index` + `_slots` to disk (e.g., via
`pickle` or `msgpack`). Faster restarts than AOF replay, but potential for data
loss between snapshots.

**GCP implementation:** Store snapshots/AOF in **Google Cloud Storage** (GCS).
On GKE pod restart, download the latest snapshot before serving traffic.
Use a GCS bucket lifecycle policy to retain only the last N snapshots.

---

## 3. Multi-node: sharding

Sharding distributes keys across N nodes so each node owns `total_keys / N` keys.

### Consistent hashing

Assign each node a set of positions on a virtual ring (e.g., using `hashlib.md5`
of the node ID). Route each key to the node whose ring position is the nearest
clockwise successor of `hash(key)`.

```python
import hashlib
import bisect

class ConsistentHashRing:
    def __init__(self, nodes: list[str], replicas: int = 150) -> None:
        self._ring: dict[int, str] = {}
        self._sorted_keys: list[int] = []
        for node in nodes:
            for i in range(replicas):
                h = int(hashlib.md5(f"{node}-{i}".encode()).hexdigest(), 16)
                self._ring[h] = node
                bisect.insort(self._sorted_keys, h)

    def get_node(self, key: str) -> str:
        h = int(hashlib.md5(key.encode()).hexdigest(), 16)
        idx = bisect.bisect_right(self._sorted_keys, h) % len(self._sorted_keys)
        return self._ring[self._sorted_keys[idx]]
```

**Client-side routing:** A thin proxy/sidecar (or the client SDK) calls
`ring.get_node(key)` and forwards the request to the correct node.

**GCP implementation:** Deploy each shard as a **GKE Deployment** (1+ replicas
behind a ClusterIP Service). A routing layer (e.g., Envoy, or a simple FastAPI
proxy) resolves the shard and proxies the request.

---

## 4. Replication (fault tolerance)

Each shard runs a **leader** and 1-2 **followers**:

- All writes go to the leader.
- Leader replicates writes to followers asynchronously (or synchronously for
  strong consistency).
- If leader fails, a follower is elected via a consensus protocol (Raft) or a
  simple heartbeat + ZooKeeper/etcd lease.

**GCP implementation:** Use **GKE StatefulSets** (stable pod identities) for
leader/follower roles. Use **Cloud Spanner** or **etcd on GKE** for leader
election coordination.

---

## 5. Auto-scaling

### Vertical (single node)
Increase pod memory limits in GKE. Adjust `max_keys` and `initial_capacity` in
`config.toml` at deploy time via a ConfigMap.

### Horizontal (add shards)
Adding a new shard requires re-distributing keys:

1. Add the new node to the consistent hash ring.
2. The affected key range (roughly `total_keys / (N+1)`) migrates from the
   existing owner to the new node.
3. Use a short dual-write period during migration.

**GCP implementation:** Use **GKE Horizontal Pod Autoscaler** on a custom metric
(e.g., Prometheus `memory_used_ratio`). When a shard pod's memory crosses a
threshold, trigger a shard-split operation.

---

## 6. gRPC adapter

The `StoragePort` Protocol makes swapping transports trivial. A gRPC adapter:

1. Define a `.proto` schema matching the `StoragePort` interface.
2. Implement a gRPC servicer that calls `MemoryStore` methods.
3. No changes to `app/core/` — only a new `app/adapters/grpc/` package.

**When to prefer gRPC over REST:** Lower latency (binary framing, multiplexed
HTTP/2), streaming (e.g., subscribe to key changes), and strong schema contracts
across polyglot clients.

---

## 7. Observability

- **Prometheus metrics** (via `prometheus-fastapi-instrumentator`): request
  latency, cache hit/miss rate, eviction count, key count.
- **Cloud Monitoring** (GCP): export Prometheus metrics to Cloud Monitoring via
  the managed collection agent on GKE.
- **Cloud Trace**: distributed tracing across the proxy → shard hops.
- **Structured logging**: emit JSON logs via Python `logging` + Cloud Logging.

---

## Summary: production architecture on GCP

```
Client
  │
  ▼
Cloud Load Balancer
  │
  ▼
GKE: Routing Proxy (FastAPI / Envoy)
  │   Consistent hash ring → shard selection
  ├──► GKE: Shard 0 (StatefulSet: leader + follower)
  ├──► GKE: Shard 1 (StatefulSet: leader + follower)
  └──► GKE: Shard N ...
           │
           ▼
        GCS: Snapshots / AOF logs
           │
           ▼
        Cloud Monitoring / Cloud Trace
```
