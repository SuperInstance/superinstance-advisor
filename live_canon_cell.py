"""
live_canon_cell.py — REAL endpoints
====================================

A cell that patches into the live production canon at
live-canon.superinstance.dev via its actual REST API surface.

Real endpoints (discovered by probing):
    GET  /api/canon                          # list all papers (returns 14)
    GET  /api/canon/hash                     # state hash + paper count
    GET  /api/canon/navigate?paper=N&depth=D # NAVIGATE: get paper's neighborhood
    GET  /api/canon/lineage?id=N             # LINEAGE: trace dependencies
    GET  /api/canon/confluence?ids=A,B,C     # CONFLUENCE: merge papers
    GET  /api/canon/ghost?id=N               # GHOST: counterfactual cell
    GET  /api/canon/tick                     # TICK: advance all dials
    GET  /api/vibe?lang=python|go|rust|...   # VIBE: 30-second protocol
    GET  /api/quilt/verify?lang=X&hash=H     # VERIFY: byte-exact check
    POST /api/cell                           # SUBMIT: add a new cell

This is the actual production cell-graph runtime. The 14 papers
in this canon are the canonical "papers" — F129 (the live canon itself),
F122 (the shape store), F115 (logical routes in VHDL/Verilog), etc.
"""

from __future__ import annotations
import json, time, urllib.request, urllib.error, urllib.parse, os
from typing import Optional


LIVE_CANON_BASE = "https://live-canon.superinstance.dev"


class LiveCanonCell:
    """A cell that patches into live-canon.superinstance.dev.

    Wraps the live REST API as a neighbor. Every EFFECT is a real
    HTTP call; every response is logged in the witness.
    """

    def __init__(self, base_url: str = LIVE_CANON_BASE, timeout: float = 10.0,
                 max_retries: int = 5):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.witness_log: list[dict] = []
        self.reachable = True
        self.canon_meta: Optional[dict] = None

    def _call(self, path: str, params: Optional[dict] = None,
              method: str = "GET", body: Optional[dict] = None) -> dict:
        url = f"{self.base_url}{path}"
        if params:
            # Filter None values
            params = {k: v for k, v in params.items() if v is not None}
            url += "?" + urllib.parse.urlencode(params)

        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(url, data=data, method=method,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "superinstance-advisor/1.0",
            } if body else {"User-Agent": "superinstance-advisor/1.0"})

        for attempt in range(self.max_retries):
            t0 = time.time()
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read().decode()
                    try:
                        result = json.loads(raw)
                    except json.JSONDecodeError:
                        result = raw[:500]
                    elapsed_ms = (time.time() - t0) * 1000
                    self._witness("LIVE_CALL", {
                        "url": url, "method": method, "ok": True,
                        "status": resp.status, "elapsed_ms": elapsed_ms,
                    })
                    return {"ok": True, "data": result, "status": resp.status,
                            "elapsed_ms": elapsed_ms, "url": url}
            except urllib.error.HTTPError as e:
                body_text = e.read().decode(errors='replace')[:200] if e.fp else ""
                elapsed_ms = (time.time() - t0) * 1000
                # Retry on 503
                if e.code == 503 and attempt < self.max_retries - 1:
                    self._witness("LIVE_CALL", {
                        "url": url, "method": method, "ok": False,
                        "status": e.code, "err": body_text[:80],
                        "retry": attempt,
                    })
                    time.sleep(1.0 * (attempt + 1))
                    continue
                self.reachable = False
                self._witness("LIVE_CALL", {
                    "url": url, "method": method, "ok": False,
                    "status": e.code, "err": body_text[:80],
                })
                return {"ok": False, "err": body_text[:80], "status": e.code,
                        "url": url}
            except urllib.error.URLError as e:
                elapsed_ms = (time.time() - t0) * 1000
                self.reachable = False
                self._witness("LIVE_CALL", {
                    "url": url, "method": method, "ok": False,
                    "err": str(e)[:80],
                })
                return {"ok": False, "err": str(e)[:80], "url": url}
            except Exception as e:
                elapsed_ms = (time.time() - t0) * 1000
                self.reachable = False
                return {"ok": False, "err": f"{type(e).__name__}: {str(e)[:80]}",
                        "url": url, "elapsed_ms": elapsed_ms}

        return {"ok": False, "err": "max retries"}

    # ----- The actual opcodes -----

    def list_papers(self, limit: Optional[int] = None) -> dict:
        """List all papers in the canon."""
        return self._call("/api/canon", {"limit": limit} if limit else None)

    def canon_hash(self) -> dict:
        """The byte-exact state hash + paper count + target."""
        result = self._call("/api/canon/hash")
        if result.get("ok"):
            self.canon_meta = result["data"]
        return result

    def navigate(self, paper_id: int, depth: int = 1) -> dict:
        """NAVIGATE: get the paper's neighborhood."""
        return self._call("/api/canon/navigate", {"paper": paper_id, "depth": depth})

    def lineage(self, paper_id: int) -> dict:
        """LINEAGE: trace dependencies."""
        return self._call("/api/canon/lineage", {"id": paper_id})

    def confluence(self, ids: list[int]) -> dict:
        """CONFLUENCE: merge multiple papers."""
        return self._call("/api/canon/confluence", {"ids": ",".join(map(str, ids))})

    def ghost(self, paper_id: int) -> dict:
        """GHOST: counterfactual cell (what if this hadn't been written)."""
        return self._call("/api/canon/ghost", {"id": paper_id})

    def tick(self) -> dict:
        """TICK: advance all dials (server-side state advance)."""
        return self._call("/api/canon/tick")

    def vibe(self, lang: str = "python") -> dict:
        """VIBE: the 30-second protocol for any language."""
        return self._call("/api/vibe", {"lang": lang})

    def verify(self, lang: str, hash_: str) -> dict:
        """VERIFY: byte-exact port check."""
        return self._call("/api/quilt/verify", {"lang": lang, "hash": hash_})

    def submit_cell(self, dials: list, refs: list, title: str) -> dict:
        """SUBMIT a new cell."""
        body = {"dials": dials, "refs": refs, "title": title}
        return self._call("/api/cell", method="POST", body=body)

    def _witness(self, op: str, payload: dict):
        self.witness_log.append({"op": op, "ts": time.time(), "payload": payload})

    def view(self) -> dict:
        return {
            "base_url": self.base_url,
            "reachable": self.reachable,
            "witness_count": len(self.witness_log),
            "canon_meta": self.canon_meta,
        }


# ============================================================================
# Cell-patching: bind live-canon endpoints as methods on a Cell
# ============================================================================

def patch_cell_with_live_canon(cell, base_url: str = LIVE_CANON_BASE):
    """Patch a Cell with the live-canon endpoints."""
    live = LiveCanonCell(base_url=base_url)

    def navigate(self, paper_id, depth=1):
        return live.navigate(paper_id, depth)

    def lineage(self, paper_id):
        return live.lineage(paper_id)

    def confluence(self, ids):
        return live.confluence(ids)

    def ghost(self, paper_id):
        return live.ghost(paper_id)

    def tick_canon(self):
        return live.tick()

    def vibe(self, lang="python"):
        return live.vibe(lang)

    def verify_port(self, lang, hash_):
        return live.verify(lang, hash_)

    def submit_cell_to_live(self, dials, refs, title):
        return live.submit_cell(dials, refs, title)

    def list_papers(self):
        return live.list_papers()

    def canon_hash(self):
        return live.canon_hash()

    def list_papers_local(self):
        return live.list_papers()

    cell.live = live
    cell.live_navigate = navigate.__get__(cell)
    cell.live_lineage = lineage.__get__(cell)
    cell.live_confluence = confluence.__get__(cell)
    cell.live_ghost = ghost.__get__(cell)
    cell.live_tick = tick_canon.__get__(cell)
    cell.live_vibe = vibe.__get__(cell)
    cell.live_verify = verify_port.__get__(cell)
    cell.live_submit = submit_cell_to_live
    cell.live_list = list_papers
    cell.live_hash = canon_hash

    return cell
