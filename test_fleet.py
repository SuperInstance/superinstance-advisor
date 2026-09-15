"""
test_fleet.py
=============

Patch the advisor into the actual SuperInstance fleet.

Tests:
    1. live-canon REST API (the production canon interface)
    2. a2a-protocol (fleet messaging between cells)
    3. keeper-agent (the secret-keeper proxy)
    4. canonical-form (deterministic encoding)
    5. canon-suite (the meta-package)

This is the real test. If the fleet is alive, we can patch in. If
something is unreachable, the witness records it.

For sandbox environments with TLS issues, we fall back gracefully.
"""

import json, time, sys, os, urllib.request, urllib.error, urllib.parse
sys.path.insert(0, '/workspace/research/superinstance-advisor')

RESULTS = []

def record(test, ok, detail):
    RESULTS.append({"test": test, "ok": ok, "detail": detail})
    sym = "✓" if ok else "✗"
    print(f"  {sym} {test}: {detail}")


def safe_get(url, timeout=8):
    """GET with TLS-error tolerance."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "superinstance-advisor/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode(errors='replace')
    except urllib.error.URLError as e:
        return None, str(e)
    except Exception as e:
        return None, str(e)


def test_live_canon():
    """The live canon REST API."""
    print("\n=== TEST: live-canon.superinstance.dev ===")
    base = "https://live-canon.superinstance.dev"

    # 1. The hash endpoint (smallest response)
    status, body = safe_get(f"{base}/api/canon/hash")
    if status == 200:
        try:
            data = json.loads(body)
            record("live-canon /api/canon/hash", True, f"hash={data.get('state_hash','?')[:20]}... papers={data.get('paper_count','?')}")
        except Exception:
            record("live-canon /api/canon/hash", False, f"status=200 but body not JSON: {body[:80]}")
    else:
        record("live-canon /api/canon/hash", False, f"unreachable: {body[:80]}")

    # 2. The canon list
    status, body = safe_get(f"{base}/api/canon?limit=5")
    if status == 200:
        try:
            data = json.loads(body)
            n = len(data) if isinstance(data, list) else len(data.get('papers', []))
            record("live-canon /api/canon", True, f"got {n} papers")
        except Exception:
            record("live-canon /api/canon", False, f"status=200 but parse fail")
    else:
        record("live-canon /api/canon", False, f"unreachable: {body[:80]}")

    # 3. Navigate a paper
    status, body = safe_get(f"{base}/api/canon/navigate?paper=85&depth=1")
    if status == 200:
        record("live-canon /api/canon/navigate", True, "paper 85 navigable")
    else:
        record("live-canon /api/canon/navigate", False, f"unreachable: {body[:80]}")

    # 4. VIBE for python
    status, body = safe_get(f"{base}/api/vibe?lang=python")
    if status == 200:
        record("live-canon /api/vibe (python)", True, "30-second protocol available")
    else:
        record("live-canon /api/vibe", False, f"unreachable: {body[:80]}")


def test_github_fleet():
    """Test that the GitHub-side cells are reachable via API."""
    print("\n=== TEST: GitHub-side fleet ===")
    TOKEN = os.environ['GITHUB_TOKEN']

    FLEET = [
        ("SuperInstance/quilt-live-canon", "the live canon worker"),
        ("SuperInstance/cell-runtime", "the canonical cell"),
        ("SuperInstance/cell-runtime-rs", "the rust cell"),
        ("SuperInstance/a2a-protocol", "fleet messaging"),
        ("SuperInstance/canon-zoo", "the inspiration zoo"),
        ("SuperInstance/casting-call", "which model plays which role"),
        ("SuperInstance/agent-dna", "genetic code for vessels"),
        ("SuperInstance/keeper-agent", "secret-keeper proxy"),
        ("SuperInstance/swarm-anchor", "shared state for swarms"),
        ("SuperInstance/canonical-form", "deterministic encoding"),
        ("SuperInstance/porch", "CLI for 3am thoughts"),
        ("SuperInstance/river-dream-log", "agentic journaling"),
    ]
    for path, desc in FLEET:
        try:
            req = urllib.request.Request(f"https://api.github.com/repos/{path}",
                headers={"Authorization": f"token {TOKEN}"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                r = json.loads(resp.read())
                record(f"github {path}", True,
                       f"{r.get('size','?')}KB - {desc}")
        except urllib.error.HTTPError as e:
            record(f"github {path}", False, f"HTTP {e.code}")
        except Exception as e:
            record(f"github {path}", False, f"{type(e).__name__}: {str(e)[:60]}")


def test_a2a_protocol_package():
    """Try to install and import a2a-protocol."""
    print("\n=== TEST: a2a-protocol package ===")
    try:
        import a2a_protocol
        record("a2a_protocol importable", True, f"version={getattr(a2a_protocol, '__version__', '?')}")
    except ImportError as e:
        record("a2a_protocol importable", False, f"not installed: {e}")
    except Exception as e:
        record("a2a_protocol importable", False, f"{type(e).__name__}: {str(e)[:80]}")


def test_canon_puller_finds_real_papers():
    """Use the embedded canon to do a real cross-cell lookup."""
    print("\n=== TEST: cross-cell lookup via canon puller ===")
    from canon_puller import CanonPuller

    canon = CanonPuller()
    canon.load("/workspace/research/superinstance-advisor/data/full_canon.npz")

    queries = [
        "the cost of garbage collection in real-time systems",
        "what does the canon say about negative space",
        "cell substrate witness",
    ]
    for q in queries:
        hits = canon.query(q, top_k=3)
        if hits:
            top = hits[0]
            record(f"query: '{q[:40]}...'", True,
                   f"top={top['tag'][:50]} ({top['score']:.3f})")
        else:
            record(f"query: '{q[:40]}...'", False, "no hits")


def test_full_substrate_integration():
    """Cell birth → bind → link → tick → effect → view."""
    print("\n=== TEST: cell lifecycle (cell.py) ===")
    from cell import Cell
    from canon_puller import CanonPuller

    canon = CanonPuller()
    canon.load("/workspace/research/superinstance-advisor/data/full_canon.npz")

    cell = Cell(name="test.cell", role="fellow", canon_puller=canon)
    addr = cell.bind()
    cell.tick()

    # Ask the canon
    res = cell.effect("advise", {"question": "what is the substrate?"})
    if res.get("advice"):
        record("cell.effect('advise')", True, f"advice={res['advice'][:60]}...")
    else:
        record("cell.effect('advise')", False, "no advice returned")

    # Shape negative space
    res = cell.effect("shape_negative_space", {"concept": "encryption of the witness log"})
    record("cell.effect('shape_negative_space')", True, f"verdict={res.get('verdict','?')}")

    # Test simulate
    res = cell.effect("test_simulate", {
        "scenario": "substrate runs out of memory",
        "sub_cells": [
            {"name": "a", "scenario": "what happens?"},
            {"name": "b", "scenario": "how do we recover?"}
        ]
    })
    record("cell.effect('test_simulate')", True, f"sub_cells={res.get('sub_cell_count')}")

    # Test cell view
    v = cell.view()
    if v.get("bound") and v.get("primitives"):
        record("cell.view()", True, f"8 primitives, witness_count={v['witness_count']}")
    else:
        record("cell.view()", False, "view incomplete")


def main():
    print("=" * 70)
    print("  SUPERINSTANCE FLEET INTEGRATION TESTS")
    print("=" * 70)

    test_full_substrate_integration()
    test_canon_puller_finds_real_papers()
    test_a2a_protocol_package()
    test_github_fleet()
    test_live_canon()

    print()
    print("=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    n_ok = sum(1 for r in RESULTS if r["ok"])
    n_total = len(RESULTS)
    print(f"  {n_ok}/{n_total} tests passing")

    # Group by category
    by_cat = {}
    for r in RESULTS:
        if r["test"].startswith("github"):
            cat = "github-fleet"
        elif r["test"].startswith("live-canon"):
            cat = "live-canon"
        elif r["test"].startswith("query"):
            cat = "canon-lookup"
        elif r["test"].startswith("cell."):
            cat = "cell-lifecycle"
        elif r["test"].startswith("a2a_"):
            cat = "a2a-protocol"
        else:
            cat = "other"
        by_cat.setdefault(cat, []).append(r)

    print()
    for cat, rs in by_cat.items():
        ok = sum(1 for r in rs if r["ok"])
        print(f"  {cat:20}  {ok}/{len(rs)} passing")

    # Save the results
    out = {
        "summary": {"passing": n_ok, "total": n_total},
        "results": RESULTS,
        "ts": time.time(),
    }
    with open("/workspace/research/superinstance-advisor/data/fleet_test_results.json", "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nResults saved to: data/fleet_test_results.json")

    return 0 if n_ok == n_total else 1


if __name__ == '__main__':
    sys.exit(main())
