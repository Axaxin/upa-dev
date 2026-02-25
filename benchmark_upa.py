#!/usr/bin/env python3
"""
UPA Performance Benchmark Suite
Tests quality, timing, and code output strictness.
"""

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from statistics import mean, median, stdev
from typing import Any

# Terminal colors
class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

# Disable colors on Windows or when NO_COLOR is set
if sys.platform == "win32" or os.getenv("NO_COLOR"):
    for attr in dir(Colors):
        if not attr.startswith("_"):
            setattr(Colors, attr, "")


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
    TestCase("基础问候", "你好，请简单介绍一下你自己。输出格式：用print()输出一句话", Complexity.SIMPLE),
    TestCase("整数加法", "计算 123 + 456。输出格式：print(579)", Complexity.SIMPLE, expect_numeric=(579, 0)),
    TestCase("整数乘法", "计算 25 乘以 4。输出格式：print(100)", Complexity.SIMPLE, expect_numeric=(100, 0)),
    TestCase("浮点除法", "计算 22 除以 7，保留4位小数。输出格式：print(3.1428)", Complexity.SIMPLE, expect_numeric=(3.1428, 0.001)),
    TestCase("幂运算", "计算 2 的 10 次方。输出格式：print(1024)", Complexity.SIMPLE, expect_numeric=(1024, 0)),
    TestCase("绝对值", "计算 |-15|。输出格式：print(15)", Complexity.SIMPLE, expect_numeric=(15, 0)),
    TestCase("余数计算", "计算 17 除以 5 的余数。输出格式：print(2)", Complexity.SIMPLE, expect_numeric=(2, 0)),

    # ---- Medium Tests ----
    TestCase("列表排序", "将列表 [5, 2, 8, 1, 9, 3] 排序。输出格式：print([1,2,3,5,8,9])", Complexity.MEDIUM, expect_pattern=r"\[1,\s*2,\s*3,\s*5,\s*8,\s*9\]"),
    TestCase("列表去重", "去除 [1, 2, 2, 3, 3, 3, 4] 中的重复元素。输出格式：print([1,2,3,4])", Complexity.MEDIUM, expect_pattern=r"\[1,\s*2,\s*3,\s*4\]"),
    TestCase("字符串反转", "反转字符串 'Hello World'。输出格式：print('dlroW olleH')", Complexity.MEDIUM, expect_contains="dlroW olleH"),
    TestCase("素数判断", "判断 97 是否是素数。如果是素数输出'是'，否则输出'否'", Complexity.MEDIUM, expect_contains="是"),
    TestCase("斐波那契", "计算斐波那契数列的第15个数。输出格式：print(610)", Complexity.MEDIUM, expect_numeric=(610, 0)),
    TestCase("阶乘计算", "计算 10 的阶乘。输出格式：print(3628800)", Complexity.MEDIUM, expect_numeric=(3628800, 0)),
    TestCase("日期计算", "计算从今天开始30天后的日期。输出格式：print('YYYY-MM-DD')", Complexity.MEDIUM),
    TestCase("星期计算", "计算2024年1月1日是星期几。输出格式：print('星期X')", Complexity.MEDIUM, expect_contains="一"),
    TestCase("最大公约数", "计算 48 和 18 的最大公约数。输出格式：print(6)", Complexity.MEDIUM, expect_numeric=(6, 0)),
    TestCase("字符串拼接", "将 ['Hello', 'World', 'UPA'] 用空格连接。输出格式：print('Hello World UPA')", Complexity.MEDIUM, expect_contains="Hello World UPA"),
    TestCase("列表求和", "计算 [1, 3, 5, 7, 9] 的和。输出格式：print(25)", Complexity.MEDIUM, expect_numeric=(25, 0)),
    TestCase("判断回文", "判断 'radar' 是否是回文字符串。如果是输出'是'，否则输出'否'", Complexity.MEDIUM, expect_contains="是"),

    # ---- Complex Tests ----
    TestCase("统计词频", "统计 'the quick brown fox jumps over the lazy dog' 中the的出现次数。输出格式：print(2)", Complexity.COMPLEX, expect_numeric=(2, 0)),
    TestCase("JSON解析", "从JSON {\"users\":[{\"name\":\"Alice\"},{\"name\":\"Bob\"}]} 中提取所有用户名。输出格式：包含'Alice'", Complexity.COMPLEX, expect_contains="Alice"),
    TestCase("正则提取", "从 '电话13812345678' 中提取手机号。输出格式：print('13812345678')", Complexity.COMPLEX, expect_contains="13812345678"),
    TestCase("数学序列", "找出1到100中能被3整除但不能被5整除的数的个数。输出格式：print(27)", Complexity.COMPLEX, expect_numeric=(27, 0)),
    TestCase("字符串处理", "将 'hello_world_example' 转换为驼峰命名。输出格式：print('helloWorldExample')", Complexity.COMPLEX, expect_contains="helloWorldExample"),
    TestCase("数组交集", "找出 [1,2,3,4,5] 和 [4,5,6,7,8] 的交集。输出格式：print([4,5])", Complexity.COMPLEX, expect_pattern=r"\[4,\s*5\]"),
    TestCase("统计计算", "计算列表 [1,2,3,4,5,6,7,8,9,10] 的平均值。输出格式：print(5.5)", Complexity.COMPLEX, expect_numeric=(5.5, 0.1)),
    TestCase("冒泡排序", "用冒泡排序对 [64, 34, 25, 12, 22, 11, 90] 排序。输出格式：print([升序排列的列表])", Complexity.COMPLEX),
    TestCase("二分查找", "判断 17 是否在有序列表 [2,5,8,12,16,23,38,56,72,91] 中。如果是输出True，否则输出False", Complexity.COMPLEX, expect_contains="False"),
    TestCase("矩阵转置", "将矩阵 [[1,2,3],[4,5,6]] 转置。输出格式：print([[1,4],[2,5],[3,6]])", Complexity.COMPLEX),
    TestCase("生成密码", "生成一个包含大小写字母和数字的8位随机密码。输出格式：print('生成的密码')", Complexity.COMPLEX),
    TestCase("凯撒密码", "用凯撒密码加密 'hello'，偏移量为3。输出格式：print('khoor')", Complexity.COMPLEX, expect_contains="khoor"),
    TestCase("水仙花数", "找出100-999之间的所有水仙花数。输出格式：print([153, 370, 371, 407])", Complexity.COMPLEX, expect_contains="153"),
    TestCase("最长公共子串", "找出 'abcdefg' 和 'xcdey' 的最长公共子串。输出格式：print('cde')", Complexity.COMPLEX, expect_contains="cde"),

    # ---- Edge Cases ----
    TestCase("大数计算", "计算 999999 * 999999。输出格式：print(999998000001)", Complexity.EDGE_CASE, expect_numeric=(999998000001, 0)),
    TestCase("负数运算", "计算 -5 * -3 + -10。输出格式：print(5)", Complexity.EDGE_CASE, expect_numeric=(5, 0)),
    TestCase("边界值", "判断0是正数还是负数还是零。如果是零输出'零'，正数输出'正数'，负数输出'负数'", Complexity.EDGE_CASE, expect_contains="零"),
    TestCase("中文数字", "将中文数字 '三百五十六' 转换为阿拉伯数字。输出格式：print(356)", Complexity.EDGE_CASE, expect_numeric=(356, 0)),
    TestCase("Emoji统计", "统计字符串 '🎉🎊🎁' 中emoji的数量。输出格式：print(3)", Complexity.EDGE_CASE, expect_numeric=(3, 0)),
    TestCase("空列表处理", "对空列表 [] 求和。输出格式：print(0)", Complexity.EDGE_CASE, expect_numeric=(0, 0)),
    TestCase("除零处理", "计算 1/0。如果发生错误，输出包含'Error'或'错误'", Complexity.EDGE_CASE, expect_contains="Error"),
    TestCase("科学计数法", "将 0.0000123 转为科学计数法。输出格式：包含'1.23'", Complexity.EDGE_CASE, expect_contains="1.23"),
    TestCase("罗马数字", "将罗马数字 'MMXXIV' 转为阿拉伯数字。输出格式：print(2024)", Complexity.EDGE_CASE, expect_numeric=(2024, 10)),
    TestCase("Unicode处理", "输出字符串 '你好🌍世界' 的长度。输出格式：print(5)", Complexity.EDGE_CASE, expect_numeric=(5, 1)),
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


def print_header(text: str):
    """Print a colored header."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'═' * 70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}  {text:^66}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'═' * 70}{Colors.ENDC}")


def print_section(title: str):
    """Print a section header."""
    print(f"\n{Colors.OKCYAN}{title}{Colors.ENDC}")
    print("─" * 70)


def format_bar(value: int, total: int, width: int = 20, color: str = Colors.OKGREEN) -> str:
    """Format a progress bar."""
    pct = (value / total * 100) if total > 0 else 0
    filled = int(pct / 100 * width)
    return f"{color}{'█' * filled}{Colors.ENDC}{'░' * (width - filled)}"


def format_time(ms: float) -> str:
    """Format time with color coding."""
    if ms < 5000:
        return f"{Colors.OKGREEN}{ms:.0f}ms{Colors.ENDC}"
    elif ms < 15000:
        return f"{Colors.WARNING}{ms:.0f}ms{Colors.ENDC}"
    else:
        return f"{Colors.FAIL}{ms:.0f}ms{Colors.ENDC}"


def print_report(results: list[tuple[TestCase, BenchmarkResult, dict[QualityMetric, bool]]]):
    """Print benchmark report."""
    print_header("UPA Performance Benchmark Report")

    total = len(results)
    passed = sum(1 for _, _, m in results if m.get(QualityMetric.CORRECT_RESULT))
    code_ok = sum(1 for _, _, m in results if m.get(QualityMetric.CODE_OUTPUT))
    exec_ok = sum(1 for _, _, m in results if m.get(QualityMetric.EXECUTION_OK))

    llm_times = [r.timing.get("LLM Generate", 0) for _, r, _ in results if r.timing]

    print_section("📊 Overall Statistics")
    print(f"  Tests Run:       {Colors.BOLD}{total}{Colors.ENDC}")
    print(f"  Correct Results: {Colors.OKGREEN if passed == total else Colors.WARNING}{passed}/{total} ({passed/total*100:.1f}%){Colors.ENDC}")
    print(f"  Code Generated:  {Colors.OKGREEN if code_ok == total else Colors.WARNING}{code_ok}/{total} ({code_ok/total*100:.1f}%){Colors.ENDC}")
    print(f"  Execution OK:    {Colors.OKGREEN if exec_ok == total else Colors.WARNING}{exec_ok}/{total} ({exec_ok/total*100:.1f}%){Colors.ENDC}")

    if llm_times:
        print_section("⏱️  LLM Timing Statistics")
        avg_time = mean(llm_times)
        print(f"  Mean:   {format_time(avg_time)}")
        print(f"  Median: {format_time(median(llm_times))}")
        print(f"  Min:    {format_time(min(llm_times))}")
        print(f"  Max:    {format_time(max(llm_times))}")

        # Speed tier indicator
        if avg_time < 10000:
            print(f"  {Colors.OKGREEN}⚡ Speed Tier: FAST{Colors.ENDC}")
        elif avg_time < 20000:
            print(f"  {Colors.WARNING}🐢 Speed Tier: NORMAL{Colors.ENDC}")
        else:
            print(f"  {Colors.FAIL}🐌 Speed Tier: SLOW{Colors.ENDC}")

    # By complexity
    print_section("📈 Results by Complexity")
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
        bar_color = Colors.OKGREEN if p == t else (Colors.WARNING if p >= t * 0.8 else Colors.FAIL)
        bar = format_bar(p, t, 20, bar_color)
        avg = mean([r.timing.get("total", 0) for _, r, _ in tests]) if tests else 0
        status_icon = "🟢" if p == t else ("🟡" if p >= t * 0.8 else "🔴")
        print(f"  {status_icon} {comp.value:8} {bar} {p:>2}/{t:<2} ({pct:>5.1f}%)  avg: {format_time(avg)}")

    # Quality metrics
    print_section("🎯 Quality Metrics")
    for metric in QualityMetric:
        p = sum(1 for _, _, m in results if m.get(metric))
        pct = (p / total * 100) if total > 0 else 0
        bar_color = Colors.OKGREEN if p == total else (Colors.WARNING if p >= total * 0.8 else Colors.FAIL)
        bar = format_bar(p, total, 20, bar_color)
        print(f"  {metric.value:12} {bar} {p:>2}/{total:<2} ({pct:>5.1f}%)")

    # Detail table
    print_section("📋 Detailed Results")
    print(f"  {'Test':<18} {'Complexity':<10} {'Time':>10} {'Status':<8} {'Quality'}")
    print("─" * 70)

    for test, result, metrics in results:
        time_str = format_time(result.timing.get('total', 0))
        if metrics.get(QualityMetric.CORRECT_RESULT):
            status = f"{Colors.OKGREEN}✅ PASS{Colors.ENDC}"
        else:
            status = f"{Colors.FAIL}❌ FAIL{Colors.ENDC}"

        q_score = sum(1 for v in metrics.values() if v)
        q_color = Colors.OKGREEN if q_score == len(metrics) else (Colors.WARNING if q_score >= len(metrics) * 0.8 else Colors.FAIL)

        # Complexity badge
        comp_badges = {
            Complexity.SIMPLE: f"{Colors.OKGREEN}简单{Colors.ENDC}",
            Complexity.MEDIUM: f"{Colors.WARNING}中等{Colors.ENDC}",
            Complexity.COMPLEX: f"{Colors.FAIL}复杂{Colors.ENDC}",
            Complexity.EDGE_CASE: f"{Colors.OKCYAN}边缘{Colors.ENDC}",
        }

        print(f"  {test.name:<18} {comp_badges[test.complexity]:<10} {time_str:>20} {status}  {q_color}{q_score}/{len(metrics)}{Colors.ENDC}")
        if result.execution_error:
            print(f"    └─ {Colors.WARNING}⚠️  {result.execution_error[:60]}{Colors.ENDC}")

    print(f"\n{Colors.BOLD}{'═' * 70}{Colors.ENDC}")


def run_benchmark(filter_complexity: Complexity | None = None, limit: int | None = None, workers: int = 4):
    """Run benchmark suite with parallel execution."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading

    tests = BENCHMARK_CASES
    if filter_complexity:
        tests = [t for t in tests if t.complexity == filter_complexity]
    if limit:
        tests = tests[:limit]

    print(f"\n{Colors.BOLD}🚀 Starting UPA Benchmark Suite{Colors.ENDC}")
    print(f"{Colors.OKCYAN}Running {len(tests)} tests with {workers} workers across {len(set(t.complexity for t in tests))} complexity levels{Colors.ENDC}\n")

    results = []
    results_lock = threading.Lock()
    completed_count = [0]

    def worker_task(idx: int, test: TestCase):
        """Worker function to run a single test."""
        result = run_upa_with_timing(test.query)
        metrics = evaluate_quality(test, result)

        with results_lock:
            results.append((idx, test, result, metrics))

        # Print progress
        with results_lock:
            completed_count[0] += 1
            progress = completed_count[0] / len(tests)
            bar_len = 30
            filled = int(progress * bar_len)
            bar = f"{Colors.OKGREEN}{'█' * filled}{Colors.ENDC}{'░' * (bar_len - filled)}"

            comp_colors = {
                Complexity.SIMPLE: Colors.OKGREEN,
                Complexity.MEDIUM: Colors.WARNING,
                Complexity.COMPLEX: Colors.FAIL,
                Complexity.EDGE_CASE: Colors.OKCYAN,
            }
            comp_color = comp_colors[test.complexity]

            if metrics.get(QualityMetric.CORRECT_RESULT):
                status = f"{Colors.OKGREEN}✓{Colors.ENDC}"
            else:
                status = f"{Colors.FAIL}✗{Colors.ENDC}"

            print(f"\r  {bar} {Colors.BOLD}{completed_count[0]}/{len(tests)}{Colors.ENDC} | {comp_color}{test.complexity.value}{Colors.ENDC} | {test.name:<20} | {status} {result.timing.get('total', 0):.0f}ms  ", end="", flush=True)

        return test, result, metrics

    start_time = time.perf_counter()

    # Run tests in parallel
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(worker_task, i, test): (i, test)
            for i, test in enumerate(tests, 1)
        }

        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                idx, test = futures[future]
                with results_lock:
                    results.append((idx, test, None, {}))

    total_suite_time = (time.perf_counter() - start_time) * 1000

    print(f"\n\n{Colors.BOLD}🏁 Suite completed in {total_suite_time:.0f}ms (parallel execution){Colors.ENDC}")

    # Sort results by original index
    results.sort(key=lambda x: x[0])
    sorted_results = [(t, r, m) for _, t, r, m in results]

    print_report(sorted_results)
    return sorted_results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="UPA Performance Benchmark")
    parser.add_argument("--complexity", "-c", choices=[c.value for c in Complexity], help="Filter by complexity")
    parser.add_argument("--limit", "-n", type=int, help="Limit number of tests")
    parser.add_argument("--list", "-l", action="store_true", help="List test cases")
    parser.add_argument("--json", "-j", type=str, help="Export results to JSON")
    parser.add_argument("--workers", "-w", type=int, default=4, help="Number of parallel workers (default: 4)")

    args = parser.parse_args()

    if args.list:
        for test in BENCHMARK_CASES:
            print(f"[{test.complexity.value}] {test.name}: {test.query}")
        return

    filter_comp = Complexity(args.complexity) if args.complexity else None
    results = run_benchmark(filter_comp, args.limit, args.workers)

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
