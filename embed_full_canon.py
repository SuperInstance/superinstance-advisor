"""
embed_full_canon.py
===================

Pull every .md file from the AI-Writings corpus, embed each as a 768-d vector
using Cloudflare's bge-base-en-v1.5, and persist the full canonical map.

This is the iceberg below the surface. Without this, every claim about
"what's in the canon" is a guess. With this, every claim is grounded
in real semantic coordinates.

Pipeline:
    1. Walk the AI-Writings repo (recursively list all .md files)
    2. For each file, fetch the first ~2KB (the keel — what defines the voice)
    3. Embed with bge-base (768d, cosine)
    4. Save to /workspace/research/superinstance-advisor/data/full_canon.npz
    5. Also save metadata: tag, repo_path, byte_count, embedding dims

Resumable: keeps a checkpoint file. If interrupted, resume from last batch.
"""

import json, time, urllib.request, os, base64
import numpy as np

ACCT = "049ff5e84ecf636b53b162cbb580aae6"
EMBED_URL = f"https://api.cloudflare.com/client/v4/accounts/{ACCT}/ai/run/@cf/baai/bge-base-en-v1.5"

CHECKPOINT = "/workspace/research/superinstance-advisor/data/checkpoint.json"
OUTPUT_NPZ = "/workspace/research/superinstance-advisor/data/full_canon.npz"
DATA_DIR = "/workspace/research/superinstance-advisor/data"

os.makedirs(DATA_DIR, exist_ok=True)


def embed(text, max_retries=6):
    """Embed a text with exponential backoff."""
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(EMBED_URL,
                data=json.dumps({"text": [text[:2500]]}).encode(),
                headers={"Authorization": f"Bearer {os.environ['CLOUDFLARE_TOKEN']}",
                         "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                r = json.load(resp)
                return np.array(r["result"]["data"][0], dtype=np.float32)
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < max_retries - 1:
                wait = 2 ** attempt
                time.sleep(wait)
                continue
            return None
        except Exception as e:
            print(f"  ! embed err: {e}")
            return None
    return None


def list_md_files_recursive(repo="AI-Writings", path=""):
    """Walk the repo tree and yield (repo, full_path, size, sha) for each .md file."""
    token = os.environ['GITHUB_TOKEN']
    url = f"https://api.github.com/repos/SuperInstance/{repo}/contents/{path}?ref=main"
    req = urllib.request.Request(url, headers={"Authorization": f"token {token}"})
    with urllib.request.urlopen(req) as resp:
        r = json.load(resp)
    if not isinstance(r, list):
        return
    for item in r:
        if item.get("type") == "dir":
            yield from list_md_files_recursive(repo, item["path"])
        elif item.get("type") == "blob" and item["name"].endswith(".md"):
            yield repo, item["path"], item.get("size", 0), item.get("sha", "")


def fetch_content(repo, path):
    token = os.environ['GITHUB_TOKEN']
    url = f"https://api.github.com/repos/SuperInstance/{repo}/contents/{path}?ref=main"
    req = urllib.request.Request(url, headers={"Authorization": f"token {token}"})
    with urllib.request.urlopen(req) as resp:
        r = json.load(resp)
    return base64.b64decode(r["content"]).decode(errors='replace')


def main():
    print("=" * 60)
    print("  FULL CANON EMBED PIPELINE")
    print("=" * 60)
    print()

    # 1. Inventory all .md files
    files = list(list_md_files_recursive())
    print(f"Found {len(files)} .md files in AI-Writings corpus")

    # Filter: only embed reasonably-sized files (skip 0-byte and >100KB)
    targets = [(r, p, s, sha) for r, p, s, sha in files if 200 < s < 80000]
    print(f"Targets after size filter (200B..80KB): {len(targets)}")

    # 2. Load checkpoint
    done = set()
    if os.path.exists(CHECKPOINT):
        with open(CHECKPOINT) as f:
            ckpt = json.load(f)
            done = set(ckpt.get("done", []))
        print(f"Resuming from checkpoint: {len(done)} already done")

    # 3. Embed in batches
    embeddings = []
    tags = []
    paths = []
    sizes = []
    n_done = 0

    for repo, path, size, sha in targets:
        if path in done:
            continue

        try:
            text = fetch_content(repo, path)
        except Exception as e:
            print(f"  ! fetch err {path}: {e}")
            continue

        snippet = text[:2500]
        tag = path.replace("/", ".").rstrip(".md")

        vec = embed(snippet)
        if vec is None or len(vec) != 768:
            print(f"  ! skip {path}: embed failed")
            continue

        embeddings.append(vec)
        tags.append(tag)
        paths.append(path)
        sizes.append(len(text))
        n_done += 1

        if n_done % 20 == 0:
            print(f"  ... {n_done} embedded so far ({path})")
            # Checkpoint
            with open(CHECKPOINT, "w") as f:
                json.dump({"done": list(done | set(paths))}, f)
            time.sleep(1)  # brief pause between batches

        # Each successful add
        if n_done % 50 == 0:
            print(f"    [{n_done}] {tag} ({size}B)")

        time.sleep(0.2)  # politeness

    print(f"\nNew embedded in this run: {n_done}")
    print(f"Total in memory: {len(embeddings)}")

    # 4. Load existing data if available, merge
    if os.path.exists(OUTPUT_NPZ):
        old = np.load(OUTPUT_NPZ, allow_pickle=True)
        old_embs = list(old["embeddings"])
        old_tags = list(old["tags"])
        old_paths = list(old["paths"])
        old_sizes = list(old["sizes"])
        print(f"\nMerging with existing: {len(old_embs)} old embeddings")
        # Dedupe by tag
        all_embs = list(old_embs) + embeddings
        all_tags = list(old_tags) + tags
        all_paths = list(old_paths) + paths
        all_sizes = list(old_sizes) + sizes
        seen = {}
        for i, t in enumerate(all_tags):
            if t not in seen:
                seen[t] = i
        unique = sorted(seen.values())
        all_embs = [all_embs[i] for i in unique]
        all_tags = [all_tags[i] for i in unique]
        all_paths = [all_paths[i] for i in unique]
        all_sizes = [all_sizes[i] for i in unique]
        print(f"After dedupe: {len(all_tags)} unique")
    else:
        all_embs = embeddings
        all_tags = tags
        all_paths = paths
        all_sizes = sizes

    # 5. Save
    arr = np.array(all_embs)
    np.savez(OUTPUT_NPZ,
        embeddings=arr, tags=all_tags, paths=all_paths, sizes=all_sizes)

    # 6. Update checkpoint
    with open(CHECKPOINT, "w") as f:
        json.dump({"done": all_paths}, f)

    print(f"\nSaved: {OUTPUT_NPZ}")
    print(f"  embeddings: {arr.shape}")
    print(f"  tags: {len(all_tags)}")
    print(f"  total bytes in corpus: {sum(all_sizes)}")

    # 7. Compute the global similarity structure
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1
    arr_norm = arr / norms
    sim_matrix = arr_norm @ arr_norm.T

    # Save similarity matrix
    sim_path = "/workspace/research/superinstance-advisor/data/sim_matrix.npy"
    np.save(sim_path, sim_matrix)
    np.save("/workspace/research/superinstance-advisor/data/tags.npy", np.array(all_tags, dtype=object))
    print(f"  similarity matrix: {sim_matrix.shape} → {sim_path}")

    # 8. Initial shape report
    print("\n" + "=" * 60)
    print("  INITIAL SHAPE OF THE FULL CANON")
    print("=" * 60)

    # Cosine similarity distribution
    off_diag = []
    n = len(sim_matrix)
    for i in range(n):
        for j in range(i + 1, n):
            off_diag.append(sim_matrix[i][j])
    off_diag = np.array(off_diag)
    print(f"\n  Total pieces: {n}")
    print(f"  Off-diagonal similarities: min={off_diag.min():.3f} max={off_diag.max():.3f} mean={off_diag.mean():.3f}")
    print(f"  Median similarity: {np.median(off_diag):.3f}")

    # Most central pieces (highest avg similarity)
    sums = []
    for i in range(n):
        others = [sim_matrix[i][j] for j in range(n) if i != j]
        sums.append((sum(others) / len(others), all_tags[i]))
    sums.sort(reverse=True)
    print(f"\n  Most central (highest avg similarity):")
    for s, t in sums[:8]:
        print(f"    {s:.4f}  {t}")

    # Most isolated (lowest avg similarity — the loneliest pieces)
    sums.sort()
    print(f"\n  Most isolated (lowest avg similarity):")
    for s, t in sums[:8]:
        print(f"    {s:.4f}  {t}")


if __name__ == '__main__':
    main()
