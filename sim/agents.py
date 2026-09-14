"""
Agent definitions for the threat/asset simulation.

Two base agent types:
  - AssetAgent: friendly/monitored entity (patrol unit, convoy, sensor platform)
  - ThreatAgent: adversarial or hazard entity (intruder, disruption event)

Agents are simple state machines driven by the SimPy environment's clock.
Movement is along the Environment graph via shortest paths, with optional
random patrol / random threat-emergence behaviors provided out of the box.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, Optional

import simpy

from .environment import Environment


@dataclass
class AgentLogEntry:
    time: float
    agent_id: str
    event: str
    node: Optional[str] = None
    detail: str = ""


class BaseAgent:
    """Common bookkeeping for asset and threat agents."""

    def __init__(self, env: simpy.Environment, world: Environment, agent_id: str,
                 start_node: str, log: list[AgentLogEntry]):
        self.env = env
        self.world = world
        self.agent_id = agent_id
        self.node = start_node
        self.log = log
        self.alive = True

    def _record(self, event: str, detail: str = "") -> None:
        self.log.append(AgentLogEntry(self.env.now, self.agent_id, event, self.node, detail))

    def move_to(self, target_node: str):
        """SimPy process: walk the shortest path to target_node, yielding travel time per hop."""
        path = self.world.shortest_path(self.node, target_node)
        for nxt in path[1:]:
            hop_time = self.world.graph[self.node][nxt]["weight"]
            yield self.env.timeout(hop_time)
            self.node = nxt
            self._record("move", f"arrived at {nxt}")


class AssetAgent(BaseAgent):
    """
    A patrol unit / convoy / monitored asset.

    route: list of node ids to cycle through (patrol loop). If empty, the
    agent idles at its start node (e.g. a static checkpoint or depot).
    """

    def __init__(self, env, world, agent_id, start_node, log,
                 route: Optional[list[str]] = None, dwell_time: float = 1.0):
        super().__init__(env, world, agent_id, start_node, log)
        self.route = route or []
        self.dwell_time = dwell_time
        self.visited_count: dict[str, int] = {}

    def run(self):
        self._record("spawn")
        if not self.route:
            while self.alive:
                yield self.env.timeout(self.dwell_time)
            return
        idx = 0
        while self.alive:
            target = self.route[idx % len(self.route)]
            yield from self.move_to(target)
            self.visited_count[target] = self.visited_count.get(target, 0) + 1
            yield self.env.timeout(self.dwell_time)
            idx += 1


class ThreatAgent(BaseAgent):
    """
    An adversarial or hazard entity. Two built-in behaviors:
      - "static": appears at a fixed node and stays until resolved
      - "random_walk": moves to a random neighboring node each step

    emergence_time: sim time at which the threat becomes active (0 = active immediately)
    duration: how long the threat remains active before auto-resolving (None = indefinite)
    """

    def __init__(self, env, world, agent_id, start_node, log,
                 behavior: str = "static", emergence_time: float = 0.0,
                 duration: Optional[float] = None, step_time: float = 1.0):
        super().__init__(env, world, agent_id, start_node, log)
        self.behavior = behavior
        self.emergence_time = emergence_time
        self.duration = duration
        self.step_time = step_time
        self.active = False
        self.detected = False
        self.detected_at: Optional[float] = None

    def run(self):
        if self.emergence_time > 0:
            yield self.env.timeout(self.emergence_time)
        self.active = True
        self._record("emerge")

        elapsed = 0.0
        while self.alive and self.active:
            if self.duration is not None and elapsed >= self.duration:
                self.active = False
                self._record("resolve")
                break
            if self.behavior == "random_walk":
                neighbors = list(self.world.graph.neighbors(self.node))
                if neighbors:
                    self.node = random.choice(neighbors)
                    self._record("move")
            yield self.env.timeout(self.step_time)
            elapsed += self.step_time

    def mark_detected(self, at_time: float) -> None:
        if not self.detected:
            self.detected = True
            self.detected_at = at_time
            self._record("detected")
