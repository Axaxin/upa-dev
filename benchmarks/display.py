"""
Terminal display utilities for benchmark output.
"""

import os
import sys
import threading
import time
from dataclasses import dataclass
from statistics import mean, median

try:
    import benchmarks.suites.base as base
except ImportError:
    from suites import base


class Colors:
    """Terminal ANSI color codes."""
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"

    @classmethod
    def disable(cls):
        """Disable all colors."""
        for attr in dir(cls):
            if not attr.startswith("_") and attr.isupper():
                setattr(cls, attr, "")


# Disable colors on Windows or when NO_COLOR is set
if sys.platform == "win32" or os.getenv("NO_COLOR"):
    Colors.disable()


@dataclass
class TimingResult:
    """Parsed timing information from stderr."""
    llm_generate: float = 0
    code_extract: float = 0
    security_check: float = 0
    code_execute: float = 0
    total: float = 0
    self_heal: float = 0  # Time spent in self-healing retries

    @classmethod
    def from_stderr(cls, stderr: str) -> "TimingResult":
        """Parse timing from UPA stderr output."""
        import re

        # Remove ANSI color codes
        clean = re.sub(r'\033\[[0-9;]+m', '', stderr)
        timing = {}

        # Match timing lines like "  LLM Generate     1234.5ms"
        pattern = r"^\s*(\w[\w\s]+?)\s+(\d+\.?\d*)ms"
        for match in re.finditer(pattern, clean, re.MULTILINE):
            key = match.group(1).strip()
            value = float(match.group(2))
            timing[key] = value

        result = cls()
        result.llm_generate = timing.get("LLM Generate", timing.get("LLM Generate (Self-Heal)", 0))
        result.code_extract = timing.get("Code Extract", timing.get("Code Extract (Self-Heal)", 0))
        result.security_check = timing.get("Security Check", timing.get("Security Check (Self-Heal)", 0))
        result.code_execute = timing.get("Code Execute", 0)

        # Sum all for total
        result.total = sum(timing.values())

        # Self-healing time includes any (Self-Heal) tagged times
        result.self_heal = sum(v for k, v in timing.items() if "Self-Heal" in k)

        return result


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
            sys.stdout.write(f"\r{' ' * 50}\r")
            sys.stdout.flush()

    def print_header(self, text: str):
        """Print a styled header."""
        self.stop_spinner()
        border = "═" * 68
        print(f"\n{Colors.BOLD}{Colors.HEADER}╔{border}╗{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}║ {text:^64} ║{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}╚{border}╝{Colors.ENDC}")

    def print_section(self, title: str):
        """Print section header."""
        self.stop_spinner()
        print(f"\n{Colors.OKCYAN}│ {Colors.BOLD}{title}{Colors.ENDC}")
        print(f"{Colors.DIM}{'─' * 70}{Colors.ENDC}")

    def print_task_start(self, idx: int, total: int, name: str, task_type: str = "", query: str = ""):
        """Print task start with animation."""
        self.stop_spinner()

        # Choose icon based on task type
        task_icons = {
            "翻译+逻辑": "🌐",
            "总结+分析": "📝",
            "情感+计算": "💭",
            "提取+处理": "🔍",
            "递归调用": "🔄",
        }
        icon = task_icons.get(task_type, "📋")

        # Choose color based on complexity
        comp_colors = {
            "简单": Colors.OKGREEN,
            "中等": Colors.WARNING,
            "复杂": Colors.FAIL,
            "边缘案例": Colors.OKCYAN,
        }
        color = comp_colors.get(task_type, Colors.ENDC)

        print(f"\n{icon} {Colors.BOLD}[{idx}/{total}]{Colors.ENDC} {color}{name}{Colors.ENDC}")
        if task_type and task_type in comp_colors:
            print(f"{Colors.DIM}   Type: {task_type}{Colors.ENDC}")
        if query:
            print(f"{Colors.DIM}   Query: {query[:50]}...{Colors.ENDC}")

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

    def print_summary(self, results: list[dict]):
        """Print final summary report."""
        self.stop_spinner()
        self.print_header("Benchmark Results")

        total = len(results)
        passed = sum(1 for r in results if r["success"])

        print(f"\n  {Colors.BOLD}Overall:{Colors.ENDC}")
        print(f"    Tests: {total}")
        print(f"    Passed: {Colors.OKGREEN if passed == total else Colors.WARNING}{passed}/{total} ({passed/total*100:.1f}%){Colors.ENDC}")

        # By task type/complexity
        type_key = "task_type" if "task_type" in results[0] else "complexity"
        if type_key in results[0]:
            print(f"\n  {Colors.BOLD}By {type_key.replace('_', ' ').title()}:{Colors.ENDC}")
            by_type: dict = {}
            for r in results:
                t = r[type_key]
                if hasattr(t, 'value'):
                    t = t.value
                if t not in by_type:
                    by_type[t] = []
                by_type[t].append(r)

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
                print(f"    {icon} {str(task_type):12} {color}{p}/{t_len}{Colors.ENDC}")

        # Timing
        times = [r["duration"] for r in results if "duration" in r]
        if times:
            print(f"\n  {Colors.BOLD}Timing:{Colors.ENDC}")
            print(f"    Mean:   {mean(times):.0f}ms")
            print(f"    Median: {median(times):.0f}ms")
            print(f"    Min:    {min(times):.0f}ms")
            print(f"    Max:    {max(times):.0f}ms")

        # Sub-agent calls (for hybrid tests)
        if any("sub_agent_calls" in r for r in results):
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
            print(f"  {status} {r['name']:<20} {r.get('duration', 0):>6.0f}ms{calls_info}")

        print()


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
