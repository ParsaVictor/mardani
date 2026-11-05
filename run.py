#!/usr/bin/env python3
"""Run ReachDesk from a checkout, no install needed: python run.py serve"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

if __name__ == "__main__":
    if sys.argv[1:2] == ["test"]:
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), top_level_dir=str(ROOT))
        sys.path.insert(0, str(ROOT))
        result = unittest.TextTestRunner(verbosity=1).run(suite)
        raise SystemExit(0 if result.wasSuccessful() else 1)
    from reachdesk.cli import main

    raise SystemExit(main())
