"""
Streamlit dashboard for the threat/asset simulation.

Run with:  streamlit run viz/dashboard.py
"""

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.scenarios import build_environment, load_scenario, run_scenario

st.set_page_config(page_title="Threat/Asset Simulation", layout="wide")
st.title("Threat / Asset Simulation Dashboard")

scenario_dir = Path(__file__).resolve().parent.parent / "scenarios"
scenario_files = sorted(scenario_dir.glob("*.json"))

col_a, col_b = st.columns([1, 3])
with col_a:
    chosen = st.selectbox("Scenario", [f.name for f in scenario_files])
    scenario_path = scenario_dir / chosen
    scenario = load_scenario(scenario_path)

    st.subheader("Run parameters")
    sim_duration = st.number_input("Sim duration", value=scenario.get("run", {}).get("sim_duration", 100))
    detection_radius = st.number_input("Detection radius",
                                        value=scenario.get("run", {}).get("detection_radius", 1.5))
    scenario.setdefault("run", {})["sim_duration"] = sim_duration
    scenario["run"]["detection_radius"] = detection_radius

    run_clicked = st.button("Run simulation", type="primary")

if run_clicked:
    metrics, log, assets, threats = run_scenario(scenario)
    world = build_environment(scenario)

    with col_b:
        st.subheader("Results")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Detection rate", f"{metrics.detection_rate:.0%}")
        m2.metric("Mean response time",
                   f"{metrics.mean_detection_time:.1f}" if metrics.mean_detection_time else "—")
        m3.metric("Coverage", f"{metrics.coverage_fraction:.0%}")
        m4.metric("Threats detected", f"{metrics.total_detected}/{metrics.total_threats}")

        # --- map view ---
        # OSM-sourced scenarios carry meta.source == "osm": node x/y are real
        # lon/lat, so render on an actual map (Scattermapbox) instead of a
        # plain xy scatter.
        is_geo = scenario.get("meta", {}).get("source") == "osm"

        if is_geo:
            fig = go.Figure()
            lons, lats = [], []
            for node in world.all_nodes():
                x, y = world.node_position(node)
                lons.append(x)
                lats.append(y)
            fig.add_trace(go.Scattermapbox(lon=lons, lat=lats, mode="markers",
                                            marker=dict(size=5, color="lightgray"),
                                            name="nodes"))
            for asset in assets:
                x, y = world.node_position(asset.node)
                fig.add_trace(go.Scattermapbox(lon=[x], lat=[y], mode="markers+text",
                                                marker=dict(size=14, color="blue"),
                                                text=[asset.agent_id], name=asset.agent_id))
            for threat in threats:
                x, y = world.node_position(threat.node)
                color = "green" if threat.detected else ("red" if threat.active else "gray")
                fig.add_trace(go.Scattermapbox(lon=[x], lat=[y], mode="markers+text",
                                                marker=dict(size=14, color=color),
                                                text=[threat.agent_id], name=threat.agent_id))
            center_lon = sum(lons) / len(lons) if lons else 0
            center_lat = sum(lats) / len(lats) if lats else 0
            fig.update_layout(height=550, showlegend=False,
                               mapbox=dict(style="open-street-map", zoom=13,
                                           center=dict(lon=center_lon, lat=center_lat)),
                               title="Final state (asset=blue, threat=red/green/gray)")
        else:
            fig = go.Figure()
            xs, ys, labels = [], [], []
            for node in world.all_nodes():
                x, y = world.node_position(node)
                xs.append(x)
                ys.append(y)
                labels.append(node)
            fig.add_trace(go.Scatter(x=xs, y=ys, mode="markers",
                                      marker=dict(size=6, color="lightgray"),
                                      name="nodes", hovertext=labels))
            for asset in assets:
                x, y = world.node_position(asset.node)
                fig.add_trace(go.Scatter(x=[x], y=[y], mode="markers+text",
                                          marker=dict(size=14, color="blue", symbol="triangle-up"),
                                          text=[asset.agent_id], textposition="top center",
                                          name=asset.agent_id))
            for threat in threats:
                x, y = world.node_position(threat.node)
                color = "green" if threat.detected else ("red" if threat.active else "gray")
                fig.add_trace(go.Scatter(x=[x], y=[y], mode="markers+text",
                                          marker=dict(size=14, color=color, symbol="x"),
                                          text=[threat.agent_id], textposition="bottom center",
                                          name=threat.agent_id))
            fig.update_layout(height=500, showlegend=False,
                               title="Final state (asset=triangle, threat=x)")

        st.plotly_chart(fig, use_container_width=True)

        # --- event log ---
        st.subheader("Event log")
        df = pd.DataFrame([e.__dict__ for e in log]).sort_values("time")
        st.dataframe(df, use_container_width=True, height=300)
else:
    with col_b:
        st.info("Configure parameters and click **Run simulation**.")
