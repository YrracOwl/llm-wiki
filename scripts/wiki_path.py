#!/usr/bin/env python3
"""Unified wiki path resolution. Imported by wiki_op.py and all wiki_op_*.py modules.

Resolution order:
  1. --wiki-path CLI flag (if passed)
  2. WIKI_PATH environment variable
  3. ~/wiki default
"""

import os
import argparse


def resolve_wiki_path(cli_path=None):
    if cli_path:
        return os.path.expanduser(cli_path)
    return os.path.expanduser(os.environ.get("WIKI_PATH", "~/wiki"))


def add_wiki_path_argument(parser: argparse.ArgumentParser):
    parser.add_argument(
        "--wiki-path", default=None,
        help="Path to wiki directory (default: $WIKI_PATH or ~/wiki)",
    )
