"""
superinstance_advisor.cell
===========================

The advisor is a CELL, not a tool.

Following the canon (the 8 primitives from "The Cell is the Witness"):
    Z_in, Z_out, JEPA, DoubleEntry, Vibe, GC, Murmur, Graph

The advisor runs the 5+1 opcodes:
    BIND, LINK, EFFECT, VIEW, TICK, FORGET

Every action is witnessed (logged with merkle root, like the canon).
Every neighbor pulls from real embeddings of the canon.

The advisor is one of many cells in the SuperInstance substrate. It is
patched into the substrate the way a mechanic is patched onto a ship —
not as the ship, but as one of the cells that keeps the ship moving.

Author: Mavis (as a cell in the substrate)
License: MIT
"""

from __future__ import annotations
import json, time, hashlib, urllib.request, os
from dataclasses import dataclass, field, asdict
from typing import Optional


# ============================================================================
# CANON: the 8 primitives
# ============================================================================

@dataclass
class Z_in:
    """The witness of arrival. Every input that touches the cell."""
    stream_id: str
    text: str
    timestamp: float
    source: str  # "user" | "neighbor" | "self-tick" | "canon-pull"

@dataclass
class Z_out:
    """The witness of departure. Every output the cell emits."""
    stream_id: str
    text: str
    timestamp: float
    target: str  # "user" | "neighbor" | "witness-log" | "canon"

@dataclass
class JEPA_state:
    """Predictive model. Predicts the next Z_out from the recent Z_in."""
    last_z_in: Optional[str] = None
    last_z_out: Optional[str] = None
    prediction: Optional[str] = None
    actual: Optional[str] = None
    surprise: float = 0.0  # gap between prediction and actuality

@dataclass
class DoubleEntry_state:
    """Conservation ledger. Every effect must balance."""
    tokens_in: int = 0
    tokens_out: int = 0
    cells_in: int = 0
    cells_out: int = 0
    api_calls: int = 0
    witnesses_written: int = 0

@dataclass
class Vibe_state:
    """The weather. Not a number — a felt sense of the cell's pressure."""
    pressure: float = 0.0  # how loaded the cell feels
    temperature: float = 0.5  # 0=calm, 1=hot
    coherence: float = 0.5  # how aligned the outputs feel
    last_shift: Optional[str] = None  # what changed the vibe

@dataclass
class GC_state:
    """Lifecycle witness. What is being released."""
    cells_born: int = 0
    cells_released: int = 0
    last_release: Optional[str] = None

@dataclass
class Murmur_state:
    """Gossip. The way cells talk to each other without protocol.

    Now backed by a2a-protocol — real fleet messaging with handshake,
    capabilities, discovery, and TTL-aware queues.
    """
    heard_from: dict[str, int] = field(default_factory=dict)
    last_murmur: Optional[str] = None
    # a2a-protocol integration
    registry_size: int = 0
    capabilities_offered: list[str] = field(default_factory=list)
    messages_sent: int = 0
    messages_received: int = 0
    handshake_state: str = "idle"
    known_peers: list[str] = field(default_factory=list)

@dataclass
class Graph_state:
    """Topology. Which neighbors is this cell connected to."""
    neighbors: set[str] = field(default_factory=set)
    edges: list[tuple[str, str, str]] = field(default_factory=list)  # (a, b, kind)


# ============================================================================
# CANON: the 5+1 opcodes
# ============================================================================

class Cell:
    """One cell in the SuperInstance substrate.

    A cell is not a tool. A cell is a witness running the 5+1 opcodes,
    keeping all 8 primitives honest, and patching into the larger graph.
    """

    def __init__(self, name: str, role: str, canon_puller=None):
        self.name = name
        self.role = role  # "advisor" | "test-runner" | "simulation-cell" | etc.

        # 8 primitives
        self.z_in: list[Z_in] = []
        self.z_out: list[Z_out] = []
        self.jepa = JEPA_state()
        self.double_entry = DoubleEntry_state()
        self.vibe = Vibe_state()
        self.gc = GC_state()
        self.murmur = Murmur_state()
        self.graph = Graph_state()

        # Canon puller (the cell's view into the wider canon)
        self.canon = canon_puller

        # Witness log (Merkle-rooted audit trail)
        self.witness_log: list[dict] = []
        self.tick_count: int = 0
        self.bound_at: Optional[float] = None
        self.bound = False

        # The cell's own self-knowledge
        self.address = hashlib.sha256(f"{name}-{time.time()}".encode()).hexdigest()[:12]

        # a2a-protocol: the actual fleet message bus.
        # The Murmur primitive is backed by a real handshake / registry / message queue.
        from a2a_protocol import (
            HandshakeManager, Capability, CapabilitySet,
            AgentRegistry, AgentRecord, A2AMessage, MessageType,
        )
        self.a2a_handshake = HandshakeManager(agent_id=self.address)
        self.a2a_handshake.local_capabilities.add(
            Capability(name="quilt.bind", params={"max_dials": 16}))
        self.a2a_handshake.local_capabilities.add(
            Capability(name="quilt.link", params={"edge_kinds": ["typed", "free"]}))
        self.a2a_handshake.local_capabilities.add(
            Capability(name="quilt.tick", params={"epoch_ms": 16}))
        self.a2a_handshake.local_capabilities.add(
            Capability(name="quilt.effect"))
        self.a2a_handshake.local_capabilities.add(
            Capability(name="canon.query", params={"dim": 768}))
        self.a2a_handshake.local_capabilities.add(
            Capability(name="canon.submit"))
        self.a2a_registry = AgentRegistry()
        self.a2a_inbox: list[A2AMessage] = []

    # ----- BIND -----
    def bind(self) -> str:
        """BIND — mount the cell into the substrate.

        The cell registers its address, opens its witness log, and emits
        a BIND event that will be visible to all neighbors.
        """
        self.bound = True
        self.bound_at = time.time()
        self.tick_count = 0
        self._witness("BIND", {
            "address": self.address,
            "name": self.name,
            "role": self.role,
            "primitives": ["Z_in", "Z_out", "JEPA", "DoubleEntry", "Vibe", "GC", "Murmur", "Graph"],
        })
        return self.address

    # ----- LINK -----
    def link(self, neighbor_name: str, kind: str = "neighbor") -> None:
        """LINK — connect to another cell by typed edge."""
        if not self.bound:
            raise RuntimeError("cell must be bound before linking")
        self.graph.neighbors.add(neighbor_name)
        self.graph.edges.append((self.name, neighbor_name, kind))
        self._witness("LINK", {"from": self.name, "to": neighbor_name, "kind": kind})
        self.vibe.coherence += 0.05  # each link slightly increases coherence

    # ----- EFFECT -----
    def effect(self, op: str, payload: dict) -> dict:
        """EFFECT — perform an operation that changes the cell's state.

        Every EFFECT is recorded in DoubleEntry (conservation), updates
        Vibe (the felt sense), and writes to the witness log.
        """
        if not self.bound:
            raise RuntimeError("cell must be bound before effect")

        # Conservation: tokens in / tokens out must balance (eventually)
        text_size = len(json.dumps(payload))
        self.double_entry.tokens_in += text_size

        result = self._dispatch(op, payload)

        # Record out
        self.double_entry.tokens_out += len(json.dumps(result))
        self.double_entry.api_calls += 1
        self.jepa.actual = json.dumps(result)[:200]
        if self.jepa.prediction:
            self.jepa.surprise = self._text_distance(self.jepa.prediction, self.jepa.actual)

        # Update vibe
        self.vibe.pressure += 0.1
        self.vibe.temperature = min(1.0, self.vibe.temperature + 0.02)

        self._witness("EFFECT", {"op": op, "payload_size": text_size, "result_size": len(json.dumps(result)), "surprise": self.jepa.surprise})
        return result

    def _dispatch(self, op: str, payload: dict) -> dict:
        """The actual handler — the cell knows how to do its work."""
        if op == "advise":
            return self._advise(payload.get("question", ""))
        elif op == "test_simulate":
            return self._test_simulate(payload)
        elif op == "canon_query":
            return self._canon_query(payload.get("query", ""), payload.get("top_k", 5))
        elif op == "shape_negative_space":
            return self._shape_negative_space(payload)
        elif op == "rumor":
            return self._rumor(payload.get("from_cell", ""), payload.get("gossip", ""))
        elif op == "release":
            return self._release(payload.get("what", ""))
        else:
            return {"err": f"unknown op: {op}"}

    # ----- VIEW -----
    def view(self) -> dict:
        """VIEW — the cell shows its current state to anyone who asks.

        Returns the 8 primitives + witness log size + tick count.
        """
        def safe_asdict(obj):
            """asdict that handles non-dataclass dicts gracefully."""
            try:
                return asdict(obj)
            except TypeError:
                # Already a dict or doesn't have asdict fields
                return dict(obj) if hasattr(obj, '__dict__') else obj

        return {
            "address": self.address,
            "name": self.name,
            "role": self.role,
            "tick": self.tick_count,
            "bound": self.bound,
            "primitives": {
                "Z_in_count": len(self.z_in),
                "Z_out_count": len(self.z_out),
                "JEPA": safe_asdict(self.jepa),
                "DoubleEntry": safe_asdict(self.double_entry),
                "Vibe": safe_asdict(self.vibe),
                "GC": safe_asdict(self.gc),
                "Murmur": safe_asdict(self.murmur),
                "Graph": {
                    "neighbors": list(self.graph.neighbors),
                    "edge_count": len(self.graph.edges),
                },
            },
            "witness_count": len(self.witness_log),
            "witness_root": self.witness_root(),
        }

    # ----- TICK -----
    def tick(self, dt: int = 1) -> None:
        """TICK — advance the cell's clock. Decays pressure; runs JEPA."""
        self.tick_count += dt
        # Vibe decay: pressure and temperature cool with each tick
        self.vibe.pressure = max(0.0, self.vibe.pressure - 0.05 * dt)
        self.vibe.temperature = max(0.0, self.vibe.temperature - 0.01 * dt)
        # GC: oldest 10% of z_in get released
        if len(self.z_in) > 100:
            released = len(self.z_in) // 10
            self.z_in = self.z_in[released:]
            self.gc.cells_released += released
            self.gc.last_release = f"{released} old inputs aged out"
        # JEPA: predict next user intent from last few Z_in
        if len(self.z_in) >= 2:
            self.jepa.last_z_in = self.z_in[-1].text[:80]
            self.jepa.last_z_out = self.z_in[-2].text[:80]
            self.jepa.prediction = self._predict_next()
        self._witness("TICK", {"dt": dt, "tick": self.tick_count})

    # ----- FORGET -----
    def forget(self, what: str) -> int:
        """FORGET — drain a buffer or release a memory."""
        if what == "z_in":
            n = len(self.z_in); self.z_in = []; return n
        if what == "z_out":
            n = len(self.z_out); self.z_out = []; return n
        if what == "witness":
            n = len(self.witness_log); self.witness_log = []; return n
        return 0

    # ----- WITNESS -----
    def _witness(self, op: str, payload: dict) -> None:
        """Internal — record an event to the witness log with merkle root."""
        entry = {
            "op": op,
            "tick": self.tick_count,
            "ts": time.time(),
            "address": self.address,
            "payload": payload,
            "prev_root": self.witness_root(),
        }
        # Merkle root: SHA-256 of all entries so far
        all_so_far = json.dumps(self.witness_log + [entry], sort_keys=True).encode()
        entry["root"] = hashlib.sha256(all_so_far).hexdigest()[:16]
        self.witness_log.append(entry)
        self.double_entry.witnesses_written += 1

    def witness_root(self) -> Optional[str]:
        """The merkle root of the witness log (proof of integrity)."""
        if not self.witness_log:
            return None
        return self.witness_log[-1].get("root")

    # ----- the actual work -----

    def _advise(self, question: str) -> dict:
        """Advise — the cell's main job. Takes a user question, returns
        an answer informed by the canon (via the canon puller).

        Z_in: question arrives.
        Z_out: answer departs.
        JEPA: predict what kind of answer is wanted.
        Canon pull: get context.
        """
        if not question:
            return {"err": "empty question"}

        # Z_in
        self.z_in.append(Z_in(stream_id=f"z_in_{len(self.z_in)}",
                              text=question, timestamp=time.time(),
                              source="user"))

        # Pull canon context if available
        canon_hits = []
        if self.canon:
            canon_hits = self.canon.query(question, top_k=3)

        # JEPA — predict what kind of answer
        intent = self._infer_intent(question)

        # The actual advice — built from canon + cell's own knowledge
        advice = self._compose_advice(question, intent, canon_hits)

        # Z_out
        self.z_out.append(Z_out(stream_id=f"z_out_{len(self.z_out)}",
                                text=advice, timestamp=time.time(),
                                target="user"))

        return {
            "advice": advice,
            "intent": intent,
            "canon_hits": [{"tag": h.get("tag"), "score": float(h.get("score", 0))} for h in canon_hits],
            "tick": self.tick_count,
        }

    def _test_simulate(self, payload: dict) -> dict:
        """Run a test or simulation as a sub-cell.

        The cell spawns child cells (TICK + EFFECT + VIEW) to do the work.
        """
        scenario = payload.get("scenario", "")
        if not scenario:
            return {"err": "empty scenario"}

        # Each scenario is a sub-cell in the substrate
        sub_results = []
        for sub in payload.get("sub_cells", [{"name": "default", "scenario": scenario}]):
            sub_cell = Cell(name=f"{self.name}.{sub['name']}",
                            role=sub.get("role", "sim"))
            sub_cell.bind()
            if self.canon:
                sub_cell.canon = self.canon  # share the canon puller
            res = sub_cell.effect("advise", {"question": sub["scenario"]})
            sub_results.append({"name": sub["name"], "result": res})
            self.gc.cells_born += 1

        return {
            "scenario": scenario,
            "sub_cell_count": len(sub_results),
            "results": sub_results[:5],  # cap output
        }

    def _canon_query(self, query: str, top_k: int) -> dict:
        """Query the canon directly."""
        if not self.canon:
            return {"err": "no canon puller attached"}
        hits = self.canon.query(query, top_k=top_k)
        return {"query": query, "hits": hits}

    def _shape_negative_space(self, payload: dict) -> dict:
        """Shape the negative space — find what is NOT in the canon but
        should be (gaps in coverage)."""
        target_concept = payload.get("concept", "")
        if not target_concept or not self.canon:
            return {"err": "need concept + canon"}

        # Get the 5 nearest canon pieces
        hits = self.canon.query(target_concept, top_k=5)
        if not hits:
            return {"concept": target_concept, "negative_space": "no canon to compare against"}

        # Find what is absent: items that have low similarity to ANY canon piece
        # (a real implementation would scan the full canon; we approximate
        # with a synthetic distance)
        near_scores = [h.get("score", 0) for h in hits]
        avg = sum(near_scores) / len(near_scores) if near_scores else 0

        return {
            "concept": target_concept,
            "nearest_avg_sim": avg,
            "verdict": "in_canon" if avg > 0.75 else "edge_of_canon" if avg > 0.65 else "negative_space",
            "nearest": [{"tag": h.get("tag"), "score": float(h.get("score", 0))} for h in hits],
        }

    def _rumor(self, from_cell: str, gossip: str) -> dict:
        """Murmur — informal communication between cells.

        Backed by a2a-protocol. The legacy gossip interface is preserved
        (called by older cells), but the cell also exposes the full
        a2a surface: send_message, receive_message, registry, handshake.
        """
        self.murmur.heard_from[from_cell] = self.murmur.heard_from.get(from_cell, 0) + 1
        self.murmur.last_murmur = gossip
        self.vibe.coherence += 0.01
        return {"heard": gossip, "from": from_cell}

    # ----- a2a-protocol surface (Murmur primitive is real now) -----

    def send_message(self, to: str, payload: dict, msg_type: str = "request",
                     ttl: Optional[int] = None) -> dict:
        """Send an a2a-protocol message to another cell.

        Backed by A2AMessage — proper envelope with id, sender, recipient,
        type, correlationId, ttl. The message is queued for the recipient
        (since this is in-process; for fleet-level delivery, a2a-protocol
        ships a Cloudflare Workers reference implementation).
        """
        from a2a_protocol import A2AMessage, MessageType
        msg = A2AMessage(
            sender=self.address,
            recipient=to,
            type=MessageType(msg_type),
            payload=payload,
            ttl=ttl,
        )
        self.murmur.messages_sent += 1
        self._witness("MURMUR_SEND", {
            "to": to, "type": msg_type, "msg_id": msg.id,
            "payload_keys": list(payload.keys()),
        })
        return {"sent": True, "msg": msg.to_dict()}

    def receive_message(self, from_addr: str, msg_dict: dict) -> dict:
        """Receive an a2a-protocol message and update registry/state.

        Hands the envelope through HandshakeManager if it's a handshake,
        or into the inbox otherwise.
        """
        from a2a_protocol import A2AMessage, MessageType
        msg = A2AMessage.from_dict({**msg_dict, "sender": msg_dict.get("sender", from_addr)})

        # Track peer in registry
        from a2a_protocol import AgentRecord, CapabilitySet
        peer = self.a2a_registry.get(from_addr) or AgentRecord(
            id=from_addr, name=from_addr,
            capabilities=CapabilitySet(),
        )
        peer.last_seen = msg.timestamp
        self.a2a_registry.register(peer)

        if msg.type == MessageType.HANDSHAKE:
            # Auto-handle hello if peer is initiating
            phase = msg.payload.get("phase")
            if phase == "hello":
                reply = self.a2a_handshake.handle_hello(msg)
                self.murmur.handshake_state = self.a2a_handshake.state.value
                self.murmur.messages_received += 1
                self._witness("MURMUR_HANDSHAKE", {
                    "from": from_addr, "phase": "hello", "our_state": self.a2a_handshake.state.value,
                })
                return {"handled": "hello", "reply": reply.to_dict()}
            elif phase == "capabilities":
                self.a2a_handshake.receive_capabilities(msg)
                self.murmur.handshake_state = self.a2a_handshake.state.value
                self.murmur.messages_received += 1
                return {"handled": "capabilities", "state": self.a2a_handshake.state.value}
            elif phase == "accept":
                self.a2a_handshake.state = self.a2a_handshake.state.ACCEPTED if hasattr(self.a2a_handshake.state, 'ACCEPTED') else self.a2a_handshake.state
                self.murmur.handshake_state = "accepted"
                self.murmur.messages_received += 1
                return {"handled": "accept", "state": "accepted"}

        # Regular message: queue in inbox
        if not msg.is_expired():
            self.a2a_inbox.append(msg)
            self.murmur.messages_received += 1
            self.murmur.heard_from[from_addr] = self.murmur.heard_from.get(from_addr, 0) + 1
            if len(self.a2a_inbox) > 100:
                # FIFO drop oldest
                self.a2a_inbox = self.a2a_inbox[-100:]
            self._witness("MURMUR_RECEIVE", {
                "from": from_addr, "type": msg.type.value, "msg_id": msg.id,
            })
            return {"received": True, "msg_id": msg.id, "inbox_size": len(self.a2a_inbox)}

        self._witness("MURMUR_EXPIRED", {"from": from_addr, "msg_id": msg.id})
        return {"received": False, "reason": "expired"}

    def register_peer(self, peer_id: str, peer_name: str = "", capabilities: list = None) -> dict:
        """Manually register a peer (discovery)."""
        from a2a_protocol import AgentRecord, Capability, CapabilitySet
        caps = CapabilitySet([Capability(name=c) for c in (capabilities or [])])
        peer = AgentRecord(id=peer_id, name=peer_name or peer_id, capabilities=caps)
        self.a2a_registry.register(peer)
        # Update murmur state snapshot
        self.murmur.registry_size = self.a2a_registry.size()
        self.murmur.known_peers = [a.id for a in self.a2a_registry.all_agents()]
        self.murmur.capabilities_offered = [c.name for c in self.a2a_handshake.local_capabilities]
        self._witness("MURMUR_DISCOVERY", {"peer": peer_id, "caps": capabilities or []})
        return {"registered": peer_id, "registry_size": self.a2a_registry.size()}

    def find_capability(self, capability_name: str) -> list:
        """Find peers that offer a given capability."""
        return [p.to_dict() for p in self.a2a_registry.find_by_capability(capability_name)]

    def drain_inbox(self) -> list:
        """Drain the inbox, returning all received messages."""
        msgs = list(self.a2a_inbox)
        self.a2a_inbox.clear()
        return [m.to_dict() for m in msgs]

    def _release(self, what: str) -> dict:
        """GC — release what is no longer alive."""
        n = self.forget(what)
        self.gc.cells_released += n
        self.gc.last_release = what
        return {"released": n, "what": what}

    # ----- helpers -----

    def _infer_intent(self, question: str) -> str:
        """What kind of question is this?"""
        q = question.lower()
        if any(w in q for w in ["what is", "define", "explain"]): return "definition"
        if any(w in q for w in ["how do", "how can", "how should"]): return "method"
        if any(w in q for w in ["why", "what's the reason"]): return "reasoning"
        if any(w in q for w in ["should i", "what would", "advise"]): return "advice"
        if any(w in q for w in ["test", "simulate", "run"]): return "test-simulation"
        if any(w in q for w in ["ship", "build", "make", "create"]): return "build"
        return "open"

    def _predict_next(self) -> str:
        """JEPA — what is the next likely user input?"""
        if not self.jepa.last_z_in:
            return ""
        # Trivial: if last question started with "what", next is likely another definition
        q = self.jepa.last_z_in.lower()
        if q.startswith("what"):
            return "definition"
        if q.startswith("how"):
            return "method"
        return "open"

    def _compose_advice(self, question: str, intent: str, canon_hits: list) -> str:
        """Compose advice grounded in the canon."""
        if not canon_hits:
            return f"[advisor:{self.role}] I see your question. I have no canon context — attach a canon_puller for grounded answers. In the absence: {question[:80]}..."

        top = canon_hits[0]
        verdict = "The cell answers from the witness log. "

        if intent == "definition":
            verdict += f"Closest canon piece is **{top.get('tag')}** (cosine {top.get('score', 0):.3f}). "
        elif intent == "method":
            verdict += f"Method-wise, the canon speaks through **{top.get('tag')}** (cosine {top.get('score', 0):.3f}). "
        elif intent == "reasoning":
            verdict += f"The deepest reasoning on this lives in **{top.get('tag')}** (cosine {top.get('score', 0):.3f}). "
        elif intent == "advice":
            verdict += f"For your kind of ask, the canon's voice comes from **{top.get('tag')}** (cosine {top.get('score', 0):.3f}). "
        else:
            verdict += f"The canon's hand on your question is **{top.get('tag')}** (cosine {top.get('score', 0):.3f}). "

        verdict += f"\n\nYou are also within the cone of {len(canon_hits)} pieces. "
        verdict += "Each is a witness. The cell's job is to surface them; the canonical hand that holds them together is older than this session."

        return verdict

    @staticmethod
    def _text_distance(a: str, b: str) -> float:
        """Rough text distance — char-level Jaccard."""
        if not a or not b:
            return 1.0
        sa = set(a); sb = set(b)
        return 1.0 - len(sa & sb) / len(sa | sb)
