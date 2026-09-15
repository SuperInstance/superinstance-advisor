"""
quilt_cli.py
============

Daily-driver CLI for canon work using multi-LLM Quilt cell.

Usage:
    python3 quilt_cli.py ask "what is the substrate?"
    python3 quilt_cli.py shape "post-quantum witness log"
    python3 quilt_cli.py write "the cost of consensus" "the consensus algorithm"
    python3 quilt_cli.py ensemble "what is a Quilt cell?"
    python3 quilt_cli.py embed canon/<file>.md
    python3 quilt_cli.py canon-stats
    python3 quilt_cli.py live-state

Subcommands route to the best LLM for the job:
    ask       → ensemble (deepseek-chat + seed-mini + deepseek-reasoner)
    shape     → seed-mini (cheap, with reasoning)
    write     → deepseek-reasoner (deep thinking)
    ensemble  → all models in parallel
    embed     → Cloudflare bge-base-en-v1.5
    canon-stats → local canon info
    live-state → live-canon.superinstance.dev state
"""

import sys, os, json, time, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from canon_puller import CanonPuller
from canon_aware_quilt import CanonAwareCell
from multi_llm_quilt import call_llm
import urllib.request


CANON_PATH = os.path.join(os.path.dirname(__file__), "data", "full_canon.npz")


def cmd_ask(args):
    cell = CanonAwareCell("cli-asker")
    cell.canon.load(CANON_PATH)
    cell.bind()
    question = " ".join(args.question)
    print(f"Q: {question}")
    r = cell.ask(question, k=args.topk)
    print(f"\nTop canon pieces:")
    for h in r["canon_hits"]:
        print(f"  {h['tag']:50} score={h['score']:.3f}")
    print(f"\nEnsemble:")
    for m, resp in r["ensemble"].items():
        if resp.get("ok"):
            content = resp["content"][:args.limit].replace("\n", "\n    ")
            print(f"\n  [{m}] (${resp['cost_usd']:.4f}, {resp['elapsed']:.1f}s)")
            print(f"    {content}")
        else:
            print(f"  [{m}] ERR: {resp.get('err', '?')}")
    print(f"\nTotal cost: ${cell.total_cost_usd:.4f}")


def cmd_shape(args):
    cell = CanonAwareCell("cli-shaper")
    cell.canon.load(CANON_PATH)
    cell.bind()
    concept = " ".join(args.concept)
    print(f"Concept: {concept}")
    r = cell.shape_negative_space(concept)
    print(f"  canon avg sim: {r['canon_avg_sim']:.3f}")
    for m, resp in r["results"].items():
        if resp.get("ok"):
            first_line = resp["content"].split("\n")[0]
            print(f"  [{m}]: {first_line}")
    print(f"\nTotal cost: ${cell.total_cost_usd:.4f}")


def cmd_write(args):
    cell = CanonAwareCell("cli-writer")
    cell.canon.load(CANON_PATH)
    cell.bind()
    title = args.title
    outline = args.outline
    print(f"Title: {title}")
    print(f"Outline: {outline[:200]}{'...' if len(outline) > 200 else ''}")
    result = cell.write_paper(title=title, outline=outline, words=args.words, model="deepseek_reasoner")
    if result.get("ok"):
        print(f"\nCost: ${result.get('cost_usd', 0):.4f} ({result.get('elapsed', 0):.1f}s)")
        print("\n=== Paper ===")
        print(result["content"])
        if args.save:
            slug = title.lower().replace(" ", "-").replace(",", "")
            path = os.path.join(os.path.dirname(__file__), "canon", f"{slug}.md")
            with open(path, "w") as f:
                f.write(f"# {title}\n\n{result['content']}\n")
            print(f"\nSaved: {path}")
    else:
        print(f"ERR: {result.get('err')}")


def cmd_ensemble(args):
    cell = CanonAwareCell("cli-ensemble")
    cell.canon.load(CANON_PATH)
    cell.bind()
    question = " ".join(args.question)
    print(f"Q: {question}")
    r = cell.ask(question, k=3, models=["deepseek_chat", "deepseek_reasoner", "seed_mini", "seed_code"])
    print(f"\nEnsemble answers:")
    for m, resp in r["ensemble"].items():
        if resp.get("ok"):
            content = resp["content"][:args.limit].replace("\n", "\n    ")
            print(f"\n  [{m}] (${resp['cost_usd']:.4f}, {resp['elapsed']:.1f}s)")
            print(f"    {content}")
        else:
            print(f"  [{m}] ERR: {resp.get('err', '?')[:80]}")
    print(f"\nTotal cost: ${cell.total_cost_usd:.4f}")


def cmd_embed(args):
    """Embed a markdown file into local canon + Vectorize."""
    import numpy as np
    cell = CanonAwareCell("cli-embed")
    cell.canon.load(CANON_PATH)
    cell.bind()

    for path in args.files:
        if not os.path.exists(path):
            print(f"  skipping {path}: not found")
            continue
        with open(path) as f:
            text = f.read()
        # Tag from filename
        tag = os.path.basename(path).replace(".md", "")
        # First-line title
        first_line = text.split("\n")[0].lstrip("#").strip()
        print(f"  Embedding: {tag} ({len(text)} chars)")

        # Embed via Cloudflare
        TOKEN = os.environ.get("CLOUDFLARE_TOKEN")
        body = json.dumps({"text": [text[:2000]]}).encode()
        req = urllib.request.Request(
            'https://api.cloudflare.com/client/v4/accounts/049ff5e84ecf636b53b162cbb580aae6/ai/run/@cf/baai/bge-base-en-v1.5',
            data=body, method='POST',
            headers={'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                vec = np.array(json.loads(r.read())['result']['data'][0], dtype=np.float32)
        except Exception as e:
            print(f"    ERR: {e}")
            continue

        # Append to local canon
        existing_tags = list(cell.canon.tags)
        existing_embs = cell.canon.embeddings
        if tag in existing_tags:
            print(f"    (already in canon, skipping)")
            continue
        all_tags = existing_tags + [tag]
        all_embs = np.concatenate([existing_embs, vec[None]], axis=0)
        np.savez_compressed(CANON_PATH, tags=np.array(all_tags), embeddings=all_embs)
        print(f"    saved to {CANON_PATH} ({len(all_tags)} pieces)")


def cmd_canon_stats(args):
    canon = CanonPuller()
    canon.load(CANON_PATH)
    print(f"Local canon: {len(canon.tags)} pieces × {canon.embeddings.shape[1]}d")
    # Cluster counts
    from collections import defaultdict
    clusters = defaultdict(int)
    for t in canon.tags:
        clusters[t.split('.')[0]] += 1
    print(f"\nTop clusters:")
    for c, n in sorted(clusters.items(), key=lambda x: -x[1])[:15]:
        print(f"  {c:30} {n:4}")


def cmd_live_state(args):
    print("=== live-canon state ===")
    try:
        req = urllib.request.Request(
            "https://live-canon.casey-digennaro.workers.dev/api/canon/hash",
            headers={"User-Agent": "quilt-cli/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read())
            print(f"  state_hash: {d.get('state_hash')}")
            print(f"  paper_count: {d.get('paper_count')}")
            print(f"  canon_target: {d.get('canon_target')}")
            print(f"  test_cell_hash: {d.get('test_cell_hash')}")
    except Exception as e:
        print(f"  ERR: {e}")

    # Also the cell-heartbeat worker
    print("\n=== cell-heartbeat worker ===")
    try:
        req = urllib.request.Request("https://cell-heartbeat.superinstance.dev/view",
            headers={"Host": "cell-heartbeat.superinstance.dev",
                     "User-Agent": "quilt-cli/1.0"})
        # Resolve DNS via DoH since sandbox DNS may fail
        doh_req = urllib.request.Request(
            "https://dns.google/resolve?name=cell-heartbeat.superinstance.dev&type=A")
        with urllib.request.urlopen(doh_req, timeout=5) as dr:
            data = json.loads(dr.read())
            ip = data.get("Answer", [{}])[0].get("data")
        import socket
        # Use the resolved IP
        socket.create_connection((ip, 443), timeout=5).close()
        req = urllib.request.Request(f"https://{ip}/view",
            headers={"Host": "cell-heartbeat.superinstance.dev"})
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read())
            print(f"  witness entries: {d.get('entries')}")
            print(f"  merkle root: {d.get('merkle_root')}")
    except Exception as e:
        print(f"  ERR: {e}")


def main():
    parser = argparse.ArgumentParser(description="Quilt multi-LLM CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # ask
    p = sub.add_parser("ask", help="Ask the canon + ensemble of LLMs")
    p.add_argument("question", nargs="+")
    p.add_argument("--topk", type=int, default=3)
    p.add_argument("--limit", type=int, default=300, help="Max chars per answer")
    p.set_defaults(func=cmd_ask)

    # shape
    p = sub.add_parser("shape", help="Probe negative-space concept")
    p.add_argument("concept", nargs="+")
    p.set_defaults(func=cmd_shape)

    # write
    p = sub.add_parser("write", help="Write a new canon paper")
    p.add_argument("title")
    p.add_argument("outline")
    p.add_argument("--words", type=int, default=350)
    p.add_argument("--save", action="store_true", help="Save to canon/")
    p.set_defaults(func=cmd_write)

    # ensemble
    p = sub.add_parser("ensemble", help="Fan out to all LLMs")
    p.add_argument("question", nargs="+")
    p.add_argument("--limit", type=int, default=300)
    p.set_defaults(func=cmd_ensemble)

    # embed
    p = sub.add_parser("embed", help="Embed a markdown file into canon")
    p.add_argument("files", nargs="+")
    p.set_defaults(func=cmd_embed)

    # canon-stats
    p = sub.add_parser("canon-stats", help="Show local canon stats")
    p.set_defaults(func=cmd_canon_stats)

    # live-state
    p = sub.add_parser("live-state", help="Show live-canon + cell-heartbeat state")
    p.set_defaults(func=cmd_live_state)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
