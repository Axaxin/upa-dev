"""
Example: Creating a Custom Test Suite

This demonstrates how to create your own benchmark test suite.
"""

from benchmarks.suites.base import (
    TestCase, TestSuite, Complexity, register_suite
)


# =============================================================================
# Step 1: Define your test cases
# =============================================================================

CUSTOM_CASES: list[TestCase] = [
    TestCase(
        "自定义示例1",
        "你的查询文本",
        Complexity.SIMPLE,
        expect_numeric=(42, 0)  # 期望数值42，容差0
    ),
    TestCase(
        "自定义示例2",
        "另一个查询",
        Complexity.MEDIUM,
        expect_contains="期望的结果文本"  # 期望输出包含此文本
    ),
    # Add more test cases as needed
]


# =============================================================================
# Step 2: Register your suite with @register_suite decorator
# =============================================================================

@register_suite
def _my_custom_suite() -> TestSuite:
    """Register my custom test suite."""
    return TestSuite(
        name="custom",          # Suite name used in CLI
        description="My custom benchmark tests",
        version="1.0.0",
        cases=CUSTOM_CASES,
    )


# =============================================================================
# Step 3: Run your tests
# =============================================================================
#
# From command line:
#   python -m benchmarks custom
#
# Or programmatically:
#   from benchmarks.runner import run_core_benchmark
#   from benchmarks.examples.custom_suite import CUSTOM_CASES
#   results = run_core_benchmark(cases=CUSTOM_CASES)
#


# =============================================================================
# Creating Semantic-Logic Hybrid Suites
# =============================================================================

# For hybrid tests (using sub-agent), use HybridTest instead:

from benchmarks.suites.base import HybridTest, TaskType

HYBRID_CUSTOM_CASES: list[HybridTest] = [
    HybridTest(
        "混合示例",
        "用 ask_sub_agent 翻译 'Hello' 成中文，然后打印",
        TaskType.TRANSLATE_LOGIC,
        "Translation example",
        expected_contains="你好"
    ),
]

# Note: Hybrid suites need custom runner logic since they use HybridTest
# See cli.py for how to handle different test types
