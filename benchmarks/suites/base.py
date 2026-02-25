"""
Base data structures for benchmark test suites.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Complexity(Enum):
    """Test complexity levels."""
    SIMPLE = "简单"
    MEDIUM = "中等"
    COMPLEX = "复杂"
    EDGE_CASE = "边缘案例"


class TaskType(Enum):
    """Semantic-Logic hybrid task types."""
    TRANSLATE_LOGIC = "翻译+逻辑"
    SUMMARIZE_ANALYZE = "总结+分析"
    SENTIMENT_CALC = "情感+计算"
    EXTRACT_PROCESS = "提取+处理"
    RECURSIVE = "递归调用"


class QualityMetric(Enum):
    """Quality evaluation metrics."""
    CODE_OUTPUT = "代码输出"
    CORRECT_RESULT = "结果正确"
    NO_EXTRA_TEXT = "无额外文本"
    SECURITY_PASS = "安全通过"
    EXECUTION_OK = "执行成功"


@dataclass
class TestCase:
    """Base test case definition."""
    name: str
    query: str
    complexity: Complexity
    expect_contains: str | None = None
    expect_pattern: str | None = None
    expect_numeric: tuple[float, float] | None = None
    description: str = ""


@dataclass
class HybridTest:
    """Semantic-Logic hybrid test case."""
    name: str
    query: str
    task_type: TaskType
    description: str
    expected_contains: str | None = None
    expected_pattern: str | None = None
    expected_numeric: tuple[float, float] | None = None


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""
    query: str
    success: bool
    output: str
    timing: dict[str, float]
    code_extracted: bool = False
    code_content: str = ""
    security_violations: list[str] = field(default_factory=list)
    execution_error: str = ""


@dataclass
class HybridResult:
    """Result of a hybrid test."""
    test: HybridTest
    success: bool
    output: str
    duration: float
    sub_agent_calls: int = 0
    execution_error: str = ""


@dataclass
class TestSuite:
    """A collection of test cases with metadata."""
    name: str
    description: str
    version: str
    cases: list[TestCase] | list[HybridTest]

    def __len__(self) -> int:
        return len(self.cases)

    def __iter__(self):
        return iter(self.cases)


def register_suite(suite_factory):
    """Decorator to register a test suite. Works with functions that return TestSuite."""
    import benchmarks.suites as suites_module
    if not hasattr(suites_module, "_registered_suites"):
        suites_module._registered_suites = {}
    # Call the function to get the actual TestSuite
    actual_suite = suite_factory()
    suites_module._registered_suites[actual_suite.name] = actual_suite
    return suite_factory


def get_registered_suites() -> dict[str, TestSuite]:
    """Get all registered test suites."""
    import benchmarks.suites as suites_module
    # Ensure all suite modules are imported
    from benchmarks.suites import core_upa, semantic
    return getattr(suites_module, "_registered_suites", {})


def get_suite(name: str) -> TestSuite | None:
    """Get a specific test suite by name."""
    return get_registered_suites().get(name)
