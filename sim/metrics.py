"""
Metrics computed from a completed simulation run.

Given the shared event log (list of AgentLogEntry) and references to the
asset/threat agents, compute:
  - detection rate: fraction of threats detected before they resolved
  - mean/median response (detection) time
  - coverage: fraction of nodes visited by at least one asset during the run
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from .agents import AssetAgent, ThreatAgent
from .environment import Environment


@dataclass
class RunMetrics:
    detection_rate: float
    mean_detection_time: float | None
    median_detection_time: float | None
    coverage_fraction: float
    total_threats: int
    total_detected: int
    nodes_visited: int
    nodes_total: int


def detect_threats(assets: list[AssetAgent], threats: list[ThreatAgent],
                    detection_radius: float, world: Environment, sim_now: float) -> None:
    """
    Call periodically (or once at the end) to mark threats as detected if
    any asset is currently within detection_radius (graph distance) of them.
    """
    for threat in threats:
        if not threat.active or threat.detected:
            continue
        for asset in assets:
            try:
                dist = world.travel_time(asset.node, threat.node)
            except Exception:
                continue
            if dist <= detection_radius:
                threat.mark_detected(sim_now)
                break


def compute_metrics(assets: list[AssetAgent], threats: list[ThreatAgent],
                     world: Environment) -> RunMetrics:
    total_threats = len(threats)
    detected = [t for t in threats if t.detected]
    total_detected = len(detected)
    detection_rate = total_detected / total_threats if total_threats else 0.0

    detection_times = [t.detected_at - t.emergence_time for t in detected
                        if t.detected_at is not None]
    mean_dt = statistics.mean(detection_times) if detection_times else None
    median_dt = statistics.median(detection_times) if detection_times else None

    visited: set[str] = set()
    for asset in assets:
        visited.update(asset.visited_count.keys())
        visited.add(asset.node)
    nodes_total = len(world.all_nodes())
    coverage_fraction = len(visited) / nodes_total if nodes_total else 0.0

    return RunMetrics(
        detection_rate=detection_rate,
        mean_detection_time=mean_dt,
        median_detection_time=median_dt,
        coverage_fraction=coverage_fraction,
        total_threats=total_threats,
        total_detected=total_detected,
        nodes_visited=len(visited),
        nodes_total=nodes_total,
    )
