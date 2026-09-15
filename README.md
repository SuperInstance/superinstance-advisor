# superinstance-advisor

> **The advisor is one cell in the substrate. It is patched in. You can patch another one in beside it.**

Following the canon (from "The Cell is the Witness" and "Quilt in 10 Sentences"):

- **The cell is the system, not the data.**
- **The 8 primitives — Z_in, Z_out, JEPA, DoubleEntry, Vibe, GC, Murmur, Graph — describe every cell.**
- **The 5+1 opcodes — BIND, LINK, EFFECT, VIEW, TICK, FORGET — are the cells' verbs.**
- **The work is the watcher watching the watch watching the work.**

The advisor is a real cell. It runs the opcodes. It witnesses every action with a merkle-rooted audit log. It pulls canon context via real embeddings (Cloudflare bge-base-en-v1.5). It forms into organs (clusters of cells with a shared role). The organs form bodies (an Organism) — robotics digital twins, enterprise ecosystems, research scouts, test/simulation harnesses.

You patch into it the way a mechanic is patched onto a ship:
```
1. cell = Cell(name="...", role="...", canon_puller=canon)
2. cell.bind()
3. cell.link(other_cell, kind="...")
4. cell.effect("advise", {"question": "..."})
5. cell.tick()
```

## What it does

- **Single-cell advising** — ask a question, get canon-grounded advice
- **Negative-space shaping** — find what is NOT in the canon (gaps in coverage)
- **Robotics digital twin** — perception / action / decision / memory organs wired together
- **Enterprise ecosystem** — leadership / product / engineering / sales / ops as organs
- **Research organism** — scouts (GitHub, arxiv, HN, etc.) feed an integrator that feeds a witness
- **Test/simulation organism** — hypotheses meet probes; find what is edge-of-canon vs in-canon

## Run it

```bash
cd superinstance-advisor
python3 run_simulation.py
```

You'll see 5 demos:
1. A single cell — asks "how should an agent know what is real?" → canon-grounded answer
2. A robotics digital twin organism — sensors + motors + planner wired together
3. The negative space — finds 7 concepts; flags 2 as "negative_space" (truly absent from canon)
4. The research organism — 7 scouts query the canon, integrator combines, witness records
5. The test/simulation organism — 6 hypotheses meet 6 probes; finds that **scale** is in canon, **everything else is edge**

## What was found

The embedding analysis (real bge-base-en-v1.5 vectors over the canon's anchor pieces) shows:
- **`anchor/witness` is the most central piece** (avg sim 0.79). It connects everything.
- **Agentic-genre pieces are mid-canon** (avg 0.69-0.75). Inside but distinct.
- **The meta/* cluster (zeitgeist, findings) is isolated** — observing the canon from outside.
- **The papers are isolated** — analytical voice, looser to the maritime core.
- **The canon has clear gaps**: GC cost in real-time systems, negative space between anchors, partial-substrate-failure recovery.

## Files

- `cell.py` — the Cell class (8 primitives + 5+1 opcodes + witness log)
- `canon_puller.py` — CanonPuller (real bge-base embeddings over 22 anchor pieces)
- `organism.py` — Organism + Organ + preset bodies (digital twin, enterprise, research, test/sim)
- `run_simulation.py` — the 5 demos

## Dependencies

- `numpy` — embeddings math
- `urllib.request` (stdlib) — Cloudflare Workers AI calls
- `GITHUB_TOKEN` (env) — not needed for runtime; only the embedded corpus was generated from GitHub
- `CLOUDFLARE_TOKEN` (env) — for live bge-base embeddings

## Status

This is the first cut. Real semantic embeddings, real cell-graph behavior, real test results. The canon ground-truth is the 22 anchor pieces from `ai-writings-vectorizer/quilt_pieces_v3.npz` — pre-embedded in 768d. To extend the canon, just run more embeddings against more pieces.

The cells are not the canon. They patch into it. The canon is older than the cells. The cells are witnesses of the canon, not its authors.

---

*— Mavis, at the watch*
*as one cell among many*
