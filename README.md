# threat-asset-sim

Agent-based / discrete-event simulation of asset (patrol, convoy, logistics)
movement and adversarial or hazard "threat" agents on a graph-based terrain
representation. Built for modeling patrol coverage, response times, and
resilience — no hardware or physical sensors involved, pure software.

## Concept

- **Environment**: a graph (via NetworkX) of nodes (locations) and weighted
  edges (routes). Comes with a quick grid-world constructor, or load a
  custom node/edge layout from a scenario file.
- **AssetAgent**: friendly/monitored entities that patrol a fixed route
  (loop) or sit static at a location.
- **ThreatAgent**: adversarial or hazard entities that emerge at a
  configurable time, either stay put ("static") or wander ("random_walk"),
  and resolve after a duration.
- **Detection loop**: periodically checks which threats fall within a
  configurable graph-distance of any asset and marks them detected.
- **Metrics**: detection rate, mean/median response (detection) time, and
  spatial coverage (fraction of nodes visited by any asset).

## Quick start

```bash
pip install -r requirements.txt

# CLI run
python run_sim.py scenarios/example_patrol.json --log

# Interactive dashboard
streamlit run viz/dashboard.py
```

## Using real terrain (OpenStreetMap)

Instead of the abstract grid, you can generate a scenario from a real
road network via [osmnx](https://osmnx.readthedocs.io/):

```bash
python3 scripts/generate_osm_scenario.py "Esposende, Portugal" \
    --network-type drive \
    --num-assets 2 \
    --num-threats 2 \
    --out scenarios/esposende.json

python3 run_sim.py scenarios/esposende.json --log
streamlit run viz/dashboard.py   # select the new scenario — it renders on a real map
```

This downloads the actual street graph for the named place (any
geocodable name works — city, town, or "Neighborhood, City, Country"),
converts it into the same node/edge format the rest of the sim already
uses, and drops in randomly placed patrol routes and threats as a
starting point. Edit the generated JSON's `assets`/`threats` afterward
for real patrol routes or specific coordinates (use
`sim.osm_environment.nearest_node(G, lat, lon)` to snap a real-world
coordinate to the nearest road node).

Requires internet access and `pip install osmnx` (already in
requirements.txt). Detection radius and edge weights are in meters for
OSM-sourced scenarios (vs. abstract "map units" for the grid).

## Writing your own scenario

Scenarios are JSON files (see `scenarios/example_patrol.json`). Either:

1. Use `"grid": {"width": W, "height": H, "spacing": S}` for a quick
   grid-world, or
2. Define custom `"nodes"` and `"edges"` for a real layout (e.g. built
   from actual geographic waypoints).

Then define `"assets"` (id, start_node, route, dwell_time) and `"threats"`
(id, start_node, behavior, emergence_time, duration, step_time), plus a
`"run"` block for sim_duration / detection_radius / detection_interval.

## Extending

Natural next steps if you want to grow this:
- Swap the grid/graph for real geographic coordinates + OSM road network
  (via `osmnx`) for a realistic terrain model.
- Add route optimization (OR-Tools) to auto-generate patrol routes that
  maximize coverage or minimize mean response time.
- Add multiple threat "teams" with coordinated behavior (pursuit/evasion
  game theory) instead of independent random walks.
- Log runs to a database and build a scenario-comparison view in the
  dashboard (A/B different patrol strategies).

## Project structure

```
threat-asset-sim/
├── sim/
│   ├── agents.py        # AssetAgent, ThreatAgent
│   ├── environment.py   # graph-based terrain model
│   ├── scenarios.py     # scenario loading + run orchestration
│   └── metrics.py       # detection rate, response time, coverage
├── viz/
│   └── dashboard.py     # Streamlit visualization
├── scenarios/
│   └── example_patrol.json
├── tests/
│   └── test_sim.py
├── run_sim.py            # CLI entry point
├── requirements.txt
└── README.md
```

## License

MIT (or pick your preferred license before publishing).
