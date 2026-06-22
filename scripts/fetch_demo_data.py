#!/usr/bin/env python3
"""Fetch + checksum-verify a vendored demo/repro dataset from its manifest.

Opt-in (network). Thin CLI over ``veritas.demos`` -- all logic (and its tests) live
in the package; this only wires argparse to it.

    python scripts/fetch_demo_data.py demos/proteingym_dms/manifest.toml /tmp/proteingym
"""

from __future__ import annotations

import argparse
from pathlib import Path

from veritas.demos.fetch import fetch_dataset
from veritas.demos.manifest import load_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch and checksum-verify a demo dataset slice.")
    parser.add_argument("manifest", type=Path, help="path to demos/<domain>/manifest.toml")
    parser.add_argument("dest", type=Path, help="destination root for the dataset")
    args = parser.parse_args()
    root = fetch_dataset(load_manifest(args.manifest), args.dest)
    print(root)


if __name__ == "__main__":
    main()
