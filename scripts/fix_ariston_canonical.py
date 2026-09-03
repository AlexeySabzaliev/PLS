#!/usr/bin/env python3
"""Обёртка: flask pls fix-ariston-canonical [--dry-run] [--no-ds5]."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    args = ["flask", "pls", "fix-ariston-canonical", *sys.argv[1:]]
    return subprocess.call(args, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
