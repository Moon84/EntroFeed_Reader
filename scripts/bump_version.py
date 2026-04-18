#!/usr/bin/env python3
"""Synchronize version from pyproject.toml to frontend/package.json."""

import json
import sys
from pathlib import Path


def sync_version():
    root = Path(__file__).parent.parent

    pyproject_path = root / "pyproject.toml"
    package_path = root / "frontend" / "package.json"

    with open(pyproject_path, "rb") as f:
        import tomllib

        version = tomllib.load(f)["project"]["version"]

    with open(package_path) as f:
        pkg = json.load(f)

    if pkg.get("version") == version:
        print(f"Version {version} already in sync")
        return

    pkg["version"] = version
    with open(package_path, "w") as f:
        json.dump(pkg, f, indent=2)

    print(f"Synced version to {version}")


if __name__ == "__main__":
    sync_version()
