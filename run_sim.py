"""
CLI entry point: run a scenario and print metrics.

Usage:
    python run_sim.py scenarios/example_patrol.json
"""

import argparse
import json

from sim.scenarios import load_scenario, run_scenario


def main():
    parser = argparse.ArgumentParser(description="Run a threat/asset simulation scenario.")
    parser.add_argument("scenario", help="Path to a scenario JSON file")
    parser.add_argument("--log", action="store_true", help="Print the full event log")
    args = parser.parse_args()

    scenario = load_scenario(args.scenario)
    metrics, log, assets, threats = run_scenario(scenario)

    print(f"Scenario: {args.scenario}")
    print(f"  Detection rate:      {metrics.detection_rate:.0%} "
          f"({metrics.total_detected}/{metrics.total_threats})")
    print(f"  Mean response time:  "
          f"{metrics.mean_detection_time:.2f}" if metrics.mean_detection_time is not None else "  Mean response time:  n/a")
    print(f"  Median response time: "
          f"{metrics.median_detection_time:.2f}" if metrics.median_detection_time is not None else "  Median response time: n/a")
    print(f"  Coverage:            {metrics.coverage_fraction:.0%} "
          f"({metrics.nodes_visited}/{metrics.nodes_total} nodes)")

    if args.log:
        print("\nEvent log:")
        for entry in log:
            print(f"  t={entry.time:6.2f}  {entry.agent_id:12s}  {entry.event:10s}  "
                  f"node={entry.node}  {entry.detail}")


if __name__ == "__main__":
    main()
