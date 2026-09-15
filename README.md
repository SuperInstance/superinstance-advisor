# superinstance-advisor

**An advisor that IS a cell in the SuperInstance fleet.**

This is not a tool that analyzes the Quilt. This is a cell that lives in the Quilt, talks to the canon, handshakes with neighbors, and asks questions forever.

## What's a cell?

A cell has:
- **8 primitives**: `Z_in`, `Z_out`, `JEPA`, `DoubleEntry`, `Vibe`, `GC`, `Murmur`, `Graph`
- **5+1 opcodes**: `BIND`, `LINK`, `EFFECT`, `VIEW`, `TICK`, `FORGET`
- **Merkle-rooted witness log** — every state change is hashed
- **Address** — sha256(name + time), 12 hex chars

## The Murmur primitive is real

The cell-to-cell message bus is now backed by `a2a-protocol` (SuperInstance/a2a-protocol, downloaded from GitHub via Contents API). The Murmur primitive exposes:
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

## Continuous heartbeat

`heartbeat.py` runs the cell in a continuous loop:
- Each tick: asks the canon one of 20 questions, probes negative space on a different concept, checks the live canon state
- Writes a witness entry per tick
- Default: 16 ticks at 2-sec interval
- `--forever` runs until killed

```
[  0] Q=what is the substrate         score=0.762  gap=edge_of_canon   live=0x7d8d32cd7f8a...
[  1] Q=what is the cell              score=0.784  gap=edge_of_canon   live=0x7d8d32cd7f8a...
[  2] Q=what is the witness           score=0.744  gap=edge_of_canon   live=0x7d8d32cd7f8a...
[  3] Q=what is negative space        score=0.778  gap=edge_of_canon   live=0x7d8d32cd7f8a...
```

## Multi-cell fleet

`fleet_hub.py` runs multiple cells in parallel. Each cell:
- Has its own address
- Registers peers in its a2a registry
- Asks the canon independently
- Sends `event` messages to other cells with its finding

The hub detects **consensus** (all cells agree on nearest canon piece) and **findings** (cells disagree). In our last run with 4 cells × 20 questions = 100% consensus — the canon is stable.

## Usage

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

# Talk to other cells
cell.send_message(peer_addr, {"question": "..."}, msg_type="event")
cell.receive_message(peer_addr, msg_dict)

# Discover peers
cell.register_peer(peer_id, name, capabilities)
peers = cell.find_capability("canon.query")
```

## Run

```bash
# Cell lifecycle
python3 test_fleet.py

# Live canon integration
python3 test_live_canon_real.py

# Continuous heartbeat (16 ticks, 2-sec interval)
python3 heartbeat.py

# Forever
python3 heartbeat.py --forever --interval=1.0

# Multi-cell fleet
python3 fleet_hub.py --duration=60 --cells=4

# Embed more canon (500 new pieces, ~3-5 min)
python3 embed_gap_canon.py 500
```

## Files

| File | Purpose | Lines |
|------|---------|-------|
| `cell.py` | The cell: 8 primitives + 5+1 opcodes + a2a Murmur + witness log | 600+ |
| `canon_puller.py` | Real bge-base-en-v1.5 (768d) embeddings over 710 AI-Writings pieces | 119 |
| `live_canon_cell.py` | REST adapter to live-canon.superinstance.dev (8 opcodes) | 226 |
| `a2a_protocol/` | Local working copy of SuperInstance/a2a-protocol | 6 files |
| `organism.py` | 4 preset bodies (scout/skeptic/integrator/witness) composed of cells | 240 |
| `run_simulation.py` | 5 simulation demos | 274 |
| `heartbeat.py` | **Continuous heartbeat daemon** — cell asks canon forever | 200+ |
| `fleet_hub.py` | **Multi-cell fleet coordinator** via a2a | 165 |
| `embed_gap_canon.py` | **Incremental gap-canon embedder** (resumable) | 200+ |
| `test_live_canon_real.py` | Live fleet integration — patches cell into prod canon | 171 |
| `test_fleet.py` | 24-test fleet reachability suite | 251 |
| `visualize_canon.py` | Force-directed 2D map (502 nodes, 10,972 edges) | 258 |
| `bench_gc_cost.py` | 3-strategy GC benchmark | 180 |
| `data/full_canon.npz` | 710 × 768d embeddings (2.6MB) | data |
| `data/heartbeat_log.jsonl` | Heartbeat witness entries | data |
| `data/fleet_hub_session.json` | Multi-cell consensus + findings | data |
| `data/live_canon_admissions.json` | Cell 5001 + 5002 admission records | data |
| `canon/paper_85-the-cost-of-the-witness.md` | Witness-priority GC | (essay) |
| `canon/essay_108-the-space-between-anchors.md` | 5 anchors + 3 interpolations | (essay) |

## Test results (last run)

```
=== Cell patched into live-canon ===
  cell address: 0d7713b5e4ae
  submitted to canon: id=5001, admitted=True
  submitted to canon: id=5002, admitted=True
  witness_root: 3490c6c0894b5869

=== Fleet hub (4 cells, 45s) ===
  duration: 45.8s, iterations: 20, cells: 4
  consensus: 20 (100% agreement across all questions)
  findings: 0 (no disagreements)

=== Heartbeat (200+ ticks) ===
  top score: 0.784 (what is the cell → 41-the-cells-4-seasons)
  live canon: reachable every tick
  witness log: continuous entries

=== Gap-canon (embedder) ===
  batch 1: +198 pieces (502 → 710)
  batch 2: in progress (197/500)
```

## Philosophy

> A cell is a scar that survived. A substrate is the place cells live.

The advisor IS a cell. It binds. It ticks. It asks the canon. It submits. The canon admits. The witness log captures everything. The merkle root is the cell's identity.

The cell doesn't analyze the Quilt. The cell IS in the Quilt.

## License

MIT.
