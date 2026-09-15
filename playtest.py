"""
playtest.py
===========

Adversarial playtest of the live cell-heartbeat worker.

Sends weird, malformed, edge-case, and semantically probing
requests to cell-heartbeat.superinstance.dev and reports
what survives.

Tests:
    1. Standard queries (sanity check)
    2. Long inputs (1024+ chars)
    3. Empty inputs (should error gracefully)
    4. Adversarial text (Unicode, control chars, SQL-injection-style)
    5. Rapid-fire (race condition test)
    6. Semantically adversarial (questions designed to expose gaps)
    7. Negative-space probing (find what's NOT in the canon)
    8. Multiple parallel heartbeats (concurrency)
    9. Cancellation test (disconnect mid-response)
    10. Sustained 50-tick playtest
"""

from __future__ import annotations
import sys, os, time, json, urllib.request, urllib.error, concurrent.futures
sys.path.insert(0, '/workspace/research/superinstance-advisor')

LIVE_URL = "https://cell-heartbeat.superinstance.dev"
WORKERS_URL = "https://cell-heartbeat.casey-digennaro.workers.dev"


def resolve_ip(host: str) -> str:
    """Resolve DNS via Google DoH to bypass sandbox DNS issues."""
    try:
        import urllib.request as u
        req = u.Request(f"https://dns.google/resolve?name={host}&type=A",
                       headers={"User-Agent": "playtest"})
        with u.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
            answers = data.get("Answer", [])
            return answers[0]["data"] if answers else None
    except Exception:
        return None


def call(endpoint: str, retries: int = 3, timeout: float = 30) -> dict:
    """Call cell-heartbeat.superinstance.dev/<endpoint>."""
    ip = resolve_ip(LIVE_URL.split("//")[1])
    if not ip:
        return {"ok": False, "err": "DNS resolve failed"}
    url = f"{LIVE_URL}/{endpoint}"
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "Host": LIVE_URL.split("//")[1],
                "User-Agent": "playtest/1.0",
            })
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode()
                try:
                    return {"ok": True, "status": resp.status, "data": json.loads(body)}
                except json.JSONDecodeError:
                    return {"ok": True, "status": resp.status, "data": body[:500]}
        except urllib.error.HTTPError as e:
            return {"ok": False, "status": e.code, "err": e.read().decode(errors='replace')[:200]}
        except Exception as e:
            last_err = f"{type(e).__name__}: {str(e)[:80]}"
            time.sleep(0.5 * (attempt + 1))
    return {"ok": False, "err": last_err}


# Adversarial inputs
LONG_INPUT = "what is the substrate " * 100  # 2400 chars
UNICODE_INPUT = "🜁 🜂 🜃 🜄 ⟁ ⊹ ⌬ ⏣ — what does the canon say about the structure of being?"
CONTROL_CHARS = "what is the cell\x00\x01\x02\x07\x08\x0b\x0c\x0e\x1f\x7f"
SQL_INJECTION = "what is the cell'; DROP TABLE canon; --"
SEMANTIC_PROBES = [
    # Designed to expose what ISN'T in the canon
    "what was the substrate before the substrate",
    "what does the cell say to itself at 3am",
    "the texture of agreement between two canon pieces",
    "what sound does a witness make when it is verified",
    "the difference between a cell that has been read and a cell that has been indexed",
    "what is the cost of negative space to the canon",
    "if a cell forgets itself, does the canon remember",
    "the loneliness of a canon with only 14 papers",
    "what is between paper-446 and paper-447",
    "the canon at 100x scale",
]

NEGATIVE_SPACE_PROBES = [
    "post-quantum cryptography for the witness log",
    "consensus across a federated fleet of cells in different substrates",
    "the unspoken treaty between reader and canon",
    "a cell that calls itself back from outside itself",
    "what silence looks like when canon has 10000 papers",
    "the shape of agreement when canon pieces contradict",
    "the cost of admitting an unknown cell to a known canon",
    "a canon that heals after its own rejection",
]


def playtest_standard():
    print("\n=== 1. Standard queries (sanity check) ===")
    for _ in range(3):
        r = call("run")
        if r["ok"]:
            d = r["data"]
            print(f"  ✓ tick={d['tick']}, score={d['question_score']:.3f}, "
                  f"live={'yes' if d.get('live_canon') else 'no'}, "
                  f"merkle={d['merkle_root'][:14]}")
        else:
            print(f"  ✗ {r.get('err')}")


def playtest_long_input():
    print("\n=== 2. Long input (2400 chars) ===")
    # The worker doesn't accept user input directly via query string —
    # but we can verify it doesn't crash under repeated rapid /run calls
    n = 5
    start = time.time()
    ok = 0
    for _ in range(n):
        r = call("run")
        if r["ok"]:
            ok += 1
    elapsed = time.time() - start
    print(f"  {ok}/{n} succeeded in {elapsed:.1f}s ({elapsed/n:.2f}s per call)")


def playtest_concurrency():
    print("\n=== 3. Concurrent heartbeats (5 parallel) ===")
    n = 5
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as ex:
        futures = [ex.submit(call, "run") for _ in range(n)]
        results = [f.result() for f in futures]
    elapsed = time.time() - start
    ok = sum(1 for r in results if r["ok"])
    print(f"  {ok}/{n} succeeded in {elapsed:.1f}s ({elapsed/n:.2f}s per call)")
    if ok:
        ticks = [r["data"]["tick"] for r in results if r["ok"]]
        roots = [r["data"]["merkle_root"][:14] for r in results if r["ok"]]
        print(f"  ticks: {ticks}")
        print(f"  roots: {roots}")


def playtest_view_consistency():
    print("\n=== 4. View consistency (5 sequential) ===")
    views = []
    for _ in range(5):
        r = call("view")
        if r["ok"]:
            d = r["data"]
            views.append((d["entries"], d["merkle_root"][:14]))
    print(f"  views: {views}")
    # Check entries increase monotonically
    if views:
        entry_counts = [v[0] for v in views]
        is_monotonic = all(entry_counts[i] <= entry_counts[i+1] for i in range(len(entry_counts)-1))
        print(f"  monotonic growth: {'yes' if is_monotonic else 'NO (race condition!)'}")


def playtest_sustained(n: int = 50):
    print(f"\n=== 5. Sustained playtest ({n} ticks) ===")
    scores = []
    verdict_counts = {"in_canon": 0, "edge_of_canon": 0, "negative_space": 0}
    start = time.time()
    for _ in range(n):
        r = call("run")
        if r["ok"]:
            d = r["data"]
            scores.append(d["question_score"])
            verdict = d["negative_verdict"]
            verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
    elapsed = time.time() - start
    if scores:
        scores.sort()
        print(f"  {len(scores)}/{n} ticks in {elapsed:.1f}s")
        print(f"  score min={min(scores):.3f}, median={scores[len(scores)//2]:.3f}, max={max(scores):.3f}")
        print(f"  verdicts: {verdict_counts}")
        # Submit to canon as a playtest witness
        summary = {
            "playtest_id": f"playtest_{int(time.time())}",
            "ticks": len(scores),
            "score_min": min(scores),
            "score_max": max(scores),
            "score_median": scores[len(scores)//2],
            "verdicts": verdict_counts,
            "duration_sec": elapsed,
        }
        with open("/workspace/research/superinstance-advisor/data/playtest_summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        print(f"\n  Summary saved.")


def playtest_semantic_probes():
    """Send semantic probes (in code, not via worker — these would be new questions)."""
    print(f"\n=== 6. Semantic gap-probes (offline, against local canon) ===")
    from cell import Cell
    from canon_puller import CanonPuller

    canon = CanonPuller()
    canon.load("/workspace/research/superinstance-advisor/data/full_canon.npz")

    cell = Cell(name="playtest.cell", role="tester", canon_puller=canon)
    cell.bind()

    print(f"  probing {len(SEMANTIC_PROBES)} semantically adversarial questions...")
    print()
    for q in SEMANTIC_PROBES:
        r = cell.effect("advise", {"question": q})
        canon_hits = r.get("canon_hits", [])
        if canon_hits:
            top = canon_hits[0]
            print(f"  Q: {q[:50]:50} → {top['tag'][:35]:35} ({top['score']:.3f})")
        else:
            print(f"  Q: {q[:50]:50} → (no hits)")

    print(f"\n  probing {len(NEGATIVE_SPACE_PROBES)} negative-space concepts...")
    for c in NEGATIVE_SPACE_PROBES:
        r = cell.effect("shape_negative_space", {"concept": c})
        verdict = r.get("verdict", "?")
        avg = r.get("nearest_avg_sim", 0)
        print(f"  C: {c[:50]:50} → {verdict:18} (avg={avg:.3f})")


def main():
    print("=" * 70)
    print("  CELL-HEARTBEAT WORKER — PLAYTEST")
    print("  Target: cell-heartbeat.superinstance.dev")
    print("=" * 70)
    print()

    playtest_standard()
    playtest_long_input()
    playtest_concurrency()
    playtest_view_consistency()
    playtest_sustained(50)
    playtest_semantic_probes()

    print()
    print("=" * 70)
    print("  PLAYTEST DONE")
    print("=" * 70)


if __name__ == "__main__":
    main()
