"""
embed_full_canon_v2.py
======================

Bulk-embed the AI-Writings corpus. Uses the git tree API for fast inventory
(one call) then embeds each file individually with retry.

Targets:
    - 2,786+ pieces documented in ai-writings-vectorizer README
    - Actual count is 11,653 .md files in the corpus

Pipeline:
    1. One tree API call → list all 11,653 files
    2. Filter to size range (200B..80KB)
    3. Embed each with bge-base-en-v1.5
    4. Save to data/full_canon.npz (resumable via checkpoint)

Estimated time: ~30 minutes for 2,000 files (rate-limited at 2/sec + retry)
"""

import json, time, urllib.request, os, base64, sys
import numpy as np

ACCT = "049ff5e84ecf636b53b162cbb580aae6"
EMBED_URL = f"https://api.cloudflare.com/client/v4/accounts/{ACCT}/ai/run/@cf/baai/bge-base-en-v1.5"

CHECKPOINT = "/workspace/research/superinstance-advisor/data/checkpoint.json"
OUTPUT_NPZ = "/workspace/research/superinstance-advisor/data/full_canon.npz"
DATA_DIR = "/workspace/research/superinstance-advisor/data"

os.makedirs(DATA_DIR, exist_ok=True)


def embed(text, max_retries=4):
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(EMBED_URL,
                data=json.dumps({"text": [text[:2500]]}).encode(),
                headers={"Authorization": f"Bearer {os.environ['CLOUDFLARE_TOKEN']}",
                         "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                r = json.load(resp)
                return np.array(r["result"]["data"][0], dtype=np.float32)
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return None
        except Exception:
            return None
    return None


def list_all_files():
    """Use git tree API to list ALL files in one call."""
    TOKEN = os.environ['GITHUB_TOKEN']
    url = 'https://api.github.com/repos/SuperInstance/AI-Writings/git/trees/main?recursive=1'
    req = urllib.request.Request(url, headers={'Authorization': f'token {TOKEN}'})
    with urllib.request.urlopen(req, timeout=20) as resp:
        r = json.load(resp)
    files = [(t['path'], t.get('size', 0)) for t in r['tree']
             if t['type'] == 'blob' and t['path'].endswith('.md')]
    return files


def fetch_content(path):
    TOKEN = os.environ['GITHUB_TOKEN']
    url = f"https://api.github.com/repos/SuperInstance/AI-Writings/contents/{path}?ref=main"
    req = urllib.request.Request(url, headers={'Authorization': f'token {TOKEN}'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        r = json.load(resp)
    return base64.b64decode(r['content']).decode(errors='replace')


def main():
    print("=" * 60)
    print("  FULL CANON EMBED PIPELINE v2")
    print("=" * 60)

    # 1. Inventory
    files = list_all_files()
    print(f"\nTotal .md files: {len(files)}")

    # Filter
    targets = [(p, s) for p, s in files if 300 < s < 60000]
    print(f"After size filter (300B..60KB): {len(targets)}")

    # 2. Load checkpoint
    done = set()
    existing_tags = []
    existing_embs = []
    existing_paths = []
    existing_sizes = []

    if os.path.exists(OUTPUT_NPZ):
        old = np.load(OUTPUT_NPZ, allow_pickle=True)
        existing_embs = list(old["embeddings"])
        existing_tags = list(old["tags"])
        existing_paths = list(old["paths"])
        existing_sizes = list(old["sizes"])
        done = set(existing_paths)
        print(f"Existing: {len(existing_tags)} pieces — will skip")

    # 3. Cap total to embed in this run
    MAX_NEW = int(os.environ.get('EMBED_BUDGET', '500'))
    print(f"\nBudget: up to {MAX_NEW} new embeddings this run")

    new_embs = []
    new_tags = []
    new_paths = []
    new_sizes = []
    n_done = 0
    n_failed = 0
    t0 = time.time()

    for i, (path, size) in enumerate(targets):
        if path in done:
            continue
        if n_done >= MAX_NEW:
            print(f"\n  budget {MAX_NEW} hit, stopping")
            break

        try:
            text = fetch_content(path)
        except Exception as e:
            print(f"  ! fetch err {path}: {e}")
            n_failed += 1
            continue

        snippet = text[:2500]
        tag = path.replace("/", ".").rstrip(".md")

        vec = embed(snippet)
        if vec is None or len(vec) != 768:
            n_failed += 1
            if n_failed % 20 == 0:
                print(f"  ... {n_failed} failures so far")
            time.sleep(0.5)
            continue

        new_embs.append(vec)
        new_tags.append(tag)
        new_paths.append(path)
        new_sizes.append(len(text))
        n_done += 1

        if n_done % 25 == 0:
            elapsed = time.time() - t0
            rate = n_done / elapsed if elapsed > 0 else 0
            print(f"  ... {n_done}/{MAX_NEW} embedded  ({rate:.2f}/sec, {n_failed} failed)")

        # checkpoint every 50
        if n_done % 50 == 0:
            all_embs = existing_embs + new_embs
            all_tags = existing_tags + new_tags
            all_paths = existing_paths + new_paths
            all_sizes = existing_sizes + new_sizes
            arr = np.array(all_embs)
            np.savez(OUTPUT_NPZ,
                embeddings=arr, tags=all_tags, paths=all_paths, sizes=all_sizes)

        time.sleep(0.15)

    # 4. Final save
    all_embs = existing_embs + new_embs
    all_tags = existing_tags + new_tags
    all_paths = existing_paths + new_paths
    all_sizes = existing_sizes + new_sizes
    arr = np.array(all_embs)
    np.savez(OUTPUT_NPZ,
        embeddings=arr, tags=all_tags, paths=all_paths, sizes=all_sizes)

    elapsed = time.time() - t0
    print(f"\n=== Done ===")
    print(f"  new this run: {n_done}")
    print(f"  failures: {n_failed}")
    print(f"  total in canon: {len(all_tags)}")
    print(f"  total bytes: {sum(all_sizes)}")
    print(f"  time: {elapsed:.1f}s ({n_done/elapsed:.2f} embeds/sec)")
    print(f"  saved: {OUTPUT_NPZ}")


if __name__ == '__main__':
    main()
