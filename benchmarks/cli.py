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

    # Planner Statistics (Phase 5)
    planner_enabled_count = sum(1 for _, _, _, d in results if d.planner_enabled)
    if planner_enabled_count > 0:
        print(f"\n  {Colors.BOLD}🧠 Planner Statistics (Phase 5){Colors.ENDC}")
        print(f"  Planner Enabled:  {planner_enabled_count}/{total} ({planner_enabled_count/total*100:.1f}%)")

        # Intent distribution
        intents = {}
        for _, _, _, d in results:
            if d.planner_intent:
                intents[d.planner_intent] = intents.get(d.planner_intent, 0) + 1
        if intents:
            print(f"  Intent Distribution:")
            for intent, count in sorted(intents.items(), key=lambda x: x[1], reverse=True):
                bar_color = Colors.OKGREEN
                bar = format_bar(count, total, 15, bar_color)
                print(f"    {intent:15} {bar} {count:>2}/{total:<2}")

        # Complexity distribution
        complexities = {}
        for _, _, _, d in results:
            if d.planner_complexity:
                complexities[d.planner_complexity] = complexities.get(d.planner_complexity, 0) + 1
        if complexities:
            print(f"  Complexity Distribution:")
            for comp, count in sorted(complexities.items(), key=lambda x: x[1], reverse=True):
                bar_color = Colors.OKGREEN
                bar = format_bar(count, total, 15, bar_color)
                print(f"    {comp:15} {bar} {count:>2}/{total:<2}")

        # Skip planning count
        skip_count = sum(1 for _, _, _, d in results if d.planner_skip_planning)
        print(f"  Skip Planning:    {skip_count}/{total} ({skip_count/total*100:.1f}%)")

        # Planner timing
        planner_times = [d.planner_timing_ms for _, _, _, d in results if d.planner_timing_ms > 0]
        if planner_times:
            print(f"  Planner Timing:")
            print(f"    Mean:   {mean(planner_times):.0f}ms")
            print(f"    Median: {median(planner_times):.0f}ms")
            print(f"    Min:    {min(planner_times):.0f}ms")
            print(f"    Max:    {max(planner_times):.0f}ms")

        # Planner Validation Statistics (for planner suite)
        validation_results = [d.planner_validation for _, _, _, d in results if d.planner_validation]
        if validation_results:
            print(f"\n  {Colors.BOLD}🔍 Planner Validation Results{Colors.ENDC}")
            # Intent accuracy
            intent_correct = sum(1 for v in validation_results if v.get('intent_correct'))
            intent_total = sum(1 for v in validation_results if 'intent_correct' in v)
            if intent_total > 0:
                intent_color = Colors.OKGREEN if intent_correct == intent_total else Colors.FAIL
                print(f"  Intent Accuracy:  {intent_color}{intent_correct}/{intent_total} ({intent_correct/intent_total*100:.1f}%){Colors.ENDC}")

            # Tools accuracy
            tools_correct = sum(1 for v in validation_results if v.get('tools_correct'))
            tools_total = sum(1 for v in validation_results if 'tools_correct' in v)
            if tools_total > 0:
                tools_color = Colors.OKGREEN if tools_correct == tools_total else Colors.FAIL
                print(f"  Tools Accuracy:   {tools_color}{tools_correct}/{tools_total} ({tools_correct/tools_total*100:.1f}%){Colors.ENDC}")

            # Skip accuracy
            skip_correct = sum(1 for v in validation_results if v.get('skip_correct'))
            skip_total = sum(1 for v in validation_results if 'skip_correct' in v)
            if skip_total > 0:
                skip_color = Colors.OKGREEN if skip_correct == skip_total else Colors.FAIL
                print(f"  Skip Accuracy:    {skip_color}{skip_correct}/{skip_total} ({skip_correct/skip_total*100:.1f}%){Colors.ENDC}")

            # Overall accuracy
            all_correct = sum(1 for v in validation_results if v.get('all_correct'))
            if validation_results:
                overall_color = Colors.OKGREEN if all_correct == len(validation_results) else Colors.FAIL
                print(f"  Overall Accuracy: {overall_color}{all_correct}/{len(validation_results)} ({all_correct/len(validation_results)*100:.1f}%){Colors.ENDC}")

    # Detail Table
    print(f"\n  {Colors.BOLD}📋 Detailed Results{Colors.ENDC}")
    print(f"  {'Test':<18} {'Complexity':<10} {'Time':>10} {'Status':<8} {'Quality'}")
    print(f"{'─' * 70}")

    for test, result, metrics, details in results:
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

        # Add planner indicator
        planner_indicator = ""
        if details.planner_enabled and details.planner_intent:
            planner_short = details.planner_intent[:4] if details.planner_intent else "N/A"
            planner_indicator = f" [{Colors.OKCYAN}{planner_short}{Colors.ENDC}]"

        print(f"  {test.name:<18} {comp_badges[test.complexity]:<10} {time_str:>20} {status}  {q_color}{q_score}/{len(metrics)}{Colors.ENDC}{planner_indicator}")
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
  # Run all tests in core suite (details saved automatically)
  python -m benchmarks core

  # Run semantic suite with 8 workers
  python -m benchmarks semantic -w 8

  # Filter by complexity
  python -m benchmarks core -c 中等

  # Export results to JSON
  python -m benchmarks core -j results.json

  # Disable automatic details saving
  python -m benchmarks core --no-details

  # Specify custom details filename
  python -m benchmarks core --save-details my-details.json

  # Disable LLM validation for failed tests
  python -m benchmarks core --no-llm-validation

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
        "--provider", "-p",
        type=str,
        default=None,
        help="LLM provider to use for validation (dashscope, cloudflare, etc.)"
    )
    parser.add_argument(
        "--no-llm-validation",
        action="store_true",
        help="Disable LLM-assisted validation for failed tests"
    )
    parser.add_argument(
        "--save-details",
        type=str,
        metavar="FILE",
        default=None,
        help="Save detailed execution logs to JSON file (default: auto-generated filename, use --no-details to disable)"
    )
    parser.add_argument(
        "--no-details",
        action="store_true",
        help="Disable automatic saving of detailed execution logs"
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
    enable_llm_validation = not args.no_llm_validation

    if args.suite in ("core", "classic", "mmlu", "planner"):
        filter_comp = Complexity(args.complexity) if args.complexity else None
        results = run_core_benchmark(
            cases=suite.cases,
            filter_complexity=filter_comp,
            limit=args.limit,
            workers=args.workers,
            provider=args.provider,
            enable_llm_validation=enable_llm_validation
        )
        print_report_core(results)

        # Export detailed logs (default unless --no-details)
        if not args.no_details:
            details_data = [details.to_dict() for _, _, _, details in results]
            # Auto-generate filename if not specified
            if args.save_details:
                details_file = args.save_details
            else:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                details_file = f"details-{args.suite}-{timestamp}.json"
            with open(details_file, "w", encoding="utf-8") as f:
                json.dump(details_data, f, ensure_ascii=False, indent=2)
            print(f"{Colors.OKGREEN}✓ Saved details to {details_file}{Colors.ENDC}")

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
            workers=args.workers,
            provider=args.provider,
            enable_llm_validation=enable_llm_validation
        )

        display = StreamingDisplay()
        display.print_summary([{
            "name": hr.test.name,
            "success": hr.success,
            "duration": hr.duration,
            "task_type": hr.test.task_type,
            "sub_agent_calls": hr.sub_agent_calls,
        } for hr, _ in results])

        # Export detailed logs (default unless --no-details)
        if not args.no_details:
            details_data = [details.to_dict() for _, details in results]
            # Auto-generate filename if not specified
            if args.save_details:
                details_file = args.save_details
            else:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                details_file = f"details-semantic-{timestamp}.json"
            with open(details_file, "w", encoding="utf-8") as f:
                json.dump(details_data, f, ensure_ascii=False, indent=2)
            print(f"{Colors.OKGREEN}✓ Saved details to {details_file}{Colors.ENDC}")

        # Planner Statistics for semantic tests
        planner_enabled_count = sum(1 for _, d in results if d.planner_enabled)
        if planner_enabled_count > 0:
            print(f"\n{Colors.BOLD}🧠 Planner Statistics (Phase 5){Colors.ENDC}")
            print(f"  Planner Enabled:  {planner_enabled_count}/{len(results)} ({planner_enabled_count/len(results)*100:.1f}%)")

            # Intent distribution
            intents = {}
            for _, d in results:
                if d.planner_intent:
                    intents[d.planner_intent] = intents.get(d.planner_intent, 0) + 1
            if intents:
                print(f"  Intent Distribution:")
                for intent, count in sorted(intents.items(), key=lambda x: x[1], reverse=True):
                    bar_color = Colors.OKGREEN
                    bar = format_bar(count, len(results), 15, bar_color)
                    print(f"    {intent:15} {bar} {count:>2}/{len(results):<2}")

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
