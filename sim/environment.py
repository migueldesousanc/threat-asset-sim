"""
Environment representation for the threat/asset simulation.

The environment is a graph (NetworkX) where nodes represent locations
(checkpoints, depots, waypoints) and edges represent traversable routes
with an associated travel time / distance / risk weight.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

import networkx as nx


@dataclass
class NodeAttributes:
    """Optional metadata attached to a location node."""
    name: str
    kind: str = "waypoint"          # e.g. "depot", "checkpoint", "waypoint", "asset_base"
    coverage_radius: float = 0.0     # sensor/patrol coverage radius, in map units
    risk_level: float = 0.0          # baseline risk score [0, 1]
    x: float = 0.0
    y: float = 0.0


class Environment:
    """Wraps a NetworkX graph with helpers for scenario loading and queries."""

    def __init__(self):
        self.graph = nx.Graph()

    # ---------- construction ----------

    def add_node(self, node_id: str, **attrs) -> None:
        na = NodeAttributes(name=attrs.pop("name", node_id), **attrs)
        self.graph.add_node(node_id, **na.__dict__)

    def add_edge(self, u: str, v: str, weight: float = 1.0, risk: float = 0.0) -> None:
        self.graph.add_edge(u, v, weight=weight, risk=risk)

    @classmethod
    def from_scenario(cls, scenario: dict) -> "Environment":
        """Build an Environment from a parsed scenario dict (see scenarios/*.json)."""
        env = cls()
        for node in scenario.get("nodes", []):
            node = dict(node)  # copy so we don't mutate the caller's scenario dict
            node_id = node.pop("id")
            env.add_node(node_id, **node)
        for edge in scenario.get("edges", []):
            env.add_edge(edge["u"], edge["v"], weight=edge.get("weight", 1.0),
                         risk=edge.get("risk", 0.0))
        return env

    @classmethod
    def grid(cls, width: int, height: int, spacing: float = 1.0) -> "Environment":
        """Convenience constructor: a simple width x height grid world."""
        env = cls()
        for x in range(width):
            for y in range(height):
                node_id = f"{x}_{y}"
                env.add_node(node_id, name=node_id, kind="waypoint",
                             x=x * spacing, y=y * spacing)
        for x in range(width):
            for y in range(height):
                node_id = f"{x}_{y}"
                if x + 1 < width:
                    env.add_edge(node_id, f"{x+1}_{y}", weight=spacing)
                if y + 1 < height:
                    env.add_edge(node_id, f"{x}_{y+1}", weight=spacing)
        return env

    @classmethod
    def from_osmnx(cls, G) -> "Environment":
        """
        Build an Environment from an osmnx road-network graph (MultiDiGraph).

        Node ids become strings of the OSM node id. Positions use
        x=longitude, y=latitude (as osmnx stores them). Edge weight uses
        the OSM 'length' attribute (meters) when present; when multiple
        parallel edges exist between two nodes (common in a MultiDiGraph),
        the shortest one is kept.
        """
        env = cls()
        for node_id, data in G.nodes(data=True):
            env.add_node(str(node_id), name=str(node_id), kind="waypoint",
                         x=data.get("x", 0.0), y=data.get("y", 0.0))

        best_weight: dict[tuple[str, str], float] = {}
        for u, v, data in G.edges(data=True):
            u, v = str(u), str(v)
            length = float(data.get("length", 1.0))
            key = (u, v) if u <= v else (v, u)
            if key not in best_weight or length < best_weight[key]:
                best_weight[key] = length

        for (u, v), weight in best_weight.items():
            env.add_edge(u, v, weight=weight)

        return env

    # ---------- queries ----------

    def shortest_path(self, source: str, target: str, weight: str = "weight") -> list[str]:
        return nx.shortest_path(self.graph, source, target, weight=weight)

    def travel_time(self, source: str, target: str, weight: str = "weight") -> float:
        return nx.shortest_path_length(self.graph, source, target, weight=weight)

    def nodes_within_radius(self, node_id: str, radius: float) -> list[str]:
        """Nodes reachable within `radius` graph-distance of node_id (proxy for coverage)."""
        lengths = nx.single_source_dijkstra_path_length(self.graph, node_id, cutoff=radius,
                                                          weight="weight")
        return list(lengths.keys())

    def node_position(self, node_id: str) -> tuple[float, float]:
        data = self.graph.nodes[node_id]
        return data.get("x", 0.0), data.get("y", 0.0)

    def all_nodes(self) -> list[str]:
        return list(self.graph.nodes)
