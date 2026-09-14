"""
Basic sanity tests for the simulation core.

Run with:  pytest
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.environment import Environment
from sim.scenarios import load_scenario, run_scenario


def test_grid_environment_basic():
    env = Environment.grid(3, 3)
    assert len(env.all_nodes()) == 9
    path = env.shortest_path("0_0", "2_2")
    assert path[0] == "0_0"
    assert path[-1] == "2_2"


def test_nodes_within_radius():
    env = Environment.grid(5, 5)
    nearby = env.nodes_within_radius("2_2", 1.0)
    # center + 4 orthogonal neighbors
    assert "2_2" in nearby
    assert len(nearby) >= 3


def test_example_scenario_runs():
    scenario_path = Path(__file__).resolve().parent.parent / "scenarios" / "example_patrol.json"
    scenario = load_scenario(scenario_path)
    metrics, log, assets, threats = run_scenario(scenario)

    assert metrics.total_threats == len(threats)
    assert 0.0 <= metrics.detection_rate <= 1.0
    assert 0.0 <= metrics.coverage_fraction <= 1.0
    assert len(log) > 0


def test_static_threat_gets_detected_when_asset_colocated():
    scenario = {
        "grid": {"width": 3, "height": 3},
        "assets": [{"id": "a1", "start_node": "1_1", "route": [], "dwell_time": 1.0}],
        "threats": [{"id": "t1", "start_node": "1_1", "behavior": "static",
                     "emergence_time": 0, "duration": 5}],
        "run": {"sim_duration": 10, "detection_radius": 0.5, "detection_interval": 1.0},
    }
    metrics, log, assets, threats = run_scenario(scenario)
    assert threats[0].detected is True
    assert metrics.detection_rate == 1.0
