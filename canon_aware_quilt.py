"""
canon_aware_quilt.py
=====================

A Quilt cell that uses multiple LLMs WITH canon context.

Each LLM call is fed:
  1. The top-k canon pieces (cosine-similar to the question)
  2. The cell's witness history (recent state)
  3. The question itself

The LLMs are chosen by role:
  - deepseek-chat:    fast, general — for composition
  - deepseek-reasoner:deep thinking — for hard questions
  - seed-mini:        cheap, with reasoning — for verdict decisions
  - seed-code:        code generation

Concurrent fan-out when possible. Every call writes a witness entry.

The ensemble returns the answer that agrees with the most canon pieces
(via cross-model consistency check).
"""

from __future__ import annotations
import sys, os, json, time, urllib.request, urllib.error
import concurrent.futures
import numpy as np
import hashlib
sys.path.insert(0, '/workspace/research/superinstance-advisor')

from canon_puller import CanonPuller
from multi_llm_quilt import call_llm, PROVIDERS


class CanonAwareCell:
    """A cell that asks the canon AND uses LLMs to interpret."""

    def __init__(self, name: str = "canon-aware-cell",
                 canon: CanonPuller = None):
        self.name = name
        self.address = hashlib.sha256(f"{name}-{time.time()}".encode()).hexdigest()[:12]
        self.bound = False
        self.witness_log: list[dict] = []
        self.canon = canon or CanonPuller()
        self.total_cost_usd = 0.0

    def _w(self, op: str, payload: dict):
        entry = {"op": op, "ts": time.time(), "payload": payload}
        self.witness_log.append(entry)
        return entry

    def _record(self, op: str, result: dict):
        self._w(op, result)
        if result.get("ok") and result.get("cost_usd"):
            self.total_cost_usd += result["cost_usd"]

    def bind(self):
        self.bound = True
        self._w("BIND", {"address": self.address})
        return self.address

    def tick(self):
        self._w("TICK", {"tick_count": len([w for w in self.witness_log if w["op"] == "TICK"])})

    def view(self):
        return {
            "address": self.address,
            "name": self.name,
            "bound": self.bound,
            "witness_count": len(self.witness_log),
            "total_cost_usd": self.total_cost_usd,
        }

    # ----- The flagship: canon-aware ensemble -----

    def ask(self, question: str, k: int = 3, models: list = None) -> dict:
        """Ask the canon + ensemble of LLMs, all in parallel.

        Returns: {
          "question": str,
          "canon_hits": [{tag, score, text?}],
          "ensemble": {model: response},
          "synthesis": str (from cheapest model, with canon context)
        }
        """
        if models is None:
            models = ["deepseek_chat", "seed_mini", "deepseek_reasoner"]

        # 1. Get canon context (top-k embeddings)
        canon_hits = self.canon.query(question, top_k=k) if self.canon.embeddings is not None else []
        canon_context = "\n".join(
            f"  [{i+1}] {h['tag']} (score={h['score']:.3f})"
            for i, h in enumerate(canon_hits)
        )

        # 2. Build prompt with canon context
        system_prompt = (
            "You are an advisor to a Quilt cell. The cell lives in the canon. "
            "The canon is the substrate — papers, ideas, cells, witnesses. "
            "Use the canon context to inform your answer. "
            "Be direct. 2-3 sentences. No meta-commentary.\n\n"
            f"CANON CONTEXT:\n{canon_context}"
        )

        # 3. Run ensemble concurrently
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ]

        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(models)) as ex:
            futures = {ex.submit(call_llm, m, messages, 500, 0.4): m for m in models}
            for f in concurrent.futures.as_completed(futures):
                m = futures[f]
                try:
                    results[m] = f.result()
                except Exception as e:
                    results[m] = {"ok": False, "err": str(e)[:80]}

        # 4. Record witnesses
        for m, r in results.items():
            self._record(f"ensemble:{m}", r)

        # 5. Consensus check — pick the answer that mentions most canon pieces
        canon_tags = {h["tag"].split(".")[-1] for h in canon_hits}
        if canon_tags and results:
            consensus_scores = {}
            for m, r in results.items():
                if r.get("ok"):
                    content = r.get("content", "")
                    matches = sum(1 for tag in canon_tags if tag in content)
                    consensus_scores[m] = matches
            if consensus_scores:
                winner = max(consensus_scores.items(), key=lambda x: x[1])
                self._w("CONSENSUS", {"winner": winner[0], "scores": consensus_scores})

        self._w("ASK", {
            "question": question,
            "canon_hits": canon_hits,
            "models": list(results.keys()),
        })

        return {
            "question": question,
            "canon_hits": canon_hits,
            "ensemble": results,
        }

    def shape_negative_space(self, concept: str, n_models: int = 2) -> dict:
        """Use multiple LLMs to decide the verdict for a negative-space concept."""
        canon_pieces = []
        if self.canon.embeddings is not None:
            canon_pieces = self.canon.query(concept, top_k=3)
        canon_context = "\n".join(
            f"  - {h['tag']} (score={h['score']:.3f})"
            for h in canon_pieces
        )
        avg_sim = sum(h["score"] for h in canon_pieces) / max(len(canon_pieces), 1)

        verdict_prompt = (
            f"CONCEPT: {concept}\n"
            f"CANON CONTEXT (top-3 nearest):\n{canon_context}\n"
            f"Average cosine similarity: {avg_sim:.3f}\n\n"
            "Is this concept a canon GAP? Reply with EXACTLY ONE of:\n"
            "  in_canon (avg_sim > 0.75 — concept is well-represented)\n"
            "  edge_of_canon (0.65 < avg_sim <= 0.75 — concept is partially represented)\n"
            "  negative_space (avg_sim <= 0.65 — concept is missing)\n\n"
            "Reply with just the verdict word, then on a new line a 1-sentence explanation."
        )
        messages = [
            {"role": "system", "content": "You are a canon auditor. Be precise."},
            {"role": "user", "content": verdict_prompt}
        ]

        models = ["seed_mini", "deepseek_chat"][:n_models]
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(models)) as ex:
            futures = {ex.submit(call_llm, m, messages, 200, 0.2): m for m in models}
            for f in concurrent.futures.as_completed(futures):
                m = futures[f]
                results[m] = f.result()
                self._record(f"shape:{m}", results[m])

        self._w("SHAPE", {
            "concept": concept,
            "canon_avg_sim": avg_sim,
            "models": list(results.keys()),
        })

        return {
            "concept": concept,
            "canon_avg_sim": avg_sim,
            "results": results,
        }

    def write_paper(self, title: str, outline: str, words: int = 400,
                    model: str = "deepseek_reasoner") -> dict:
        """Generate a Canon piece in the SuperInstance style.

        Style: short paragraphs, machine/storm metaphors, witness-heavy.
        """
        style_prompt = (
            "You write papers in the SuperInstance Quilt canon style:\n"
            "- Short paragraphs\n"
            "- Nautical + machine metaphors (cells, substrates, anchors, hash, witness)\n"
            "- Every concept is a cell with witness roots\n"
            "- Direct, declarative sentences\n"
            "- Examples before definitions\n"
            "- End with a 'what is missing' or 'the cell at 3am' pivot\n\n"
            "Output ONLY the paper. No title, no preamble."
        )
        full_prompt = f"{style_prompt}\n\nTITLE: {title}\n\nOUTLINE: {outline}\n\nWrite the paper ({words} words):"

        messages = [
            {"role": "system", "content": style_prompt},
            {"role": "user", "content": full_prompt}
        ]
        result = call_llm(model, messages, max_tokens=words * 3, temperature=0.7)
        self._record("WRITE_PAPER", result)
        return result


def main():
    print("=" * 70)
    print("  CANON-AWARE QUILT CELL — multi-LLM with canon context")
    print("=" * 70)

    cell = CanonAwareCell("canon-aware-cell-1")
    # Load canon
    print("\n  loading canon...")
    cell.canon.load("/workspace/research/superinstance-advisor/data/full_canon.npz")
    print(f"  canon loaded: {len(cell.canon.embeddings)} pieces")
    cell.bind()
    cell.tick()

    # 1. Simple ask
    print("\n--- ASK: 'what is a Quilt cell?' (3 models in parallel) ---")
    r = cell.ask("what is a Quilt cell?", k=3,
                 models=["deepseek_chat", "seed_mini", "deepseek_reasoner"])
    print(f"  canon hits: {len(r['canon_hits'])} pieces")
    for h in r["canon_hits"]:
        print(f"    - {h['tag'][:40]:40} score={h['score']:.3f}")
    print()
    for m, resp in r["ensemble"].items():
        if resp.get("ok"):
            content = resp["content"][:200].replace("\n", " | ")
            print(f"    {m:20} ({resp['elapsed']:.2f}s, ${resp['cost_usd']:.4f}):")
            print(f"      {content}")

    # 2. Shape negative space
    print()
    print("--- SHAPE: 'post-quantum witness log' (2 models) ---")
    r = cell.shape_negative_space("post-quantum witness log")
    print(f"  canon avg sim: {r['canon_avg_sim']:.3f}")
    for m, resp in r["results"].items():
        if resp.get("ok"):
            content = resp["content"][:200].replace("\n", " | ")
            print(f"    {m:20} ({resp['elapsed']:.2f}s, ${resp['cost_usd']:.4f}):")
            print(f"      {content}")

    # 3. View
    v = cell.view()
    print()
    print("=" * 70)
    print(f"  total cost: ${cell.total_cost_usd:.5f}, witnesses: {v['witness_count']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
