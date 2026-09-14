"""
Optimize patrol routes in an existing scenario file.

Two modes:
  --mode tsp       Keep each asset's existing waypoints, but reorder them
                    for minimal total travel time (nearest-neighbor + 2-opt).
  --mode coverage  Replace each asset's route with a greedily-grown route
                    that maximizes distinct locations visited within
                    --budget travel distance/time from its start node.

Usage:
    python scripts/optimize_route.py scenarios/esposende.json --mode coverage --budget 4000
    python scripts/optimize_route.py scenarios/esposende.json --mode tsp
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.environment import Environment
from sim.route_optimizer import greedy_coverage_route, optimize_route


def main():
    parser = argparse.ArgumentParser(description="Optimize patrol routes in a scenario file.")
    parser.add_argument("scenario", help="Path to a scenario JSON file (edited in place unless --out is given)")
    parser.add_argument("--mode", choices=["tsp", "coverage"], default="coverage")
    parser.add_argument("--budget", type=float, default=4000,
                         help="Travel distance/time budget per route (coverage mode only; "
                              "meters for OSM scenarios, map units for the grid)")
    parser.add_argument("--out", default=None, help="Output path (defaults to overwriting the input)")
    args = parser.parse_args()

    with open(args.scenario) as f:
        scenario = json.load(f)

    env = Environment.from_scenario(scenario)

    for asset in scenario.get("assets", []):
        start = asset["start_node"]
        if args.mode == "tsp":
            waypoints = asset.get("route", [start])
            if start not in waypoints:
                waypoints = [start] + waypoints
            new_route = optimize_route(env, waypoints, start=start)
        else:
            new_route = greedy_coverage_route(env, start, args.budget)
        print(f"{asset['id']}: {len(new_route)} waypoints (mode={args.mode})")
        asset["route"] = new_route

    out_path = args.out or args.scenario
    with open(out_path, "w") as f:
        json.dump(scenario, f, indent=2)
    print(f"Wrote optimized scenario to {out_path}")


if __name__ == "__main__":
    main()
