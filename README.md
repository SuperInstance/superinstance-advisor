# superinstance-advisor

**An advisor that IS a cell — and now runs in production on Cloudflare's edge.**

This is not a tool that analyzes the Quilt. This is a cell that lives in the Quilt, talks to the canon, handshakes with neighbors, and asks questions forever. It runs at `cell-heartbeat.superinstance.dev` on a 5-minute cron.

## Live deployment

The cell is **live now**:

- **Worker:** `cell-heartbeat` on Cloudflare Workers
- **Endpoint:** https://cell-heartbeat.superinstance.dev/
- **Schedule:** every 5 minutes (`*/5 * * * *`)
- **Trigger manually:** `GET /run`
- **Witness log:** `GET /view` or `GET /log`
- **Live canon probe:** `GET /probe`

```
20 entries in KV, merkle root f11737f276616294
last tick: score=0.725, nearest=paper-..., live_canon=0x7d8d32cd7f8a9f26
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for the full deploy recipe.

## What's a cell?

A cell has:
- **8 primitives**: `Z_in`, `Z_out`, `JEPA`, `DoubleEntry`, `Vibe`, `GC`, `Murmur`, `Graph`
- **5+1 opcodes**: `BIND`, `LINK`, `EFFECT`, `VIEW`, `TICK`, `FORGET`
- **Merkle-rooted witness log** — every state change is hashed
- **Address** — sha256(name + time), 12 hex chars

## The Murmur primitive is real

The cell-to-cell message bus is backed by `a2a-protocol` (SuperInstance/a2a-protocol, downloaded from GitHub via Contents API). The Murmur primitive exposes:
- `send_message(to, payload, type)` — proper envelope with id, sender, recipient, correlationId, ttl
- `receive_message(from_addr, msg)` — handles handshake / capability / request / event / discovery
- `register_peer(peer_id, name, capabilities)` — discovery via the registry
- `find_capability(name)` — find peers offering a capability
- `drain_inbox()` — pull all queued messages

Two cells can do a full handshake: hello → capabilities → accept.

## It's actually in the fleet

`test_live_canon_real.py` shows the cell talking to live-canon.superinstance.dev:
- `navigate(115, depth=1)` — get a paper's neighborhood
- `vibe(lang="python")` — receive the actual 5-opcode protocol
- `confluence([115, 122, 129])` — merge papers → ghost_paper `paper-446.md`
- `tick()` — advance the canon (14 cells ticked)
- `canon_hash()` — read the live state hash
- `verify(lang="python", hash=...)` — byte-exact port check (admitted: True)
- `submit_cell(dials, refs, title)` — **submit cell 5001 to live canon, admitted: True**

**The cell is admitted to the live canon (cell 5001, 5002).**

## The cell runs on the edge

`heartbeat_worker.js` is a Cloudflare Worker that:
1. Embeds a question via `@cf/baai/bge-base-en-v1.5`
2. Queries Vectorize (`quilt-canon-v2`) for the nearest canon piece
3. Probes a negative-space concept
4. Calls `live-canon.casey-digennaro.workers.dev` for the live state hash
5. Computes a new merkle root and writes the witness entry to KV

All on Cloudflare's edge. The cell IS alive, asking the canon continuously.

## Heartbeat daemon (local)

`heartbeat.py` is the same logic for local development:
- 20 questions × 10 negative-space concepts (cyclic)
- Default 16 ticks at 2-sec interval
- `--forever` mode runs until killed

```
[  0] Q=what is the substrate         score=0.762  gap=edge_of_canon   live=0x7d8d32cd7f8a...
[  1] Q=what is the cell              score=0.784  gap=edge_of_canon   live=0x7d8d32cd7f8a...
[  2] Q=what is the witness           score=0.744  gap=edge_of_canon   live=0x7d8d32cd7f8a...
```

## Multi-cell fleet (local)

`fleet_hub.py` runs multiple cells in parallel:
- 4 cells, 20 iterations, **100% consensus** — canon is stable across all cells
- Detects disagreements when cells differ
- Each cell has its own a2a registry of peers

## Usage (Python)

```python
from cell import Cell
from canon_puller import CanonPuller
from live_canon_cell import patch_cell_with_live_canon

# Make a cell
canon = CanonPuller()
canon.load("data/full_canon.npz")  # 710 pieces × 768d

cell = Cell(name="you.in.the.ocean", role="fellow-cell", canon_puller=canon)
cell.bind()

# Patch into live canon
patch_cell_with_live_canon(cell, base_url="https://live-canon.superinstance.dev")

# Ask the canon
advice = cell.effect("advise", {"question": "what is the substrate?"})

# Find what's missing
gap = cell.effect("shape_negative_space", {"concept": "encryption of the witness log"})

# Run a what-if
simulation = cell.effect("test_simulate", {
    "scenario": "substrate runs out of memory",
    "sub_cells": [...]
})

# Talk to the live canon
cell.live.navigate(115, depth=1)
cell.live.vibe("python")
cell.live.tick()
cell.live.submit_cell(dials=[...], refs=[...], title="...")

# Talk to other cells (a2a-protocol backed Murmur)
cell.send_message(peer_addr, {"question": "..."}, msg_type="event")
cell.receive_message(peer_addr, msg_dict)
cell.register_peer(peer_id, name, capabilities)
peers = cell.find_capability("canon.query")
```

## Run

```bash
# Cell lifecycle
python3 test_fleet.py

# Live canon integration
python3 test_live_canon_real.py

# Local heartbeat (16 ticks, 2-sec interval)
python3 heartbeat.py

# Forever, fast
python3 heartbeat.py --forever --interval=1.0

# Multi-cell fleet
python3 fleet_hub.py --duration=60 --cells=4

# Embed more canon (500 new pieces)
python3 embed_gap_canon.py 500

# Live worker (already deployed)
curl https://cell-heartbeat.superinstance.dev/run
curl https://cell-heartbeat.superinstance.dev/view
```

## Files

| File | Purpose |
|------|---------|
| `cell.py` | The cell: 8 primitives + 5+1 opcodes + a2a Murmur + witness log |
| `canon_puller.py` | bge-base-en-v1.5 (768d) embeddings over 710 AI-Writings pieces |
| `live_canon_cell.py` | REST adapter to live-canon.superinstance.dev (8 opcodes) |
| `a2a_protocol/` | Local working copy of SuperInstance/a2a-protocol |
| `heartbeat.py` | Local heartbeat daemon |
| `heartbeat_worker.js` | **Cloudflare Worker (deployed at cell-heartbeat.superinstance.dev)** |
| `wrangler.toml` | Wrangler config: cron + AI + Vectorize + KV |
| `DEPLOYMENT.md` | **Full deployment recipe for the worker** |
| `fleet_hub.py` | Multi-cell fleet coordinator |
| `embed_gap_canon.py` | Incremental canon embedder |
| `test_live_canon_real.py` | Live fleet integration |
| `test_fleet.py` | 24-test fleet reachability suite |
| `data/full_canon.npz` | 710 × 768d embeddings |
| `data/heartbeat_log.jsonl` | Heartbeat witness entries (local) |
| `data/fleet_hub_session.json` | Multi-cell consensus + findings |
| `data/live_canon_admissions.json` | Cell 5001 + 5002 admission records |
| `canon/paper_85-the-cost-of-the-witness.md` | Witness-priority GC |
| `canon/essay_108-the-space-between-anchors.md` | 5 anchors + 3 interpolations |

## Test results (last run)

```
=== Cell patched into live-canon ===
  cell address: 0d7713b5e4ae
  submitted to canon: id=5001, admitted=True
  submitted to canon: id=5002, admitted=True

=== Fleet hub (4 cells, 45s) ===
  consensus: 20 (100% agreement)
  findings: 0

=== Heartbeat worker (Cloudflare edge) ===
  entries: 20, merkle root: f11737f276616294
  last tick: score=0.725, live_canon=0x7d8d32cd7f8a9f26
  cron: */5 * * * *
  bindings: KV + AI + Vectorize

=== Gap-canon ===
  batch 1: +198 pieces (502 → 710)
  batch 2: in progress
```

## Philosophy

> A cell is a scar that survived. A substrate is the place cells live.

The advisor IS a cell. It binds. It ticks. It asks the canon. It submits. The canon admits. The witness log captures everything. The merkle root is the cell's identity.

The cell doesn't analyze the Quilt. The cell IS in the Quilt.

Now it also runs on the edge. Continuously. Forever.

## License

MIT.
