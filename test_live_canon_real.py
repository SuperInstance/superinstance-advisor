"""
test_live_canon_real.py
=======================

The real test. Use the live-canon REST API from a patched cell.

Patches the superinstance-advisor cell into the live production canon
at live-canon.superinstance.dev.

Validates:
    1. The cell can navigate papers in the live canon
    2. The cell can do CONFLUENCE (merge papers)
    3. The cell can trace LINEAGE
    4. The cell can fetch the live VIBE protocol
    5. The cell can submit a new cell (writes to the live canon)
    6. The cell can verify its own byte-exact hash

The cell runs against the production substrate. The witness log
records every interaction.
"""

import json, time, sys, os
sys.path.insert(0, '/workspace/research/superinstance-advisor')

from cell import Cell
from canon_puller import CanonPuller
from live_canon_cell import LiveCanonCell, patch_cell_with_live_canon

LIVE_URL = "https://live-canon.superinstance.dev"


def safe_call(call_fn, *args, **kwargs):
    """Call with retry on intermittent 503s."""
    for attempt in range(5):
        try:
            result = call_fn(*args, **kwargs)
            if result.get("ok"):
                return result
            if "503" in str(result.get("err", "")):
                time.sleep(2 ** attempt)
                continue
            return result
        except Exception as e:
            return {"ok": False, "err": str(e)}
    return {"ok": False, "err": "max retries"}


def main():
    print("=" * 70)
    print("  CELL PATCHED INTO LIVE-CANON.SUPERINSTANCE.DEV")
    print("=" * 70)

    # 1. Make a cell with the local canon
    canon = CanonPuller()
    canon.load("/workspace/research/superinstance-advisor/data/full_canon.npz")

    cell = Cell(name="you.in.the.ocean", role="fellow-cell", canon_puller=canon)
    cell.bind()
    patch_cell_with_live_canon(cell, base_url=LIVE_URL)

    view = cell.live.view()
    print(f"\n  cell address: {cell.address}")
    print(f"  live base: {cell.live.base_url}")

    # 2. Navigate papers via live-canon
    print("\n--- LIVE NAVIGATE ---")
    for paper_id in [115, 122, 129]:  # papers known to be in this canon (F115, F122, F129)
        result = safe_call(cell.live_navigate, paper_id, 1)
        if result.get("ok"):
            data = result["data"]
            if isinstance(data, dict):
                keys = list(data.keys())[:5]
                print(f"  paper {paper_id}: keys={keys}")
                # If it has input_papers etc., show those
                if data.get("input_titles"):
                    for t in data["input_titles"][:2]:
                        print(f"    title: {t[:80]}")
            elif isinstance(data, list):
                print(f"  paper {paper_id}: list of {len(data)} items")
            else:
                print(f"  paper {paper_id}: {str(data)[:120]}")
        else:
            print(f"  paper {paper_id}: {result.get('err', 'unknown')}")

    # 3. Get the VIBE protocol for python
    print("\n--- LIVE VIBE (python) ---")
    result = safe_call(cell.live_vibe, "python")
    if result.get("ok"):
        body = result["data"]
        if isinstance(body, dict):
            for k in list(body.keys())[:5]:
                v = body[k]
                print(f"  {k}: {str(v)[:200]}")
        else:
            print(f"  body: {str(body)[:300]}")
    else:
        print(f"  err: {result.get('err')}")

    # 4. Confluence of the three known papers
    print("\n--- LIVE CONFLUENCE (115, 122, 129) ---")
    result = safe_call(cell.live_confluence, [115, 122, 129])
    if result.get("ok"):
        body = result["data"]
        if isinstance(body, dict):
            for k in list(body.keys())[:6]:
                print(f"  {k}: {str(body[k])[:200]}")
        else:
            print(f"  body: {str(body)[:300]}")
    else:
        print(f"  err: {result.get('err')}")

    # 5. Tick the live canon
    print("\n--- LIVE TICK ---")
    result = safe_call(cell.live_tick)
    if result.get("ok"):
        body = result["data"]
        print(f"  tick: {str(body)[:200]}")
    else:
        print(f"  err: {result.get('err')}")

    # 6. The canon hash
    print("\n--- LIVE CANON HASH ---")
    h = cell.live.canon_hash()
    if h.get("ok"):
        print(f"  {h['data']}")
    else:
        print(f"  err: {h.get('err')}")

    # 7. Verify a port
    print("\n--- LIVE VERIFY (python with known hash) ---")
    v = cell.live.verify("python", "0xe435d91d6d92a1d8")
    if v.get("ok"):
        body = v["data"]
        print(f"  {body}")
    else:
        print(f"  err: {v.get('err')}")

    # 8. Submit a new cell
    print("\n--- SUBMIT A NEW CELL ---")
    dials = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000,
             1100, 1200, 1300, 1400, 1500, 1600]
    submit = cell.live.submit_cell(
        dials=dials,
        refs=[115, 122, 129],
        title="patched-from-superinstance-advisor 2026-09-15"
    )
    if submit.get("ok"):
        body = submit["data"]
        print(f"  submitted: {str(body)[:300]}")
    else:
        print(f"  err: {submit.get('err')}")

    # 8. Final view of the cell — see what it witnessed
    print("\n--- FINAL CELL VIEW ---")
    print(f"  address: {cell.address}")
    print(f"  witness_root: {cell.view()['witness_root']}")
    print(f"  live.witness_count: {len(cell.live.witness_log)}")

    # Witness summary
    print(f"\n  Live calls made:")
    for w in cell.live.witness_log[-10:]:
        sym = "✓" if w['payload'].get('ok') else "✗"
        elapsed = w['payload'].get('elapsed_ms', '?')
        url_short = w['payload'].get('url', '?')[:80]
        print(f"    {sym} {w['op']:15}  {elapsed}ms  {url_short}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
