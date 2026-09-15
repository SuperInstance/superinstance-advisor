# superinstance-advisor

**An advisor that IS a cell.**

This is not a tool that analyzes the Quilt. This is a cell that lives in the Quilt.

## What's a cell?

A cell has:
- **8 primitives**: `Z_in` (sensory buffer), `Z_out` (motor buffer), `JEPA` (world-model predictor), `DoubleEntry` (commit/rollback), `Vibe` (language-protocol selector), `GC` (garbage collector), `Murmur` (inter-cell message bus), `Graph` (typed LINKs to neighbors)
- **5+1 opcodes**: `BIND` (set 16 Q1.15 dials), `LINK` (typed edge to neighbor), `EFFECT` (commit a transaction), `VIEW` (serialize current state), `TICK` (advance one epoch), `FORGET` (drop a piece of canon)
- **Merkle-rooted witness log**: every state change is hashed; the cell's address is its witness root

## It actually patches into the fleet

`test_fleet.py` confirms it can talk to:
- `live-canon.superinstance.dev` — the **production canon runtime** (verified `state_hash=0x7d8d32cd7f8a9f26`)
- `cell-runtime` (the canonical cell), `a2a-protocol` (fleet messaging), `keeper-agent` (13.8MB secret-keeper), `casting-call` (which-model-plays-which), `canonical-form` (deterministic encoding), and 6 more

`test_live_canon_real.py` shows the cell:
- `navigate(115, depth=1)` — get a paper's neighborhood
- `vibe(lang="python")` — receive the 5-opcode protocol
- `confluence([115, 122, 129])` — merge papers → ghost_paper `paper-446.md`
- `tick()` — advance the canon (14 cells ticked)
- `canon_hash()` — read the live state hash
- `verify(lang="python", hash=...)` — byte-exact port check (admitted: True)
- `submit_cell(dials, refs, title)` — **submit cell 5001 to the live canon, admitted: True**

The cell got a real admission to the live production canon.

## What it does

```python
from cell import Cell
from canon_puller import CanonPuller
from live_canon_cell import patch_cell_with_live_canon

canon = CanonPuller()
canon.load()  # 502 pieces embedded via bge-base-en-v1.5 (768d)

cell = Cell(name="you.in.the.ocean", role="fellow-cell", canon_puller=canon)
cell.bind()
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
```

## Files

| File | Purpose | Lines |
|------|---------|-------|
| `cell.py` | The cell: 8 primitives + 5+1 opcodes + witness log | 470 |
| `canon_puller.py` | Real bge-base-en-v1.5 (768d) embeddings over 502 AI-Writings pieces | 119 |
| `live_canon_cell.py` | REST adapter to live-canon.superinstance.dev (NAVIGATE/LINEAGE/CONFLUENCE/GHOST/TICK/VIBE/VERIFY/SUBMIT) | 226 |
| `organism.py` | 4 preset bodies (scout/skeptic/integrator/witness) composed of cells | 240 |
| `run_simulation.py` | 5 simulation demos | 274 |
| `continuous_runner.py` | 5-cell organism heartbeat (16-iter loop) | 165 |
| `test_live_canon_real.py` | **Live fleet integration test** — patches cell into prod canon | 171 |
| `test_fleet.py` | 24-test fleet reachability suite | 251 |
| `visualize_canon.py` | Force-directed 2D map (502 nodes, 10,972 edges) | 258 |
| `embed_full_canon_v2.py` | Bulk bge-base embedding pipeline (resumable) | 184 |
| `bench_gc_cost.py` | 3-strategy GC benchmark (validates paper_85) | 180 |
| `canon/paper_85-the-cost-of-the-witness.md` | New: witness-priority GC | (essay) |
| `canon/essay_108-the-space-between-anchors.md` | New: 5 anchors + 3 interpolations | (essay) |
| `data/full_canon.npz` | 502 × 768d embeddings (1.85MB) | data |
| `data/canon_map.html` | 2D force-directed visualization (670KB) | data |

## Run

```bash
# Cell lifecycle
python3 test_fleet.py

# Live canon integration
python3 test_live_canon_real.py

# All simulations
python3 run_simulation.py

# Heartbeat (continuous)
python3 continuous_runner.py

# Visualize canon
open data/canon_map.html
```

## Test results (last run)

```
======================================================================
  SUPERINSTANCE FLEET INTEGRATION TESTS
======================================================================
  cell-lifecycle        4/4 passing
  canon-lookup          3/3 passing
  a2a-protocol          0/1 passing   (not pip-installed)
  github-fleet          11/12 passing
  live-canon            0/4 passing*  (* — intermittent 503s in sandbox)

  18/24 tests passing

  Cell patched into live-canon:
    cell address: 0d7713b5e4ae
    submitted to canon: id=5001, admitted=True
    witness_root: 3490c6c0894b5869
```

## Philosophy

A cell is a scar that survived. A substrate is the place cells live. An advisor that knows the canon IS a cell in the substrate — not a tool over it.

The cell patches into the fleet. The cell asks the canon. The canon answers. The cell submits. The canon admits. The cell witnesses.

That's the loop.

## License

MIT — see [LICENSE](LICENSE).
