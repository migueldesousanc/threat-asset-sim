"""
Fetch real road-network terrain from OpenStreetMap via osmnx, and convert it
into the sim's Environment graph.

This module requires network access and the `osmnx` package (see
requirements.txt). It's kept separate from environment.py so the core sim
never needs osmnx unless you're actually building an OSM-based scenario.

Typical usage (from your own machine, with internet):

    from sim.osm_environment import fetch_road_network, nearest_node
    G = fetch_road_network("Esposende, Portugal", network_type="drive")
    env = Environment.from_osmnx(G)
    start = nearest_node(G, lat=41.535, lon=-8.783)

Or just use scripts/generate_osm_scenario.py to go straight from a place
name to a ready-to-run scenario JSON file.
"""

from __future__ import annotations

from typing import Optional


def fetch_road_network(place: str, network_type: str = "drive", simplify: bool = True):
    """
    Download the road network for `place` (a geocodable name, e.g.
    "Esposende, Portugal" or "Braga, Portugal") via osmnx.

    network_type: "drive", "walk", "bike", or "all" — controls which OSM
    ways are included. "drive" is the usual choice for vehicle patrol
    routes; use "walk" for foot patrols.
    """
    try:
        import osmnx as ox
    except ImportError as e:
        raise ImportError(
            "osmnx is required for OSM terrain. Install with: pip install osmnx"
        ) from e

    G = ox.graph_from_place(place, network_type=network_type, simplify=simplify)
    return G


def fetch_road_network_bbox(north: float, south: float, east: float, west: float,
                             network_type: str = "drive", simplify: bool = True):
    """Same as fetch_road_network but bounded by an explicit lat/lon bounding box."""
    try:
        import osmnx as ox
    except ImportError as e:
        raise ImportError(
            "osmnx is required for OSM terrain. Install with: pip install osmnx"
        ) from e

    G = ox.graph_from_bbox((north, south, east, west), network_type=network_type,
                            simplify=simplify)
    return G


def nearest_node(G, lat: float, lon: float) -> str:
    """Find the OSM node id nearest to (lat, lon), as a string (matches Environment ids)."""
    try:
        import osmnx as ox
    except ImportError as e:
        raise ImportError(
            "osmnx is required for OSM terrain. Install with: pip install osmnx"
        ) from e

    node_id = ox.distance.nearest_nodes(G, X=lon, Y=lat)
    return str(node_id)


def save_graph(G, path: str) -> None:
    """Cache a fetched graph to disk (GraphML) so you don't re-download it every run."""
    import osmnx as ox
    ox.save_graphml(G, path)


def load_graph(path: str):
    """Load a previously cached graph from disk (GraphML)."""
    import osmnx as ox
    return ox.load_graphml(path)
