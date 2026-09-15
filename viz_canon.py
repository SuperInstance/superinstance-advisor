"""
viz_canon.py
============

Force-directed visualization of the canon embedding.
"""

from __future__ import annotations
import sys, os, json
sys.path.insert(0, '/workspace/research/superinstance-advisor')

import numpy as np
from collections import defaultdict


def cluster_by_tag(tags):
    """Cluster tags by their first path segment."""
    clusters = defaultdict(int)
    for t in tags:
        cluster = t.split('.')[0]
        clusters[cluster] += 1
    return clusters


def main():
    print("=" * 60)
    print("  CANON LANDSCAPE — pieces × 768d -> 2D")
    print("=" * 60)

    npz_path = "/workspace/research/superinstance-advisor/data/full_canon.npz"
    if not os.path.exists(npz_path):
        print(f"  ERR: {npz_path} not found")
        return

    data = np.load(npz_path, allow_pickle=True)
    embs = data["embeddings"]
    tags = list(data["tags"])
    print(f"\n  loaded {len(tags)} pieces x {embs.shape[1]}d")

    # 1. PCA to 50d
    print("  PCA to 50d...")
    mean = embs.mean(axis=0)
    centered = embs - mean
    U, S, Vt = np.linalg.svd(centered, full_matrices=False)
    pca50 = U[:, :50] * S[:50]

    # 2. Cluster-aware subsample for performance
    print("  Building subsample...")
    indices = list(range(len(tags)))
    n_sub = min(400, len(tags))
    if len(tags) > n_sub:
        clusters_for_sub = defaultdict(list)
        for i, t in enumerate(tags):
            clusters_for_sub[t.split('.')[0]].append(i)
        per_cluster = max(5, n_sub // len(clusters_for_sub))
        for c, items in clusters_for_sub.items():
            indices.extend(items[:per_cluster])
        indices = list(set(indices))[:n_sub]
    indices = np.array(indices)
    print(f"  subsampled to {len(indices)}")

    # 3. Force-directed layout
    print("  Force-directed layout...")
    np.random.seed(42)
    pos = np.random.randn(len(tags), 2).astype(np.float32) * 0.5

    pca_sub = pca50[indices]
    # Compute distance matrix
    distances = np.zeros((len(indices), len(indices)), dtype=np.float32)
    for i in range(len(indices)):
        distances[i] = np.linalg.norm(pca_sub - pca_sub[i], axis=1)

    velocities = np.zeros((len(tags), 2), dtype=np.float32)
    for it in range(40):
        forces = np.zeros((len(tags), 2), dtype=np.float32)
        sample_size = min(60, len(indices))
        sampled = np.random.choice(len(indices), size=sample_size, replace=False)
        for j in sampled:
            diff = pos[indices] - pos[indices[j]]
            dist = np.linalg.norm(diff, axis=1) + 0.01
            force_mag = 0.05 / (dist * dist)
            forces[indices] += (diff.T * force_mag).T
        # Spring
        threshold = distances.mean() * 0.5
        for j in sampled:
            close_mask = distances[j] < threshold
            if close_mask.sum() == 0:
                continue
            diff = pos[indices[close_mask]] - pos[indices[j]]
            d = distances[j, close_mask] + 0.01
            target = 1.0 + (d - 1.0) * 0.3
            f_mag = 0.01 * (target - d)
            forces[indices[close_mask]] += (diff.T * f_mag / d).T
            forces[indices[j]] -= ((diff.T * f_mag / d).T).sum(axis=0)
        velocities = velocities * 0.85 + forces * 0.3
        pos += velocities

    # 4. Build HTML
    clusters = cluster_by_tag(tags)
    cluster_list = sorted(clusters.keys(), key=lambda c: -clusters[c])
    cluster_color = {c: f"hsl({i * 360 / max(len(cluster_list),1):.0f}, 70%, 50%)"
                     for i, c in enumerate(cluster_list)}

    points = []
    for i in indices:
        cluster = tags[i].split('.')[0]
        points.append({
            "x": float(pos[i, 0]),
            "y": float(pos[i, 1]),
            "tag": str(tags[i]),
            "cluster": cluster,
            "color": cluster_color.get(cluster, "#888"),
        })

    html_parts = ['<!DOCTYPE html><html><head><title>Canon Landscape</title>',
        '<style>',
        'body { font-family: -apple-system, sans-serif; margin: 0; background: #0a0a14; color: #eee; }',
        '#header { padding: 12px 24px; background: #1a1a2e; border-bottom: 1px solid #333; }',
        'h1 { margin: 0; font-size: 18px; }',
        '#legend { padding: 8px 24px; background: #1a1a2e; border-bottom: 1px solid #333; font-size: 12px; }',
        '#legend span.s { display: inline-block; margin-right: 12px; }',
        '#legend .swatch { width: 12px; height: 12px; display: inline-block; margin-right: 4px; vertical-align: middle; border-radius: 2px; }',
        '#canvas { position: relative; display: block; width: 100%; height: calc(100vh - 100px); }',
        '.dot { position: absolute; width: 7px; height: 7px; border-radius: 50%; cursor: pointer; transform: translate(-50%, -50%); }',
        '.dot:hover { transform: translate(-50%, -50%) scale(1.8); z-index: 10; outline: 1px solid #fff; }',
        '#info { position: fixed; bottom: 16px; right: 16px; background: #1a1a2e; padding: 8px 16px; border-radius: 8px; font-size: 12px; border: 1px solid #333; }',
        '</style></head><body>',
        f'<div id="header"><h1>Canon Landscape - {len(tags)} pieces x 768d - force-directed</h1></div>',
        '<div id="legend">']

    sorted_clusters = sorted(clusters.items(), key=lambda x: -x[1])
    for c, count in sorted_clusters[:20]:
        if c in cluster_color:
            html_parts.append(f'<span class="s"><span class="swatch" style="background:{cluster_color[c]}"></span>{c} ({count})</span>')
    html_parts.append('</div>')
    html_parts.append('<div id="canvas"></div>')
    html_parts.append(f'<div id="info">{len(points)} points - 50-PC - force-directed</div>')

    html_parts.append('<script>')
    html_parts.append(f'const points = {json.dumps(points)};')
    html_parts.append('const canvas = document.getElementById("canvas");')
    html_parts.append('let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;')
    html_parts.append('for (const p of points) {')
    html_parts.append('  minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x);')
    html_parts.append('  minY = Math.min(minY, p.y); maxY = Math.max(maxY, p.y);')
    html_parts.append('}')
    html_parts.append('const w = maxX - minX + 0.1;')
    html_parts.append('const h = maxY - minY + 0.1;')
    html_parts.append('for (const p of points) {')
    html_parts.append('  const dot = document.createElement("div");')
    html_parts.append('  dot.className = "dot";')
    html_parts.append('  dot.style.left = ((p.x - minX) / w * 100) + "%";')
    html_parts.append('  dot.style.top = ((p.y - minY) / h * 100) + "%";')
    html_parts.append('  dot.style.background = p.color;')
    html_parts.append('  dot.title = p.tag;')
    html_parts.append('  dot.onclick = () => alert(p.tag + "\\ncluster: " + p.cluster);')
    html_parts.append('  canvas.appendChild(dot);')
    html_parts.append('}')
    html_parts.append('</script></body></html>')

    out_path = "/workspace/research/superinstance-advisor/data/canon_landscape.html"
    with open(out_path, "w") as f:
        f.write("\n".join(html_parts))
    print(f"\n  wrote: {out_path}")
    print(f"  size: {os.path.getsize(out_path) / 1024:.1f} KB")
    print(f"\n  Top clusters:")
    for c in cluster_list[:10]:
        print(f"    {c:30} {clusters[c]:4}")


if __name__ == "__main__":
    main()
