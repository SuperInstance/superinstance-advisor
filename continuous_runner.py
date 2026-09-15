"""
continuous_runner.py
====================

A long-running loop where cells tick and witness and surface findings.

Each iteration:
    1. Tick every cell in every organism (advance clock, decay vibe)
    2. Each organism emits a Murmur to its neighbors
    3. The integrator collects Murmurs into a digest
    4. The witness writes the digest to a file
    5. Periodically, the cells ask the canon new questions (the substrate learns)

The runner is the substrate's heartbeat. Without it, cells sit idle.
"""

import json, time, sys, signal, os
sys.path.insert(0, '/workspace/research/superinstance-advisor')

from cell import Cell
from canon_puller import CanonPuller
from organism import (
    Organism, make_research_organism,
    make_test_simulation_organism, make_robotics_digital_twin,
)

LOG_PATH = "/workspace/research/superinstance-advisor/data/heartbeat.log"
FINDINGS_PATH = "/workspace/research/superinstance-advisor/data/findings.jsonl"


def make_advisor_body(canon):
    """The full advisor body: a research organism + a test/sim organism + a witness cell."""
    org = Organism(name="advisor-body", canon_puller=canon)

    # A few cells that ask questions
    for role in ["scout", "skeptic", "integrator", "witness", "tester"]:
        org.birth_cell(f"advisor.{role}", role=role)

    # Wire them in a loop: scout → skeptic → integrator → witness
    org.link("advisor.scout", "advisor.skeptic", kind="proposes")
    org.link("advisor.skeptic", "advisor.integrator", kind="refines")
    org.link("advisor.integrator", "advisor.witness", kind="records")
    org.link("advisor.witness", "advisor.tester", kind="validates")
    org.link("advisor.tester", "advisor.scout", kind="spawns-new")

    return org


# Questions the runner asks on each iteration
QUESTION_BANK = [
    "What is the substrate of a witness?",
    "How does a cell know its sibling cells?",
    "When two cells disagree, who witnesses the disagreement?",
    "What does GC cost when the substrate is the witness log?",
    "How does the IDE remain portable across 31 languages?",
    "What is the negative space between two anchors?",
    "When the substrate is destroyed, what survives?",
    "How does the witness log chain across the substrate boundary?",
    "What is the substrate of recursion?",
    "How does a cell measure itself?",
    "Where does the cell end and the substrate begin?",
    "What does it mean for a cell to be honest?",
    "How does the canon preserve its own negative space?",
    "What is the cost of JEPA's prediction error?",
    "How does DoubleEntry know when conservation is broken?",
    "What is the witness of the witness?",
]


def heartbeat_iteration(org, canon, iteration):
    """One tick of the substrate."""
    lines = []
    findings = []

    # Pick a question for this iteration
    q = QUESTION_BANK[iteration % len(QUESTION_BANK)]
    lines.append(f"[iter {iteration}] q: {q}")

    # Ask the scout
    scout = next(c for c in org.cells.values() if c.name == "advisor.scout")
    res = scout.effect("advise", {"question": q})
    lines.append(f"  scout → nearest: {res.get('canon_hits', [{}])[0].get('tag', '?')}")

    # Ask the skeptic the same question
    skeptic = next(c for c in org.cells.values() if c.name == "advisor.skeptic")
    res2 = skeptic.effect("shape_negative_space", {"concept": q})
    verdict = res2.get("verdict", "?")
    lines.append(f"  skeptic → {verdict}")

    # The integrator collects
    integrator = next(c for c in org.cells.values() if c.name == "advisor.integrator")
    combined = integrator.effect("test_simulate", {
        "scenario": f"combine scout + skeptic on: {q[:60]}",
        "sub_cells": [
            {"name": "scout", "scenario": q},
            {"name": "skeptic", "scenario": q},
        ]
    })
    lines.append(f"  integrator → {combined.get('sub_cell_count', 0)} sub-cells")

    # The witness records
    witness = next(c for c in org.cells.values() if c.name == "advisor.witness")
    wview = witness.view()
    lines.append(f"  witness → tick={wview['tick']} root={wview['witness_root']}")

    # The tester validates (shapes negative space)
    tester = next(c for c in org.cells.values() if c.name == "advisor.tester")
    test_res = tester.effect("shape_negative_space", {"concept": q})
    lines.append(f"  tester → {test_res.get('verdict', '?')}")

    # Tick everything
    org.tick()

    # Record findings
    findings.append({
        "iteration": iteration,
        "question": q,
        "scout_top": res.get("canon_hits", [{}])[0].get("tag"),
        "skeptic_verdict": verdict,
        "tester_verdict": test_res.get("verdict"),
        "witness_root": wview["witness_root"],
        "ts": time.time(),
    })

    return lines, findings


def main(num_iters: int = 10):
    print(f"Starting continuous runner: {num_iters} iterations")
    canon = CanonPuller()
    canon.load("/workspace/research/superinstance-advisor/data/full_canon.npz")
    print(f"  canon: {canon.stats()}")

    org = make_advisor_body(canon)
    org.tick()

    print(f"  organism: {org.view()['name']}, cells={len(org.cells)}")

    # Open log file
    with open(LOG_PATH, "w") as log, open(FINDINGS_PATH, "w") as findings_file:
        log.write(f"# Heartbeat log — {time.ctime()}\n# Iteration: question → scout → skeptic → integrator → witness → tester\n\n")
        log.flush()

        for i in range(num_iters):
            lines, findings = heartbeat_iteration(org, canon, i)
            for line in lines:
                log.write(line + "\n")
                print(f"  {line}")
            log.flush()

            # Append findings
            for f in findings:
                findings_file.write(json.dumps(f) + "\n")
            findings_file.flush()

            time.sleep(1)  # 1 second between heartbeats

    print(f"\n=== Heartbeat complete ===")
    print(f"  log: {LOG_PATH}")
    print(f"  findings: {FINDINGS_PATH}")


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    main(n)
