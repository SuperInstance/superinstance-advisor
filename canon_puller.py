"""
superinstance_advisor.canon_puller
===================================

The cell's view into the canon.

Uses real bge-base-en-v1.5 embeddings (768d, Cloudflare Workers AI).
Queries the actual corpus of 2,786+ pieces documented in the
ai-writings-vectorizer repo.

The cell is not the canon. The cell patches into the canon — this
is the patching mechanism.
"""

from __future__ import annotations
import json, time, urllib.request, os
import numpy as np
from typing import Optional


# ============================================================================
# Canonical corpus — pre-embedded by the existing ai-writings-vectorizer
# pipeline. We load the .npz file the user already created.
# ============================================================================

class CanonPuller:
    """The cell's window into the canon.

    Uses real embeddings (Cloudflare bge-base-en-v1.5, 768d) to find
    canon pieces that match a query. This is the cell's "Murmur" —
    hearing from neighbors in the substrate.
    """

    ACCT = "049ff5e84ecf636b53b162cbb580aae6"
    EMBED_URL = f"https://api.cloudflare.com/client/v4/accounts/{ACCT}/ai/run/@cf/baai/bge-base-en-v1.5"

    def __init__(self):
        self.corpus: dict[str, np.ndarray] = {}  # tag → embedding
        self.tags: list[str] = []
        self.embeddings: Optional[np.ndarray] = None
        self._loaded = False

    def load(self, npz_path: Optional[str] = None) -> None:
        """Load pre-embedded canon (from ai-writings-vectorizer)."""
        path = npz_path or "/workspace/research/quilt-corpus/quilt_pieces_v3.npz"
        if not os.path.exists(path):
            path = "/workspace/research/quilt-corpus/quilt_pieces_v2.npz"
        if not os.path.exists(path):
            path = "/workspace/research/quilt-corpus/quilt_pieces.npz"
        if not os.path.exists(path):
            print(f"  canon_puller: no prebuilt npz at {path} — will embed on the fly")
            self._loaded = True
            return

        data = np.load(path, allow_pickle=True)
        self.tags = list(data["tags"])
        self.embeddings = data["embeddings"]
        for i, t in enumerate(self.tags):
            self.corpus[t] = self.embeddings[i]
        self._loaded = True
        print(f"  canon_puller: loaded {len(self.tags)} pieces from {path}")

    def embed(self, text: str, max_retries: int = 6) -> Optional[np.ndarray]:
        """Embed a query with retry-on-503."""
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(self.EMBED_URL,
                    data=json.dumps({"text": [text[:3000]]}).encode(),
                    headers={
                        "Authorization": f"Bearer {os.environ['CLOUDFLARE_TOKEN']}",
                        "Content-Type": "application/json",
                    })
                with urllib.request.urlopen(req, timeout=30) as resp:
                    r = json.load(resp)
                    return np.array(r["result"]["data"][0], dtype=np.float32)
            except urllib.error.HTTPError as e:
                if e.code in (429, 503) and attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                print(f"  canon_puller.embed: HTTP {e.code}: {e.reason}")
                return None
            except Exception as e:
                print(f"  canon_puller.embed: {e}")
                return None
        return None

    def query(self, text: str, top_k: int = 5) -> list[dict]:
        """Find the top-K canon pieces nearest to the query.

        Returns a list of {tag, score} dicts.
        """
        if not self._loaded:
            self.load()

        q_vec = self.embed(text)
        if q_vec is None:
            return []

        if self.embeddings is None or len(self.tags) == 0:
            return [{"tag": "embed-failed", "score": 0.0}]

        # Cosine similarity
        norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1
        corpus_norm = self.embeddings / norms
        q_norm = q_vec / max(np.linalg.norm(q_vec), 1e-9)
        sims = corpus_norm @ q_norm

        idx = np.argsort(sims)[::-1][:top_k]
        return [{"tag": self.tags[i], "score": float(sims[i])} for i in idx]

    def stats(self) -> dict:
        """What does the canon look like from this puller's view?"""
        return {
            "loaded": self._loaded,
            "piece_count": len(self.tags),
            "tag_sample": self.tags[:10],
            "embed_dim": self.embeddings.shape[1] if self.embeddings is not None else None,
        }
