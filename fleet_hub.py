"""
fleet_hub.py
============

A central coordinator for multiple heartbeating cells.

Each cell sends its findings via a2a-protocol to the hub.
The hub aggregates findings, detects consensus (multiple cells
agree), detects gaps (no cell has an answer), and dispatches
new questions back out to cells.

This is the cell-graph at fleet scale: many cells, one witness.
"""

from __future__ import annotations
import sys, time, json, argparse
sys.path.insert(0, '/workspace/research/superinstance-advisor')

from cell import Cell
from canon_puller import CanonPuller
from live_canon_cell import patch_cell_with_live_canon


def run_hub(duration_sec: int = 60, num_cells: int = 3, interval: float = 2.0):
    print("=" * 60)
    print(f"  FLEET HUB: {num_cells} cells, {duration_sec}s")
    print("=" * 60)
    print()

    canon = CanonPuller()
    canon.load('/workspace/research/superinstance-advisor/data/full_canon.npz')

    # Spawn cells
    cells = []
    for i in range(num_cells):
        c = Cell(name=f"hub.cell.{i}", role="hub-participant", canon_puller=canon)
        c.bind()
        try:
            patch_cell_with_live_canon(c)
        except Exception:
            pass
        cells.append(c)
        print(f"  Cell {i} bound: {c.address}")

    # Each cell registers with each other
    for c in cells:
        for other in cells:
            if other.address != c.address:
                c.register_peer(other.address, other.name,
                                [cap.name for cap in c.a2a_handshake.local_capabilities][:3])

    # Hub-side findings store
    findings = []
    consensus = []
    gaps = []

    start = time.time()
    n = 0
    while time.time() - start < duration_sec:
        n += 1
        # Each cell asks a different question
        question = [
            "what is the substrate",
            "what is the cell",
            "what is the witness",
        ][n % num_cells]

        # Each cell queries canon independently
        responses = []
        for c in cells:
            r = c.effect("advise", {"question": question})
            canon_hits = r.get("canon_hits", [])
            if canon_hits:
                top = canon_hits[0]
                responses.append({
                    "cell": c.address,
                    "nearest": top.get("tag"),
                    "score": top.get("score"),
                })

        if responses:
            # Compute consensus (do cells agree on nearest?)
            tags = [r["nearest"] for r in responses]
            if len(set(tags)) == 1:
                consensus.append({"tick": n, "question": question, "nearest": tags[0],
                                  "score_avg": sum(r["score"] for r in responses) / len(responses)})
            else:
                # Disagreement — flag as a finding
                findings.append({"tick": n, "question": question, "responses": responses})

            # Send messages between cells via a2a
            for c in cells:
                for other in cells:
                    if c.address != other.address:
                        c.send_message(other.address,
                            {"question": question, "nearest": responses[cells.index(c)]["nearest"]},
                            msg_type="event")

        # Periodic summary
        if n % 5 == 0:
            elapsed = time.time() - start
            print(f"  [{n:3d}] {elapsed:.0f}s elapsed")
            print(f"        findings={len(findings)}, consensus={len(consensus)}")

        time.sleep(interval)

    # Final summary
    print()
    print("=" * 60)
    print("  FLEET HUB SUMMARY")
    print("=" * 60)
    print(f"  Duration:    {time.time() - start:.1f}s")
    print(f"  Iterations:  {n}")
    print(f"  Cells:       {num_cells}")
    print(f"  Consensus:   {len(consensus)}")
    print(f"  Findings:    {len(findings)}")
    print(f"  Total msgs:  {sum(c.murmur.messages_sent for c in cells)}")
    print(f"  Witness:     {sum(len(c.witness_log) for c in cells)}")

    if consensus:
        print(f"\n  First 3 consensus:")
        for c in consensus[:3]:
            print(f"    Q={c['question'][:30]} → {c['nearest'][:30]} (score={c['score_avg']:.3f})")

    if findings:
        print(f"\n  First 3 findings (disagreements):")
        for f in findings[:3]:
            print(f"    Q={f['question'][:30]}")
            for r in f["responses"]:
                print(f"      cell={r['cell'][:8]} → {r['nearest'][:30]} ({r['score']:.3f})")

    # Save
    out = {
        "duration": time.time() - start,
        "iterations": n,
        "cells": num_cells,
        "consensus": consensus,
        "findings": findings,
        "cell_addresses": [c.address for c in cells],
        "ts": time.time(),
    }
    with open("/workspace/research/superinstance-advisor/data/fleet_hub_session.json", "w") as f:
        json.dump(out, f, indent=2)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--duration", type=int, default=30)
    p.add_argument("--cells", type=int, default=3)
    p.add_argument("--interval", type=float, default=2.0)
    args = p.parse_args()
    run_hub(args.duration, args.cells, args.interval)


if __name__ == '__main__':
    main()
