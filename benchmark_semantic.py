#!/usr/bin/env python3
"""
DEPRECATED: UPA Semantic-Logic Hybrid Benchmark Suite

This file is deprecated. Use the unified benchmark framework instead:

    uv run python -m benchmarks semantic

For more options, see benchmarks/cli.py
"""

import sys
import warnings

warnings.warn(
    "benchmark_semantic.py is deprecated. Use 'uv run python -m benchmarks semantic' instead.",
    DeprecationWarning,
    stacklevel=2
)

print("DEPRECATED: benchmark_semantic.py is deprecated.", file=sys.stderr)
print("Use 'uv run python -m benchmarks semantic' instead.", file=sys.stderr)
print("Redirecting to unified benchmark framework...", file=sys.stderr)
print()

# Redirect to unified benchmark framework
from benchmarks.cli import main

if __name__ == "__main__":
    sys.argv = [sys.argv[0], "semantic"] + sys.argv[1:]
    main()
