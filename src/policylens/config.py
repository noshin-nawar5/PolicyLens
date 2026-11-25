"""Loads the standards registry and the parsed requirement files.

All paths are relative to the current working directory, so run every
command from the repository root.
"""
import json
from pathlib import Path

import yaml

CONFIG_PATH = Path("config/standards.yaml")


def load_standards(path=CONFIG_PATH):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)["standards"]


def get_standard(standard_id, path=CONFIG_PATH):
    for std in load_standards(path):
        if std["id"] == standard_id:
            return std
    known = ", ".join(s["id"] for s in load_standards(path))
    raise KeyError(f"Unknown standard '{standard_id}'. Known: {known}")


def load_requirements(standard_id):
    std = get_standard(standard_id)
    out = Path(std["output"])
    if not out.exists():
        raise FileNotFoundError(
            f"{out} not found. Run: policylens ingest {standard_id}"
        )
    with open(out, encoding="utf-8") as f:
        return json.load(f)
