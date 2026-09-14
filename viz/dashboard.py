"""
Streamlit dashboard for the threat/asset simulation.

Run with:  streamlit run viz/dashboard.py
"""

import math
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.scenarios import build_environment, load_scenario, run_scenario

st.set_page_config(page_title="Threat/Asset Simulation", page_icon=":radar:", layout="wide")

COLOR_ROUTE = "#1f6feb"
COLOR_ASSET = "#58a6ff"
COLOR_THREAT_ACTIVE = "#f85149"
COLOR_THREAT_DETECTED = "#3fb950"
COLOR_THREAT_INACTIVE = "#8b949e"


def expand_route_path(world, route):
    """Turn a list of waypoints into the full sequence of nodes along the
    real roads/edges connecting them, so the drawn line follows the actual
    terrain instead of jumping straight between waypoints."""
    if len(route) < 2:
        return route
    full = [route[0]]
    for a, b in zip(route, route[1:]):
        try:
            path = world.shortest_path(a, b)
        except Exception:
            path = [a, b]
        full.extend(path[1:])
    return full


def compute_view(lons, lats, padding=1.6, min_zoom=3, max_zoom=16):
    """Center + zoom that fits all given points, instead of a fixed zoom
    level centered on the whole road network's average position."""
    lon_min, lon_max = min(lons), max(lons)
    lat_min, lat_max = min(lats), max(lats)
    center_lon = (lon_min + lon_max) / 2
    center_lat = (lat_min + lat_max) / 2
    lon_diff = max((lon_max - lon_min) * padding, 0.0015)
    lat_diff = max((lat_max - lat_min) * padding, 0.0015)
    zoom = math.log2(360 / max(lon_diff, lat_diff)) - 1
    zoom = max(min_zoom, min(max_zoom, zoom))
    return center_lon, center_lat, zoom


st.title("Threat / asset simulation")
st.caption("Patrol coverage and threat detection, on a grid or a real road network.")

scenario_dir = Path(__file__).resolve().parent.parent / "scenarios"
scenario_files = sorted(scenario_dir.glob("*.json"))

with st.sidebar:
    st.header("Scenario")
    chosen = st.selectbox("File", [f.name for f in scenario_files])
    scenario_path = scenario_dir / chosen
    scenario = load_scenario(scenario_path)

    st.header("Run parameters")
    sim_duration = st.number_input("Sim duration", value=scenario.get("run", {}).get("sim_duration", 100))
    detection_radius = st.number_input("Detection radius",
                                        value=scenario.get("run", {}).get("detection_radius", 1.5))
    scenario.setdefault("run", {})["sim_duration"] = sim_duration
    scenario["run"]["detection_radius"] = detection_radius

    run_clicked = st.button("Run simulation", type="primary", use_container_width=True)

if run_clicked:
    metrics, log, assets, threats = run_scenario(scenario)
    world = build_environment(scenario)

    st.subheader("Results")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Detection rate", f"{metrics.detection_rate:.0%}")
    with m2:
        st.metric("Mean response time",
                   f"{metrics.mean_detection_time:.1f}" if metrics.mean_detection_time else "—")
    with m3:
        st.metric("Coverage", f"{metrics.coverage_fraction:.0%}")
    with m4:
        st.metric("Threats detected", f"{metrics.total_detected}/{metrics.total_threats}")

    is_geo = scenario.get("meta", {}).get("source") == "osm"
    fig = go.Figure()

    all_lons, all_lats = [], []

    if is_geo:
        for i, asset in enumerate(assets):
            full_path = expand_route_path(world, asset.route) if asset.route else [asset.node]
            positions = [world.node_position(n) for n in full_path]
            lons = [p[0] for p in positions]
            lats = [p[1] for p in positions]
            all_lons.extend(lons)
            all_lats.extend(lats)
            fig.add_trace(go.Scattermap(
                lon=lons, lat=lats, mode="lines", line=dict(width=3, color=COLOR_ROUTE),
                name="Patrol route", legendgroup="route", showlegend=(i == 0),
                hoverinfo="skip"))

        asset_lons, asset_lats, asset_text = [], [], []
        for asset in assets:
            x, y = world.node_position(asset.node)
            asset_lons.append(x)
            asset_lats.append(y)
            asset_text.append(asset.agent_id)
        if asset_lons:
            all_lons.extend(asset_lons)
            all_lats.extend(asset_lats)
            fig.add_trace(go.Scattermap(
                lon=asset_lons, lat=asset_lats, mode="markers", text=asset_text,
                marker=dict(size=16, color=COLOR_ASSET), name="Patrol asset"))

        groups = {
            "Undetected threat": (COLOR_THREAT_ACTIVE, lambda t: t.active and not t.detected),
            "Detected threat": (COLOR_THREAT_DETECTED, lambda t: t.detected),
            "Inactive threat": (COLOR_THREAT_INACTIVE, lambda t: not t.active and not t.detected),
        }
        for label, (color, predicate) in groups.items():
            group = [t for t in threats if predicate(t)]
            if not group:
                continue
            lons, lats, text = [], [], []
            for t in group:
                x, y = world.node_position(t.node)
                lons.append(x)
                lats.append(y)
                text.append(t.agent_id)
            all_lons.extend(lons)
            all_lats.extend(lats)
            fig.add_trace(go.Scattermap(
                lon=lons, lat=lats, mode="markers", text=text,
                marker=dict(size=16, color=color), name=label))

        if all_lons:
            center_lon, center_lat, zoom = compute_view(all_lons, all_lats)
        else:
            center_lon, center_lat, zoom = 0, 0, 3

        fig.update_layout(
            height=600, margin=dict(l=0, r=0, t=0, b=0),
            legend=dict(bgcolor="rgba(0,0,0,0.4)", font=dict(color="white"),
                        yanchor="top", y=0.98, xanchor="left", x=0.02),
            map=dict(style="open-street-map", zoom=zoom,
                     center=dict(lon=center_lon, lat=center_lat)),
        )
    else:
        for i, asset in enumerate(assets):
            full_path = expand_route_path(world, asset.route) if asset.route else [asset.node]
            positions = [world.node_position(n) for n in full_path]
            xs = [p[0] for p in positions]
            ys = [p[1] for p in positions]
            fig.add_trace(go.Scatter(
                x=xs, y=ys, mode="lines", line=dict(width=2, color=COLOR_ROUTE),
                name="Patrol route", legendgroup="route", showlegend=(i == 0),
                hoverinfo="skip"))

        asset_xs, asset_ys, asset_text = [], [], []
        for asset in assets:
            x, y = world.node_position(asset.node)
            asset_xs.append(x)
            asset_ys.append(y)
            asset_text.append(asset.agent_id)
        if asset_xs:
            fig.add_trace(go.Scatter(
                x=asset_xs, y=asset_ys, mode="markers+text", text=asset_text,
                textposition="top center",
                marker=dict(size=14, color=COLOR_ASSET, symbol="triangle-up"),
                name="Patrol asset"))

        groups = {
            "Undetected threat": (COLOR_THREAT_ACTIVE, lambda t: t.active and not t.detected),
            "Detected threat": (COLOR_THREAT_DETECTED, lambda t: t.detected),
            "Inactive threat": (COLOR_THREAT_INACTIVE, lambda t: not t.active and not t.detected),
        }
        for label, (color, predicate) in groups.items():
            group = [t for t in threats if predicate(t)]
            if not group:
                continue
            xs, ys, text = [], [], []
            for t in group:
                x, y = world.node_position(t.node)
                xs.append(x)
                ys.append(y)
                text.append(t.agent_id)
            fig.add_trace(go.Scatter(
                x=xs, y=ys, mode="markers+text", text=text, textposition="bottom center",
                marker=dict(size=14, color=color, symbol="x"), name=label))

        fig.update_layout(height=550, margin=dict(l=0, r=0, t=0, b=0))

    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Event log"):
        df = pd.DataFrame([e.__dict__ for e in log]).sort_values("time")
        st.dataframe(df, use_container_width=True, height=300)
else:
    st.info("Configure parameters in the sidebar and click **Run simulation**.")
