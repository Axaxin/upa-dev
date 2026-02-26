"""
Test Suite Definitions
"""

from .base import (
    TestCase,
    HybridTest,
    TestSuite,
    Complexity,
    TaskType,
    QualityMetric,
    BenchmarkResult,
    HybridResult,
    register_suite,
    get_registered_suites,
    get_suite,
)

# Import suites to register them
from . import core_upa
from . import semantic
from . import classic
from . import mmlu
from . import planner

__all__ = [
    "TestCase",
    "HybridTest",
    "TestSuite",
    "Complexity",
    "TaskType",
    "QualityMetric",
    "BenchmarkResult",
    "HybridResult",
    "register_suite",
    "get_registered_suites",
    "get_suite",
]
