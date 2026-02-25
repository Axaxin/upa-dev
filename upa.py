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

# =============================================================================
# Sub-Agent Context (for recursive calls)
# =============================================================================

class SubAgentContext:
    """Context for tracking sub-agent recursion depth."""
    _depth = 0
    _enabled = True

    @classmethod
    def depth(cls) -> int:
        """Get current recursion depth."""
        return cls._depth

    @classmethod
    def increment(cls) -> int:
        """Increment depth and return new value."""
        cls._depth += 1
        return cls._depth

    @classmethod
    def decrement(cls) -> int:
        """Decrement depth and return new value."""
        cls._depth = max(0, cls._depth - 1)
        return cls._depth

    @classmethod
    def reset(cls):
        """Reset depth to zero."""
        cls._depth = 0

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if sub-agent calls are enabled."""
        return cls._enabled

    @classmethod
    def disable(cls):
        """Disable sub-agent calls (for security)."""
        cls._enabled = False

DASHSCOPE_URL = os.getenv("DASHSCOPE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_MODEL = os.getenv("DASHSCOPE_MODEL", "qwen-plus")

# =============================================================================
# Provider Configuration
# =============================================================================

@dataclass
class ProviderConfig:
    """LLM provider configuration."""
    name: str
    url: str
    api_key: str
    model: str

# Predefined providers
PROVIDERS = {
    "dashscope": ProviderConfig(
        name="DashScope (阿里云)",
        url=DASHSCOPE_URL,
        api_key=DASHSCOPE_API_KEY,
        model=DASHSCOPE_MODEL,
    ),
    "cloudflare": ProviderConfig(
        name="Cloudflare Gateway + Grok",
        url=os.getenv("CLOUDFLARE_URL", "https://gateway.ai.cloudflare.com/v1/632ba9b9506a87e7fe1d5f7e7db78d57/gemini/compat"),
        api_key=os.getenv("CLOUDFLARE_API_KEY", ""),
        model=os.getenv("CLOUDFLARE_MODEL", "grok/grok-4-1-fast-non-reasoning"),
    ),
}

# Default provider (can be overridden by env var or CLI)
DEFAULT_PROVIDER = os.getenv("UPA_PROVIDER", "cloudflare")

def get_provider(provider_name: str | None = None) -> ProviderConfig:
    """Get provider configuration by name."""
    if provider_name is None:
        provider_name = DEFAULT_PROVIDER

    if provider_name in PROVIDERS:
        return PROVIDERS[provider_name]

    # Try to load from environment with custom provider name
    env_url = os.getenv(f"{provider_name.upper()}_URL")
    env_key = os.getenv(f"{provider_name.upper()}_API_KEY")
    env_model = os.getenv(f"{provider_name.upper()}_MODEL")

    if env_url and env_key:
        return ProviderConfig(
            name=provider_name,
            url=env_url,
            api_key=env_key,
            model=env_model or "default",
        )

    raise ValueError(f"Unknown provider: {provider_name}. Available: {list(PROVIDERS.keys())}")

def list_providers() -> None:
    """List all available providers."""
    print("Available LLM Providers:")
    print("─" * 50)
    for key, provider in PROVIDERS.items():
        default = " (default)" if key == DEFAULT_PROVIDER else ""
        print(f"  {key:12} → {provider.name}{default}")
    print()
    print("Usage:")
    print(f"  upa.py --provider <name> \"your query\"")

# System Prompt: Always-Code
SYSTEM_PROMPT = """你是一个 Python 逻辑单元。你的回答必须仅包含一个 Python 代码块。

规则：
1. 所有输出都必须通过 print() 语句输出
2. 闲聊场景：生成 print("回复内容")
3. 计算场景：生成计算逻辑并 print 结果
4. 数据处理：可以使用 datetime, json, re, math 等标准库

可用的特殊函数：
- ask_sub_agent(query: str) -> str: 用于处理语义理解、翻译、总结等需要 AI 的任务。
  调用后会返回处理结果的字符串。
  示例: result = ask_sub_agent("请总结这段文本的主旨")

使用场景：
- 纯逻辑/计算任务：直接用 Python 代码
- 需要语义理解/翻译/总结：使用 ask_sub_agent()
- 混合任务：先获取语义信息，再做逻辑处理

重要：
- 不要输出任何代码块之外的文字
- 只输出 ```python ... ``` 格式的代码"""

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

# Sub-Agent configuration
MAX_SUB_AGENT_DEPTH = 3   # Max recursive depth for sub-agent calls
SUB_AGENT_TIMEOUT = 60    # Timeout for sub-agent calls in seconds


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


def ask_sub_agent(query: str, client: OpenAI | None = None, model: str = None) -> str:
    """
    Sub-agent function for semantic tasks.
    This function is injected into the sandbox for LLM-generated code to call.

    Args:
        query: The semantic query to process
        client: OpenAI client (will be created if not provided)
        model: Model name to use

    Returns:
        The output string from executing the sub-agent's code

    Example usage in sandbox:
        summary = ask_sub_agent("总结这段文字")
        translation = ask_sub_agent("Translate to English: Hello")
    """
    # Check if sub-agent calls are enabled
    if not SubAgentContext.is_enabled():
        return "[Error: Sub-agent calls disabled]"

    # Check recursion depth
    current_depth = SubAgentContext.depth()
    if current_depth >= MAX_SUB_AGENT_DEPTH:
        return f"[Error: Maximum sub-agent depth ({MAX_SUB_AGENT_DEPTH}) reached]"

    # Increment depth for this call
    SubAgentContext.increment()
    depth = SubAgentContext.depth()

    # Output sub-agent call info to stderr for tracking
    print(f"Sub-Agent Call (L{depth}): {query[:50]}...", file=sys.stderr)

    # Get default model if not specified
    if model is None:
        provider = get_provider()
        model = provider.model

    try:
        # Create client if not provided
        if client is None:
            client = create_client()

        # Sub-agent system prompt (similar but indicates it's a sub-agent call)
        sub_prompt = f"""你是一个 Python 语义处理子程序（深度 {depth}/{MAX_SUB_AGENT_DEPTH}）。
你的回答必须仅包含一个 Python 代码块，用 print() 输出结果。

这是一个子任务，专注于语义处理：
- 翻译任务：输出翻译后的文本
- 总结任务：输出总结内容
- 理解任务：输出理解结果

只输出代码，不要解释。"""

        # Call LLM for sub-agent
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError("Sub-agent call timed out")

        # Set timeout (works on Unix systems)
        if hasattr(signal, 'SIGALRM'):
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(SUB_AGENT_TIMEOUT)

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": sub_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.7,
            )
        finally:
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)  # Cancel alarm

        response_content = response.choices[0].message.content or ""

        # Extract code from response
        code = extract_code(response_content)
        if not code:
            return f"[Error: Sub-agent did not return valid code]"

        # Optional: security check for sub-agent code
        violations = check_code_safety(code)
        if violations:
            return f"[Error: Sub-agent code security violation: {violations[0]}]"

        # Execute sub-agent code
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

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
            return output.rstrip()  # Remove trailing whitespace
        except Exception as e:
            return f"[Error: Sub-agent execution failed: {str(e)}]"
        finally:
            sys.stdout = old_stdout

    except TimeoutError:
        return f"[Error: Sub-agent call timed out after {SUB_AGENT_TIMEOUT}s]"
    except Exception as e:
        return f"[Error: Sub-agent call failed: {str(e)}]"
    finally:
        # Always decrement depth when done
        SubAgentContext.decrement()


def create_client(provider: ProviderConfig | None = None) -> OpenAI:
    """Create OpenAI client configured for the specified provider."""
    if provider is None:
        provider = get_provider()
    return OpenAI(
        api_key=provider.api_key,
        base_url=provider.url,
    )


def generate_code(client: OpenAI, query: str, model: str, error_feedback: str | None = None, conversation_history: list | None = None) -> tuple[str, list]:
    """
    Call LLM to generate Python code for the query.

    Args:
        client: OpenAI client
        query: User query
        model: Model name to use
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
        model=model,
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


def execute_code(code: str, client: OpenAI | None = None, provider: ProviderConfig | None = None) -> tuple[str, str]:
    """
    Execute Python code in a sandbox-like environment.
    Returns (stdout, error_message).
    """
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    # Get provider for model name (use passed provider or default)
    if provider is None:
        provider = get_provider()

    # Create a partial function for ask_sub_agent with the client and model
    def make_ask_sub_agent(llm_client: OpenAI, model_name: str):
        def ask_sub_agent_wrapper(query: str) -> str:
            return ask_sub_agent(query, client=llm_client, model=model_name)
        return ask_sub_agent_wrapper

    # Get model name for sub-agent calls
    if client:
        ask_sub_agent_fn = make_ask_sub_agent(client, provider.model)
    else:
        ask_sub_agent_fn = lambda q: "[Error: No LLM client]"

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
        # Inject ask_sub_agent if client is available
        "ask_sub_agent": ask_sub_agent_fn,
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
        description="UPA - Unified Programmatic Architecture CLI",
        epilog="Available providers: " + ", ".join(PROVIDERS.keys())
    )
    parser.add_argument("query", nargs='?', help="The query to process")
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
    parser.add_argument(
        "--provider", "-p",
        choices=list(PROVIDERS.keys()),
        help=f"LLM provider to use (default: {DEFAULT_PROVIDER})",
    )
    parser.add_argument(
        "--list-providers",
        action="store_true",
        help="List all available LLM providers",
    )

    args = parser.parse_args()

    # Handle --list-providers
    if args.list_providers:
        list_providers()
        sys.exit(0)

    # Validate query is provided
    if not args.query:
        parser.print_help()
        sys.exit(1)

    # Reset sub-agent context for fresh execution
    SubAgentContext.reset()

    # Get provider configuration
    provider = get_provider(args.provider)

    # Initialize timer
    timer = Timer()

    # Validate API key
    if not provider.api_key:
        print(f"Error: API key not set for provider '{args.provider or DEFAULT_PROVIDER}'", file=sys.stderr)
        sys.exit(1)

    # Create client with selected provider
    client = create_client(provider)
    model = provider.model

    # Show provider info
    print(f"Using: {provider.name} ({model})", file=sys.stderr)

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
            model,
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
    output, error = execute_code(code, client=client, provider=provider)
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
