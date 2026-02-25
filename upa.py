#!/usr/bin/env python3
"""
UPA (Unified Programmatic Architecture) MVP
A single-file CLI that implements the "Always-Code Execution" paradigm.

Usage:
    uv run python upa.py "你的问题"
    uv run python upa.py --show-code "你的问题"
    uv run python upa.py --timing "你的问题"
"""

import argparse
import ast
import io
import re
import sys
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


# =============================================================================
# Timing Infrastructure
# =============================================================================

@dataclass
class TimingRecord:
    """Record for a single timing measurement."""
    name: str
    duration_ms: float


@dataclass
class Timer:
    """Timer for tracking execution phases."""
    records: list[TimingRecord] = field(default_factory=list)
    _start_time: float | None = field(default=None, repr=False)
    _current_name: str = ""

    def start(self, name: str) -> "Timer":
        """Start timing a phase."""
        self._current_name = name
        self._start_time = time.perf_counter()
        return self

    def stop(self) -> "Timer":
        """Stop timing and record the duration."""
        if self._start_time is not None:
            duration = (time.perf_counter() - self._start_time) * 1000
            self.records.append(TimingRecord(self._current_name, duration))
            self._start_time = None
        return self

    def total_ms(self) -> float:
        """Get total time in milliseconds."""
        return sum(r.duration_ms for r in self.records)

    def print_report(self, file=None):
        """Print a terminal-friendly timing report."""
        if file is None:
            file = sys.stderr

        total = self.total_ms()
        if total == 0:
            return

        print("\n⏱  Timing Report", file=file)
        print("─" * 40, file=file)

        for record in self.records:
            pct = (record.duration_ms / total) * 100 if total > 0 else 0
            bar_len = int(pct / 5)
            bar = "█" * bar_len + "░" * (20 - bar_len)

            # Color coding based on duration
            if record.duration_ms < 100:
                color = "\033[92m"  # Green
            elif record.duration_ms < 1000:
                color = "\033[93m"  # Yellow
            else:
                color = "\033[91m"  # Red
            reset = "\033[0m"

            print(f"  {record.name:16} {color}{record.duration_ms:>7.1f}ms{reset} [{bar}] {pct:>5.1f}%", file=file)

        print("─" * 40, file=file)
        print(f"  {'Total':16} \033[96m{total:>7.1f}ms\033[0m", file=file)


# Load environment variables
load_dotenv()

# Configuration from .env
import os

DASHSCOPE_URL = os.getenv("DASHSCOPE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_MODEL = os.getenv("DASHSCOPE_MODEL", "qwen-plus")

# System Prompt: Always-Code
SYSTEM_PROMPT = """你是一个 Python 逻辑单元。你的回答必须仅包含一个 Python 代码块。

规则：
1. 所有输出都必须通过 print() 语句输出
2. 闲聊场景：生成 print("回复内容")
3. 计算场景：生成计算逻辑并 print 结果
4. 数据处理：可以使用 datetime, json, re, math 等标准库

重要：不要输出任何代码块之外的文字，只输出 ```python ... ```"""

# Security: Blocked modules and functions
BLOCKED_MODULES = {
    "os", "subprocess", "sys", "socket", "shutil", "pathlib",
    "builtins", "importlib", "ctypes", "multiprocessing", "threading",
    "pickle", "shelve", "marshal", "code", "codeop", "commands",
    "pty", "fcntl", "pipes", "posix", "posixpath", "signal",
}

BLOCKED_BUILTINS = {
    "eval", "exec", "compile", "__import__", "open", "input",
    "breakpoint", "globals", "locals", "vars", "dir",
    "getattr", "setattr", "delattr", "hasattr",
    "__build_class__", "__name__", "__doc__",
}

# Allowed modules for sandbox
ALLOWED_MODULES = {
    "datetime", "json", "re", "math", "random", "collections",
    "itertools", "functools", "operator", "string", "textwrap",
    "unicodedata", "decimal", "fractions", "statistics", "copy",
}


class SecurityChecker(ast.NodeVisitor):
    """AST visitor to check for dangerous code patterns."""

    def __init__(self):
        self.violations: list[str] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            module_name = alias.name.split(".")[0]
            if module_name in BLOCKED_MODULES:
                self.violations.append(f"Blocked import: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            module_name = node.module.split(".")[0]
            if module_name in BLOCKED_MODULES:
                self.violations.append(f"Blocked import from: {node.module}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            if node.func.id in BLOCKED_BUILTINS:
                self.violations.append(f"Blocked function call: {node.func.id}()")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        # Block __subclasses__, __class__, __bases__, etc.
        if node.attr.startswith("_"):
            if node.attr in {"__subclasses__", "__class__", "__bases__", "__mro__",
                             "__globals__", "__code__", "__builtins__"}:
                self.violations.append(f"Blocked attribute access: {node.attr}")
        self.generic_visit(node)


def check_code_safety(code: str) -> list[str]:
    """
    Perform AST-based security check on code.
    Returns list of violations (empty if safe).
    """
    try:
        tree = ast.parse(code)
        checker = SecurityChecker()
        checker.visit(tree)
        return checker.violations
    except SyntaxError as e:
        return [f"Syntax error: {e}"]


def create_client() -> OpenAI:
    """Create OpenAI client configured for DashScope."""
    return OpenAI(
        api_key=DASHSCOPE_API_KEY,
        base_url=DASHSCOPE_URL,
    )


def generate_code(client: OpenAI, query: str) -> str:
    """Call LLM to generate Python code for the query."""
    response = client.chat.completions.create(
        model=DASHSCOPE_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content or ""


def extract_code(response: str) -> str | None:
    """Extract Python code from LLM response."""
    # Try to find ```python ... ``` block
    pattern = r"```python\s*\n(.*?)\n```"
    match = re.search(pattern, response, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Fallback: try ``` ... ``` without language specifier
    pattern = r"```\s*\n(.*?)\n```"
    match = re.search(pattern, response, re.DOTALL)
    if match:
        return match.group(1).strip()

    return None


def execute_code(code: str) -> tuple[str, str]:
    """
    Execute Python code in a sandbox-like environment.
    Returns (stdout, error_message).
    """
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    # Restricted globals for sandbox
    sandbox_globals = {
        "__builtins__": __builtins__,
        "datetime": __import__("datetime"),
        "json": __import__("json"),
        "re": __import__("re"),
        "math": __import__("math"),
        "random": __import__("random"),
        "collections": __import__("collections"),
        "itertools": __import__("itertools"),
    }

    try:
        exec(code, sandbox_globals)
        output = sys.stdout.getvalue()
        return output, ""
    except Exception:
        return "", traceback.format_exc()
    finally:
        sys.stdout = old_stdout


def main():
    parser = argparse.ArgumentParser(
        description="UPA - Unified Programmatic Architecture CLI"
    )
    parser.add_argument("query", help="The query to process")
    parser.add_argument(
        "--show-code",
        action="store_true",
        help="Show the generated Python code before execution",
    )
    parser.add_argument(
        "--timing",
        action="store_true",
        help="Show timing report after execution",
    )

    args = parser.parse_args()

    # Initialize timer
    timer = Timer()

    # Validate API key
    if not DASHSCOPE_API_KEY:
        print("Error: DASHSCOPE_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)

    # Create client
    client = create_client()

    # Generate code (LLM call)
    print("Thinking...", file=sys.stderr)
    timer.start("LLM Generate")
    response = generate_code(client, args.query)
    timer.stop()

    # Extract code
    timer.start("Code Extract")
    code = extract_code(response)
    timer.stop()

    if not code:
        print("No Python code found in response:", file=sys.stderr)
        print(response)
        sys.exit(1)

    # Show code if requested
    if args.show_code:
        print("--- Generated Code ---", file=sys.stderr)
        print(code, file=sys.stderr)
        print("--- Execution Result ---", file=sys.stderr)

    # Security check
    timer.start("Security Check")
    violations = check_code_safety(code)
    timer.stop()

    if violations:
        print("Security violations detected:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        sys.exit(1)

    # Execute code
    timer.start("Code Execute")
    output, error = execute_code(code)
    timer.stop()

    if error:
        print("Execution Error:", file=sys.stderr)
        print(error, file=sys.stderr)
        sys.exit(1)

    # Print result
    print(output, end="")

    # Show timing report if requested
    if args.timing:
        timer.print_report()


if __name__ == "__main__":
    main()
