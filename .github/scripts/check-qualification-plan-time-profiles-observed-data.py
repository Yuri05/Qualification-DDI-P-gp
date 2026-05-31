#!/usr/bin/env python3
"""
Check that all observed data referenced in time profile plots are defined in ObservedDataSets.

This script validates a qualification plan JSON file to ensure that:
1. All ObservedData references in ComparisonTimeProfilePlots exist in the ObservedDataSets section
2. Provides a clear error message listing all missing observed data sets

Usage:
    python check-qualification-plan-time-profiles-observed-data.py \
        --qualification-plan <path-to-json> \
        [--ignore <obs-data-name1>] [--ignore <obs-data-name2>] ...
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Set, List, Tuple


def load_qualification_plan(path: str) -> dict:
    """Load and parse the qualification plan JSON file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Qualification plan file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in qualification plan: {e}", file=sys.stderr)
        sys.exit(1)


def get_defined_observed_data_sets(plan: dict) -> Set[str]:
    """Extract all defined ObservedDataSet IDs from the qualification plan."""
    observed_data_sets = set()
    for obs in plan.get('ObservedDataSets', []):
        if 'Id' in obs:
            observed_data_sets.add(obs['Id'])
    return observed_data_sets


def get_referenced_observed_data(plan: dict) -> List[Tuple[str, str, str]]:
    """
    Extract all ObservedData references from ComparisonTimeProfilePlots.

    Returns a list of tuples: (project, observed_data_name, plot_title)
    """
    referenced_data = []

    for plot in plan.get('Plots', {}).get('ComparisonTimeProfilePlots', []):
        plot_title = plot.get('Title', 'Unknown Plot')

        for mapping in plot.get('OutputMappings', []):
            project = mapping.get('Project', 'Unknown Project')
            obs_data = mapping.get('ObservedData')

            if obs_data:
                # ObservedData can be a string or a list of strings
                if isinstance(obs_data, list):
                    for item in obs_data:
                        if item:
                            referenced_data.append((project, item, plot_title))
                else:
                    referenced_data.append((project, obs_data, plot_title))

    return referenced_data


def check_observed_data(
    defined_sets: Set[str],
    referenced_data: List[Tuple[str, str, str]],
    ignore_list: Set[str]
) -> List[Tuple[str, str]]:
    """
    Check which referenced observed data are not defined.

    Returns a list of tuples: (project, observed_data_name) for missing data.
    """
    missing_data = []

    for project, obs_data_name, plot_title in referenced_data:
        # Skip if in ignore list
        if obs_data_name in ignore_list:
            continue

        # Check if the observed data is defined
        if obs_data_name not in defined_sets:
            missing_data.append((project, obs_data_name))

    return missing_data


def format_error_message(missing_data: List[Tuple[str, str]]) -> str:
    """Format the error message for missing observed data."""
    if not missing_data:
        return ""

    # Remove duplicates and sort
    unique_missing = sorted(set(missing_data))

    message_lines = [
        "ERROR: The following observed data sets are referenced in ComparisonTimeProfilePlots",
        "but are not defined in the ObservedDataSets section:",
        ""
    ]

    for project, obs_data_name in unique_missing:
        message_lines.append(f"  - Project: {project}")
        message_lines.append(f"    Observed Data: {obs_data_name}")
        message_lines.append("")

    message_lines.append(f"Total missing observed data sets: {len(unique_missing)}")

    return "\n".join(message_lines)


def main():
    parser = argparse.ArgumentParser(
        description="Check observed data sets in qualification plan time profiles"
    )
    parser.add_argument(
        '--qualification-plan',
        required=True,
        help='Path to the qualification plan JSON file'
    )
    parser.add_argument(
        '--ignore',
        action='append',
        default=[],
        help='Observed data set names to ignore (can be used multiple times)'
    )

    args = parser.parse_args()

    # Load qualification plan
    plan = load_qualification_plan(args.qualification_plan)

    # Get defined observed data sets
    defined_sets = get_defined_observed_data_sets(plan)
    print(f"Found {len(defined_sets)} defined ObservedDataSets")

    # Get referenced observed data
    referenced_data = get_referenced_observed_data(plan)
    unique_referenced = set(obs for _, obs, _ in referenced_data)
    print(f"Found {len(unique_referenced)} unique ObservedData references in ComparisonTimeProfilePlots")

    # Check for missing data
    ignore_set = set(args.ignore)
    if ignore_set:
        print(f"Ignoring {len(ignore_set)} observed data sets")

    missing_data = check_observed_data(defined_sets, referenced_data, ignore_set)

    if missing_data:
        error_message = format_error_message(missing_data)
        print("\n" + error_message, file=sys.stderr)

        # Output GitHub annotation format
        print("\n::error::Some observed data sets are not defined in ObservedDataSets section. "
              f"See the log for the list of {len(set(missing_data))} missing data sets.")

        sys.exit(1)
    else:
        print("\n✓ All referenced observed data sets are properly defined!")
        sys.exit(0)


if __name__ == '__main__':
    main()
