"""
Core benchmark execution engine.
"""

import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from typing import Any

from benchmarks.suites.base import (
    TestCase, HybridTest, BenchmarkResult, HybridResult,
    QualityMetric, Complexity, TaskType
)
from benchmarks.display import StreamingDisplay, Colors, format_bar, format_time


def run_upa_test(test: TestCase) -> tuple[TestCase, BenchmarkResult, dict[QualityMetric, bool]]:
    """Run a single core UPA test."""
    cmd = ["uv", "run", "python", "upa.py", "--timing", test.query]

    start_time = time.perf_counter()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        total_time = (time.perf_counter() - start_time) * 1000

        stdout = result.stdout
        stderr = result.stderr

        # Parse timing
        timing = _parse_timing_report(stderr)
        timing["total"] = total_time

        code_extracted = "Thinking..." in stderr
        violations = re.findall(r"- (Blocked .+)", stderr) if "Security violations" in stderr else []

        exec_error = ""
        if "Execution Error:" in stderr:
            match = re.search(r"Execution Error:\n(.+)", stderr, re.DOTALL)
            if match:
                exec_error = match.group(1).strip()[:100]

        benchmark_result = BenchmarkResult(
            query=test.query,
            success=result.returncode == 0,
            output=stdout,
            timing=timing,
            code_extracted=code_extracted,
            security_violations=violations,
            execution_error=exec_error,
        )

        metrics = _evaluate_quality(test, benchmark_result)
        return test, benchmark_result, metrics

    except subprocess.TimeoutExpired:
        result = BenchmarkResult(
            query=test.query,
            success=False,
            output="",
            timing={"total": 120000},
            code_extracted=False,
            execution_error="Timeout"
        )
        return test, result, {}

    except Exception as e:
        result = BenchmarkResult(
            query=test.query,
            success=False,
            output="",
            timing={},
            code_extracted=False,
            execution_error=str(e)
        )
        return test, result, {}


def run_hybrid_test(test: HybridTest) -> HybridResult:
    """Run a single semantic-logic hybrid test."""
    cmd = ["uv", "run", "python", "upa.py", "--timing", test.query]

    start_time = time.perf_counter()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "PYTHONUNBUFFERED": "1"}
        )

        duration = (time.perf_counter() - start_time) * 1000
        output = result.stdout
        stderr = result.stderr

        # Count sub-agent calls
        sub_calls = len(re.findall(r"Sub-Agent Call \(L(\d+)\)", stderr))

        # Evaluate result
        success = result.returncode == 0
        if success and test.expected_contains:
            success = test.expected_contains in output
        elif success and test.expected_pattern:
            success = bool(re.search(test.expected_pattern, output))
        elif success and test.expected_numeric:
            expected, tolerance = test.expected_numeric
            numbers = re.findall(r"[-+]?\d*\.?\d+", output)
            if numbers:
                try:
                    actual = float(numbers[0])
                    success = abs(actual - expected) <= tolerance
                except ValueError:
                    success = False

        return HybridResult(
            test=test,
            success=success,
            output=output,
            duration=duration,
            sub_agent_calls=sub_calls,
            execution_error=stderr if result.returncode != 0 else ""
        )

    except subprocess.TimeoutExpired:
        return HybridResult(
            test=test,
            success=False,
            output="",
            duration=120000,
            sub_agent_calls=0,
            execution_error="Timeout"
        )
    except Exception as e:
        duration = (time.perf_counter() - start_time) * 1000
        return HybridResult(
            test=test,
            success=False,
            output="",
            duration=duration,
            sub_agent_calls=0,
            execution_error=str(e)
        )


def run_core_benchmark(
    cases: list[TestCase] | None = None,
    filter_complexity: Complexity | None = None,
    limit: int | None = None,
    workers: int = 4
) -> list[tuple[TestCase, BenchmarkResult, dict[QualityMetric, bool]]]:
    """Run core UPA benchmark suite."""
    from benchmarks.suites.core_upa import CORE_CASES

    tests = cases or CORE_CASES
    if filter_complexity:
        tests = [t for t in tests if t.complexity == filter_complexity]
    if limit:
        tests = tests[:limit]

    print(f"\n{Colors.BOLD}🚀 Starting Core UPA Benchmark{Colors.ENDC}")
    print(f"{Colors.OKCYAN}Running {len(tests)} tests with {workers} workers{Colors.ENDC}\n")

    results = []
    results_lock = threading.Lock()
    completed_count = [0]

    def worker_task(idx: int, test: TestCase):
        """Worker function to run a single test."""
        test_result = run_upa_test(test)

        with results_lock:
            results.append((idx, test_result))
            completed_count[0] += 1

        # Print progress
        _, _, metrics = test_result
        with results_lock:
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

            print(f"\r  {bar} {Colors.BOLD}{completed_count[0]}/{len(tests)}{Colors.ENDC} | "
                  f"{comp_color}{test.complexity.value}{Colors.ENDC} | "
                  f"{test.name:<20} | {status} ", end="", flush=True)

        return test_result

    start_time = time.perf_counter()

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
                    results.append((idx, (test, None, {})))

    total_suite_time = (time.perf_counter() - start_time) * 1000

    print(f"\n\n{Colors.BOLD}🏁 Suite completed in {total_suite_time:.0f}ms{Colors.ENDC}")

    results.sort(key=lambda x: x[0])
    return [(t, r, m) for _, (t, r, m) in results]


def run_hybrid_benchmark(
    cases: list[HybridTest] | None = None,
    filter_type: TaskType | None = None,
    limit: int | None = None,
    workers: int = 4
) -> list[HybridResult]:
    """Run semantic-logic hybrid benchmark suite."""
    from benchmarks.suites.semantic import HYBRID_CASES

    tests = cases or HYBRID_CASES
    if filter_type:
        tests = [t for t in tests if t.task_type == filter_type]
    if limit:
        tests = tests[:limit]

    display = StreamingDisplay()
    display.print_header("🚀 Semantic-Logic Hybrid Benchmark")
    print(f"\n  Running {len(tests)} tests with {workers} workers...\n")

    results = []
    results_lock = threading.Lock()
    progress_lock = threading.Lock()
    completed_count = [0]

    def worker_task(idx: int, test: HybridTest):
        """Worker function to run a single test."""
        result = run_hybrid_test(test)

        with progress_lock:
            completed_count[0] += 1
            display.print_task_start(completed_count[0], len(tests), test.name, test.task_type.value, test.query)
            display.print_task_result(result.success, result.duration, result.output)
            if result.sub_agent_calls > 0:
                print(f"    {Colors.OKCYAN}📊 Sub-agent calls: {result.sub_agent_calls}{Colors.ENDC}")

        with results_lock:
            results.append((idx, result))

        return result

    start_time = time.perf_counter()

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
                    results.append((idx, HybridResult(
                        test=test,
                        success=False,
                        output="",
                        duration=0,
                        execution_error=str(e)
                    )))

    total_duration = (time.perf_counter() - start_time) * 1000

    print(f"\n{Colors.BOLD}⏱️  Suite completed in {total_duration:.0f}ms{Colors.ENDC}")

    results.sort(key=lambda x: x[0])
    return [r for _, r in results]


def _parse_timing_report(stderr: str) -> dict[str, float]:
    """Parse timing report from stderr."""
    timing = {}
    clean = re.sub(r'\033\[[0-9;]+m', '', stderr)
    pattern = r"^\s*(\w[\w\s]+?)\s+(\d+\.?\d*)ms"
    for match in re.finditer(pattern, clean, re.MULTILINE):
        timing[match.group(1).strip()] = float(match.group(2))
    return timing


def _evaluate_quality(test: TestCase, result: BenchmarkResult) -> dict[QualityMetric, bool]:
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
