"""
Generate a scenario JSON file from a real place, using OpenStreetMap road
data. Requires internet access and osmnx (pip install osmnx).

Usage:
    python scripts/generate_osm_scenario.py "Esposende, Portugal" \\
        --network-type drive \\
        --num-assets 2 \\
        --num-threats 2 \\
        --sim-duration 200 \\
        --out scenarios/esposende.json

The generated scenario bakes in the fetched nodes/edges (so `run_sim.py`
and the dashboard need no network access afterward) plus randomly placed
assets and threats. Asset routes are a random walk of `--route-length`
waypoints; edit the JSON afterward for real patrol routes.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.environment import Environment
from sim.osm_environment import fetch_road_network


def environment_to_scenario_dict(env: Environment) -> dict:
    nodes = []
    for node_id, data in env.graph.nodes(data=True):
        nodes.append({"id": node_id, "name": data.get("name", node_id),
                       "kind": data.get("kind", "waypoint"),
                       "x": data.get("x", 0.0), "y": data.get("y", 0.0)})
    edges = []
    for u, v, data in env.graph.edges(data=True):
        edges.append({"u": u, "v": v, "weight": data.get("weight", 1.0)})
    return {"nodes": nodes, "edges": edges}


def random_route(env: Environment, start: str, length: int) -> list[str]:
    """Random walk of `length` connected nodes starting from `start`, for a placeholder route."""
    route = [start]
    current = start
    for _ in range(length - 1):
        neighbors = list(env.graph.neighbors(current))
        if not neighbors:
            break
        current = random.choice(neighbors)
        route.append(current)
    return route


def main():
    parser = argparse.ArgumentParser(description="Generate an OSM-based scenario file.")
    parser.add_argument("place", help='Geocodable place name, e.g. "Esposende, Portugal"')
    parser.add_argument("--network-type", default="drive", choices=["drive", "walk", "bike", "all"])
    parser.add_argument("--num-assets", type=int, default=2)
    parser.add_argument("--num-threats", type=int, default=2)
    parser.add_argument("--route-length", type=int, default=6,
                         help="Number of waypoints per placeholder patrol route")
    parser.add_argument("--sim-duration", type=float, default=200)
    parser.add_argument("--detection-radius", type=float, default=150.0,
                         help="Detection radius in meters (OSM edge weights are meters)")
    parser.add_argument("--out", default=None, help="Output scenario JSON path")
    args = parser.parse_args()

    print(f"Fetching road network for: {args.place} ({args.network_type})...")
    G = fetch_road_network(args.place, network_type=args.network_type)
    env = Environment.from_osmnx(G)
    print(f"  {len(env.all_nodes())} nodes, {env.graph.number_of_edges()} edges")

    all_nodes = env.all_nodes()
    random.shuffle(all_nodes)

    assets = []
    for i in range(args.num_assets):
        start = all_nodes[i % len(all_nodes)]
        route = random_route(env, start, args.route_length)
        assets.append({"id": f"patrol_{i+1}", "start_node": start,
                        "route": route, "dwell_time": 5.0})

    threats = []
    for i in range(args.num_threats):
        start = all_nodes[(args.num_assets + i) % len(all_nodes)]
        threats.append({
            "id": f"threat_{i+1}",
            "start_node": start,
            "behavior": "random_walk" if i % 2 == 0 else "static",
            "emergence_time": 10 + i * 15,
            "duration": 60,
            "step_time": 5.0,
        })

    scenario = environment_to_scenario_dict(env)
    scenario["assets"] = assets
    scenario["threats"] = threats
    scenario["run"] = {
        "sim_duration": args.sim_duration,
        "detection_radius": args.detection_radius,
        "detection_interval": 5.0,
    }
    scenario["meta"] = {"source": "osm", "place": args.place,
                         "network_type": args.network_type}

    out_path = args.out or f"scenarios/{args.place.split(',')[0].strip().lower().replace(' ', '_')}.json"
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(scenario, f, indent=2)

    print(f"Wrote scenario to {out_path}")
    print(f"Run it with: python3 run_sim.py {out_path} --log")


if __name__ == "__main__":
    main()
