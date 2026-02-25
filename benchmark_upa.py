#!/usr/bin/env python3
"""
UPA Performance Benchmark Suite
Tests quality, timing, and code output strictness.
"""

import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from statistics import mean, median, stdev
from typing import Any


class Complexity(Enum):
    """Test complexity level."""
    SIMPLE = "简单"
    MEDIUM = "中等"
    COMPLEX = "复杂"
    EDGE_CASE = "边缘案例"


class QualityMetric(Enum):
    """Quality evaluation metrics."""
    CODE_OUTPUT = "代码输出"
    CORRECT_RESULT = "结果正确"
    NO_EXTRA_TEXT = "无额外文本"
    SECURITY_PASS = "安全通过"
    EXECUTION_OK = "执行成功"


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""
    query: str
    success: bool
    output: str
    timing: dict[str, float]
    code_extracted: bool
    code_content: str = ""
    security_violations: list[str] = field(default_factory=list)
    execution_error: str = ""


@dataclass
class TestCase:
    """Benchmark test case definition."""
    name: str
    query: str
    complexity: Complexity
    expect_contains: str | None = None
    expect_pattern: str | None = None
    expect_numeric: tuple[float, float] | None = None
    description: str = ""


# =============================================================================
# Test Cases
# =============================================================================

BENCHMARK_CASES: list[TestCase] = [
    # ---- Simple Tests ----
    TestCase("基础问候", "你好，请简单介绍一下你自己", Complexity.SIMPLE),
    TestCase("整数加法", "计算 123 + 456", Complexity.SIMPLE, expect_numeric=(579, 0)),
    TestCase("整数乘法", "计算 25 乘以 4", Complexity.SIMPLE, expect_numeric=(100, 0)),
    TestCase("浮点除法", "计算 22 除以 7，保留4位小数", Complexity.SIMPLE, expect_numeric=(3.1428, 0.001)),
    TestCase("幂运算", "计算 2 的 10 次方", Complexity.SIMPLE, expect_numeric=(1024, 0)),

    # ---- Medium Tests ----
    TestCase("列表排序", "将列表 [5, 2, 8, 1, 9, 3] 排序并输出", Complexity.MEDIUM, expect_pattern=r"\[1,\s*2,\s*3,\s*5,\s*8,\s*9\]"),
    TestCase("列表去重", "去除 [1, 2, 2, 3, 3, 3, 4] 中的重复元素", Complexity.MEDIUM, expect_pattern=r"\[1,\s*2,\s*3,\s*4\]"),
    TestCase("字符串反转", "反转字符串 'Hello World'", Complexity.MEDIUM, expect_contains="dlroW olleH"),
    TestCase("素数判断", "判断 97 是否是素数", Complexity.MEDIUM, expect_contains="是"),
    TestCase("斐波那契", "计算斐波那契数列的第15个数", Complexity.MEDIUM, expect_numeric=(610, 0)),
    TestCase("阶乘计算", "计算 10 的阶乘", Complexity.MEDIUM, expect_numeric=(3628800, 0)),
    TestCase("日期计算", "计算从今天开始30天后的日期", Complexity.MEDIUM),
    TestCase("星期计算", "计算2024年1月1日是星期几", Complexity.MEDIUM, expect_contains="一"),

    # ---- Complex Tests ----
    TestCase("统计词频", "统计 'the quick brown fox jumps over the lazy dog' 中the的出现次数", Complexity.COMPLEX, expect_numeric=(2, 0)),
    TestCase("JSON解析", "从JSON {\"users\":[{\"name\":\"Alice\"},{\"name\":\"Bob\"}]} 中提取所有用户名", Complexity.COMPLEX, expect_contains="Alice"),
    TestCase("正则提取", "从 '电话13812345678' 中提取手机号", Complexity.COMPLEX, expect_contains="13812345678"),
    TestCase("数学序列", "找出1到100中能被3整除但不能被5整除的数的个数", Complexity.COMPLEX, expect_numeric=(27, 0)),
    TestCase("字符串处理", "将 'hello_world_example' 转换为驼峰命名", Complexity.COMPLEX, expect_contains="helloWorldExample"),
    TestCase("数组交集", "找出 [1,2,3,4,5] 和 [4,5,6,7,8] 的交集", Complexity.COMPLEX, expect_pattern=r"\[4,\s*5\]"),
    TestCase("统计计算", "计算列表 [1,2,3,4,5,6,7,8,9,10] 的平均值", Complexity.COMPLEX, expect_numeric=(5.5, 0.1)),

    # ---- Edge Cases ----
    TestCase("大数计算", "计算 999999 * 999999", Complexity.EDGE_CASE, expect_numeric=(999998000001, 0)),
    TestCase("负数运算", "计算 -5 * -3 + -10", Complexity.EDGE_CASE, expect_numeric=(5, 0)),
    TestCase("边界值", "判断0是正数还是负数还是零", Complexity.EDGE_CASE, expect_contains="零"),
    TestCase("中文数字", "将中文数字 '三百五十六' 转换为阿拉伯数字", Complexity.EDGE_CASE, expect_numeric=(356, 0)),
    TestCase("Emoji统计", "统计字符串 '🎉🎊🎁' 中emoji的数量", Complexity.EDGE_CASE, expect_numeric=(3, 0)),
]


def run_upa_with_timing(query: str) -> BenchmarkResult:
    """Run UPA and collect timing metrics."""
    cmd = ["uv", "run", "python", "upa.py", "--timing", query]

    start_time = time.perf_counter()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        total_time = (time.perf_counter() - start_time) * 1000

        stdout = result.stdout
        stderr = result.stderr

        timing = parse_timing_report(stderr)
        timing["total"] = total_time

        code_extracted = "Thinking..." in stderr
        violations = re.findall(r"- (Blocked .+)", stderr) if "Security violations" in stderr else []

        exec_error = ""
        if "Execution Error:" in stderr:
            match = re.search(r"Execution Error:\n(.+)", stderr, re.DOTALL)
            if match:
                exec_error = match.group(1).strip()[:100]

        return BenchmarkResult(
            query=query,
            success=result.returncode == 0,
            output=stdout,
            timing=timing,
            code_extracted=code_extracted,
            security_violations=violations,
            execution_error=exec_error,
        )
    except subprocess.TimeoutExpired:
        return BenchmarkResult(query=query, success=False, output="", timing={"total": 120000}, code_extracted=False, execution_error="Timeout")
    except Exception as e:
        return BenchmarkResult(query=query, success=False, output="", timing={}, code_extracted=False, execution_error=str(e))


def parse_timing_report(stderr: str) -> dict[str, float]:
    """Parse timing report from stderr."""
    timing = {}
    # Remove ANSI color codes
    clean = re.sub(r'\033\[[0-9;]+m', '', stderr)
    # Match timing lines like "  LLM Generate     1234.5ms"
    pattern = r"^\s*(\w[\w\s]+?)\s+(\d+\.?\d*)ms"
    for match in re.finditer(pattern, clean, re.MULTILINE):
        timing[match.group(1).strip()] = float(match.group(2))
    return timing


def evaluate_quality(test: TestCase, result: BenchmarkResult) -> dict[QualityMetric, bool]:
    """Evaluate quality metrics."""
    metrics = {
        QualityMetric.CODE_OUTPUT: result.code_extracted,
        QualityMetric.SECURITY_PASS: len(result.security_violations) == 0,
        QualityMetric.EXECUTION_OK: result.success and not result.execution_error,
    }

    if not result.success:
        metrics[QualityMetric.CORRECT_RESULT] = False
    elif test.expect_contains:
        metrics[QualityMetric.CORRECT_RESULT] = test.expect_contains in result.output
    elif test.expect_pattern:
        metrics[QualityMetric.CORRECT_RESULT] = bool(re.search(test.expect_pattern, result.output))
    elif test.expect_numeric:
        expected, tolerance = test.expect_numeric
        numbers = re.findall(r"[-+]?\d*\.?\d+", result.output)
        if numbers:
            try:
                actual = float(numbers[0])
                metrics[QualityMetric.CORRECT_RESULT] = abs(actual - expected) <= tolerance
            except ValueError:
                metrics[QualityMetric.CORRECT_RESULT] = False
        else:
            metrics[QualityMetric.CORRECT_RESULT] = False
    else:
        metrics[QualityMetric.CORRECT_RESULT] = result.success

    metrics[QualityMetric.NO_EXTRA_TEXT] = len(result.output) < 500 or result.success

    return metrics


def print_report(results: list[tuple[TestCase, BenchmarkResult, dict[QualityMetric, bool]]]):
    """Print benchmark report."""
    print("\n" + "═" * 70)
    print("  UPA Performance Benchmark Report")
    print("═" * 70)

    total = len(results)
    passed = sum(1 for _, _, m in results if m.get(QualityMetric.CORRECT_RESULT))
    code_ok = sum(1 for _, _, m in results if m.get(QualityMetric.CODE_OUTPUT))
    exec_ok = sum(1 for _, _, m in results if m.get(QualityMetric.EXECUTION_OK))

    llm_times = [r.timing.get("LLM Generate", 0) for _, r, _ in results if r.timing]

    print(f"\n📊 Overall Statistics")
    print("─" * 50)
    print(f"  Tests Run:       {total}")
    print(f"  Correct Results: {passed}/{total} ({passed/total*100:.1f}%)")
    print(f"  Code Generated:  {code_ok}/{total} ({code_ok/total*100:.1f}%)")
    print(f"  Execution OK:    {exec_ok}/{total} ({exec_ok/total*100:.1f}%)")

    if llm_times:
        print(f"\n⏱  LLM Timing (ms)")
        print("─" * 50)
        print(f"  Mean:   {mean(llm_times):.1f}")
        print(f"  Median: {median(llm_times):.1f}")
        print(f"  Min:    {min(llm_times):.1f}")
        print(f"  Max:    {max(llm_times):.1f}")

    # By complexity
    print(f"\n📈 Results by Complexity")
    print("─" * 50)
    by_comp: dict[Complexity, list] = {c: [] for c in Complexity}
    for test, result, metrics in results:
        by_comp[test.complexity].append((test, result, metrics))

    for comp in Complexity:
        tests = by_comp[comp]
        if not tests:
            continue
        p = sum(1 for _, _, m in tests if m.get(QualityMetric.CORRECT_RESULT))
        t = len(tests)
        pct = (p / t * 100) if t > 0 else 0
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        avg = mean([r.timing.get("total", 0) for _, r, _ in tests]) if tests else 0
        print(f"  {comp.value:6} [{bar}] {p:>2}/{t:<2} ({pct:>5.1f}%)  avg: {avg:>6.0f}ms")

    # Quality metrics
    print(f"\n🎯 Quality Metrics")
    print("─" * 50)
    for metric in QualityMetric:
        p = sum(1 for _, _, m in results if m.get(metric))
        pct = (p / total * 100) if total > 0 else 0
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"  {metric.value:10} [{bar}] {p:>2}/{total:<2} ({pct:>5.1f}%)")

    # Detail table
    print(f"\n📋 Detailed Results")
    print("─" * 70)
    print(f"  {'Test':<16} {'Comp':<6} {'Time':>8} {'Result':<8} {'Quality'}")
    print("─" * 70)

    for test, result, metrics in results:
        time_str = f"{result.timing.get('total', 0):.0f}ms"
        status = "✅" if metrics.get(QualityMetric.CORRECT_RESULT) else "❌"
        q_score = sum(1 for v in metrics.values() if v)
        print(f"  {test.name:<16} {test.complexity.value:<6} {time_str:>8} {status}     {q_score}/{len(metrics)}")
        if result.execution_error:
            print(f"    └─ ⚠️  {result.execution_error[:50]}")

    print("═" * 70)


def run_benchmark(filter_complexity: Complexity | None = None, limit: int | None = None):
    """Run benchmark suite."""
    tests = BENCHMARK_CASES
    if filter_complexity:
        tests = [t for t in tests if t.complexity == filter_complexity]
    if limit:
        tests = tests[:limit]

    print(f"Running {len(tests)} benchmark tests...\n")

    results = []
    for i, test in enumerate(tests, 1):
        print(f"[{i}/{len(tests)}] {test.name}...", end=" ", flush=True)
        result = run_upa_with_timing(test.query)
        metrics = evaluate_quality(test, result)
        results.append((test, result, metrics))

        status = "✅" if metrics.get(QualityMetric.CORRECT_RESULT) else "❌"
        print(f"{status} ({result.timing.get('total', 0):.0f}ms)")

    print_report(results)
    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="UPA Performance Benchmark")
    parser.add_argument("--complexity", "-c", choices=[c.value for c in Complexity], help="Filter by complexity")
    parser.add_argument("--limit", "-n", type=int, help="Limit number of tests")
    parser.add_argument("--list", "-l", action="store_true", help="List test cases")
    parser.add_argument("--json", "-j", type=str, help="Export results to JSON")

    args = parser.parse_args()

    if args.list:
        for test in BENCHMARK_CASES:
            print(f"[{test.complexity.value}] {test.name}: {test.query}")
        return

    filter_comp = Complexity(args.complexity) if args.complexity else None
    results = run_benchmark(filter_comp, args.limit)

    if args.json:
        data = [{
            "test": t.name, "query": t.query, "complexity": t.complexity.value,
            "success": r.success, "timing": r.timing,
            "quality": {m.value: v for m, v in m.items()}
        } for t, r, m in results]
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\nExported to {args.json}")


if __name__ == "__main__":
    main()
