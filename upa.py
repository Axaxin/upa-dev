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

# Retry configuration
MAX_SECURITY_RETRIES = 3  # Max retries for security violations


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


def generate_code(client: OpenAI, query: str, error_feedback: str | None = None, conversation_history: list | None = None) -> tuple[str, list]:
    """
    Call LLM to generate Python code for the query.

    Args:
        client: OpenAI client
        query: User query
        error_feedback: Optional error message from previous attempt
        conversation_history: Previous messages for retry context

    Returns:
        (response_content, updated_conversation_history)
    """
    # Build message list
    if conversation_history is None:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]
    else:
        messages = conversation_history

    # Add error feedback if provided
    if error_feedback:
        messages.append({
            "role": "user",
            "content": f"{query}\n\n【上一次代码的安全检查错误】：\n{error_feedback}\n\n请修复上述问题，重新生成代码。只输出代码，不要解释。"
        })
    else:
        messages.append({
            "role": "user",
            "content": query
        })

    response = client.chat.completions.create(
        model=DASHSCOPE_MODEL,
        messages=messages,
        temperature=0.7,
    )

    return response.choices[0].message.content or "", messages


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

    # ==========================================================================
    # Phase 1: Code Generation with Security Retry Loop
    # ==========================================================================
    print("Thinking...", file=sys.stderr)

    # Use separate timers for nested operations
    llm_timer = Timer()
    security_timer = Timer()
    code_extract_timer = Timer()

    code = None
    response = None
    conversation_history = None
    error_feedback = None

    for attempt in range(MAX_SECURITY_RETRIES):
        # Generate code (with error feedback on retry)
        llm_timer.start("LLM Generate")
        response, conversation_history = generate_code(
            client,
            args.query,
            error_feedback=error_feedback,
            conversation_history=conversation_history
        )
        llm_timer.stop()

        # Extract code
        code_extract_timer.start("Code Extract")
        code = extract_code(response)
        code_extract_timer.stop()

        if not code:
            if attempt < MAX_SECURITY_RETRIES - 1:
                error_feedback = "错误：未找到Python代码块。请确保输出格式为 ```python ... ```"
                print(f"  No code block found, retrying... ({attempt + 1}/{MAX_SECURITY_RETRIES})", file=sys.stderr)
                continue
            else:
                print("\n无法生成有效的Python代码。", file=sys.stderr)
                print(f"LLM原始响应:\n{response}", file=sys.stderr)
                sys.exit(1)

        # Security check
        security_timer.start("Security Check")
        violations = check_code_safety(code)
        security_timer.stop()

        if violations:
            if attempt < MAX_SECURITY_RETRIES - 1:
                # Build error feedback for retry
                error_feedback = "安全违规：\n" + "\n".join(f"  - {v}" for v in violations)
                print(f"  Security violations detected, retrying... ({attempt + 1}/{MAX_SECURITY_RETRIES})", file=sys.stderr)
                continue
            else:
                print(f"\n经过 {MAX_SECURITY_RETRIES} 次尝试，仍无法生成符合安全要求的代码。", file=sys.stderr)
                print("检测到的安全问题:", file=sys.stderr)
                for v in violations:
                    print(f"  - {v}", file=sys.stderr)
                if args.show_code:
                    print("\n生成的代码:", file=sys.stderr)
                    print(code, file=sys.stderr)
                sys.exit(1)

        # Security passed, exit retry loop
        break

    # Merge all timers into the main timer for reporting
    timer.records.extend(llm_timer.records)
    timer.records.extend(code_extract_timer.records)
    timer.records.extend(security_timer.records)

    # Show code if requested
    if args.show_code:
        print("--- Generated Code ---", file=sys.stderr)
        print(code, file=sys.stderr)
        print("--- Execution Result ---", file=sys.stderr)

    # ==========================================================================
    # Phase 2: Execute Code (with error reporting, no retry for logic errors)
    # ==========================================================================
    timer.start("Code Execute")
    output, error = execute_code(code)
    timer.stop()

    if error:
        print(f"\n代码执行时发生错误:", file=sys.stderr)
        print(error, file=sys.stderr)
        print(f"\n问题类型: 代码逻辑错误（非安全问题）", file=sys.stderr)
        print(f"建议: 检查代码逻辑或重新表述您的需求", file=sys.stderr)
        if args.show_code:
            print("\n执行的代码:", file=sys.stderr)
            print(code, file=sys.stderr)
        sys.exit(1)

    # Print result
    print(output, end="")

    # Show timing report if requested
    if args.timing:
        timer.print_report()


if __name__ == "__main__":
    main()
