# cell-heartbeat worker — DEPLOYMENT

The cell-heartbeat Worker runs the cell canon loop on Cloudflare's edge.
This is how it was deployed for `superinstance.dev`.

## Live URLs

- **Production endpoint:** https://cell-heartbeat.superinstance.dev/
- **Workers.dev mirror:** https://cell-heartbeat.casey-digennaro.workers.dev/
- **Trigger heartbeat:** `GET /run` — does one tick
- **View witness log:** `GET /view` — entry count + merkle root
- **Full log:** `GET /log` — all entries
- **Probe live-canon:** `GET /probe` — direct check of live-canon reachability

## Live Status

Currently deployed as of 2026-09-15:
- ✅ Worker: `cell-heartbeat` (handler: `scheduled` + `fetch`)
- ✅ KV: `cell-witness-kv` (id: `f1882454a316494ebd8b9a75fe7856df`)
- ✅ Vectorize: `quilt-canon-v2` (768d, cosine)
- ✅ AI: `@cf/baai/bge-base-en-v1.5`
- ✅ Route: `cell-heartbeat.superinstance.dev/*`
- ✅ DNS: CNAME `cell-heartbeat.superinstance.dev` → `superinstance.dev` (proxied)

Latest witness log: **20 entries**, merkle root `f11737f276616294`.

## Architecture

```
+------------+      +-------------+      +------------------+
| Cloudflare |      | Cloudflare  |      | Cloudflare       |
| Workers    | ---> | Vectorize   |      | Workers AI       |
| (cron +    |      | (768d canon) |      | (bge-base-en-v1.5|
|  fetch)    |      +-------------+      |  embeddings)     |
|            |                            +------------------+
|            |
|            |      +-------------+      +------------------+
|            | ---> | Live Canon  |      | Cloudflare KV    |
|            |      | (Worker)    |      | (cell-witness-kv)|
+------------+      +-------------+      +------------------+
```

Each tick:
1. Picks a question from QUESTIONS (cyclic)
2. Embeds the question via Cloudflare AI (`@cf/baai/bge-base-en-v1.5`)
3. Queries Vectorize (`quilt-canon-v2`) for top-3 nearest
4. Embeds a negative-space concept, probes verdict
5. Calls live-canon.casey-digennaro.workers.dev for state hash
6. Computes entry hash + new merkle root
7. Appends to KV witness log
8. Returns the entry as JSON

## Deploy

### 1. Create the KV namespace

```bash
curl -X POST "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT/storage/kv/namespaces" \
  -H "Authorization: Bearer $CLOUDFLARE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"cell-witness-kv"}'
```

Returns: `{"id": "f1882454a316494ebd8b9a75fe7856df", ...}`

### 2. Upload the worker (multipart)

```python
import json, urllib.request

boundary = "----FormBoundaryABC123"
with open('heartbeat_worker.js') as f:
    worker_js = f.read()

meta = {
    "main_module": "heartbeat_worker.js",
    "compatibility_date": "2024-09-01",
    "bindings": [
        {"type": "kv_namespace", "name": "CELL_WITNESS_KV",
         "namespace_id": "f1882454a316494ebd8b9a75fe7856df"},
        {"type": "ai", "name": "AI"},
        {"type": "vectorize", "name": "VECTORIZE",
         "index_name": "quilt-canon-v2"},
    ],
}

# build multipart body
parts = [
    f"--{boundary}\r\n",
    'Content-Disposition: form-data; name="metadata"\r\n\r\n',
    json.dumps(meta),
    f"\r\n--{boundary}\r\n",
    'Content-Disposition: form-data; name="script"; filename="heartbeat_worker.js"\r\n',
    'Content-Type: application/javascript+module\r\n\r\n',
    worker_js,
    f"\r\n--{boundary}--\r\n",
]
body = "".join(parts).encode("utf-8")

req = urllib.request.Request(
    f"https://api.cloudflare.com/client/v4/accounts/$ACCOUNT/workers/scripts/cell-heartbeat",
    data=body, method='PUT',
    headers={
        'Authorization': 'Bearer $CLOUDFLARE_TOKEN',
        'Content-Type': f'multipart/form-data; boundary={boundary}',
    })
urllib.request.urlopen(req)
```

### 3. Add the worker route

```bash
curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/workers/routes" \
  -H "Authorization: Bearer $CLOUDFLARE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"pattern":"cell-heartbeat.superinstance.dev/*","script":"cell-heartbeat"}'
```

### 4. Add the DNS record

```bash
curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  -H "Authorization: Bearer $CLOUDFLARE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type":"CNAME","name":"cell-heartbeat","content":"superinstance.dev","proxied":true}'
```

### 5. Verify

```bash
IP=$(curl -s "https://dns.google/resolve?name=cell-heartbeat.superinstance.dev&type=A" \
     | python3 -c "import sys,json; print(json.load(sys.stdin)['Answer'][0]['data'])")

curl -s --max-time 30 "https://cell-heartbeat.superinstance.dev/view" \
  -H "Host: cell-heartbeat.superinstance.dev" \
  --resolve "cell-heartbeat.superinstance.dev:443:$IP"
```

## Schedule

The worker can run on a cron schedule. Set via wrangler or by editing the
worker metadata with `triggers: [{"type": "cron", "cron": "*/5 * * * *"}]`.

Current schedule: every 5 minutes.

## Live Canon connection

The worker fetches `https://live-canon.casey-digennaro.workers.dev/...` directly
(workers.dev subdomain works around the GitHub Pages fallback on the apex).

In production you may want to use:
- `https://live-canon.superinstance.dev/...` if Pages fallback is resolved
- Or your own workers.dev URL

## Troubleshooting

- **503 DNS resolution failure:** the route is missing or DNS hasn't propagated
- **200 with `live_canon: null`:** the workers.dev URL is wrong, or live-canon is down
- **Uncaught SyntaxError on deploy:** JSDoc comments with `*/` confuse the parser; use `//` comments
