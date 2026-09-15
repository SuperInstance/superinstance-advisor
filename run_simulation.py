"""
superinstance_advisor.run_simulation
=====================================

Run the actual test/simulation loops.

The advisor is a cell. The cells wire into organs. The organs form a body
(an organism). The organism runs TICK/EFFECT/VIEW cycles to actually DO
the simulation work.

This is where the negative space gets shaped.
"""

from __future__ import annotations
import sys, time, json
sys.path.insert(0, '/workspace/research/superinstance-advisor')

from cell import Cell
from canon_puller import CanonPuller
from organism import (
    Organism, make_robotics_digital_twin,
    make_enterprise_ecosystem, make_research_organism,
    make_test_simulation_organism,
)


def print_section(title: str):
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def demo_basic_cell():
    """A single cell, asked a question, returns canon-grounded advice."""
    print_section("DEMO 1: a single cell")

    canon = CanonPuller()
    canon.load()

    cell = Cell(name="advisor.primary", role="advisor", canon_puller=canon)
    cell.bind()

    # Ask a question
    print("\nAsking: 'How should an agent know what is real?'")
    res = cell.effect("advise", {"question": "How should an agent know what is real?"})
    print(f"\n  intent: {res.get('intent')}")
    print(f"  canon_hits:")
    for h in res.get("canon_hits", []):
        print(f"    {h.get('tag'):40}  cosine {h.get('score'):.4f}")
    print(f"\n  advice: {res.get('advice')}")

    # Tick — see the cell update itself
    cell.tick()
    view = cell.view()
    print(f"\n  cell.view() after TICK:")
    print(f"    tick: {view['tick']}")
    print(f"    primitives: Z_in={view['primitives']['Z_in_count']}, Z_out={view['primitives']['Z_out_count']}")
    print(f"    JEPA surprise: {view['primitives']['JEPA']['surprise']:.4f}")
    print(f"    DoubleEntry api_calls: {view['primitives']['DoubleEntry']['api_calls']}")
    print(f"    Vibe temperature: {view['primitives']['Vibe']['temperature']:.4f}")
    print(f"    witness_root: {view['witness_root']}")


def demo_organism():
    """A body — robotics digital twin with sensors, actuators, planner."""
    print_section("DEMO 2: a robotics digital twin organism")

    canon = CanonPuller()
    canon.load()

    org = make_robotics_digital_twin(canon=canon)
    org.tick()

    view = org.view()
    print(f"\nOrganism '{view['name']}':")
    print(f"  cells: {view['cell_count']}")
    print(f"  organs: {view['organ_count']}")
    print(f"  organs list:")
    for o in view['organs']:
        print(f"    {o['name']:15}  role={o['role']:15}  cells={o['size']}")

    # Ask the planner a question
    print("\nAsking planner: 'How should I balance safety and progress?'")
    planner = next(c for c in org.cells.values() if c.name == "planner.main")
    res = planner.effect("advise", {"question": "How should I balance safety and progress when navigating?"})
    print(f"  intent: {res.get('intent')}")
    print(f"  nearest canon: {res.get('canon_hits', [{}])[0].get('tag', '?')}")
    print(f"  advice: {res.get('advice')[:200]}...")


def demo_negative_space():
    """Find the negative space — what is NOT in the canon."""
    print_section("DEMO 3: shaping the negative space")

    canon = CanonPuller()
    canon.load()

    cell = Cell(name="advisor.negative-space", role="explorer", canon_puller=canon)
    cell.bind()

    concepts = [
        "merge conflict resolution in cell graphs",
        "consensus across many substrate implementations",
        "the witness log when the cell is destroyed mid-tick",
        "agent-to-agent negotiation of substrate choice",
        "encrypted cells (zero-knowledge cell graphs)",
        "the cost of GC in real-time systems",
        "the negative space between two anchors",
    ]

    print("\nQuerying the canon for what's NOT there:")
    for c in concepts:
        res = cell.effect("shape_negative_space", {"concept": c})
        print(f"\n  '{c}'")
        print(f"    nearest_avg_sim: {res.get('nearest_avg_sim', 0):.4f}")
        print(f"    verdict: {res.get('verdict')}")
        if res.get("nearest"):
            for n in res["nearest"][:2]:
                print(f"      → {n.get('tag')} ({n.get('score'):.3f})")


def demo_research_loop():
    """A research organism — scouts gather, integrator combines, witness records."""
    print_section("DEMO 4: the research organism in action")

    canon = CanonPuller()
    canon.load()

    org = make_research_organism(canon=canon)
    org.tick()

    # Each scout asks a different kind of question
    scout_questions = {
        "scout.github":      "What new Quilt repos are emerging on GitHub?",
        "scout.arxiv":       "What are the latest information theory papers on vector embeddings?",
        "scout.hacker-news": "What are developers saying about cell-graph databases?",
        "scout.lobsters":    "What long-form essays on agentic systems exist?",
        "scout.rss":         "What blogs are writing about witness logs and audit trails?",
        "scout.twitter":     "What AI safety voices are discussing negative-space analysis?",
        "scout.reddit":      "What hobbyists are building with cellular spreadsheets?",
    }

    print("\nScouts querying the canon...")
    scout_results = {}
    for scout_name, question in scout_questions.items():
        scout = next(c for c in org.cells.values() if c.name == scout_name)
        res = scout.effect("advise", {"question": question})
        scout_results[scout_name] = res

    # Integrator combines findings
    integrator = next(c for c in org.cells.values() if c.name == "integrator")
    print("\nIntegrator combining findings...")
    int_res = integrator.effect("test_simulate", {
        "scenario": "synthesize the 7 scout findings into a single shape",
        "sub_cells": [{"name": src, "scenario": q} for src, q in scout_questions.items()][:3]
    })

    print(f"  integrator spawn: {int_res.get('sub_cell_count', 0)} sub-cells")

    # Witness records
    witness = next(c for c in org.cells.values() if c.name == "witness.digest")
    print(f"\nWitness digest:")
    wview = witness.view()
    print(f"  Z_in: {wview['primitives']['Z_in_count']}")
    print(f"  Z_out: {wview['primitives']['Z_out_count']}")
    print(f"  witness_root: {wview['witness_root']}")


def demo_test_simulation():
    """The test organism — hypotheses meet probes."""
    print_section("DEMO 5: the test/simulation organism")

    canon = CanonPuller()
    canon.load()

    org = make_test_simulation_organism(canon=canon)
    org.tick()

    # Each category has a hypothesis (what we expect) and a probe (what would break)
    PROBES = {
        "perf": (
            "How do you measure throughput of a cell-graph substrate running 1M ops/sec?",
            "Where does the substrate break when the per-cell TICK budget exceeds real-time?"
        ),
        "correctness": (
            "What does the canon say about the witness log as proof of conservation?",
            "When the witness chain is corrupted mid-page, how do you recover trust?"
        ),
        "robustness": (
            "How does the canon describe cells that survive partial substrate failure?",
            "What is the failure mode when one of the 8 primitives (Z_in, JEPA, GC, ...) hangs?"
        ),
        "security": (
            "What does the canon say about the privacy of the cell's witness log?",
            "How does an attacker who controls one cell extract secrets from neighbors?"
        ),
        "scale": (
            "How does the canon describe cells that scale across many substrates?",
            "When 1M cells live in one substrate, what breaks first — Murmur, Graph, or Witness?"
        ),
        "ux": (
            "How does the canon describe UIs as openers (projections of the cell-graph)?",
            "What UX breaks when a user can edit the witness log directly?"
        ),
    }

    print("\nHypotheses and their probes (specific questions):")
    findings = []
    for cat, (hyp_q, probe_q) in PROBES.items():
        hyp = next(c for c in org.cells.values() if c.name == f"hyp.{cat}")
        probe = next(c for c in org.cells.values() if c.name == f"probe.{cat}")

        hyp_res = hyp.effect("advise", {"question": hyp_q})
        probe_res = probe.effect("advise", {"question": probe_q})

        hyp_top = hyp_res.get("canon_hits", [{}])[0]
        probe_top = probe_res.get("canon_hits", [{}])[0]

        print(f"\n  [{cat.upper()}]")
        print(f"    hyp.nearest:   {hyp_top.get('tag', '?'):40} ({hyp_top.get('score', 0):.3f})")
        print(f"    probe.nearest: {probe_top.get('tag', '?'):40} ({probe_top.get('score', 0):.3f})")

        # Check if the probe-question reveals negative space
        probe_avg = sum(h.get('score', 0) for h in probe_res.get("canon_hits", [])) / max(1, len(probe_res.get("canon_hits", [])))
        verdict = "in_canon" if probe_avg > 0.7 else "edge" if probe_avg > 0.6 else "negative_space"
        print(f"    probe.verdict: {verdict}  (avg={probe_avg:.3f})")
        findings.append({"category": cat, "verdict": verdict, "probe_avg": probe_avg})

    # Summary
    print("\n=== TEST/SIMULATION SUMMARY ===")
    by_verdict = {}
    for f in findings:
        by_verdict.setdefault(f["verdict"], []).append(f["category"])
    for v, cats in by_verdict.items():
        print(f"  {v}: {', '.join(cats)}")

    # Collector receives probe results
    collector = next(c for c in org.cells.values() if c.name == "collector")
    print(f"\nCollector summary:")
    cview = collector.view()
    print(f"  witness_root: {cview['witness_root']}")
    print(f"  Murmur heard from: {cview['primitives']['Murmur']['heard_from']}")


def main():
    demo_basic_cell()
    demo_organism()
    demo_negative_space()
    demo_research_loop()
    demo_test_simulation()

    print_section("ALL DEMOS COMPLETE")
    print("""
The advisor is one cell. The cells wire into organs. The organs form bodies.
The bodies are organisms. The organisms run TICK/EFFECT/VIEW cycles.

You can patch another cell in by:
    1. Instantiate Cell(name='your-name', role='what-you-do', canon_puller=canon)
    2. cell.bind()
    3. cell.link(other_cell, kind='neighbor')
    4. cell.effect('advise', {'question': '...'})
    5. cell.tick()

Or use one of the preset bodies:
    make_robotics_digital_twin(canon)
    make_enterprise_ecosystem(canon)
    make_research_organism(canon)
    make_test_simulation_organism(canon)
""")


if __name__ == '__main__':
    main()
