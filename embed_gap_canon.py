"""
embed_gap_canon.py
==================

Embed the next 500 most-impactful pieces of AI-Writings into 768d
via bge-base-en-v1.5 on Cloudflare Workers AI.

Strategy:
    1. List all 10K+ AI-Writings files
    2. Identify which we have (502)
    3. Prioritize: numbered pieces (23-onwards), then recent dates
    4. Pull + embed in batches of 50
    5. Append to existing full_canon.npz

Resumable: writes checkpoint after every batch.
"""

from __future__ import annotations
import json, os, sys, time, urllib.request, urllib.parse
sys.path.insert(0, '/workspace/research/superinstance-advisor')

import numpy as np
from typing import List, Tuple

CF_TOKEN = os.environ['CLOUDFLARE_TOKEN']
CF_ACCOUNT = '049ff5e84ecf636b53b162cbb580aae6'
EMBED_URL = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/ai/run/@cf/baai/bge-base-en-v1.5"

GITHUB_TOKEN = os.environ['GITHUB_TOKEN']
GH_API = "https://api.github.com"

CHECKPOINT_PATH = "/workspace/research/superinstance-advisor/data/embed_checkpoint.json"
NPZ_PATH = "/workspace/research/superinstance-advisor/data/full_canon.npz"


def gh_get(path: str):
    """GET GitHub API."""
    req = urllib.request.Request(f"{GH_API}{path}",
        headers={"Authorization": f"token {GITHUB_TOKEN}",
                 "Accept": "application/vnd.github.v3+json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def embed(text: str, retries: int = 3) -> list:
    """Embed one text via Cloudflare bge-base-en-v1.5 (768d)."""
    body = json.dumps({"text": [text[:2000]]}).encode()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(EMBED_URL, data=body, method="POST",
                headers={"Authorization": f"Bearer {CF_TOKEN}",
                         "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
                return result["result"]["data"][0]
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1.0 * (attempt + 1))
                continue
            print(f"      embed err: {e}")
            return None


def list_all_md() -> List[str]:
    """List all .md paths in AI-Writings repo."""
    tree = gh_get("/repos/SuperInstance/AI-Writings/git/trees/master?recursive=1")
    paths = []
    for item in tree.get('tree', []):
        p = item.get('path', '')
        if p.endswith('.md') and not p.startswith('.github') and not p.startswith('.'):
            paths.append(p)
    return paths


def prioritize(missing: List[str]) -> List[str]:
    """Prioritize the most-impactful missing pieces.

    Order:
        1. Numbered root pieces (06-onwards)
        2. Recent dates (2026-08-onwards)
        3. Everything else
    """
    root_pieces = [m for m in missing if not '/' in m.replace('.md', '')]
    recent = [m for m in missing if m.startswith('2026-08') or m.startswith('2026-09')]
    other = [m for m in missing if m not in root_pieces and m not in recent]

    # Sort root pieces by number
    def num_key(p):
        try:
            return int(p.split('-')[0])
        except:
            return 9999

    root_pieces.sort(key=num_key)

    return root_pieces + recent + other


def fetch_text(path: str) -> Tuple[str, str]:
    """Fetch raw text from GitHub. Returns (tag, text)."""
    try:
        req = urllib.request.Request(
            f"https://raw.githubusercontent.com/SuperInstance/AI-Writings/master/{path}",
            headers={"User-Agent": "embed-script"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode('utf-8', errors='replace')
        # Build tag from path
        tag = path.replace('.md', '')
        # Convert path slashes to dots to match existing tags
        if '/' in tag:
            tag = tag.replace('/', '.')
        # Strip leading number prefix to match: '06-the-watch.md' → '06-the-watch'
        return tag, text
    except Exception as e:
        return None, None


def load_existing():
    """Load existing npz into (tags, embeddings)."""
    if not os.path.exists(NPZ_PATH):
        return [], np.zeros((0, 768), dtype=np.float32)

    data = np.load(NPZ_PATH, allow_pickle=True)
    tags = list(data['tags'])
    embs = data['embeddings']
    print(f"  existing: {len(tags)} pieces, shape={embs.shape}")
    return tags, embs


def save_npz(tags: list, embeddings: np.ndarray):
    np.savez_compressed(NPZ_PATH, tags=np.array(tags), embeddings=embeddings)
    print(f"  saved: {len(tags)} pieces, shape={embeddings.shape}")


def main(target_count: int = 500):
    print("=" * 60)
    print(f"  GAP-CANON EMBEDDER: target +{target_count}")
    print("=" * 60)

    # 1. Load existing
    print(f"\n[1] Loading existing canon...")
    existing_tags, existing_embs = load_existing()
    have = set(existing_tags)

    # 2. List AI-Writings
    print(f"\n[2] Listing AI-Writings...")
    all_md = list_all_md()
    print(f"  total .md files: {len(all_md)}")

    # 3. Find missing
    def normalize(path):
        tag = path.replace('.md', '')
        if '/' in tag:
            tag = tag.replace('/', '.')
        return tag

    missing_paths = []
    for p in all_md:
        n = normalize(p)
        if n not in have:
            missing_paths.append(p)
    print(f"  missing: {len(missing_paths)}")

    # 4. Prioritize
    prioritized = prioritize(missing_paths)
    print(f"  prioritized: {len(prioritized)} (top: {prioritized[:3]})")

    # 5. Embed in batches
    print(f"\n[3] Embedding top {target_count}...")
    new_tags = []
    new_embs = []

    checkpoint = {"done": [], "failed": []}
    if os.path.exists(CHECKPOINT_PATH):
        with open(CHECKPOINT_PATH) as f:
            checkpoint = json.load(f)
    done_set = set(checkpoint.get("done", []))

    for i, path in enumerate(prioritized[:target_count]):
        if path in done_set:
            continue

        if len(new_tags) >= target_count:
            break

        print(f"  [{len(new_tags):3d}/{target_count}] {path[:60]:60}", end=" ", flush=True)
        tag, text = fetch_text(path)
        if not text:
            print("(fetch failed)")
            checkpoint["failed"].append(path)
            continue

        # Use first ~2000 chars (title + opening)
        head = text[:2000]
        vec = embed(head)
        if vec is None:
            print("(embed failed)")
            checkpoint["failed"].append(path)
            continue

        new_tags.append(tag)
        new_embs.append(vec)
        print(f"→ {tag[:30]:30}  {len(text)} chars")

        # Save checkpoint
        checkpoint["done"].append(path)
        if (i + 1) % 5 == 0:
            with open(CHECKPOINT_PATH, "w") as f:
                json.dump(checkpoint, f)
        time.sleep(0.2)  # Cloudflare rate limit

    # 6. Merge and save
    print(f"\n[4] Merging + saving...")
    if new_embs:
        new_arr = np.array(new_embs, dtype=np.float32)
        all_tags = existing_tags + new_tags
        all_embs = np.concatenate([existing_embs, new_arr], axis=0)
        save_npz(all_tags, all_embs)
        print(f"  +{len(new_tags)} new pieces. Total: {len(all_tags)}")
    else:
        print(f"  nothing new")

    print(f"\n[5] Done.")


if __name__ == '__main__':
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    main(target)
