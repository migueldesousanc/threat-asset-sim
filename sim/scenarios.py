"""
Scenario loading and simulation orchestration.

A scenario is a JSON/dict describing:
  - the environment (nodes + edges), OR a "grid": {width, height} shortcut
  - a list of asset agents (patrol routes, dwell times)
  - a list of threat agents (emergence time, behavior, duration)
  - run parameters (sim_duration, detection_radius, detection_interval)

See scenarios/example_patrol.json for a worked example.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import simpy

from .agents import AgentLogEntry, AssetAgent, ThreatAgent
from .environment import Environment
from .metrics import RunMetrics, compute_metrics, detect_threats


def load_scenario(path: str | Path) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def build_environment(scenario: dict) -> Environment:
    if "grid" in scenario:
        g = scenario["grid"]
        return Environment.grid(g["width"], g["height"], g.get("spacing", 1.0))
    return Environment.from_scenario(scenario)


def run_scenario(scenario: dict) -> tuple[RunMetrics, list[AgentLogEntry],
                                           list[AssetAgent], list[ThreatAgent]]:
    """Build and execute a scenario. Returns metrics, the event log, and the agents."""
    world = build_environment(scenario)
    env = simpy.Environment()
    log: list[AgentLogEntry] = []

    assets: list[AssetAgent] = []
    for a in scenario.get("assets", []):
        agent = AssetAgent(env, world, a["id"], a["start_node"], log,
                            route=a.get("route", []), dwell_time=a.get("dwell_time", 1.0))
        assets.append(agent)
        env.process(agent.run())

    threats: list[ThreatAgent] = []
    for t in scenario.get("threats", []):
        agent = ThreatAgent(env, world, t["id"], t["start_node"], log,
                             behavior=t.get("behavior", "static"),
                             emergence_time=t.get("emergence_time", 0.0),
                             duration=t.get("duration"),
                             step_time=t.get("step_time", 1.0))
        threats.append(agent)
        env.process(agent.run())

    run_params = scenario.get("run", {})
    sim_duration = run_params.get("sim_duration", 100)
    detection_radius = run_params.get("detection_radius", 1.5)
    detection_interval = run_params.get("detection_interval", 1.0)

    def detection_loop():
        while True:
            detect_threats(assets, threats, detection_radius, world, env.now)
            yield env.timeout(detection_interval)

    env.process(detection_loop())
    env.run(until=sim_duration)

    # final sweep in case detection_interval didn't land exactly on sim end
    detect_threats(assets, threats, detection_radius, world, env.now)

    metrics = compute_metrics(assets, threats, world)
    return metrics, log, assets, threats
