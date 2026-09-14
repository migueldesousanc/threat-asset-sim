"""
Route optimization for patrol agents.

Two complementary approaches:

  - optimize_route(): given a fixed set of waypoints that must all be
    visited, find a short visiting order (nearest-neighbor construction +
    2-opt local search). Use this when you already know which locations
    matter (checkpoints, depots) and want to minimize travel time between
    them -- directly improves mean response time.

  - greedy_coverage_route(): given a travel-time/distance budget, greedily
    grow a route that visits as many distinct nearby locations as possible
    without exceeding the budget. Use this when you want to maximize
    spatial coverage rather than hit a specific list of waypoints.

Both operate on the same Environment graph the rest of the sim uses, so
distances/times are real travel times (shortest path along the road
network for OSM scenarios, or grid distance for the toy grid).

These are pure-Python heuristics -- no extra dependencies. They're not
exact solvers, but for the route sizes this sim deals with (a handful to
a few dozen waypoints) nearest-neighbor + 2-opt is normally within a few
percent of optimal, and coverage is a reasonable greedy approximation of
the (NP-hard) orienteering problem.
"""

from __future__ import annotations

from typing import Optional

from .environment import Environment


def pairwise_distances(env: Environment, nodes: list[str]) -> dict[tuple[str, str], float]:
    """All-pairs shortest-path distance among `nodes` (symmetric dict)."""
    dist: dict[tuple[str, str], float] = {}
    for i, a in enumerate(nodes):
        for b in nodes[i + 1:]:
            d = env.travel_time(a, b)
            dist[(a, b)] = d
            dist[(b, a)] = d
    return dist


def tour_cost(tour: list[str], dist: dict[tuple[str, str], float]) -> float:
    return sum(dist[(tour[i], tour[i + 1])] for i in range(len(tour) - 1))


def nearest_neighbor_tour(env: Environment, nodes: list[str],
                           start: Optional[str] = None) -> tuple[list[str], dict]:
    """Construct an initial tour by always stepping to the nearest unvisited node."""
    if start is None:
        start = nodes[0]
    dist = pairwise_distances(env, nodes)
    unvisited = set(nodes) - {start}
    tour = [start]
    current = start
    while unvisited:
        nxt = min(unvisited, key=lambda n: dist[(current, n)])
        tour.append(nxt)
        unvisited.remove(nxt)
        current = nxt
    return tour, dist


def two_opt(tour: list[str], dist: dict[tuple[str, str], float],
            max_iters: int = 200) -> list[str]:
    """Classic 2-opt local search: repeatedly reverse segments that shorten the tour."""
    best = tour[:]
    improved = True
    it = 0
    while improved and it < max_iters:
        improved = False
        it += 1
        for i in range(1, len(best) - 1):
            for j in range(i + 1, len(best)):
                if j - i == 1:
                    continue
                candidate = best[:i] + best[i:j][::-1] + best[j:]
                if tour_cost(candidate, dist) < tour_cost(best, dist):
                    best = candidate
                    improved = True
    return best


def optimize_route(env: Environment, nodes: list[str], start: Optional[str] = None) -> list[str]:
    """
    Find a short visiting order for a fixed set of waypoints.

    This is the "visit all these specific checkpoints as efficiently as
    possible" problem -- minimizes total travel time, which directly
    improves mean response time in the sim's metrics.
    """
    if len(nodes) <= 2:
        return nodes
    tour, dist = nearest_neighbor_tour(env, nodes, start)
    return two_opt(tour, dist)


def greedy_coverage_route(env: Environment, start: str, budget: float,
                           pool: Optional[list[str]] = None) -> list[str]:
    """
    Greedily build a route that maximizes the number of distinct nodes
    visited without exceeding `budget` total travel distance/time.

    If `pool` isn't given, candidates are limited to nodes reachable
    within `budget` of the start (any node farther than that can never be
    included anyway) -- this keeps the search fast on large graphs.
    """
    if pool is None:
        pool = env.nodes_within_radius(start, budget)

    candidates = set(pool) - {start}
    route = [start]
    current = start
    remaining = budget

    while candidates:
        nxt, nxt_dist = None, None
        for c in candidates:
            d = env.travel_time(current, c)
            if nxt_dist is None or d < nxt_dist:
                nxt, nxt_dist = c, d
        if nxt is None or nxt_dist > remaining:
            break
        route.append(nxt)
        remaining -= nxt_dist
        candidates.discard(nxt)
        current = nxt

    return route
