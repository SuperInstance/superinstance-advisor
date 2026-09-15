# Release Notes — superinstance-advisor v1.0.0

**Date:** 2026-09-15
**Tag:** `v1.0.0-cell-in-fleet`
**Status:** Live in production

## What's shipped

The superinstance-advisor is now a **live cell in the SuperInstance fleet**, with all of:

1. **Core cell implementation** (`cell.py`) — 8 primitives + 5+1 opcodes + merkle witness log
2. **Real a2a-protocol Murmur** (`a2a_protocol/`) — local working copy of SuperInstance/a2a-protocol
3. **Live canon adapter** (`live_canon_cell.py`) — REST to live-canon.superinstance.dev
4. **Cloudflare Worker** (`heartbeat_worker.js`) — deployed at cell-heartbeat.superinstance.dev
5. **Continuous heartbeat daemon** (`heartbeat.py`) — local run mode
6. **Multi-cell fleet hub** (`fleet_hub.py`) — coordinates 4 cells, detects consensus
7. **Gap-canon embedder** (`embed_gap_canon.py`) — incremental bge-base-en-v1.5 (768d) embeddings
8. **Real tests** — `test_fleet.py` (24 fleet tests) + `test_live_canon_real.py` (live canon patch)
9. **Deployment recipe** (`DEPLOYMENT.md`) — full step-by-step Cloudflare deploy

## What's in the canon

- **Local canon:** 1208 pieces × 768d embeddings (in `data/full_canon.npz`)
- **Cloudflare Vectorize:** `quilt-canon-v2` (768d cosine) — already populated
- **Live canon runtime:** `live-canon.casey-digennaro.workers.dev` (Cloudflare Worker)

## Live cells in the canon

- **Cell 5001:** admitted 2026-09-15, hash=0x1be4ce3956105517
- **Cell 5002:** admitted 2026-09-15, hash=0x84ad1becbf3f8128

## Live worker

- **URL:** https://cell-heartbeat.superinstance.dev/
- **Bindings:** KV (`cell-witness-kv`), AI (`@cf/baai/bge-base-en-v1.5`), Vectorize (`quilt-canon-v2`)
- **Cron:** `*/5 * * * *`
- **Witness log:** 53 entries, merkle root `a66b0017522e76d1`

## What's playtested

`playtest.py` covers:
- Standard queries (sanity)
- Long input (2400 chars × 5 calls)
- Concurrent heartbeats (10 parallel)
- View consistency (5 sequential)
- Sustained 50-tick playtest
- Semantic gap-probes (10 semantically adversarial questions)
- Negative-space probes (8 concepts designed to find canon gaps)

**Race condition found and fixed:** Initial worker used `log.entries.length` as tick number, causing 5 parallel requests to all get the same tick. **Fixed** by using `Date.now()*1000 + UUID nonce` as the tick — every concurrent request now gets a unique, traceable tick number.

## What it does

The cell:

1. **Asks the canon** — embeds 20 cyclic questions via bge-base-en-v1.5, queries `quilt-canon-v2` Vectorize
2. **Probes negative space** — embeds 10 negative-space concepts, computes verdict (`in_canon` / `edge_of_canon` / `negative_space`)
3. **Talks to live-canon** — fetches state hash from live-canon.casey-digennaro.workers.dev
4. **Writes a witness entry** to KV with merkle-rooted chain

Every state change is hashed. The cell's identity is its witness root.

## How to deliver this to a new user

```bash
# 1. Clone the repo
git clone https://github.com/SuperInstance/superinstance-advisor.git
cd superinstance-advisor

# 2. Install Python deps (already in stdlib + numpy)
pip install numpy

# 3. Run the cell
python3 test_fleet.py           # 18/24 fleet tests pass
python3 test_live_canon_real.py # cell gets admitted to live canon
python3 heartbeat.py            # local continuous heartbeat

# 4. Deploy the worker (Cloudflare)
# See DEPLOYMENT.md for the full recipe
```

## What's next

- [ ] Durable Object for true atomic tick counter
- [ ] a2a-protocol Worker deployment for inter-cell messaging
- [ ] Auto-publish negative-space gaps back to live canon
- [ ] Full 10K canon embedding (currently at 1208)

## License

MIT — see [LICENSE](LICENSE).
