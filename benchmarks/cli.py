#!/usr/bin/env python3
"""
UPA Benchmark CLI
Unified command-line interface for running benchmark test suites.
"""

import argparse
import json
import sys
from statistics import mean, median
from typing import Any

from benchmarks.suites.base import (
    Complexity, TaskType, QualityMetric,
    TestCase, HybridTest, BenchmarkResult, HybridResult, TestDetails,
    get_registered_suites, get_suite
)
from benchmarks.runner import run_core_benchmark, run_hybrid_benchmark
from benchmarks.display import Colors, format_bar, format_time, StreamingDisplay


def print_report_core(results: list[tuple[TestCase, BenchmarkResult, dict[QualityMetric, bool], TestDetails]]):
    """Print core UPA benchmark report."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'═' * 70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}  UPA Core Benchmark Report{'':>48}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'═' * 70}{Colors.ENDC}")

    total = len(results)
    passed = sum(1 for _, _, m, _ in results if m.get(QualityMetric.CORRECT_RESULT))
    code_ok = sum(1 for _, _, m, _ in results if m.get(QualityMetric.CODE_OUTPUT))
    exec_ok = sum(1 for _, _, m, _ in results if m.get(QualityMetric.EXECUTION_OK))

    llm_times = [r.timing.get("LLM Generate", 0) for _, r, _, _ in results if r.timing]

    # Overall Statistics
    print(f"\n  {Colors.BOLD}📊 Overall Statistics{Colors.ENDC}")
    print(f"  Tests Run:       {Colors.BOLD}{total}{Colors.ENDC}")
    print(f"  Correct Results: {Colors.OKGREEN if passed == total else Colors.WARNING}{passed}/{total} ({passed/total*100:.1f}%){Colors.ENDC}")
    print(f"  Code Generated:  {Colors.OKGREEN if code_ok == total else Colors.WARNING}{code_ok}/{total} ({code_ok/total*100:.1f}%){Colors.ENDC}")
    print(f"  Execution OK:    {Colors.OKGREEN if exec_ok == total else Colors.WARNING}{exec_ok}/{total} ({exec_ok/total*100:.1f}%){Colors.ENDC}")

    if llm_times:
        print(f"\n  {Colors.BOLD}⏱️  LLM Timing Statistics{Colors.ENDC}")
        avg_time = mean(llm_times)
        print(f"  Mean:   {format_time(avg_time)}")
        print(f"  Median: {format_time(median(llm_times))}")
        print(f"  Min:    {format_time(min(llm_times))}")
        print(f"  Max:    {format_time(max(llm_times))}")

        if avg_time < 10000:
            print(f"  {Colors.OKGREEN}⚡ Speed Tier: FAST{Colors.ENDC}")
        elif avg_time < 20000:
            print(f"  {Colors.WARNING}🐢 Speed Tier: NORMAL{Colors.ENDC}")
        else:
            print(f"  {Colors.FAIL}🐌 Speed Tier: SLOW{Colors.ENDC}")

    # By Complexity
    print(f"\n  {Colors.BOLD}📈 Results by Complexity{Colors.ENDC}")
    by_comp: dict[Complexity, list] = {c: [] for c in Complexity}
    for test, result, metrics, _ in results:
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

    # Quality Metrics
    print(f"\n  {Colors.BOLD}🎯 Quality Metrics{Colors.ENDC}")
    for metric in QualityMetric:
        p = sum(1 for _, _, m, _ in results if m.get(metric))
        pct = (p / total * 100) if total > 0 else 0
        bar_color = Colors.OKGREEN if p == total else (Colors.WARNING if p >= total * 0.8 else Colors.FAIL)
        bar = format_bar(p, total, 20, bar_color)
        print(f"  {metric.value:12} {bar} {p:>2}/{total:<2} ({pct:>5.1f}%)")

    # Detail Table
    print(f"\n  {Colors.BOLD}📋 Detailed Results{Colors.ENDC}")
    print(f"  {'Test':<18} {'Complexity':<10} {'Time':>10} {'Status':<8} {'Quality'}")
    print(f"{'─' * 70}")

    for test, result, metrics, _ in results:
        time_str = format_time(result.timing.get('total', 0))
        if metrics.get(QualityMetric.CORRECT_RESULT):
            status = f"{Colors.OKGREEN}✅ PASS{Colors.ENDC}"
        else:
            status = f"{Colors.FAIL}❌ FAIL{Colors.ENDC}"

        q_score = sum(1 for v in metrics.values() if v)
        q_color = Colors.OKGREEN if q_score == len(metrics) else (Colors.WARNING if q_score >= len(metrics) * 0.8 else Colors.FAIL)

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


def list_suites():
    """List all available test suites."""
    suites = get_registered_suites()

    print(f"\n{Colors.BOLD}📚 Available Test Suites{Colors.ENDC}")
    print(f"{'─' * 70}\n")

    for name, suite in suites.items():
        print(f"  {Colors.OKCYAN}{name}{Colors.ENDC} - {suite.description}")
        print(f"      Version: {suite.version}")
        print(f"      Tests: {len(suite.cases)}\n")


def list_tests(suite_name: str | None = None):
    """List test cases in a suite."""
    if suite_name:
        suite = get_suite(suite_name)
        if not suite:
            print(f"{Colors.FAIL}Error: Suite '{suite_name}' not found{Colors.ENDC}", file=sys.stderr)
            return
        suites = {suite_name: suite}
    else:
        suites = get_registered_suites()

    for name, suite in suites.items():
        print(f"\n{Colors.BOLD}Suite: {name}{Colors.ENDC}")
        print(f"{'─' * 70}")
        for i, case in enumerate(suite.cases, 1):
            if isinstance(case, TestCase):
                print(f"  [{i}] {case.name}")
                print(f"      Type: {case.complexity.value}")
                print(f"      Query: {case.query}\n")
            elif isinstance(case, HybridTest):
                print(f"  [{i}] {case.name}")
                print(f"      Type: {case.task_type.value}")
                print(f"      Query: {case.query}\n")


def main():
    parser = argparse.ArgumentParser(
        description="UPA Benchmark Framework - Run test suites",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests in core suite
  python -m benchmarks core

  # Run semantic suite with 8 workers
  python -m benchmarks semantic -w 8

  # Filter by complexity
  python -m benchmarks core -c 中等

  # Export results to JSON
  python -m benchmarks core -j results.json

  # Save detailed execution logs (for failed test analysis)
  python -m benchmarks core --save-details core-details.json

  # List available suites
  python -m benchmarks --list-suites
        """
    )

    parser.add_argument(
        "suite",
        nargs="?",
        help="Test suite to run (core, semantic, or custom)"
    )
    parser.add_argument(
        "--complexity", "-c",
        choices=[c.value for c in Complexity],
        help="Filter by complexity (core suite only)"
    )
    parser.add_argument(
        "--type", "-t",
        choices=[t.value for t in TaskType],
        help="Filter by task type (semantic suite only)"
    )
    parser.add_argument(
        "--limit", "-n",
        type=int,
        help="Limit number of tests"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List test cases in suite"
    )
    parser.add_argument(
        "--list-suites",
        action="store_true",
        help="List all available test suites"
    )
    parser.add_argument(
        "--json", "-j",
        type=str,
        help="Export results to JSON file"
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4)"
    )
    parser.add_argument(
        "--save-details",
        type=str,
        metavar="FILE",
        help="Save detailed execution logs to JSON file (includes code, stderr, etc.)"
    )

    args = parser.parse_args()

    # Handle list commands
    if args.list_suites:
        list_suites()
        return

    if args.list:
        list_tests(args.suite)
        return

    # Require suite name for running tests
    if not args.suite:
        parser.print_help()
        print(f"\n{Colors.WARNING}Error: Please specify a test suite or use --list-suites{Colors.ENDC}", file=sys.stderr)
        return

    suite = get_suite(args.suite)
    if not suite:
        print(f"{Colors.FAIL}Error: Suite '{args.suite}' not found{Colors.ENDC}", file=sys.stderr)
        print(f"Available: {', '.join(get_registered_suites().keys())}")
        return

    # Run the appropriate benchmark
    if args.suite in ("core", "classic"):
        filter_comp = Complexity(args.complexity) if args.complexity else None
        results = run_core_benchmark(
            cases=suite.cases,
            filter_complexity=filter_comp,
            limit=args.limit,
            workers=args.workers
        )
        print_report_core(results)

        # Export detailed logs if requested
        if args.save_details:
            details_data = [details.to_dict() for _, _, _, details in results]
            with open(args.save_details, "w", encoding="utf-8") as f:
                json.dump(details_data, f, ensure_ascii=False, indent=2)
            print(f"{Colors.OKGREEN}✓ Saved details to {args.save_details}{Colors.ENDC}")

        if args.json:
            data = [{
                "test": t.name,
                "query": t.query,
                "complexity": t.complexity.value,
                "success": r.success,
                "timing": r.timing,
                "quality": {m.value: v for m, v in m.items()}
            } for t, r, m, _ in results]
            with open(args.json, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"{Colors.OKGREEN}✓ Exported to {args.json}{Colors.ENDC}")

    elif args.suite == "semantic":
        filter_type = None
        if args.type:
            for t in TaskType:
                if t.value == args.type:
                    filter_type = t
                    break

        results = run_hybrid_benchmark(
            cases=suite.cases,
            filter_type=filter_type,
            limit=args.limit,
            workers=args.workers
        )

        display = StreamingDisplay()
        display.print_summary([{
            "name": hr.test.name,
            "success": hr.success,
            "duration": hr.duration,
            "task_type": hr.test.task_type,
            "sub_agent_calls": hr.sub_agent_calls,
        } for hr, _ in results])

        # Export detailed logs if requested
        if args.save_details:
            details_data = [details.to_dict() for _, details in results]
            with open(args.save_details, "w", encoding="utf-8") as f:
                json.dump(details_data, f, ensure_ascii=False, indent=2)
            print(f"{Colors.OKGREEN}✓ Saved details to {args.save_details}{Colors.ENDC}")

        if args.json:
            data = [{
                "name": hr.test.name,
                "query": hr.test.query,
                "task_type": hr.test.task_type.value,
                "success": hr.success,
                "duration_ms": hr.duration,
                "sub_agent_calls": hr.sub_agent_calls,
                "output": hr.output[:200],
            } for hr, _ in results]
            with open(args.json, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"{Colors.OKGREEN}✓ Exported to {args.json}{Colors.ENDC}")

    else:
        print(f"{Colors.FAIL}Error: Unknown suite type '{args.suite}'{Colors.ENDC}", file=sys.stderr)


if __name__ == "__main__":
    main()
