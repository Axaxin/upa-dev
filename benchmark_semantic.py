#!/usr/bin/env python3
"""
UPA Semantic-Logic Hybrid Benchmark Suite
Tests tasks that combine semantic understanding (sub-agent) with logic processing.
Features streaming-style terminal output for real-time visibility.
"""

import json
import os
import re
import subprocess
import sys
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from statistics import mean, median
from typing import Any

# =============================================================================
# Terminal Colors & Effects
# =============================================================================

class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    BLINK = "\033[5m"
    REVERSE = "\033[7m"

# Cursor controls
CURSOR_UP = "\033[A"
CURSOR_DOWN = "\033[B"
CURSOR_FORWARD = "\033[C"
CURSOR_BACK = "\033[D"
CLEAR_LINE = "\033[2K"
SAVE_CURSOR = "\033[s"
RESTORE_CURSOR = "\033[u"

# Disable colors on Windows or when NO_COLOR is set
if sys.platform == "win32" or os.getenv("NO_COLOR"):
    for attr in dir(Colors):
        if not attr.startswith("_"):
            setattr(Colors, attr, "")


class TaskType(Enum):
    """Type of hybrid task."""
    TRANSLATE_LOGIC = "翻译+逻辑"
    SUMMARIZE_ANALYZE = "总结+分析"
    SENTIMENT_CALC = "情感+计算"
    EXTRACT_PROCESS = "提取+处理"
    RECURSIVE = "递归调用"


@dataclass
class HybridTest:
    """Hybrid task test case."""
    name: str
    query: str
    task_type: TaskType
    description: str
    expected_contains: str | None = None
    expected_pattern: str | None = None
    expected_numeric: tuple[float, float] | None = None


# =============================================================================
# Hybrid Test Cases
# =============================================================================

HYBRID_CASES: list[HybridTest] = [
    # ---- Translation + Logic ----
    HybridTest(
        "翻译后计数",
        "把 'Hello World' 翻译成中文，然后计算翻译结果的字符数量。输出格式：print(字符数)",
        TaskType.TRANSLATE_LOGIC,
        "Translation followed by character counting",
        expected_numeric=(5, 2)  # "你好，世界" ~5 chars
    ),
    HybridTest(
        "多语言连接",
        "用 ask_sub_agent 把 'Hello' 翻译成中文，把 'World' 翻译成中文，然后用空格连接输出。输出格式：print('你好 世界')",
        TaskType.TRANSLATE_LOGIC,
        "Multiple translations concatenated",
        expected_contains="你好"
    ),
    HybridTest(
        "翻译长度比较",
        "将 'I love programming' 翻译成中文。如果中文译文更长输出'中文更长'，否则输出'英文更长'",
        TaskType.TRANSLATE_LOGIC,
        "Compare original and translated lengths",
        expected_contains="英文更长"
    ),

    # ---- Summary + Analysis ----
    HybridTest(
        "摘要后提取关键词",
        "用 ask_sub_agent 总结 'Python是一种广泛使用的高级编程语言'，然后从摘要中提取所有中文词汇的数量。输出格式：print(数量)",
        TaskType.SUMMARIZE_ANALYZE,
        "Summarize then extract keywords",
        expected_numeric=(3, 5)
    ),
    HybridTest(
        "情感分类统计",
        "分析以下句子的情感：'今天太棒了'、'真倒霉'、'还不错'，然后统计积极情感的句子数量。输出格式：print(数量)",
        TaskType.SENTIMENT_CALC,
        "Sentiment analysis and counting",
        expected_numeric=(2, 1)  # 2 positive: 太棒了, 还不错
    ),
    HybridTest(
        "文本摘要评分",
        "总结这段话：'机器学习是人工智能的一个分支。它使计算机能够在没有明确编程的情况下学习。'，然后给摘要打分（每字1分）。输出格式：print(分数)",
        TaskType.SUMMARIZE_ANALYZE,
        "Summarize and score by length",
        expected_numeric=(20, 15)
    ),

    # ---- Sentiment + Calculation ----
    HybridTest(
        "情感加权计算",
        "分析'我很开心'的情感（积极=10分，消极=0分），然后分数乘以2输出。格式：print(20)",
        TaskType.SENTIMENT_CALC,
        "Sentiment score multiplied",
        expected_numeric=(20, 0)
    ),
    HybridTest(
        "多句情感平均分",
        "分析这3句：'天气真好'、'太差了'、'很喜欢'。积极=10分，消极=0分。计算3句的平均分（保留整数）。输出格式：print(平均分)",
        TaskType.SENTIMENT_CALC,
        "Average sentiment score",
        expected_numeric=(5, 1)
    ),
    HybridTest(
        "情感判断转换",
        "判断'今天天气真好'的情感，如果是积极输出1，消极输出0。输出格式：print(1或0)",
        TaskType.SENTIMENT_CALC,
        "Sentiment to binary conversion",
        expected_numeric=(1, 0)
    ),

    # ---- Extract + Process ----
    HybridTest(
        "提取数字求和",
        "从'我有3个苹果和5个橙子'中提取所有数字并求和。输出格式：print(8)",
        TaskType.EXTRACT_PROCESS,
        "Extract numbers and sum",
        expected_numeric=(8, 0)
    ),
    HybridTest(
        "提取邮箱验证",
        "用正则表达式判断'联系我@example.com'是否是有效邮箱格式，如果是输出'valid'，否则输出'invalid'",
        TaskType.EXTRACT_PROCESS,
        "Extract and validate email",
        expected_contains="valid"
    ),
    HybridTest(
        "提取排序",
        "从'分数：85, 92, 78, 95'中提取所有数字，排序后输出。输出格式：print([78,85,92,95])",
        TaskType.EXTRACT_PROCESS,
        "Extract and sort numbers",
        expected_pattern=r"78.*85.*92.*95"
    ),

    # ---- Recursive / Multi-step ----
    HybridTest(
        "链式翻译",
        "用 ask_sub_agent 把'你好'翻译成英文，再用 ask_sub_agent 把结果翻译回中文。输出格式：print(翻译结果)",
        TaskType.RECURSIVE,
        "Chain translation (zh->en->zh)",
        expected_contains="你好"
    ),
    HybridTest(
        "嵌套语义调用",
        "用 ask_sub_agent 问：'5乘以3等于几'，打印返回的答案。输出格式：print(15)",
        TaskType.RECURSIVE,
        "Nested sub-agent returning number",
        expected_numeric=(15, 1)
    ),
    HybridTest(
        "三级处理链",
        "1) 翻译'Hello'成中文 2) 统计字数 3) 乘以3。只输出最终结果数字。输出格式：print(6)",
        TaskType.RECURSIVE,
        "Three-step processing chain",
        expected_numeric=(6, 1)  # "你好"(2) * 3 = 6
    ),

    # ---- Complex Real-world Scenarios ----
    HybridTest(
        "评论分析系统",
        "分析评论'这个产品很棒，但价格有点贵'。规则：包含'很棒'等积极词+40分，包含'贵'等消极词-20分，基础分50分。输出最终评分。输出格式：print(70)",
        TaskType.SENTIMENT_CALC,
        "Complex sentiment scoring",
        expected_numeric=(70, 20)
    ),
    HybridTest(
        "多语言处理",
        "将'How are you?'翻译成中文，然后翻译成法语（用子Agent），统计总共调用了几次子Agent。输出格式：print(2)",
        TaskType.RECURSIVE,
        "Multi-language processing",
        expected_contains="2"
    ),
]


# =============================================================================
# Streaming Output Utilities
# =============================================================================

class StreamingDisplay:
    """Manages streaming-style terminal output with dynamic updates."""

    def __init__(self):
        self.lines = []
        self.active_spinner = False
        self.spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self.spinner_pos = 0
        self._stop_spinner = False
        self._spinner_thread = None

    def start_spinner(self, message: str = ""):
        """Start animated spinner."""
        self.active_spinner = True
        self._stop_spinner = False

        def spin():
            while not self._stop_spinner:
                char = self.spinner_chars[self.spinner_pos]
                sys.stdout.write(f"\r{Colors.OKCYAN}{char}{Colors.ENDC} {message}")
                sys.stdout.flush()
                self.spinner_pos = (self.spinner_pos + 1) % len(self.spinner_chars)
                time.sleep(0.1)

        self._spinner_thread = threading.Thread(target=spin, daemon=True)
        self._spinner_thread.start()

    def stop_spinner(self):
        """Stop animated spinner."""
        if self._spinner_thread:
            self._stop_spinner = True
            self._spinner_thread.join(timeout=0.2)
            self.active_spinner = False
            sys.stdout.write(f"\r{' ' * 50}\r")  # Clear spinner line
            sys.stdout.flush()

    def print_header(self, text: str):
        """Print a styled header."""
        self.stop_spinner()
        print(f"\n{Colors.BOLD}{Colors.HEADER}{'╔' + '═' * 68 + '╗'}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}║{Colors.ENDC} {text:^66} {Colors.BOLD}{Colors.HEADER}║{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}{'╚' + '═' * 68 + '╝'}{Colors.ENDC}")

    def print_section(self, title: str):
        """Print section header."""
        self.stop_spinner()
        print(f"\n{Colors.OKCYAN}│ {Colors.BOLD}{title}{Colors.ENDC}")
        print(f"{Colors.DIM}{'─' * 70}{Colors.ENDC}")

    def print_task_start(self, idx: int, total: int, task: HybridTest):
        """Print task start with animation."""
        self.stop_spinner()
        task_icons = {
            TaskType.TRANSLATE_LOGIC: "🌐",
            TaskType.SUMMARIZE_ANALYZE: "📝",
            TaskType.SENTIMENT_CALC: "💭",
            TaskType.EXTRACT_PROCESS: "🔍",
            TaskType.RECURSIVE: "🔄",
        }
        icon = task_icons.get(task.task_type, "📋")

        type_colors = {
            TaskType.TRANSLATE_LOGIC: Colors.OKBLUE,
            TaskType.SUMMARIZE_ANALYZE: Colors.OKCYAN,
            TaskType.SENTIMENT_CALC: Colors.WARNING,
            TaskType.EXTRACT_PROCESS: Colors.OKGREEN,
            TaskType.RECURSIVE: Colors.FAIL,
        }
        color = type_colors.get(task.task_type, Colors.ENDC)

        print(f"\n{icon} {Colors.BOLD}[{idx}/{total}]{Colors.ENDC} {color}{task.name}{Colors.ENDC}")
        print(f"{Colors.DIM}   Type: {task.task_type.value}{Colors.ENDC}")
        print(f"{Colors.DIM}   Query: {task.query[:50]}...{Colors.ENDC}")

    def print_sub_agent_call(self, depth: int, query: str):
        """Print sub-agent call with indentation."""
        indent = "  │  " * depth
        print(f"{indent}{Colors.OKCYAN}📞 Sub-Agent Call (L{depth}){Colors.ENDC}")
        print(f"{indent}{Colors.DIM}    → {query[:40]}...{Colors.ENDC}")
        self.start_spinner(f"{indent}    thinking")

    def print_sub_agent_result(self, depth: int, result: str):
        """Print sub-agent result."""
        self.stop_spinner()
        indent = "  │  " * depth
        preview = result[:30].replace("\n", " ")
        print(f"{indent}{Colors.OKGREEN}✓{Colors.ENDC} {preview}...")

    def print_logic_step(self, step: str):
        """Print logic processing step."""
        self.stop_spinner()
        print(f"  {Colors.WARNING}⚙{Colors.ENDC}  {step}")

    def print_task_result(self, success: bool, duration: float, output_preview: str):
        """Print final task result."""
        self.stop_spinner()
        if success:
            status = f"{Colors.OKGREEN}✓ PASS{Colors.ENDC}"
        else:
            status = f"{Colors.FAIL}✗ FAIL{Colors.ENDC}"

        time_str = self._format_duration(duration)
        preview = output_preview[:40].replace("\n", " ")

        print(f"  {status}  {time_str}  {Colors.DIM}{preview}...{Colors.ENDC}")

    def _format_duration(self, ms: float) -> str:
        """Format duration with color."""
        if ms < 5000:
            return f"{Colors.OKGREEN}{ms:.0f}ms{Colors.ENDC}"
        elif ms < 15000:
            return f"{Colors.WARNING}{ms:.0f}ms{Colors.ENDC}"
        else:
            return f"{Colors.FAIL}{ms:.0f}ms{Colors.ENDC}"

    def print_progress_bar(self, current: int, total: int):
        """Print progress bar."""
        pct = current / total
        bar_len = 40
        filled = int(pct * bar_len)
        bar = f"{Colors.OKGREEN}{'█' * filled}{Colors.ENDC}{Colors.DIM}{'░' * (bar_len - filled)}{Colors.ENDC}"
        print(f"\r  {bar} {current}/{total} ({pct*100:.0f}%)", end="", flush=True)

    def print_summary(self, results: list):
        """Print final summary report."""
        self.stop_spinner()
        self.print_header("Semantic-Logic Hybrid Benchmark Results")

        total = len(results)
        passed = sum(1 for r in results if r["success"])

        print(f"\n  {Colors.BOLD}Overall:{Colors.ENDC}")
        print(f"    Tests: {total}")
        print(f"    Passed: {Colors.OKGREEN if passed == total else Colors.WARNING}{passed}/{total} ({passed/total*100:.1f}%){Colors.ENDC}")

        # By task type
        print(f"\n  {Colors.BOLD}By Task Type:{Colors.ENDC}")
        by_type: dict[TaskType, list] = {t: [] for t in TaskType}
        for r in results:
            by_type[r["task_type"]].append(r)

        for task_type, tasks in by_type.items():
            if not tasks:
                continue
            p = sum(1 for t in tasks if t["success"])
            t_len = len(tasks)
            if p == t_len:
                icon = "🟢"
                color = Colors.OKGREEN
            elif p >= t_len * 0.5:
                icon = "🟡"
                color = Colors.WARNING
            else:
                icon = "🔴"
                color = Colors.FAIL
            print(f"    {icon} {task_type.value:12} {color}{p}/{t_len}{Colors.ENDC}")

        # Timing
        times = [r["duration"] for r in results]
        print(f"\n  {Colors.BOLD}Timing:{Colors.ENDC}")
        print(f"    Mean:   {mean(times):.0f}ms")
        print(f"    Median: {median(times):.0f}ms")
        print(f"    Min:    {min(times):.0f}ms")
        print(f"    Max:    {max(times):.0f}ms")

        # Sub-agent calls
        total_calls = sum(r.get("sub_agent_calls", 0) for r in results)
        print(f"\n  {Colors.BOLD}Sub-Agent Calls:{Colors.ENDC}")
        print(f"    Total: {total_calls}")
        print(f"    Avg per test: {total_calls/total:.1f}" if total > 0 else "    Avg per test: 0")

        # Detailed results
        print(f"\n  {Colors.BOLD}Detailed Results:{Colors.ENDC}")
        print(f"{'─' * 70}")
        for r in results:
            status = f"{Colors.OKGREEN}✓{Colors.ENDC}" if r["success"] else f"{Colors.FAIL}✗{Colors.ENDC}"
            calls_info = f" [{r.get('sub_agent_calls', 0)} calls]" if r.get('sub_agent_calls', 0) > 0 else ""
            print(f"  {status} {r['name']:<20} {r['duration']:>6.0f}ms{calls_info}")

        print()


# =============================================================================
# Test Execution
# =============================================================================

@dataclass
class HybridResult:
    """Result of a hybrid test."""
    test: HybridTest
    success: bool
    output: str
    duration: float
    sub_agent_calls: int = 0
    execution_error: str = ""


def parse_sub_agent_calls(stderr: str) -> int:
    """Parse sub-agent call count from stderr."""
    # Look for patterns like "Sub-Agent Call (L1)"
    matches = re.findall(r"Sub-Agent Call \(L(\d+)\)", stderr)
    return len(matches) if matches else 0


def run_hybrid_test(test: HybridTest, display: StreamingDisplay) -> HybridResult:
    """Run a single hybrid test with streaming display."""
    cmd = ["uv", "run", "python", "upa.py", "--timing", test.query]

    start_time = time.perf_counter()

    try:
        # Run command and capture output
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
        sub_calls = parse_sub_agent_calls(stderr)

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
        duration = 120000
        return HybridResult(
            test=test,
            success=False,
            output="",
            duration=duration,
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


def run_hybrid_benchmark(limit: int | None = None, filter_type: TaskType | None = None, workers: int = 4):
    """Run the hybrid benchmark suite with parallel execution."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading

    tests = HYBRID_CASES
    if filter_type:
        tests = [t for t in tests if t.task_type == filter_type]
    if limit:
        tests = tests[:limit]

    display = StreamingDisplay()
    display.print_header("🚀 UPA Semantic-Logic Hybrid Benchmark")
    print(f"\n  Running {len(tests)} hybrid tests with {workers} workers...")
    print(f"  Testing: ask_sub_agent() integration + logic processing\n")

    results = []
    results_lock = threading.Lock()
    progress_lock = threading.Lock()
    completed_count = [0]  # Use list for mutable closure

    def worker_task(idx: int, test: HybridTest):
        """Worker function to run a single test."""
        result = run_hybrid_test(test, display)

        with progress_lock:
            completed_count[0] += 1
            display.print_task_start(completed_count[0], len(tests), test)
            display.print_task_result(
                result.success,
                result.duration,
                result.output
            )
            if result.sub_agent_calls > 0:
                print(f"    {Colors.OKCYAN}📊 Sub-agent calls: {result.sub_agent_calls}{Colors.ENDC}")

        with results_lock:
            results.append((idx, result))

        return result

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
                    results.append((idx, HybridResult(
                        test=test,
                        success=False,
                        output="",
                        duration=0,
                        execution_error=str(e)
                    )))

    total_duration = (time.perf_counter() - start_time) * 1000

    # Sort results by original index
    results.sort(key=lambda x: x[0])
    sorted_results = [r for _, r in results]

    # Print summary
    print(f"\n{Colors.BOLD}⏱️  Suite completed in {total_duration:.0f}ms (parallel execution){Colors.ENDC}")
    display.print_summary([
        {
            "name": r.test.name,
            "success": r.success,
            "duration": r.duration,
            "task_type": r.test.task_type,
            "sub_agent_calls": r.sub_agent_calls,
        }
        for r in sorted_results
    ])

    return sorted_results


# =============================================================================
# CLI
# =============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="UPA Semantic-Logic Hybrid Benchmark"
    )
    parser.add_argument(
        "--type", "-t",
        choices=[t.value for t in TaskType],
        help="Filter by task type"
    )
    parser.add_argument(
        "--limit", "-n",
        type=int,
        help="Limit number of tests"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List test cases"
    )
    parser.add_argument(
        "--json", "-j",
        type=str,
        help="Export results to JSON"
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4)"
    )

    args = parser.parse_args()

    if args.list:
        print(f"\n{Colors.BOLD}Semantic-Logic Hybrid Test Cases:{Colors.ENDC}\n")
        for i, test in enumerate(HYBRID_CASES, 1):
            print(f"  [{i}] {test.name}")
            print(f"      Type: {test.task_type.value}")
            print(f"      Query: {test.query}")
            print(f"      Desc: {test.description}\n")
        return

    filter_type = None
    if args.type:
        for t in TaskType:
            if t.value == args.type:
                filter_type = t
                break

    results = run_hybrid_benchmark(limit=args.limit, filter_type=filter_type, workers=args.workers)

    if args.json:
        data = [{
            "name": r.test.name,
            "query": r.test.query,
            "task_type": r.test.task_type.value,
            "success": r.success,
            "duration_ms": r.duration,
            "sub_agent_calls": r.sub_agent_calls,
            "output": r.output[:200],
        } for r in results]
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"{Colors.OKGREEN}✓ Exported to {args.json}{Colors.ENDC}")


if __name__ == "__main__":
    main()
