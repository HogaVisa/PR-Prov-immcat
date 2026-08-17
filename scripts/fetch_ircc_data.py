"""
fetch_ircc_data.py
-------------------
Downloads the latest IRCC "Permanent Residents by Country of Citizenship"
open data file and saves it to data/raw/.

Source dataset: "Permanent Residents – Monthly IRCC Updates"
https://open.canada.ca/data/en/dataset/f7e5498e-0ad8-4417-85c9-9b8aff9b9eda

Usage:
    python fetch_ircc_data.py [--output data/raw/EN_ODP-PR-Citz.xlsx]
"""

import argparse
import os
import sys

import requests

SOURCE_URL = "https://www.ircc.canada.ca/opendata-donneesouvertes/data/EN_ODP-PR-Citz.xlsx"
DEFAULT_OUTPUT = os.path.join("data", "raw", "EN_ODP-PR-Citz.xlsx")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; hogavisa-pr-dashboard/1.0)"}
TIMEOUT = 60


def fetch(url, output_path):
    print(f"Fetching: {url}")
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(resp.content)

    print(f"Saved:    {output_path} ({len(resp.content):,} bytes)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=SOURCE_URL)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    try:
        fetch(args.url, args.output)
    except requests.RequestException as e:
        print(f"Fetch failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
