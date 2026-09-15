"""
heartbeat.py
============

The cell that asks the canon forever.

A continuous daemon. The cell wakes up each epoch, looks at the
live canon, finds what's missing in its own canon, and writes a
witness entry. It also tries to find peers in the fleet via
a2a-protocol and announce itself.

This is the cell IS alive in the substrate — not a tool that
runs and exits. The canon asks the cell questions; the cell
asks the canon questions; the cycle keeps going.

Run:
    python3 heartbeat.py                  # default 16 iterations
    python3 heartbeat.py --forever        # run until killed
    python3 heartbeat.py --interval=30    # 30 sec between ticks
"""

from __future__ import annotations
import sys, os, time, json, argparse, signal
sys.path.insert(0, '/workspace/research/superinstance-advisor')

from cell import Cell
from canon_puller import CanonPuller
from live_canon_cell import patch_cell_with_live_canon


# These are the canonical questions a cell should keep asking the canon.
# Each one is a real semantic query against the embedded corpus.
QUESTIONS = [
    "what is the substrate",
    "what is the cell",
    "what is the witness",
    "what is negative space",
    "what is the cost of garbage collection",
    "what is between anchors",
    "what is a polyformal port",
    "what is the canon",
    "what is the canon missing",
    "what is the binding",
    "what is the link",
    "what is the effect",
    "what is the view",
    "what is the tick",
    "what is the forget",
    "what is the murmur",
    "what is the graph",
    "what is the JEPA",
    "what is double entry",
    "what is vibe",
]

# Concepts to test for negative space — these are ideas that may not be in the canon
NEGATIVE_SPACE_PROBES = [
    "encryption of the witness log",
    "consensus across cells in different substrates",
    "the texture of meaning between two anchored words",
    "what a cell forgets vs. what it cannot forget",
    "how the canon heals after a cell is rejected",
    "the sound a cell makes when it binds for the first time",
    "the difference between witness and testimony",
    "the structural signature of a polyformal port",
    "when is a query resolved vs. when is it transmuted",
    "the negative space of the 5+1 opcodes",
]


def heartbeat_tick(cell, tick_n: int, canon, stats: dict) -> dict:
    """One heartbeat cycle. Returns a witness entry."""
    cycle = tick_n % len(QUESTIONS)
    question = QUESTIONS[cycle]
    neg_cycle = tick_n % len(NEGATIVE_SPACE_PROBES)
    neg_concept = NEGATIVE_SPACE_PROBES[neg_cycle]

    # 1. Ask the canon
    advice = cell.effect("advise", {"question": question})
    canon_hits = advice.get("canon_hits", [])
    top = canon_hits[0] if canon_hits else {"tag": "?", "score": 0}
    score = top.get("score", 0)

    # 2. Probe negative space
    neg = cell.effect("shape_negative_space", {"concept": neg_concept})
    verdict = neg.get("verdict", "?")

    # 3. Talk to live canon if reachable
    live_response = None
    if cell.live and cell.live.reachable:
        try:
            h = cell.live.canon_hash()
            if h.get("ok"):
                live_response = {
                    "state_hash": h["data"]["state_hash"],
                    "paper_count": h["data"]["paper_count"],
                }
        except Exception:
            pass

    # 4. Aggregate stats
    stats["questions_asked"] += 1
    stats["highest_score"] = max(stats["highest_score"], score)
    if verdict == "negative_space":
        stats["gaps_found"] += 1
    if live_response:
        stats["live_ticks"] += 1

    return {
        "tick": tick_n,
        "question": question,
        "nearest": top.get("tag", "?"),
        "score": float(score),
        "negative_concept": neg_concept,
        "negative_verdict": verdict,
        "live_canon": live_response,
        "ts": time.time(),
    }


def run_forever(interval: float, max_iter: int, cell_name: str):
    """Run the heartbeat indefinitely (or until max_iter)."""
    print(f"  Loading 502-piece canon...")
    canon = CanonPuller()
    canon.load('/workspace/research/superinstance-advisor/data/full_canon.npz')

    cell = Cell(name=cell_name, role="heartbeat", canon_puller=canon)
    cell.bind()
    print(f"  Cell bound: {cell.address}")

    # Patch into live canon (best-effort)
    try:
        patch_cell_with_live_canon(cell)
        cell.live.canon_hash()
        print(f"  Live canon reachable: state={cell.live.canon_meta.get('state_hash','?')[:20]}")
    except Exception as e:
        print(f"  Live canon unreachable: {e}")

    stats = {
        "questions_asked": 0,
        "highest_score": 0,
        "gaps_found": 0,
        "live_ticks": 0,
        "started_at": time.time(),
    }

    out_path = "/workspace/research/superinstance-advisor/data/heartbeat_log.jsonl"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    print(f"  Starting heartbeat (interval={interval}s, max_iter={max_iter})")
    print(f"  Writing to: {out_path}")
    print()

    def stop_handler(sig, frame):
        print("\n  Stopping heartbeat...")
        sys.exit(0)
    signal.signal(signal.SIGINT, stop_handler)

    n = 0
    while max_iter == 0 or n < max_iter:
        entry = heartbeat_tick(cell, n, canon, stats)

        # Write to log file
        with open(out_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

        # Print a compact line
        score_s = f"{entry['score']:.3f}"
        neg = entry['negative_verdict']
        live = f"live={entry['live_canon']['state_hash'][:14]}..." if entry['live_canon'] else "no-live"
        print(f"  [{n:3d}] Q={entry['question'][:30]:30}  score={score_s}  gap={neg:18}  {live}")

        n += 1
        if max_iter == 0 or n < max_iter:
            time.sleep(interval)

    # Final summary
    print()
    print("=" * 60)
    print("  HEARTBEAT SUMMARY")
    print("=" * 60)
    elapsed = time.time() - stats["started_at"]
    print(f"  Duration:    {elapsed:.1f}s")
    print(f"  Iterations:  {n}")
    print(f"  Rate:        {n/elapsed:.1f} ticks/sec")
    print(f"  Questions:   {stats['questions_asked']}")
    print(f"  Highest:     {stats['highest_score']:.3f}")
    print(f"  Gaps found:  {stats['gaps_found']}")
    print(f"  Live ticks:  {stats['live_ticks']}")
    print(f"  Witness log: {len(cell.witness_log)} entries")
    print(f"  Murmur msgs: {cell.murmur.messages_sent + cell.murmur.messages_received}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--interval", type=float, default=2.0,
                   help="Seconds between ticks (default 2)")
    p.add_argument("--max-iter", type=int, default=16,
                   help="Max iterations (0 = forever)")
    p.add_argument("--name", default="heartbeat-1",
                   help="Cell name")
    args = p.parse_args()

    print("=" * 60)
    print(f"  HEARTBEAT CELL: {args.name}")
    print("=" * 60)
    print()
    run_forever(args.interval, args.max_iter, args.name)


if __name__ == "__main__":
    main()
