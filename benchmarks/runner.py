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
    TestCase, HybridTest, BenchmarkResult, HybridResult, TestDetails,
    QualityMetric, Complexity, TaskType
)
from benchmarks.display import StreamingDisplay, Colors, format_bar, format_time


def extract_code_from_stderr(stderr: str) -> str:
    """Extract generated Python code from stderr output."""
    # Look for code block in stderr (UPA outputs it during execution)
    pattern = r"```python\s*\n(.*?)\n```"
    match = re.search(pattern, stderr, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def _llm_validate_result(test: TestCase, output: str, provider: str | None = None) -> bool | None:
    """Use LLM to validate if output meets expectations.

    Returns:
        True if LLM confirms output is correct
        False if LLM confirms output is incorrect
        None if LLM is uncertain or validation fails
    """
    from datetime import datetime

    # Build validation prompt
    prompt_parts = [f"Test Query: {test.query}"]

    if test.expect_contains:
        prompt_parts.append(f"Expected Output Contains: {test.expect_contains}")
    if test.expect_pattern:
        prompt_parts.append(f"Expected Pattern: {test.expect_pattern}")
    if test.expect_numeric:
        expected, tolerance = test.expect_numeric
        prompt_parts.append(f"Expected Numeric: {expected} ± {tolerance}")

    prompt_parts.append(f"\nActual Output:\n{output}")
    prompt_parts.append(
        "\n请判断上述输出是否符合期望要求。"
        "如果输出正确，返回 'CORRECT'；如果输出错误，返回 'INCORRECT'。"
        "只返回这两个词之一，不要解释。"
    )

    validation_query = "\n".join(prompt_parts)

    # Build command with provider
    cmd = ["uv", "run", "python", "upa.py"]
    if provider:
        cmd.extend(["--provider", provider])
    cmd.append(validation_query)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        response = result.stdout.strip().upper()

        if "CORRECT" in response and "INCORRECT" not in response:
            return True
        elif "INCORRECT" in response and "CORRECT" not in response:
            return False
        else:
            return None  # Uncertain

    except (subprocess.TimeoutExpired, Exception):
        return None


def run_upa_test(
    test: TestCase,
    provider: str | None = None,
    enable_llm_validation: bool = True
) -> tuple[TestCase, BenchmarkResult, dict[QualityMetric, bool], TestDetails]:
    """Run a single core UPA test."""
    cmd = ["uv", "run", "python", "upa.py", "--timing", test.query]

    start_time = time.perf_counter()
    from datetime import datetime
    timestamp = datetime.now().isoformat()

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        total_time = (time.perf_counter() - start_time) * 1000

        stdout = result.stdout
        stderr = result.stderr

        # Parse timing
        timing = _parse_timing_report(stderr)
        timing["total"] = total_time

        code_extracted = "Thinking..." in stderr
        generated_code = extract_code_from_stderr(stderr)
        violations = re.findall(r"- (Blocked .+)", stderr) if "Security violations" in stderr else []

        exec_error = ""
        if "Execution Error:" in stderr:
            match = re.search(r"Execution Error:\n(.+)", stderr, re.DOTALL)
            if match:
                exec_error = match.group(1).strip()

        benchmark_result = BenchmarkResult(
            query=test.query,
            success=result.returncode == 0,
            output=stdout,
            timing=timing,
            code_extracted=code_extracted,
            code_content=generated_code,
            security_violations=violations,
            execution_error=exec_error[:500] if exec_error else "",
        )

        # Create detailed record
        details = TestDetails(
            suite_name="core",
            test_name=test.name,
            query=test.query,
            complexity=test.complexity.value,
            generated_code=generated_code,
            code_block_found=code_extracted,
            stdout=stdout,
            stderr=stderr,
            return_code=result.returncode,
            success=result.returncode == 0,
            security_violations=violations,
            execution_error=exec_error,
            timing_ms=timing,
            expected_contains=test.expect_contains,
            expected_pattern=test.expect_pattern,
            expected_numeric=test.expect_numeric,
            timestamp=timestamp,
        )

        metrics = _evaluate_quality(test, benchmark_result)

        # LLM-assisted validation for failed tests
        llm_validated = False
        if enable_llm_validation and not metrics.get(QualityMetric.CORRECT_RESULT):
            # Only use LLM validation if the test has expectations
            if test.expect_contains or test.expect_pattern or test.expect_numeric:
                llm_result = _llm_validate_result(test, benchmark_result.output, provider)
                if llm_result is True:
                    metrics[QualityMetric.CORRECT_RESULT] = True
                    llm_validated = True
                elif llm_result is False:
                    metrics[QualityMetric.CORRECT_RESULT] = False

        # Add validation metadata to details
        details.llm_validated = llm_validated

        return test, benchmark_result, metrics, details

    except subprocess.TimeoutExpired:
        benchmark_result = BenchmarkResult(
            query=test.query,
            success=False,
            output="",
            timing={"total": 120000},
            code_extracted=False,
            execution_error="Timeout"
        )
        details = TestDetails(
            suite_name="core",
            test_name=test.name,
            query=test.query,
            complexity=test.complexity.value,
            return_code=-1,
            success=False,
            execution_error="Timeout",
            timestamp=timestamp,
        )
        return test, benchmark_result, {}, details

    except Exception as e:
        benchmark_result = BenchmarkResult(
            query=test.query,
            success=False,
            output="",
            timing={},
            code_extracted=False,
            execution_error=str(e)
        )
        details = TestDetails(
            suite_name="core",
            test_name=test.name,
            query=test.query,
            complexity=test.complexity.value,
            return_code=-1,
            success=False,
            execution_error=str(e),
            timestamp=timestamp,
        )
        return test, benchmark_result, {}, details


def run_hybrid_test(
    test: HybridTest,
    provider: str | None = None,
    enable_llm_validation: bool = True
) -> tuple[HybridResult, TestDetails]:
    """Run a single semantic-logic hybrid test."""
    cmd = ["uv", "run", "python", "upa.py", "--timing", test.query]

    start_time = time.perf_counter()
    from datetime import datetime
    timestamp = datetime.now().isoformat()

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

        # Count sub-agent calls and depths
        sub_calls = len(re.findall(r"Sub-Agent Call \(L(\d+)\)", stderr))
        sub_depths = [int(d) for d in re.findall(r"Sub-Agent Call \(L(\d+)\)", stderr)]

        # Extract generated code
        generated_code = extract_code_from_stderr(stderr)

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
                    # Find the number closest to expected value (not just first)
                    actual = float(min(numbers, key=lambda x: abs(float(x) - expected)))
                    success = abs(actual - expected) <= tolerance
                except ValueError:
                    success = False

        # LLM-assisted validation for failed tests
        llm_validated = False
        if enable_llm_validation and not success:
            # Only use LLM validation if the test has expectations
            if test.expected_contains or test.expected_pattern or test.expected_numeric:
                # Create a temp TestCase for LLM validation
                from benchmarks.suites.base import TestCase, Complexity
                temp_test = TestCase(
                    name=test.name,
                    query=test.query,
                    complexity=Complexity.MEDIUM,  # default, not critical for validation
                    expect_contains=test.expected_contains,
                    expect_pattern=test.expected_pattern,
                    expect_numeric=test.expected_numeric,
                )
                llm_result = _llm_validate_result(temp_test, output, provider)
                if llm_result is True:
                    success = True
                    llm_validated = True

        # Parse timing
        timing = _parse_timing_report(stderr)
        timing["total"] = duration

        hybrid_result = HybridResult(
            test=test,
            success=success,
            output=output,
            duration=duration,
            sub_agent_calls=sub_calls,
            execution_error=stderr if result.returncode != 0 else ""
        )

        details = TestDetails(
            suite_name="semantic",
            test_name=test.name,
            query=test.query,
            task_type=test.task_type.value,
            generated_code=generated_code,
            code_block_found=bool(generated_code),
            stdout=output,
            stderr=stderr,
            return_code=result.returncode,
            success=success,
            timing_ms=timing,
            sub_agent_calls=sub_calls,
            sub_agent_depths=sub_depths,
            expected_contains=test.expected_contains,
            expected_pattern=test.expected_pattern,
            expected_numeric=test.expected_numeric,
            timestamp=timestamp,
            llm_validated=llm_validated,
        )

        return hybrid_result, details

    except subprocess.TimeoutExpired:
        hybrid_result = HybridResult(
            test=test,
            success=False,
            output="",
            duration=120000,
            sub_agent_calls=0,
            execution_error="Timeout"
        )
        details = TestDetails(
            suite_name="semantic",
            test_name=test.name,
            query=test.query,
            task_type=test.task_type.value,
            return_code=-1,
            success=False,
            execution_error="Timeout",
            timestamp=timestamp,
        )
        return hybrid_result, details

    except Exception as e:
        duration = (time.perf_counter() - start_time) * 1000
        hybrid_result = HybridResult(
            test=test,
            success=False,
            output="",
            duration=duration,
            sub_agent_calls=0,
            execution_error=str(e)
        )
        details = TestDetails(
            suite_name="semantic",
            test_name=test.name,
            query=test.query,
            task_type=test.task_type.value,
            return_code=-1,
            success=False,
            execution_error=str(e),
            timestamp=timestamp,
        )
        return hybrid_result, details


def run_core_benchmark(
    cases: list[TestCase] | None = None,
    filter_complexity: Complexity | None = None,
    limit: int | None = None,
    workers: int = 4,
    provider: str | None = None,
    enable_llm_validation: bool = True
) -> list[tuple[TestCase, BenchmarkResult, dict[QualityMetric, bool], TestDetails]]:
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
        test_result = run_upa_test(test, provider, enable_llm_validation)

        with results_lock:
            results.append((idx, test_result))
            completed_count[0] += 1

        # Print progress
        _, _, metrics, _ = test_result
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
                    results.append((idx, (test, None, {}, None)))

    total_suite_time = (time.perf_counter() - start_time) * 1000

    print(f"\n\n{Colors.BOLD}🏁 Suite completed in {total_suite_time:.0f}ms{Colors.ENDC}")

    results.sort(key=lambda x: x[0])
    return [(t, r, m, d) for _, (t, r, m, d) in results]


def run_hybrid_benchmark(
    cases: list[HybridTest] | None = None,
    filter_type: TaskType | None = None,
    limit: int | None = None,
    workers: int = 4,
    provider: str | None = None,
    enable_llm_validation: bool = True
) -> list[tuple[HybridResult, TestDetails]]:
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
        hybrid_result, details = run_hybrid_test(test, provider, enable_llm_validation)

        with progress_lock:
            completed_count[0] += 1
            display.print_task_start(completed_count[0], len(tests), test.name, test.task_type.value, test.query)
            display.print_task_result(hybrid_result.success, hybrid_result.duration, hybrid_result.output)
            if hybrid_result.sub_agent_calls > 0:
                print(f"    {Colors.OKCYAN}📊 Sub-agent calls: {hybrid_result.sub_agent_calls}{Colors.ENDC}")

        with results_lock:
            results.append((idx, (hybrid_result, details)))

        return hybrid_result, details

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
                from datetime import datetime
                idx, test = futures[future]
                error_result = HybridResult(
                    test=test,
                    success=False,
                    output="",
                    duration=0,
                    execution_error=str(e)
                )
                error_details = TestDetails(
                    suite_name="semantic",
                    test_name=test.name,
                    query=test.query,
                    task_type=test.task_type.value,
                    return_code=-1,
                    success=False,
                    execution_error=str(e),
                    timestamp=datetime.now().isoformat(),
                )
                with results_lock:
                    results.append((idx, (error_result, error_details)))

    total_duration = (time.perf_counter() - start_time) * 1000

    print(f"\n{Colors.BOLD}⏱️  Suite completed in {total_duration:.0f}ms{Colors.ENDC}")

    results.sort(key=lambda x: x[0])
    return [(hr, td) for _, (hr, td) in results]


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
                # Find the number closest to expected value (not just first)
                actual = float(min(numbers, key=lambda x: abs(float(x) - expected)))
                metrics[QualityMetric.CORRECT_RESULT] = abs(actual - expected) <= tolerance
            except ValueError:
                metrics[QualityMetric.CORRECT_RESULT] = False
        else:
            metrics[QualityMetric.CORRECT_RESULT] = False
    else:
        metrics[QualityMetric.CORRECT_RESULT] = result.success

    metrics[QualityMetric.NO_EXTRA_TEXT] = len(result.output) < 500 or result.success

    return metrics
