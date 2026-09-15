"""
superinstance_advisor.organism
===============================

A body made of cells. The organism wires cells together into organs,
which together form a working system (a body, an enterprise, a fleet).

In the canon:
- A cell is the irreducible unit.
- An organ is a cluster of cells with a shared role.
- An organism is a graph of organs that holds a coherent purpose.

This module provides Organism — a cell-graph builder for bodies,
ecosystems, robotics digital twins, etc.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from cell import Cell


@dataclass
class Organ:
    """A cluster of cells with a shared role."""
    name: str
    role: str  # "perception" | "action" | "memory" | "communication" | "regulation"
    cells: list[str] = field(default_factory=list)  # cell addresses

    def add_cell(self, cell: Cell) -> None:
        if cell.address not in self.cells:
            self.cells.append(cell.address)


class Organism:
    """A body — cells wired into organs.

    An organism holds:
        - cells: the running cells (Cell objects)
        - organs: named clusters of cells
        - a shared canon puller (so all cells see the same canon)

    The organism is the patch-panel: where individual cells get organized
    into something with a coherent shape.
    """

    def __init__(self, name: str, canon_puller=None):
        self.name = name
        self.canon = canon_puller
        self.cells: dict[str, Cell] = {}  # address → Cell
        self.organs: dict[str, Organ] = {}
        self.tick_count: int = 0

        # The organism itself is bound on creation
        self._witness("ORGANISM_BIND", {"name": name})

    def _witness(self, op: str, payload: dict):
        """The organism's own witness log."""
        if not hasattr(self, "_org_witness"):
            self._org_witness: list[dict] = []
        self._org_witness.append({"op": op, "ts": time.time(), "payload": payload})

    def birth_cell(self, name: str, role: str = "general") -> Cell:
        """BIND a new cell, patched into the organism."""
        cell = Cell(name=name, role=role, canon_puller=self.canon)
        cell.bind()
        self.cells[cell.address] = cell
        self._witness("CELL_BIRTH", {"name": name, "role": role, "address": cell.address})
        return cell

    def form_organ(self, organ_name: str, role: str, cell_names: list[str]) -> Organ:
        """Form an organ — wire a set of cells together by role."""
        organ = Organ(name=organ_name, role=role)
        for cname in cell_names:
            if cname in [c.name for c in self.cells.values()]:
                # Find the cell
                cell = next(c for c in self.cells.values() if c.name == cname)
                organ.add_cell(cell)
        self.organs[organ_name] = organ
        self._witness("ORGAN_FORM", {"name": organ_name, "role": role, "cells": len(organ.cells)})
        return organ

    def link(self, from_name: str, to_name: str, kind: str = "neighbor") -> None:
        """Link two cells by name."""
        from_cell = next((c for c in self.cells.values() if c.name == from_name), None)
        to_cell = next((c for c in self.cells.values() if c.name == to_name), None)
        if from_cell and to_cell:
            from_cell.link(to_cell.name, kind)

    def tick(self, dt: int = 1) -> None:
        """Tick the whole organism — every cell advances."""
        self.tick_count += dt
        for cell in self.cells.values():
            cell.tick(dt)
        self._witness("TICK", {"dt": dt, "tick": self.tick_count, "cells_alive": len(self.cells)})

    def view(self) -> dict:
        """VIEW — see the whole organism."""
        return {
            "name": self.name,
            "tick": self.tick_count,
            "cell_count": len(self.cells),
            "organ_count": len(self.organs),
            "cells": [
                {"name": c.name, "role": c.role, "address": c.address, "tick": c.tick_count}
                for c in self.cells.values()
            ],
            "organs": [
                {"name": o.name, "role": o.role, "size": len(o.cells)}
                for o in self.organs.values()
            ],
            "witness_count": len(self._org_witness) if hasattr(self, "_org_witness") else 0,
        }

    def broadcast(self, op: str, payload: dict) -> list:
        """EFFECT — broadcast an opcode to every cell."""
        results = []
        for cell in self.cells.values():
            try:
                r = cell.effect(op, payload)
                results.append({"name": cell.name, "ok": True, "result": r})
            except Exception as e:
                results.append({"name": cell.name, "ok": False, "err": str(e)})
        return results


# ============================================================================
# PRESET BODIES — common organism shapes for common purposes
# ============================================================================

def make_robotics_digital_twin(canon=None) -> Organism:
    """A digital twin of a robot — sensor cells, motor cells, decision cells."""
    org = Organism(name="robotics-digital-twin", canon_puller=canon)

    # Perception organ: sensors
    perception_cells = []
    for sensor in ["camera", "lidar", "imu", "gps"]:
        c = org.birth_cell(f"sensor.{sensor}", role="perception")
        perception_cells.append(c.name)
    org.form_organ("perception", role="perception", cell_names=perception_cells)

    # Action organ: motors / actuators
    action_cells = []
    for motor in ["wheel.fl", "wheel.fr", "wheel.rl", "wheel.rr", "arm.gripper"]:
        c = org.birth_cell(f"actuator.{motor}", role="action")
        action_cells.append(c.name)
    org.form_organ("action", role="action", cell_names=action_cells)

    # Decision organ: planner
    planner = org.birth_cell("planner.main", role="decision")
    org.form_organ("decision", role="decision", cell_names=[planner.name])

    # Memory organ: world model
    memory = org.birth_cell("memory.world", role="memory")
    org.form_organ("memory", role="memory", cell_names=[memory.name])

    # Wire: sensors → planner, planner → motors, planner ↔ memory
    for sname in perception_cells:
        org.link(sname, "planner.main", kind="perceives-to")
    for aname in action_cells:
        org.link("planner.main", aname, kind="commands")
    org.link("planner.main", "memory.world", kind="reads-writes")

    return org


def make_enterprise_ecosystem(canon=None) -> Organism:
    """An enterprise — teams as organs, individuals as cells."""
    org = Organism(name="enterprise-ecosystem", canon_puller=canon)

    # Organs: leadership, product, engineering, sales, ops
    teams = {
        "leadership": ["ceo", "cto", "cfo"],
        "product":   ["pm.lead", "pm.fe", "pm.be"],
        "engineering": ["eng.lead", "eng.fe1", "eng.fe2", "eng.be1", "eng.be2", "eng.devops"],
        "sales":     ["sales.lead", "sales.ae1", "sales.ae2"],
        "ops":       ["ops.finance", "ops.hr", "ops.legal"],
    }

    for team_name, members in teams.items():
        for m in members:
            org.birth_cell(f"{team_name}.{m}", role="team-member")
        org.form_organ(team_name, role=team_name, cell_names=[f"{team_name}.{m}" for m in members])

    # Wire: leadership → all teams, engineering ↔ product, sales ↔ product
    for team in ["product", "engineering", "sales", "ops"]:
        org.link("leadership.ceo", f"{team}.{teams[team][0]}", kind="oversees")
    org.link("product.pm.lead", "engineering.eng.lead", kind="specs-to")
    org.link("engineering.eng.lead", "product.pm.lead", kind="delivers-to")
    org.link("sales.sales.lead", "product.pm.lead", kind="feeds-back")

    return org


def make_research_organism(canon=None) -> Organism:
    """A research organism — scout cells, integrator cell, witness cell."""
    org = Organism(name="research-organism", canon_puller=canon)

    # Scout cells — each scans a different source
    for src in ["github", "arxiv", "hacker-news", "lobsters", "rss", "twitter", "reddit"]:
        org.birth_cell(f"scout.{src}", role="scout")

    # Integrator cell — combines scout findings
    org.birth_cell("integrator", role="integrator")

    # Witness cell — records findings, creates the digest
    org.birth_cell("witness.digest", role="witness")

    # Connect all scouts to integrator to witness
    for src in ["github", "arxiv", "hacker-news", "lobsters", "rss", "twitter", "reddit"]:
        org.link(f"scout.{src}", "integrator", kind="feeds")
    org.link("integrator", "witness.digest", kind="records")

    return org


def make_test_simulation_organism(canon=None) -> Organism:
    """A test/simulation organism — the negative-space finder."""
    org = Organism(name="test-sim-organism", canon_puller=canon)

    # Hypothesis cells — each proposes a boundary
    for h in ["perf", "correctness", "robustness", "security", "scale", "ux"]:
        org.birth_cell(f"hyp.{h}", role="hypothesis")

    # Probe cells — try to break
    for h in ["perf", "correctness", "robustness", "security", "scale", "ux"]:
        org.birth_cell(f"probe.{h}", role="probe")

    # Result collector
    org.birth_cell("collector", role="collector")

    # Connect: hyp <-> probe, probe -> collector
    for h in ["perf", "correctness", "robustness", "security", "scale", "ux"]:
        org.link(f"hyp.{h}", f"probe.{h}", kind="proposes")
        org.link(f"probe.{h}", "collector", kind="reports")

    return org


import time  # for the Organism witness
