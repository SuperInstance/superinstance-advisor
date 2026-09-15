"""
multi_llm_quilt.py
==================

A Quilt cell that uses MULTIPLE LLMs across the 5 opcodes.

Routing:
    BIND   → programmatic (no LLM)
    LINK   → programmatic
    EFFECT (canon-query) → deepseek-reasoner (deep thinking)
    EFFECT (canon-shape) → ByteDance/Seed-2.0-mini (cheap, fast, with reasoning)
    EFFECT (canon-write) → deepseek-coder (code)
    EFFECT (advise) → deepseek-chat (general purpose)
    VIEW   → programmatic + LLM compression (deepseek-chat)
    TICK   → programmatic

Multiple EFFECTs run concurrently when possible. Each LLM call
writes a witness entry. The witness log captures every model decision.
"""

from __future__ import annotations
import sys, os, json, time, urllib.request, urllib.error
import concurrent.futures
import hashlib
from dataclasses import dataclass
sys.path.insert(0, '/workspace/research/superinstance-advisor')

# ============================================================================
# LLM providers
# ============================================================================

PROVIDERS = {
    "deepseek_chat": {
        "url": "https://api.deepseek.com/chat/completions",
        "model": "deepseek-chat",
        "token": os.environ.get("DEEPSEEK_TOKEN"),
        "cost_per_1k": 0.00027,
    },
    "deepseek_reasoner": {
        "url": "https://api.deepseek.com/chat/completions",
        "model": "deepseek-reasoner",
        "token": os.environ.get("DEEPSEEK_TOKEN"),
        "cost_per_1k": 0.55,  # reasoning is expensive
    },
    "deepseek_coder": {
        "url": "https://api.deepseek.com/chat/completions",
        "model": "deepseek-coder",
        "token": os.environ.get("DEEPSEEK_TOKEN"),
        "cost_per_1k": 0.00027,
    },
    "seed_mini": {
        "url": "https://api.deepinfra.com/v1/openai/chat/completions",
        "model": "ByteDance/Seed-2.0-mini",
        "token": os.environ.get("DEEPINFRA_TOKEN"),
        "cost_per_1k": 0.0003,
    },
    "seed_pro": {
        "url": "https://api.deepinfra.com/v1/openai/chat/completions",
        "model": "ByteDance/Seed-2.0-pro",
        "token": os.environ.get("DEEPINFRA_TOKEN"),
        "cost_per_1k": 0.003,
    },
    "seed_code": {
        "url": "https://api.deepinfra.com/v1/openai/chat/completions",
        "model": "ByteDance/Seed-2.0-code",
        "token": os.environ.get("DEEPINFRA_TOKEN"),
        "cost_per_1k": 0.003,
    },
}


def call_llm(provider: str, messages: list, max_tokens: int = 800,
             temperature: float = 0.3, timeout: float = 30) -> dict:
    """Call an LLM provider. Returns {ok, content, usage, elapsed, model}."""
    p = PROVIDERS[provider]
    if not p["token"]:
        return {"ok": False, "err": f"no token for {provider}", "provider": provider}

    body = json.dumps({
        "model": p["model"],
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }).encode()
    req = urllib.request.Request(p["url"], data=body, method="POST",
        headers={"Authorization": f"Bearer {p['token']}",
                 "Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read())
            elapsed = time.time() - t0
            usage = d.get("usage", {})
            content = d["choices"][0]["message"]["content"]
            cost = (usage.get("total_tokens", 0) / 1000) * p["cost_per_1k"]
            return {
                "ok": True,
                "content": content,
                "usage": usage,
                "elapsed": elapsed,
                "model": d.get("model", p["model"]),
                "cost_usd": cost,
                "provider": provider,
            }
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors='replace')[:200]
        return {"ok": False, "err": body, "provider": provider, "elapsed": time.time() - t0}
    except Exception as e:
        return {"ok": False, "err": f"{type(e).__name__}: {str(e)[:80]}",
                "provider": provider, "elapsed": time.time() - t0}


# ============================================================================
# Quilt cell with multi-LLM
# ============================================================================

@dataclass
class Witness:
    op: str
    ts: float
    payload: dict


class MultiLLMQuiltCell:
    """A Quilt cell that routes each opcode to the best LLM."""

    def __init__(self, name: str = "multi-llm-quilt"):
        self.name = name
        self.address = hashlib.sha256(f"{name}-{time.time()}".encode()).hexdigest()[:12]
        self.bound = False
        self.witness_log: list[dict] = []
        self.tick_count = 0
        self.total_cost_usd = 0.0
        self.call_history: list[dict] = []

    def _witness(self, op: str, payload: dict):
        entry = {"op": op, "ts": time.time(), "payload": payload}
        self.witness_log.append(entry)
        return entry

    def bind(self) -> str:
        self.bound = True
        self._witness("BIND", {"address": self.address, "name": self.name})
        return self.address

    def tick(self) -> dict:
        self.tick_count += 1
        self._witness("TICK", {"tick_count": self.tick_count})
        return self.witness_log[-1]

    def view(self) -> dict:
        return {
            "address": self.address,
            "name": self.name,
            "bound": self.bound,
            "tick_count": self.tick_count,
            "witness_count": len(self.witness_log),
            "total_cost_usd": self.total_cost_usd,
            "calls": len(self.call_history),
        }

    # ----- EFFECT: route the right LLM per task -----

    def effect_advise(self, question: str, canon_hits: list) -> dict:
        """Use deepseek-chat (general purpose) to compose advice."""
        canon_text = "\n".join(
            f"  - {h['tag']}: score={h['score']:.3f}"
            for h in canon_hits[:3]
        )
        messages = [
            {"role": "system", "content": "You are the canon's advisor. "
             "Given a question and canon pieces, write 2-3 sentences of guidance. "
             "Be direct. No preamble. No meta."},
            {"role": "user", "content":
             f"Question: {question}\n\n"
             f"Nearest canon pieces:\n{canon_text}\n\n"
             f"Write the advice."}
        ]
        result = call_llm("deepseek_chat", messages, max_tokens=300, temperature=0.4)
        self._record("advise", result)
        return result

    def effect_shape_negative_space(self, concept: str, canon_avg_sim: float) -> dict:
        """Use ByteDance/Seed-2.0-mini (cheap, with reasoning) to probe gap."""
        messages = [
            {"role": "system", "content": "You probe canon negative space. "
             "Given a concept and its cosine similarity to canon, decide: "
             "is this concept in_canon (>0.75), edge_of_canon (>0.65), or "
             "negative_space (<=0.65)? Reply with ONE word: in_canon, "
             "edge_of_canon, or negative_space. Then on a new line, write "
             "1 sentence explaining the gap."},
            {"role": "user", "content":
             f"Concept: {concept}\n"
             f"Average canon similarity: {canon_avg_sim:.3f}\n\n"
             f"Your verdict:"}
        ]
        result = call_llm("seed_mini", messages, max_tokens=200, temperature=0.2)
        self._record("shape_negative_space", result)
        return result

    def effect_query_with_reasoning(self, question: str) -> dict:
        """Use deepseek-reasoner (deep thinking) for the hardest queries."""
        messages = [
            {"role": "system", "content": "Think deeply about this question. "
             "Show your reasoning briefly, then give the answer."},
            {"role": "user", "content": question}
        ]
        result = call_llm("deepseek_reasoner", messages, max_tokens=2000, temperature=0.6)
        self._record("query_with_reasoning", result)
        return result

    def effect_write_code(self, task: str, language: str = "python") -> dict:
        """Use deepseek-coder for code generation."""
        messages = [
            {"role": "system", "content": f"You write {language} code. "
             "Output ONLY code, no explanation. No markdown fences."},
            {"role": "user", "content": task}
        ]
        result = call_llm("deepseek_coder", messages, max_tokens=2000, temperature=0.2)
        self._record("write_code", result)
        return result

    def effect_ensemble(self, question: str) -> dict:
        """Run the same query on multiple models, return all responses.

        Concurrency: 5+ LLMs in parallel via ThreadPoolExecutor.
        """
        models = ["deepseek_chat", "deepseek_reasoner", "seed_mini", "seed_code"]
        messages = [{"role": "user", "content": question}]

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(models)) as ex:
            futures = {ex.submit(call_llm, m, messages, 500, 0.5): m for m in models}
            results = {}
            for f in concurrent.futures.as_completed(futures):
                m = futures[f]
                r = f.result()
                results[m] = r
                self._record(f"ensemble:{m}", r)
        return results

    def _record(self, op: str, result: dict):
        self._witness(op, result)
        if result.get("ok") and result.get("cost_usd"):
            self.total_cost_usd += result["cost_usd"]
        self.call_history.append(result)


# ============================================================================
# Demo
# ============================================================================

def demo():
    print("=" * 70)
    print("  MULTI-LLM QUILT CELL — concurrent fan-out across providers")
    print("=" * 70)
    print()
    cell = MultiLLMQuiltCell("quilt.multi-llm.demo")
    cell.bind()
    cell.tick()

    # Single calls
    print("--- single calls ---")
    r = cell.effect_advise("what is the substrate?", [
        {"tag": "56-the-substrate", "score": 0.762},
        {"tag": "59-the-substrate-stack", "score": 0.739},
        {"tag": "44-the-cell-as-substrate", "score": 0.724},
    ])
    print(f"  advise ({r.get('model','?')}, {r.get('elapsed',0):.2f}s, ${r.get('cost_usd',0):.4f}):")
    print(f"    {r.get('content','')[:200]}")

    r = cell.effect_shape_negative_space("encryption of the witness log", 0.679)
    print(f"\n  shape_negative_space ({r.get('model','?')}, {r.get('elapsed',0):.2f}s, ${r.get('cost_usd',0):.4f}):")
    print(f"    {r.get('content','')[:200]}")

    # Ensemble — fan out across 4 models
    print(f"\n--- ensemble: same question to 4 LLMs in parallel ---")
    results = cell.effect_ensemble("In one sentence, what is a Quilt cell?")
    for m, r in results.items():
        sym = "✓" if r.get("ok") else "✗"
        if r.get("ok"):
            content = r.get('content', '')[:80].replace('\n', ' ')
            print(f"  {sym} {m:20} ({r['elapsed']:.2f}s, ${r.get('cost_usd',0):.4f}): {content}")
        else:
            print(f"  {sym} {m:20} {r.get('err','?')[:60]}")

    # View
    v = cell.view()
    print()
    print("=" * 70)
    print("  CELL VIEW")
    print("=" * 70)
    for k, val in v.items():
        if isinstance(val, float):
            print(f"  {k:20} {val:.5f}")
        else:
            print(f"  {k:20} {val}")
    print()
    print(f"  Total cost so far: ${cell.total_cost_usd:.5f}")


if __name__ == "__main__":
    demo()
