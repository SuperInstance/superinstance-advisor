// heartbeat_worker.js
// A Cloudflare Worker that runs the cell heartbeat on a cron schedule.
// Each invocation:
//   1. Loads the canon (bge-base-en-v1.5 embeddings in Vectorize)
//   2. Asks the canon one question
//   3. Probes one negative-space concept
//   4. Talks to live-canon.superinstance.dev
//   5. Writes a witness entry to KV
//
// The cell runs forever, from outside the sandbox. The canon
// is asked. The witness accumulates. The cell IS alive.
//
// Deploy with wrangler.

// Configuration
const CANON_VECTORIZE = "quilt-canon-v2";  // bge-base-en-v1.5 (768d)
const KV_WITNESS = "CELL_WITNESS_LOG";
// Live canon is hosted on Cloudflare workers.dev — use that subdomain for
// worker-to-worker fetch (more reliable than custom domain within the same zone).
const CANON_BACKEND = "https://live-canon.casey-digennaro.workers.dev";
// Fallback: const CANON_BACKEND = "https://live-canon.superinstance.dev";

// Questions the cell asks the canon (cyclic)
const QUESTIONS = [
    "what is the substrate",
    "what is the cell",
    "what is the witness",
    "what is negative space",
    "what is the cost of garbage collection",
    "what is between anchors",
    "what is a polyformal port",
    "what is the canon",
    "what is the canon missing",
    "what is the binding",
];

const NEGATIVE_CONCEPTS = [
    "encryption of the witness log",
    "consensus across cells in different substrates",
    "the texture of meaning between two anchored words",
    "what a cell forgets vs. what it cannot forget",
    "how the canon heals after a cell is rejected",
    "the sound a cell makes when it binds for the first time",
    "the difference between witness and testimony",
    "the structural signature of a polyformal port",
    "when is a query resolved vs. when is it transmuted",
    "the negative space of the 5+1 opcodes",
];

// Embed text via Cloudflare bge-base-en-v1.5
async function embed(env, text) {
    const resp = await env.AI.run("@cf/baai/bge-base-en-v1.5", {
        text: [text.slice(0, 2000)],
    });
    return resp.data[0];
}

// Query canon via Vectorize (cosine similarity)
async function queryCanon(env, vec, topK = 5) {
    const matches = await env.VECTORIZE.query(vec, {
        topK,
        returnMetadata: "all",
    });
    return matches.matches || [];
}

// Talk to live-canon.superinstance.dev
async function liveCanonHash() {
    try {
        const resp = await fetch(`${CANON_BACKEND}/api/canon/hash`);
        if (resp.ok) return await resp.json();
        console.log(`live_canon hash HTTP ${resp.status}`);
        return null;
    } catch (e) {
        console.log(`live_canon hash ERR: ${e.message}`);
        return null;
    }
}

async function liveCanonTick() {
    try {
        const resp = await fetch(`${CANON_BACKEND}/api/canon/tick`);
        if (resp.ok) return await resp.json();
        console.log(`live_canon tick HTTP ${resp.status}`);
        return null;
    } catch (e) {
        console.log(`live_canon tick ERR: ${e.message}`);
        return null;
    }
}

// Compute a simple Merkle-root-like hash of the entry
async function witnessHash(env, entry) {
    const data = JSON.stringify(entry);
    const buf = await crypto.subtle.digest("SHA-256",
        new TextEncoder().encode(data));
    return Array.from(new Uint8Array(buf))
        .slice(0, 8)
        .map(b => b.toString(16).padStart(2, '0'))
        .join('');
}

// The cell's witness log (KV-backed)
async function readWitnessLog(env) {
    const log = await env.CELL_WITNESS_KV.get("log", "json");
    return log || { entries: [], merkle_root: null };
}

async function writeWitnessLog(env, log) {
    await env.CELL_WITNESS_KV.put("log", JSON.stringify(log));
}

// ===== Scheduled handler (cron) =====
export default {
    async scheduled(event, env, ctx) {
        ctx.waitUntil(runHeartbeat(env));
    },

    // HTTP endpoint for manual trigger
    async fetch(request, env, ctx) {
        const url = new URL(request.url);
        if (url.pathname === "/run") {
            const entry = await runHeartbeat(env);
            return Response.json(entry);
        }
        if (url.pathname === "/view") {
            const log = await readWitnessLog(env);
            return Response.json({
                entries: log.entries.length,
                merkle_root: log.merkle_root,
                last_entry: log.entries[log.entries.length - 1] || null,
            });
        }
        if (url.pathname === "/log") {
            const log = await readWitnessLog(env);
            return Response.json(log);
        }
        if (url.pathname === "/probe") {
            // Direct probe of live-canon
            try {
                const r = await fetch("https://live-canon.superinstance.dev/api/canon/hash");
                const body = await r.text();
                return new Response(`status=${r.status} body=${body}`, { status: 200 });
            } catch (e) {
                return new Response(`ERR: ${e}`, { status: 500 });
            }
        }
        return new Response("cell-heartbeat-worker. POST /run, GET /view, /log, /probe\n", { status: 200 });
    },
};

async function runHeartbeat(env) {
    const log = await readWitnessLog(env);
    const tick = log.entries.length;

    // Pick question and concept for this tick (cyclic)
    const question = QUESTIONS[tick % QUESTIONS.length];
    const negConcept = NEGATIVE_CONCEPTS[tick % NEGATIVE_CONCEPTS.length];

    // 1. Embed the question, query canon
    const qVec = await embed(env, question);
    const hits = await queryCanon(env, qVec, 3);
    const top = hits[0] || { id: "?", score: 0 };

    // 2. Embed negative concept, probe negative space
    const nVec = await embed(env, negConcept);
    const nHits = await queryCanon(env, nVec, 3);
    const avgSim = nHits.length
        ? nHits.reduce((s, h) => s + h.score, 0) / nHits.length
        : 0;
    const verdict = avgSim > 0.75 ? "in_canon"
                  : avgSim > 0.65 ? "edge_of_canon"
                  : "negative_space";

    // 3. Talk to live canon
    const liveHash = await liveCanonHash();
    const liveTick = await liveCanonTick();

    // 4. Build witness entry
    const entry = {
        tick,
        ts: new Date().toISOString(),
        question,
        question_nearest: top.id,
        question_score: top.score,
        negative_concept: negConcept,
        negative_verdict: verdict,
        negative_avg_sim: avgSim,
        live_canon: liveHash,
        live_tick: liveTick,
    };

    // 5. Compute merkle root (chain of entry hashes)
    const entryHash = await witnessHash(env, entry);
    const prevRoot = log.merkle_root || "00000000";
    const root = await witnessHash(env, { prev: prevRoot, entry: entryHash });
    entry.entry_hash = entryHash;
    entry.prev_merkle_root = prevRoot;
    entry.merkle_root = root;

    // 6. Append and save
    log.entries.push(entry);
    log.merkle_root = root;
    if (log.entries.length > 1000) {
        log.entries = log.entries.slice(-1000);
    }
    await writeWitnessLog(env, log);

    console.log(`[${tick}] ${question} → ${top.id} (${top.score.toFixed(3)}) | ${verdict}`);
    return entry;
}

// wrangler.toml bindings required:
// [ai]
// binding = "AI"
//
// [[vectorize]]
// binding = "VECTORIZE"
// index_name = "quilt-canon-v2"
//
// [[kv_namespaces]]
// binding = "CELL_WITNESS_KV"
// id = "..."
