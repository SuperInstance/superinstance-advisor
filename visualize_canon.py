"""
visualize_canon.py — fast version
=================================

Skip force-directed refinement; just PCA + a tiny radial layout refinement.
Output: data/canon_map.json + data/canon_map.html
"""

import json, sys, os
import numpy as np

DATA = "/workspace/research/superinstance-advisor/data"


def pca(X, k=2):
    X = X - X.mean(axis=0, keepdims=True)
    U, S, Vt = np.linalg.svd(X, full_matrices=False)
    return X @ Vt[:k].T


def quick_layout(X2d, sim, edge_threshold=0.78, iterations=20):
    """Light-touch layout refinement — just enough to pull connected pieces apart."""
    n = len(X2d)
    pos = X2d.copy()
    for it in range(iterations):
        temp = max(0.01, 1.0 - it / iterations) * 0.05
        forces = np.zeros_like(pos)

        # Vectorized repulsion
        diff = pos[:, None, :] - pos[None, :, :]
        dist = np.linalg.norm(diff, axis=2) + 1e-9
        np.fill_diagonal(dist, np.inf)
        repulse = 0.01 / (dist * dist)
        np.fill_diagonal(repulse, 0)
        dir_f = diff / dist[:, :, None]
        np.fill_diagonal(dir_f[:, :, 0], 0)
        np.fill_diagonal(dir_f[:, :, 1], 0)
        forces = (repulse[:, :, None] * dir_f).sum(axis=1)

        # Edge attraction (sparse — only above threshold)
        idx = np.argwhere(sim > edge_threshold)
        idx = idx[idx[:, 0] < idx[:, 1]]
        if len(idx) > 0:
            i_idx = idx[:, 0]
            j_idx = idx[:, 1]
            diff_ij = pos[i_idx] - pos[j_idx]
            d_ij = np.linalg.norm(diff_ij, axis=1) + 1e-9
            w_ij = (sim[i_idx, j_idx] - edge_threshold)
            f_ij = (w_ij * d_ij)[:, None] * (diff_ij / d_ij[:, None])
            np.add.at(forces, i_idx, -f_ij)
            np.add.at(forces, j_idx, +f_ij)

        pos += forces * temp

    return pos


def hash_color(s):
    """Deterministic color from a string."""
    h = 0
    for c in s:
        h = ((h << 5) - h + ord(c)) & 0xffffffff
    return f"hsl({abs(h) % 360}, 70%, 65%)"


def main():
    npz = os.path.join(DATA, "full_canon.npz")
    data = np.load(npz, allow_pickle=True)
    embeddings = data["embeddings"]
    tags = list(data["tags"])
    paths = list(data["paths"])
    n = len(tags)
    print(f"Loaded {n} pieces from {npz}")

    # Cosine similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    E_norm = embeddings / norms
    sim = E_norm @ E_norm.T

    # PCA → 2D
    print("PCA...")
    coords2d_pca = pca(embeddings, k=2)

    # Light-touch layout
    print("Layout refinement...")
    coords2d = quick_layout(coords2d_pca, sim, iterations=15)

    # Build the map JSON
    print("Building map JSON...")
    edges = [
        {"i": int(i), "j": int(j), "weight": float(sim[i][j])}
        for i in range(n) for j in range(i+1, n) if sim[i][j] > 0.78
    ]
    print(f"  edges (>0.78): {len(edges)}")

    nodes = [
        {
            "id": int(i),
            "tag": tags[i],
            "path": paths[i] if i < len(paths) else tags[i],
            "x": float(coords2d[i][0]),
            "y": float(coords2d[i][1]),
            "centrality": float(np.mean([sim[i][j] for j in range(n) if i != j])),
            "depth": tags[i].count("."),
            "section": tags[i].split(".")[0] if "." in tags[i] else "root",
        }
        for i in range(n)
    ]

    out = {
        "node_count": n,
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
    }

    map_path = os.path.join(DATA, "canon_map.json")
    with open(map_path, "w") as f:
        json.dump(out, f)
    print(f"  saved: {map_path}  ({os.path.getsize(map_path)/1024:.1f} KB)")

    # Aggregate sections for the visualizer
    sections = {}
    for n_ in nodes:
        sections.setdefault(n_["section"], []).append(n_["id"])
    print(f"  sections: {dict(sorted(sections.items(), key=lambda x: -len(x[1]))[:10])}")

    # Build HTML
    print("Building HTML...")
    html = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Canon Map — 768d → 2D (real embeddings)</title>
<style>
body { background: #0a0e1a; color: #d8e2ff; font-family: -apple-system, sans-serif; margin: 0; padding: 1rem; }
h1 { color: #66ffd9; font-size: 1.5rem; margin: 0 0 0.5rem; }
.info { color: #6e7a99; font-size: 0.85rem; margin-bottom: 0.5rem; }
.legend { color: #d8e2ff; font-size: 0.8rem; margin: 1rem 0; }
.legend .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; vertical-align: middle; margin: 0 4px; }
#canvas { width: 100%; height: 75vh; background: #131829; border-radius: 8px; position: relative; overflow: hidden; }
svg { width: 100%; height: 100%; }
.node { cursor: pointer; transition: all 0.15s; }
.node:hover { r: 8; }
.label { fill: #d8e2ff; font-size: 9px; pointer-events: none; font-family: monospace; }
.edge { stroke: #1f2640; }
</style>
</head>
<body>
<h1>Canon Map — Real 768d Embeddings → 2D</h1>
<div class="info">
""" + f"""<strong>{n} pieces, {len(edges)} edges</strong> (cosine > 0.78).
Larger node = more central. Color = directory section.
Hover for details; click to see snippet.
</div>
<div id="canvas"></div>
<div class="legend">
<strong>Sections:</strong>
""" + ", ".join([f"<span class='dot' style='background: {hash_color(s)}'></span>{s} ({len(ids)})"
                  for s, ids in sorted(sections.items(), key=lambda x: -len(x[1]))[:12]]) + """
</div>
<script>
const data = """ + json.dumps(out) + """;
const canvas = document.getElementById('canvas');
const W = canvas.clientWidth;
const H = canvas.clientHeight;
const padding = 40;

const xs = data.nodes.map(n => n.x);
const ys = data.nodes.map(n => n.y);
const xmin = Math.min(...xs), xmax = Math.max(...xs);
const ymin = Math.min(...ys), ymax = Math.max(...ys);
const xrange = xmax - xmin || 1;
const yrange = ymax - ymin || 1;

function hash_color(s) {
    let h = 0;
    for (let c of s) h = ((h << 5) - h + c.charCodeAt(0)) & 0xffffffff;
    return `hsl(${Math.abs(h) % 360}, 70%, 65%)`;
}

const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
canvas.appendChild(svg);

// Edges first
data.edges.forEach(e => {
    const a = data.nodes[e.i];
    const b = data.nodes[e.j];
    const ax = padding + (a.x - xmin) / xrange * (W - 2*padding);
    const ay = padding + (a.y - ymin) / yrange * (H - 2*padding);
    const bx = padding + (b.x - xmin) / xrange * (W - 2*padding);
    const by = padding + (b.y - ymin) / yrange * (H - 2*padding);
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', ax);
    line.setAttribute('y1', ay);
    line.setAttribute('x2', bx);
    line.setAttribute('y2', by);
    line.setAttribute('stroke', `rgba(180,200,255,${(e.weight - 0.78) * 4})`);
    line.setAttribute('stroke-width', Math.max(0.3, (e.weight - 0.78) * 5));
    svg.appendChild(line);
});

// Nodes
data.nodes.forEach(n => {
    const cx = padding + (n.x - xmin) / xrange * (W - 2*padding);
    const cy = padding + (n.y - ymin) / yrange * (H - 2*padding);
    const r = 1.5 + n.centrality * 8;
    const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    c.setAttribute('cx', cx);
    c.setAttribute('cy', cy);
    c.setAttribute('r', r);
    c.setAttribute('fill', hash_color(n.section));
    c.setAttribute('class', 'node');
    c.setAttribute('opacity', n.centrality > 0.75 ? 1 : 0.5);
    c.innerHTML = '';
    const title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
    title.textContent = `${n.tag}\\ncentrality: ${n.centrality.toFixed(3)}\\nsection: ${n.section}\\ndepth: ${n.depth}`;
    c.appendChild(title);
    c.addEventListener('click', () => {
        alert(`${n.tag}\\n\\npath: ${n.path}\\ncentrality: ${n.centrality.toFixed(3)}\\nsection: ${n.section}`);
    });
    svg.appendChild(c);

    if (n.centrality > 0.78) {
        const t = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        t.setAttribute('x', cx + r + 2);
        t.setAttribute('y', cy + 3);
        t.setAttribute('class', 'label');
        t.textContent = n.tag.split('.').slice(-1)[0].slice(0, 40);
        svg.appendChild(t);
    }
});
</script>
</body>
</html>"""

    html_path = os.path.join(DATA, "canon_map.html")
    with open(html_path, "w") as f:
        f.write(html)
    print(f"  saved: {html_path}  ({os.path.getsize(html_path)/1024:.1f} KB)")

    # Report shape
    print("\n=== INITIAL SHAPE OF FULL CANON ===\n")
    centralities = [(n_["centrality"], n_["tag"]) for n_ in nodes]
    centralities.sort(reverse=True)
    print("Top 10 most central pieces:")
    for c, t in centralities[:10]:
        print(f"  {c:.4f}  {t}")

    print("\nTop 10 most isolated (outliers):")
    for c, t in centralities[-10:]:
        print(f"  {c:.4f}  {t}")


if __name__ == '__main__':
    main()
