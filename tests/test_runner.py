#!/usr/bin/env python3
"""
Unit tests for UPA Benchmark Runner.

Run with: uv run pytest tests/test_runner.py -v
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmarks.suites.base import (
    TestCase,
    HybridTest,
    Complexity,
    TaskType,
    QualityMetric,
    BenchmarkResult,
    HybridResult,
    TestDetails,
    TestSuite,
    register_suite,
    get_registered_suites,
    get_suite,
)
from benchmarks.runner import extract_code_from_stderr


class TestTestCase:
    """Tests for TestCase dataclass."""

    def test_create_test_case(self):
        """Should create test case with required fields."""
        tc = TestCase(
            name="Test",
            query="计算 1+1",
            complexity=Complexity.SIMPLE,
        )
        assert tc.name == "Test"
        assert tc.query == "计算 1+1"
        assert tc.complexity == Complexity.SIMPLE
        assert tc.expect_contains is None
        assert tc.expect_pattern is None
        assert tc.expect_numeric is None

    def test_test_case_with_expectations(self):
        """Should create test case with expectations."""
        tc = TestCase(
            name="Math Test",
            query="计算 1+1",
            complexity=Complexity.SIMPLE,
            expect_numeric=(2, 0),
            description="Basic addition",
        )
        assert tc.expect_numeric == (2, 0)
        assert tc.description == "Basic addition"


class TestHybridTest:
    """Tests for HybridTest dataclass."""

    def test_create_hybrid_test(self):
        """Should create hybrid test with required fields."""
        ht = HybridTest(
            name="Translate Test",
            query="翻译 Hello 并计算字符数",
            task_type=TaskType.TRANSLATE_LOGIC,
            description="Translate and count",
        )
        assert ht.name == "Translate Test"
        assert ht.task_type == TaskType.TRANSLATE_LOGIC


class TestTestDetails:
    """Tests for TestDetails dataclass."""

    def test_create_test_details(self):
        """Should create test details with defaults."""
        details = TestDetails(
            suite_name="test",
            test_name="test",
            query="test query",
        )
        assert details.success == False
        assert details.security_violations == []
        assert details.timing_ms == {}

    def test_to_dict(self):
        """Should serialize to dict."""
        details = TestDetails(
            suite_name="test",
            test_name="test",
            query="test query",
            success=True,
            timing_ms={"LLM": 100.0},
        )
        d = details.to_dict()
        assert d["suite_name"] == "test"
        assert d["success"] == True
        assert d["timing_ms"]["LLM"] == 100.0


class TestExtractCodeFromStderr:
    """Tests for extract_code_from_stderr function."""

    def test_extract_simple_code(self):
        """Should extract code from stderr with code block."""
        stderr = """
Some output
```python
print("Hello")
```
More output
"""
        code = extract_code_from_stderr(stderr)
        assert code == 'print("Hello")'

    def test_extract_multiline_code(self):
        """Should extract multiline code."""
        stderr = '''
```python
x = 1
y = 2
print(x + y)
```
'''
        code = extract_code_from_stderr(stderr)
        assert "x = 1" in code
        assert "y = 2" in code
        assert "print(x + y)" in code

    def test_no_code_block(self):
        """Should return empty string if no code block."""
        stderr = "No code block here"
        code = extract_code_from_stderr(stderr)
        assert code == ""

    def test_empty_stderr(self):
        """Should return empty string for empty input."""
        code = extract_code_from_stderr("")
        assert code == ""


class TestSuiteRegistration:
    """Tests for suite registration."""

    def test_get_registered_suites(self):
        """Should return registered suites."""
        suites = get_registered_suites()
        assert isinstance(suites, dict)
        assert "core" in suites
        assert "semantic" in suites
        assert "classic" in suites
        assert "mmlu" in suites
        assert "planner" in suites

    def test_get_suite_by_name(self):
        """Should get suite by name."""
        suite = get_suite("core")
        assert suite is not None
        assert suite.name == "core"
        assert len(suite.cases) > 0

    def test_get_nonexistent_suite(self):
        """Should return None for nonexistent suite."""
        suite = get_suite("nonexistent")
        assert suite is None


class TestComplexityEnum:
    """Tests for Complexity enum."""

    def test_complexity_values(self):
        """Should have expected complexity values."""
        assert Complexity.SIMPLE.value == "简单"
        assert Complexity.MEDIUM.value == "中等"
        assert Complexity.COMPLEX.value == "复杂"
        assert Complexity.EDGE_CASE.value == "边缘案例"


class TestTaskTypeEnum:
    """Tests for TaskType enum."""

    def test_task_type_values(self):
        """Should have expected task type values."""
        assert TaskType.TRANSLATE_LOGIC.value == "翻译+逻辑"
        assert TaskType.SUMMARIZE_ANALYZE.value == "总结+分析"
        assert TaskType.SENTIMENT_CALC.value == "情感+计算"
        assert TaskType.EXTRACT_PROCESS.value == "提取+处理"
        assert TaskType.RECURSIVE.value == "递归调用"


class TestQualityMetricEnum:
    """Tests for QualityMetric enum."""

    def test_metric_values(self):
        """Should have expected quality metric values."""
        assert QualityMetric.CODE_OUTPUT.value == "代码输出"
        assert QualityMetric.CORRECT_RESULT.value == "结果正确"
        assert QualityMetric.NO_EXTRA_TEXT.value == "无额外文本"
        assert QualityMetric.SECURITY_PASS.value == "安全通过"
        assert QualityMetric.EXECUTION_OK.value == "执行成功"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])