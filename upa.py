#!/usr/bin/env python3
"""
UPA (Unified Programmatic Architecture) MVP
A single-file CLI that implements the "Always-Code Execution" paradigm.

Usage:
    uv run python upa.py "你的问题"
    uv run python upa.py --show-code "你的问题"
    uv run python upa.py --timing "你的问题"
    uv run python upa.py --show-config  # Show current configuration
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import os
import re
import sys
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# =============================================================================
# Planner Module (Phase 5: Dynamic Prompt Construction)
# =============================================================================

from typing import Any


@dataclass
class PlanStep:
    """Single step in a decomposed plan."""
    order: int
    description: str
    tool_needed: str | None
    expected_output: str
    dependencies: list[int] = field(default_factory=list)


@dataclass
class Plan:
    """Structured output from Planner."""
    # Intent classification
    intent: str  # "simple_chat" | "computation" | "semantic" | "hybrid" | "multi_step"
    complexity: str  # "trivial" | "simple" | "medium" | "complex"

    # Task decomposition
    steps: list[PlanStep] = field(default_factory=list)

    # Dynamic tool selection
    required_tools: list[str] = field(default_factory=list)
    relevant_modules: list[str] = field(default_factory=list)

    # Guidance for Coder
    coding_hints: list[str] = field(default_factory=list)
    expected_output_type: str = "string"

    # Planner confidence
    confidence: float = 0.8

    # Fallback flag
    skip_planning: bool = False

    # Post-processing configuration
    requires_post_processing: bool = False  # 是否需要输出整理
    output_format_hint: str = ""  # 输出格式提示


@dataclass
class ToolDefinition:
    """Definition of an injectable tool."""
    name: str
    description: str
    usage_doc: str
    categories: list[str]
    complexity_score: int


# Tool Registry
TOOL_REGISTRY: dict[str, ToolDefinition] = {
    "ask_sub_agent": ToolDefinition(
        name="ask_sub_agent",
        description="Delegate semantic tasks to sub-agent",
        usage_doc="""- ask_sub_agent(query: str) -> str: 用于处理语义理解、翻译、总结等需要 AI 的任务。
  调用后会返回处理结果的字符串。内部有自愈机制，执行失败时会自动修复。
  示例: result = ask_sub_agent("请总结这段文本的主旨")""",
        categories=["semantic"],
        complexity_score=2,
    ),
    "web_search": ToolDefinition(
        name="web_search",
        description="Search the web for real-time information",
        usage_doc="""- web_search(query: str, num_results: int = 5) -> dict: 网络搜索获取实时信息。
  返回结构化数据: {"answer": "...", "results": [{"title": "...", "content": "...", "url": "..."}], "error": None}

  示例:
    data = web_search("Python 3.12 新特性")

    # 检查错误
    if data.get("error"):
        print(f"搜索失败: {data['error']}")
    else:
        # 格式化输出
        if data["answer"]:
            print(f"答案: {data['answer']}")
        for r in data["results"]:
            print(f"• {r['title']}: {r['content'][:100]}...")

    # 复杂任务可加 assert 自检
    assert data.get("results"), "搜索无结果"
    assert len(data["results"]) > 0, "未找到相关信息"
""",
        categories=["search", "fact-checking"],
        complexity_score=2,
    ),
    "safe_sub_agent": ToolDefinition(
        name="safe_sub_agent",
        description="Decorator syntax sugar for sub-agent calls",
        usage_doc="""- safe_sub_agent(query): 装饰器，简化 ask_sub_agent 调用的语法糖。

  使用方式 1 - 装饰空函数:
  ```python
@safe_sub_agent("将 'Hello' 翻译成中文")
def translation(result):
    print(result)

translation()
```

  使用方式 2 - 装饰带参数的函数:
  ```python
@safe_sub_agent("总结文字")
def summarize(text, result):
    print(f"原文: {text}")
    print(f"摘要: {result}")

summarize("长文本...")
```""",
        categories=["utility"],
        complexity_score=1,
    ),
}


# Planner System Prompt
PLANNER_SYSTEM_PROMPT = """你是一个任务规划器。分析用户查询并输出结构化的执行计划。

你的职责：
1. 识别用户意图（闲聊、计算、语义处理、多步骤任务）
2. 评估任务复杂度
3. 确定需要哪些工具（ask_sub_agent, web_search, safe_sub_agent）
4. 为复杂任务分解步骤
5. 提供编码提示
6. 判断是否需要输出整理（对执行结果进行二次格式化）

输出格式（严格JSON）：
{
  "intent": "simple_chat|computation|semantic|hybrid|multi_step",
  "complexity": "trivial|simple|medium|complex",
  "required_tools": ["ask_sub_agent", "web_search"],
  "relevant_modules": ["datetime", "json", "re", "math"],
  "steps": [
    {"order": 1, "description": "...", "tool_needed": "ask_sub_agent", "expected_output": "...", "dependencies": []},
    {"order": 2, "description": "...", "tool_needed": null, "expected_output": "...", "dependencies": [0]}
  ],
  "coding_hints": ["提示1", "提示2"],
  "expected_output_type": "number|string|list|dict|mixed",
  "confidence": 0.95,
  "skip_planning": false,
  "requires_post_processing": false,
  "output_format_hint": ""
}

工具说明：
- ask_sub_agent: 用于翻译、总结、情感分析等语义任务
- web_search: 用于查询实时信息、事实核查
- safe_sub_agent: 语法糖装饰器，简化 sub-agent 调用

判断规则：
- 简单问候/闲聊 → intent="simple_chat", complexity="trivial", required_tools=[], skip_planning=true
- 纯数学计算（一步运算）→ intent="computation", complexity="simple", required_tools=[], relevant_modules=["math"]
- 需要设计算法/多步推理 → intent="computation", complexity="medium" 或 "complex"
- 需要翻译/总结 → intent="semantic", required_tools=["ask_sub_agent"]
- 翻译+计算等混合 → intent="hybrid", required_tools=["ask_sub_agent"], steps详细分解
- 多步骤复杂任务 → intent="multi_step", complexity="medium" 或 "complex", 提供完整steps分解
- 需要查资料 → required_tools加入["web_search"]

复杂度判断：
- trivial: 简单问候、感谢、纯表情
- simple: 单步计算、简单问答、基础操作
- medium: 需要设计算法、多步逻辑、数据处理
- complex: 需要深度推理、复杂算法设计、多约束条件

输出整理判断（requires_post_processing）：
- 网络搜索任务 → requires_post_processing=true（搜索结果需要格式化）
- 获取复杂数据需要总结 → requires_post_processing=true
- 需要多步骤整合的信息 → requires_post_processing=true
- 简单计算/翻译 → requires_post_processing=false

只输出JSON，不要其他文字。
"""


def is_trivial_query(query: str) -> bool:
    """Detect queries that don't need planning."""
    trivial_patterns = [
        r'^[你好吗嗨嘿嗯]+[！!？?。.，,]*$',  # Simple greetings
        r'^(谢谢|感谢|thanks|thank you)',  # Thank you
        r'^[0-9+\-*/\s().ps()]+$',  # Pure math expression (including ^ for power)
        r'^.{1,3}$',  # Very short queries
    ]

    for pattern in trivial_patterns:
        if re.match(pattern, query.strip(), re.IGNORECASE):
            return True
    return False


def create_default_plan(
    intent: str = "unknown",
    skip_planning: bool = False,
    confidence: float = 0.5,
) -> Plan:
    """Create a safe default plan when planner fails."""
    return Plan(
        intent=intent,
        complexity="simple",
        steps=[],
        required_tools=["ask_sub_agent"],  # Include most common tool
        relevant_modules=["datetime", "json", "re", "math"],
        coding_hints=[],
        expected_output_type="string",
        confidence=confidence,
        skip_planning=skip_planning,
    )


def validate_plan(plan: Plan) -> Plan:
    """Validate and sanitize plan output."""
    # Ensure required_tools only contains valid tools
    valid_tools = set(TOOL_REGISTRY.keys())
    plan.required_tools = [t for t in plan.required_tools if t in valid_tools]

    # Cap steps to prevent runaway decomposition
    if len(plan.steps) > 5:
        plan.steps = plan.steps[:5]
        plan.coding_hints.append("任务已简化，专注于核心步骤")

    # Ensure confidence is in valid range
    plan.confidence = max(0.0, min(1.0, plan.confidence))

    return plan


def parse_plan_from_json(json_str: str) -> Plan | None:
    """Parse Plan from JSON string."""
    try:
        data = json.loads(json_str)

        # Parse steps
        steps = []
        for step_data in data.get("steps", []):
            steps.append(PlanStep(
                order=step_data.get("order", 0),
                description=step_data.get("description", ""),
                tool_needed=step_data.get("tool_needed"),
                expected_output=step_data.get("expected_output", ""),
                dependencies=step_data.get("dependencies", []),
            ))

        return Plan(
            intent=data.get("intent", "unknown"),
            complexity=data.get("complexity", "simple"),
            steps=steps,
            required_tools=data.get("required_tools", []),
            relevant_modules=data.get("relevant_modules", []),
            coding_hints=data.get("coding_hints", []),
            expected_output_type=data.get("expected_output_type", "string"),
            confidence=data.get("confidence", 0.8),
            skip_planning=data.get("skip_planning", False),
            requires_post_processing=data.get("requires_post_processing", False),
            output_format_hint=data.get("output_format_hint", ""),
        )
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def run_planner(
    client: OpenAI,
    query: str,
    model: str,
    timeout: float = 5.0,
) -> Plan:
    """
    Run planner with comprehensive fallback handling.

    Args:
        client: OpenAI client
        query: User query
        model: Model to use for planning
        timeout: Request timeout in seconds

    Returns:
        Plan object (may be a default plan on failure)
    """
    import signal

    def timeout_handler(signum, frame):
        raise TimeoutError("Planner call timed out")

    # Set timeout (works on Unix systems)
    if hasattr(signal, 'SIGALRM'):
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(timeout))

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                {"role": "user", "content": query}
            ],
            temperature=0.3,  # Lower for more deterministic planning
            max_tokens=500,   # Plans should be concise
        )

        content = response.choices[0].message.content or ""

        # Try to extract JSON from response (in case there's extra text)
        json_match = re.search(r'\{[^{}]*\{.*\}[^{}]*\}|\{[^{}]+\}', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)

        plan = parse_plan_from_json(content)

        if plan is None:
            print(f"Planner: Failed to parse JSON, using default plan", file=sys.stderr)
            if content.strip():
                print(f"  Raw response: {content[:200]}...", file=sys.stderr)
            return create_default_plan(intent="unknown", confidence=0.0)

        # Validate the plan
        plan = validate_plan(plan)

        # Log to stderr
        print(f"Planner: intent={plan.intent}, complexity={plan.complexity}, "
              f"tools={plan.required_tools}, steps={len(plan.steps)}, "
              f"confidence={plan.confidence:.2f}", file=sys.stderr)

        return plan

    except TimeoutError:
        print(f"Planner: Timeout after {timeout}s, using default plan", file=sys.stderr)
        return create_default_plan(skip_planning=True)
    except Exception as e:
        print(f"Planner: Error - {str(e)}, using default plan", file=sys.stderr)
        return create_default_plan(skip_planning=True)
    finally:
        if hasattr(signal, 'SIGALRM'):
            signal.alarm(0)  # Cancel alarm


# Base static prompt for fallback
STATIC_CODER_PROMPT = """你是一个 Python 逻辑单元。你的回答必须仅包含一个 Python 代码块。

【重要提示】以下函数已经预定义，直接调用即可，不要重新定义：
- web_search(query, num_results=5) -> dict: 网络搜索函数，返回结构化数据
- ask_sub_agent(query) -> str: 子代理调用函数
- safe_sub_agent(query): 装饰器

规则：
1. 所有输出都必须通过 print() 语句输出
2. 只输出最终答案，不要输出任何中间数据或调试信息
3. 【绝对不要重新定义 web_search、ask_sub_agent 等预定义函数】
4. 闲聊场景：生成 print("回复内容")
5. 计算场景：生成计算逻辑并 print 结果
6. 数据处理：可以使用 datetime, json, re, math 等标准库

可用的特殊函数：
- ask_sub_agent(query: str) -> str: 用于处理语义理解、翻译、总结等需要 AI 的任务。
  内部有自愈机制，执行失败时会自动修复。
  示例:
    result = ask_sub_agent("请总结这段文本的主旨")
    print(result)

- web_search(query: str, num_results: int = 5) -> dict: 网络搜索获取实时信息。
  返回结构化数据: {"answer": "...", "results": [{"title": "...", "content": "...", "url": "..."}], "error": None}
  示例:
    data = web_search("今天的科技新闻")
    if data.get("error"):
        print(f"搜索失败: {data['error']}")
    else:
        for r in data["results"]:
            print(f"• {r['title']}")

- safe_sub_agent(query): 装饰器，简化 ask_sub_agent 调用的语法糖。

使用场景：
- 纯逻辑/计算任务：直接用 Python 代码
- 需要语义理解/翻译/总结：使用 ask_sub_agent()
- 需要查资料/事实信息：使用 web_search()，处理返回的 dict 数据
- 混合任务：先获取信息，再做逻辑处理

重要：
- ask_sub_agent 和 web_search 都有自愈机制，执行失败会自动修复
- 不要输出任何代码块之外的文字
- 只输出 ```python ... ``` 格式的代码"""


def build_coder_prompt(plan: Plan) -> str:
    """Build optimized SYSTEM_PROMPT based on plan."""
    # If skip_planning, use static prompt
    if plan.skip_planning:
        return STATIC_CODER_PROMPT

    base_prompt = """你是一个 Python 逻辑单元。你的回答必须仅包含一个 Python 代码块。

【重要提示】以下函数已经预定义，直接调用即可，不要重新定义：
- web_search(query, num_results=5) -> dict: 网络搜索函数，返回结构化数据
- ask_sub_agent(query) -> str: 子代理调用函数
- safe_sub_agent(query): 装饰器

规则：
1. 所有输出都必须通过 print() 语句输出
2. 只输出最终答案，不要输出任何中间数据或调试信息
3. 【绝对不要重新定义 web_search、ask_sub_agent 等预定义函数】
4. 闲聊场景：生成 print("回复内容")
5. 计算场景：生成计算逻辑并 print 结果
6. 数据处理：可以使用 datetime, json, re, math 等标准库
"""

    # Dynamically add tool documentation
    if plan.required_tools:
        base_prompt += "\n可用的特殊函数：\n"
        for tool_name in plan.required_tools:
            if tool_name in TOOL_REGISTRY:
                base_prompt += TOOL_REGISTRY[tool_name].usage_doc + "\n"

    # Add relevant module hints
    if plan.relevant_modules:
        base_prompt += f"\n推荐使用的标准库：{', '.join(plan.relevant_modules)}\n"

    # Add task-specific hints
    if plan.coding_hints:
        base_prompt += "\n编码提示：\n"
        for hint in plan.coding_hints:
            base_prompt += f"- {hint}\n"

    # Add step breakdown for complex tasks
    if plan.steps and len(plan.steps) > 1:
        base_prompt += "\n执行步骤：\n"
        for step in plan.steps:
            base_prompt += f"{step.order}. {step.description}\n"

    # Add output format hint
    base_prompt += f"\n期望输出类型：{plan.expected_output_type}\n"

    # Add self-check requirements for medium/complex tasks (TDD in Agent)
    if plan.complexity in ("medium", "complex"):
        base_prompt += """
【自检要求】（重要！）
在 print() 输出前，请添加 assert 语句对关键结果进行校验。如果 assert 失败，系统会自动修复代码。

检查类型：
1. 数值结果：类型和合理范围
   assert isinstance(result, (int, float)), f"类型错误: {type(result)}"
   assert 0 <= result <= 1000000, f"结果超出合理范围: {result}"

2. 列表/字典结果：非空、元素类型、结构正确
   assert len(results) > 0, "结果为空"
   assert all(isinstance(x, dict) for x in results), "元素类型错误"

3. 字符串结果：非空、长度合理
   assert len(text) > 0, "结果为空"
   assert len(text) < 10000, "输出过长"

4. 格式检查：确保输出符合预期格式
   assert "@" in email, "邮箱格式无效"
   assert re.match(r'\\d{4}-\\d{2}-\\d{2}', date_str), "日期格式错误"

5. 业务逻辑：结果符合业务规则
   assert total == sum(items), "汇总不匹配"
   assert max_val >= min_val, "最大值小于最小值"

示例：
```python
data = web_search("Python 3.12 新特性")
assert data.get("results"), "搜索无结果"  # 检查数据结构
assert len(data["results"]) > 0, "未找到相关信息"
for r in data["results"]:
    print(f"• {r['title']}")
```
"""

    base_prompt += """
重要：
- ask_sub_agent 内部有自愈机制，执行失败会自动修复（最多3次）
- web_search 可获取网络信息，用于回答需要最新知识或具体事实的问题
- @safe_sub_agent 只是语法糖，让代码更简洁
- 不要输出任何代码块之外的文字
- 只输出 ```python ... ``` 格式的代码"""

    return base_prompt


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

    def to_dict(self) -> dict[str, float]:
        """Export timing data as a dictionary."""
        result = {}
        for record in self.records:
            result[record.name] = record.duration_ms
        result["Total"] = self.total_ms()
        return result


# Load environment variables
load_dotenv()


# =============================================================================
# Centralized Configuration
# =============================================================================

# Provider registry - 所有支持的 provider 预设配置
# 格式：provider_key: {name, url, default_model, api_key_prefix}
PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    # 阿里云 DashScope (Qwen 系列)
    "dashscope": {
        "name": "DashScope (阿里云)",
        "url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-plus",
        "api_key_prefix": "sk-",
    },
    # Cloudflare Gateway (Grok 系列)
    "cloudflare": {
        "name": "Cloudflare Gateway + Grok",
        "url": "https://gateway.ai.cloudflare.com/v1/ACCOUNT_ID/gemini/compat",
        "default_model": "grok/grok-4-1-fast-non-reasoning",
        "api_key_prefix": "",  # Cloudflare 使用 bearer token
    },
    # OpenAI 原生
    "openai": {
        "name": "OpenAI",
        "url": "https://api.openai.com/v1",
        "default_model": "gpt-4o",
        "api_key_prefix": "sk-",
    },
    # Anthropic (通过 OpenAI 兼容层，如 openrouter)
    "anthropic": {
        "name": "Anthropic (兼容层)",
        "url": "https://api.anthropic.com/v1",
        "default_model": "claude-sonnet-4-5-20251022",
        "api_key_prefix": "sk-ant-",
    },
    # 自定义 provider (通过环境变量配置)
    "custom": {
        "name": "Custom Provider",
        "url": "",  # 必须通过 CUSTOM_URL 配置
        "default_model": "",  # 必须通过 CUSTOM_MODEL 配置
        "api_key_prefix": "",
    },
}


@dataclass
class Config:
    """Centralized configuration management."""
    # Coder (main) provider
    provider: str = "dashscope"
    url: str = ""
    api_key: str = ""
    model: str = ""

    # Planner provider and model (optional - defaults to coder)
    planner_provider: str | None = None  # None = use same as coder
    planner_model: str | None = None
    planner_timeout: float = 5.0

    # Sub-agent provider and model (optional - defaults to coder)
    sub_agent_provider: str | None = None  # None = use same as coder
    sub_agent_model: str | None = None
    sub_agent_max_depth: int = 3
    sub_agent_timeout: float = 60.0

    # Feature flags
    web_search_enabled: bool = True
    post_process_enabled: bool = False  # Default to disabled for backward compatibility

    # Retry settings
    max_security_retries: int = 3
    max_execution_retries: int = 3

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        provider = os.getenv("UPA_PROVIDER", "dashscope")

        # Build provider-specific env var names for coder
        url_key = f"{provider.upper()}_URL"
        key_key = f"{provider.upper()}_API_KEY"
        model_key = f"{provider.upper()}_MODEL"

        # Get defaults from presets if provider exists
        preset = PROVIDER_PRESETS.get(provider, {})
        default_url = preset.get("url", "")
        default_model = preset.get("default_model", "")

        # Get planner provider/model
        planner_provider = os.getenv("UPA_PLANNER_PROVIDER", None)
        planner_model = os.getenv("UPA_PLANNER_MODEL", None)

        # Get sub-agent provider/model
        sub_agent_provider = os.getenv("UPA_SUB_AGENT_PROVIDER", None)
        sub_agent_model = os.getenv("UPA_SUB_AGENT_MODEL", None)

        return cls(
            # Coder config
            provider=provider,
            url=os.getenv(url_key, default_url),
            api_key=os.getenv(key_key, ""),
            model=os.getenv(model_key, default_model),
            # Planner config
            planner_provider=planner_provider,
            planner_model=planner_model,
            planner_timeout=float(os.getenv("UPA_PLANNER_TIMEOUT", "5.0")),
            # Sub-agent config
            sub_agent_provider=sub_agent_provider,
            sub_agent_model=sub_agent_model,
            sub_agent_max_depth=int(os.getenv("UPA_SUB_AGENT_DEPTH", "3")),
            sub_agent_timeout=float(os.getenv("UPA_SUB_AGENT_TIMEOUT", "60.0")),
            web_search_enabled=os.getenv("UPA_WEB_SEARCH", "true").lower() == "true",
            post_process_enabled=os.getenv("UPA_POST_PROCESS", "false").lower() == "true",
            max_security_retries=int(os.getenv("UPA_MAX_SECURITY_RETRIES", "3")),
            max_execution_retries=int(os.getenv("UPA_MAX_EXECUTION_RETRIES", "3")),
        )

    def validate(self) -> list[str]:
        """
        Validate configuration and return list of errors.
        Returns empty list if configuration is valid.
        """
        errors = []
        if not self.api_key:
            errors.append(f"{self.provider.upper()}_API_KEY is required but not set")
        if not self.url:
            errors.append(f"{self.provider.upper()}_URL is required but not set")
        if not self.model:
            errors.append(f"{self.provider.upper()}_MODEL is required but not set")
        return errors

    def show(self) -> str:
        """Return a formatted string showing current configuration."""
        lines = [
            "UPA Configuration:",
            "─" * 50,
            f"  Provider:          {self.provider}",
            f"  URL:               {self.url[:50]}..." if len(self.url) > 50 else f"  URL:               {self.url}",
            f"  API Key:           {'*' * 8}{'' if len(self.api_key) <= 8 else '...'} ({len(self.api_key)} chars)",
            f"  Model:             {self.model}",
            "",
            "  Planner:",
            f"    Provider:        {self.planner_provider or '(same as coder)'}",
            f"    Model:           {self.planner_model or '(same as coder)'}",
            f"    Timeout:         {self.planner_timeout}s",
            "",
            "  Sub-Agent:",
            f"    Provider:        {self.sub_agent_provider or '(same as coder)'}",
            f"    Model:           {self.sub_agent_model or '(same as coder)'}",
            f"    Max Depth:       {self.sub_agent_max_depth}",
            f"    Timeout:         {self.sub_agent_timeout}s",
            "",
            "  Features:",
            f"    Web Search:      {self.web_search_enabled}",
            f"    Post-Process:    {self.post_process_enabled}",
            "",
            "  Retry Settings:",
            f"    Max Security:    {self.max_security_retries}",
            f"    Max Execution:   {self.max_execution_retries}",
        ]
        return "\n".join(lines)


# Global configuration instance (loaded once at startup)
CONFIG: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global CONFIG
    if CONFIG is None:
        CONFIG = Config.from_env()
    return CONFIG


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


def _build_providers_from_presets() -> dict[str, ProviderConfig]:
    """Build PROVIDERS dict from PROVIDER_PRESETS."""
    providers = {}
    for key, preset in PROVIDER_PRESETS.items():
        providers[key] = ProviderConfig(
            name=preset.get("name", key),
            url=preset.get("url", ""),
            api_key="",  # API key always from env
            model=preset.get("default_model", ""),
        )
    return providers


# Predefined providers (from presets)
PROVIDERS = _build_providers_from_presets()

# Default provider (can be overridden by env var or CLI)
DEFAULT_PROVIDER = os.getenv("UPA_PROVIDER", "dashscope")

def get_provider(provider_name: str | None = None) -> ProviderConfig:
    """Get provider configuration by name."""
    config = get_config()

    if provider_name is None:
        provider_name = config.provider

    # If requested provider matches config provider, use loaded config values
    if provider_name == config.provider:
        return ProviderConfig(
            name=config.provider,
            url=config.url,
            api_key=config.api_key,
            model=config.model,
        )

    if provider_name in PROVIDERS:
        # For predefined providers, load API key from env and merge with preset
        preset = PROVIDER_PRESETS.get(provider_name, {})
        env_key = os.getenv(f"{provider_name.upper()}_API_KEY", "")
        env_model = os.getenv(f"{provider_name.upper()}_MODEL", preset.get("default_model", ""))
        env_url = os.getenv(f"{provider_name.upper()}_URL", preset.get("url", ""))
        return ProviderConfig(
            name=preset.get("name", provider_name),
            url=env_url,
            api_key=env_key,
            model=env_model,
        )

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
        preset = PROVIDER_PRESETS.get(key, {})
        models = preset.get("default_model", provider.model)
        print(f"  {key:12} → {provider.name}{default}")
        print(f"               Default Model: {models}")
        print(f"               URL: {provider.url[:50]}...")
    print()
    print("Usage:")
    print(f"  upa.py --provider <name> \"your query\"")
    print(f"  upa.py --model <model> \"your query\"  # Override model")
    print(f"  upa.py --config <provider> <model>    # Set default")
    print()
    print("Environment Variables:")
    print(f"  {DEFAULT_PROVIDER.upper()}_API_KEY  - API key for current provider")
    print(f"  {DEFAULT_PROVIDER.upper()}_MODEL    - Model to use")
    print(f"  {DEFAULT_PROVIDER.upper()}_URL      - API endpoint URL")

def set_default_config(provider_name: str, model: str) -> None:
    """Update .env file with new default provider and model."""
    # Validate provider
    if provider_name not in PROVIDERS:
        print(f"Error: Unknown provider '{provider_name}'. Available: {list(PROVIDERS.keys())}", file=sys.stderr)
        sys.exit(1)

    env_path = Path(".env")
    env_example_path = Path(".env.example")

    # Read existing .env or create from .env.example
    if env_path.exists():
        content = env_path.read_text()
    elif env_example_path.exists():
        content = env_example_path.read_text()
        # Remove placeholder values
        content = content.replace("your_", "").replace("_api_key_here", "").replace("_YOUR_ACCOUNT", "/632ba9b9506a87e7fe1d5f7e7db78d57")
    else:
        content = f"# UPA Configuration\nUPA_PROVIDER={provider_name}\n"

    lines = content.splitlines()
    updated_lines = []
    config_updated = False

    # Update or add UPA_PROVIDER
    for line in lines:
        if line.startswith("UPA_PROVIDER="):
            updated_lines.append(f"UPA_PROVIDER={provider_name}")
            config_updated = True
        elif line.startswith(f"{provider_name.upper()}_MODEL="):
            updated_lines.append(f"{provider_name.upper()}_MODEL={model}")
            config_updated = True
        else:
            updated_lines.append(line)

    # If not found, append to end
    if not config_updated:
        updated_lines.append(f"UPA_PROVIDER={provider_name}")
        updated_lines.append(f"{provider_name.upper()}_MODEL={model}")

    # Write back to .env
    env_path.write_text("\n".join(updated_lines) + "\n")

    print(f"✓ Default configuration updated:")
    print(f"  Provider: {provider_name}")
    print(f"  Model: {model}")
    print(f"  Config file: {env_path.absolute()}")

# =============================================================================
# Planner Configuration
# =============================================================================
# Note: These are now loaded via Config.from_env() and accessed via get_config()
# Constants below are kept for backward compatibility, loaded from Config at runtime

# System Prompt: Always-Code (use static prompt from planner module for backward compatibility)
SYSTEM_PROMPT = STATIC_CODER_PROMPT

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


# =============================================================================
# Configuration Property Accessors
# =============================================================================
# These functions provide backward compatibility by loading from Config

def _get_planner_enabled() -> bool:
    return get_config().planner_enabled

def _get_planner_model() -> str | None:
    return get_config().planner_model

def _get_planner_timeout() -> float:
    return get_config().planner_timeout

def _get_web_search_enabled() -> bool:
    return get_config().web_search_enabled

def _get_max_sub_agent_depth() -> int:
    return get_config().sub_agent_max_depth

def _get_sub_agent_timeout() -> float:
    return get_config().sub_agent_timeout

def _get_max_security_retries() -> int:
    return get_config().max_security_retries

def _get_max_execution_retries() -> int:
    return get_config().max_execution_retries

# Module-level constants (loaded from Config at module import time)
# These are evaluated once when the module loads, after Config is initialized
PLANNER_ENABLED: bool = True  # Placeholder, will be updated below
PLANNER_MODEL: str | None = None
PLANNER_TIMEOUT: float = 5.0
WEB_SEARCH_ENABLED: bool = True
MAX_SUB_AGENT_DEPTH: int = 3
SUB_AGENT_TIMEOUT: float = 60.0
MAX_SECURITY_RETRIES: int = 3
MAX_EXECUTION_RETRIES: int = 3


def _init_constants():
    """Initialize module-level constants from Config."""
    global PLANNER_ENABLED, PLANNER_MODEL, PLANNER_TIMEOUT
    global WEB_SEARCH_ENABLED, MAX_SUB_AGENT_DEPTH, SUB_AGENT_TIMEOUT
    global MAX_SECURITY_RETRIES, MAX_EXECUTION_RETRIES

    config = get_config()
    PLANNER_ENABLED = True  # Always enabled, controlled by config
    PLANNER_MODEL = config.planner_model
    PLANNER_TIMEOUT = config.planner_timeout
    WEB_SEARCH_ENABLED = config.web_search_enabled
    MAX_SUB_AGENT_DEPTH = config.sub_agent_max_depth
    SUB_AGENT_TIMEOUT = config.sub_agent_timeout
    MAX_SECURITY_RETRIES = config.max_security_retries
    MAX_EXECUTION_RETRIES = config.max_execution_retries


# Initialize constants from Config
_init_constants()


def get_planner_provider_config() -> ProviderConfig:
    """Get the provider configuration for planner."""
    config = get_config()

    # If planner has its own provider
    if config.planner_provider:
        return get_provider(config.planner_provider)

    # Otherwise use coder's provider
    return get_provider(config.provider)


def get_sub_agent_provider_config() -> ProviderConfig:
    """Get the provider configuration for sub-agent."""
    config = get_config()

    # If sub-agent has its own provider
    if config.sub_agent_provider:
        return get_provider(config.sub_agent_provider)

    # Otherwise use coder's provider
    return get_provider(config.provider)


def get_sub_agent_model(coder_model: str) -> str:
    """Get the model to use for sub-agent calls.

    Args:
        coder_model: The model used by the main coder

    Returns:
        The model name for sub-agent calls
    """
    config = get_config()
    return config.sub_agent_model or coder_model


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
        model: Model name to use (defaults to sub-agent model from config)

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

    # Get sub-agent model if not specified
    if model is None:
        # Use sub-agent's provider config (may be different from coder)
        sub_agent_config = get_sub_agent_provider_config()
        model = get_sub_agent_model(sub_agent_config.model)

    try:
        # Create client if not provided
        if client is None:
            # Use sub-agent's provider config (may be different from coder)
            client = create_client(get_sub_agent_provider_config())

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

        # ==========================================================================
        # Sub-Agent Self-Healing Execution Loop
        # ==========================================================================
        # Create recursive ask_sub_agent for this sub-agent's sandbox
        def sub_agent_recursive_wrapper(sub_query: str) -> str:
            return ask_sub_agent(sub_query, client=client, model=model)

        # Create safe_sub_agent decorator for sub-agent (simplified - just for syntax sugar)
        def create_safe_sub_agent_sub(ask_sub_fn):
            def safe_sub_agent(query: str):
                """Decorator factory for sub-agent calls (syntax sugar, no retry logic)."""
                def decorator(func):
                    def wrapper(*args, **kwargs):
                        result = ask_sub_fn(query)
                        return func(result, *args, **kwargs)
                    return wrapper
                return decorator
            return safe_sub_agent

        sandbox_globals = {
            "__builtins__": __builtins__,
            "datetime": __import__("datetime"),
            "json": __import__("json"),
            "re": __import__("re"),
            "math": __import__("math"),
            "random": __import__("random"),
            "collections": __import__("collections"),
            "itertools": __import__("itertools"),
            # Inject recursive ask_sub_agent and safe_sub_agent
            "ask_sub_agent": sub_agent_recursive_wrapper,
            "safe_sub_agent": create_safe_sub_agent_sub(sub_agent_recursive_wrapper),
        }

        # Self-healing execution loop
        output = ""
        execution_error = None
        conversation_history_sub = [
            {"role": "system", "content": sub_prompt},
            {"role": "user", "content": query}
        ]

        for sub_attempt in range(MAX_EXECUTION_RETRIES):
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()

            try:
                exec(code, sandbox_globals)
                output = sys.stdout.getvalue()
                sys.stdout = old_stdout
                break  # Success
            except Exception as e:
                sys.stdout = old_stdout
                execution_error = traceback.format_exc()

                if sub_attempt < MAX_EXECUTION_RETRIES - 1:
                    # Build error feedback for sub-agent LLM
                    error_feedback = f"""子代理代码执行时发生错误：
{execution_error}

请修复上述错误，确保：
1. 正确处理所有异常情况
2. 变量在使用前已定义
3. 语法和逻辑正确

只输出修复后的代码，不要解释。"""

                    # Add error feedback to conversation
                    conversation_history_sub.append({
                        "role": "user",
                        "content": error_feedback
                    })

                    # Generate healed code
                    healed_response = client.chat.completions.create(
                        model=model,
                        messages=conversation_history_sub,
                        temperature=0.7,
                    )

                    healed_content = healed_response.choices[0].message.content or ""
                    code = extract_code(healed_content)

                    if not code:
                        return f"[Error: Sub-agent failed to generate healed code]"

                    # Security check for healed code
                    violations = check_code_safety(code)
                    if violations:
                        return f"[Error: Healed code has security violation: {violations[0]}]"

                    # Add the new assistant message to history
                    conversation_history_sub.append({
                        "role": "assistant",
                        "content": healed_content
                    })

        # After all attempts, check if we still have an error
        if execution_error and not output:
            return f"[Error: Sub-agent execution failed after {MAX_EXECUTION_RETRIES} attempts:\n{execution_error}]"

        return output.rstrip()  # Remove trailing whitespace

    except TimeoutError:
        return f"[Error: Sub-agent call timed out after {SUB_AGENT_TIMEOUT}s]"
    except Exception as e:
        return f"[Error: Sub-agent call failed: {str(e)}]"
    finally:
        # Always decrement depth when done
        SubAgentContext.decrement()


# Web Search configuration
WEB_SEARCH_TIMEOUT = 30    # Timeout for web search calls in seconds
WEB_SEARCH_ENABLED = os.getenv("UPA_WEB_SEARCH", "true").lower() == "true"
# Tavily API configuration (default key for testing)
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "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")


def web_search(query: str, num_results: int = 5) -> dict:
    """
    Web search function for fact-checking and information retrieval.
    Uses Tavily Search API - optimized for AI agents.

    This function is injected into the sandbox for LLM-generated code to call.

    When network search fails, returns error dict for code to handle gracefully.

    Args:
        query: The search query
        num_results: Number of search results to return (default: 5)

    Returns:
        A dict with structured search results:
        {
            "answer": "Direct answer from Tavily (if available)",
            "results": [{"title": "...", "content": "...", "url": "..."}, ...],
            "query": "Original query",
            "error": null or "Error message"
        }

    Example usage in sandbox:
        # Search and process results
        data = web_search("Python 3.12 新特性")

        # Check for errors
        if data.get("error"):
            print(f"搜索失败: {data['error']}")
        else:
            # Format output as needed
            for r in data["results"]:
                print(f"• {r['title']}: {r['content'][:100]}...")
    """
    # Check if web search is enabled
    if not WEB_SEARCH_ENABLED:
        return {"query": query, "results": [], "answer": None, "error": "Web search disabled"}

    # Output search call info to stderr for tracking
    print(f"Web Search (Tavily): {query[:50]}...", file=sys.stderr)

    try:
        import urllib.request
        import json as json_module

        # Use Tavily Search API
        url = "https://api.tavily.com/search"

        # Build request payload
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": query,
            "search_depth": "basic",
            "include_answer": True,
            "max_results": num_results,
        }

        # Create request
        data = json_module.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        # Execute request
        with urllib.request.urlopen(request, timeout=WEB_SEARCH_TIMEOUT) as response:
            result = json_module.loads(response.read().decode())

        # Build structured response
        response_data = {
            "query": query,
            "answer": result.get("answer"),
            "results": [],
            "error": None
        }

        # Extract search results
        if result.get("results"):
            for r in result["results"][:num_results]:
                response_data["results"].append({
                    "title": r.get("title", ""),
                    "content": r.get("content", ""),
                    "url": r.get("url", "")
                })

        return response_data

    except urllib.error.HTTPError as e:
        error_msg = f"API 错误 ({e.code})" if e.code not in (401, 429) else ("API 密钥无效" if e.code == 401 else "API 限流")
        return {"query": query, "results": [], "answer": None, "error": error_msg}
    except urllib.error.URLError:
        return {"query": query, "results": [], "answer": None, "error": "网络错误"}
    except Exception as e:
        return {"query": query, "results": [], "answer": None, "error": str(e)}
    except json.JSONDecodeError:
        return f"[解析错误，使用内置知识回答: {query}]"
    except Exception as e:
        return f"[搜索失败: {str(e)}，使用内置知识回答: {query}]"


def create_client(provider: ProviderConfig | None = None) -> OpenAI:
    """Create OpenAI client configured for the specified provider."""
    if provider is None:
        provider = get_provider()
    return OpenAI(
        api_key=provider.api_key,
        base_url=provider.url,
    )


def generate_code(
    client: OpenAI,
    query: str,
    model: str,
    error_feedback: str | None = None,
    conversation_history: list | None = None,
    system_prompt: str | None = None,
) -> tuple[str, list]:
    """
    Call LLM to generate Python code for the query.

    Args:
        client: OpenAI client
        query: User query
        model: Model name to use
        error_feedback: Optional error message from previous attempt
        conversation_history: Previous messages for retry context
        system_prompt: Optional custom system prompt (defaults to SYSTEM_PROMPT)

    Returns:
        (response_content, updated_conversation_history)
    """
    # Build message list
    if conversation_history is None:
        messages = [
            {"role": "system", "content": system_prompt or SYSTEM_PROMPT},
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

    # Create safe_sub_agent decorator (syntax sugar, retry logic is inside ask_sub_agent)
    def create_safe_sub_agent(ask_sub_fn):
        def safe_sub_agent(query: str):
            """Decorator factory for sub-agent calls (syntax sugar, retry logic is inside ask_sub_agent)."""
            def decorator(func):
                def wrapper(*args, **kwargs):
                    result = ask_sub_fn(query)
                    return func(result, *args, **kwargs)
                return wrapper
            return decorator
        return safe_sub_agent

    # Get model name for sub-agent calls
    if client:
        ask_sub_agent_fn = make_ask_sub_agent(client, provider.model)
        safe_sub_agent_decorator = create_safe_sub_agent(ask_sub_agent_fn)
    else:
        ask_sub_agent_fn = lambda q: "[Error: No LLM client]"
        safe_sub_agent_decorator = lambda q: lambda f: f

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
        # Inject ask_sub_agent and safe_sub_agent
        "ask_sub_agent": ask_sub_agent_fn,
        "safe_sub_agent": safe_sub_agent_decorator,
        # Inject web_search for fact-checking
        "web_search": web_search,
    }

    try:
        exec(code, sandbox_globals)
        output = sys.stdout.getvalue()
        return output, ""
    except Exception:
        return "", traceback.format_exc()
    finally:
        sys.stdout = old_stdout


def post_process_output(
    client: OpenAI,
    query: str,
    execution_output: str,
    model: str,
    format_hint: str = "",
) -> str:
    """
    Post-process execution output with LLM for better formatting.

    Args:
        client: OpenAI client
        query: Original user query
        execution_output: Raw output from code execution
        model: Model to use for post-processing
        format_hint: Optional format hint from planner

    Returns:
        Formatted output string
    """
    if not execution_output.strip():
        return execution_output

    system_prompt = """你是一个输出格式化助手。你的任务是将代码执行的原始结果格式化为更易读的输出。

规则：
1. 保持原始信息的准确性，不要改变核心内容
2. 用更自然、更人性化的语言重新组织
3. 如果是搜索结果，整理成清晰的结构（标题+内容）
4. 如果是计算结果，适当添加解释说明
5. 如果是列表/表格，使用更清晰的格式展示
6. 只输出格式化后的内容，不要添加额外的解释或标记

输出格式：直接输出格式化后的文本，不要使用任何代码块或标记。"""

    user_message = f"""原始用户问题：
{query}

代码执行结果：
{execution_output}

{f"格式提示：{format_hint}" if format_hint else ""}

请将上述执行结果格式化为更易读的输出。"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,  # Lower for more consistent formatting
            max_tokens=2000,
        )

        return response.choices[0].message.content or execution_output
    except Exception:
        # If post-processing fails, return original output
        return execution_output


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
        "--show-config",
        action="store_true",
        help="Show current configuration and exit",
    )
    parser.add_argument(
        "--provider", "-p",
        choices=list(PROVIDERS.keys()),
        help=f"LLM provider to use (default: {DEFAULT_PROVIDER})",
    )
    parser.add_argument(
        "--model", "-m",
        help="Override the default model for the selected provider",
    )
    parser.add_argument(
        "--list-providers",
        action="store_true",
        help="List all available LLM providers",
    )
    parser.add_argument(
        "--config",
        nargs=2,
        metavar=("PROVIDER", "MODEL"),
        help="Set default provider and model (updates .env file). Example: --config dashscope qwen-plus",
    )
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Output execution details in JSON format to stderr (for benchmarking)",
    )
    parser.add_argument(
        "--post-process",
        action="store_true",
        help="Enable post-processing to format execution output",
    )
    parser.add_argument(
        "--no-post-process",
        action="store_true",
        help="Disable post-processing even if planner suggests it",
    )

    args = parser.parse_args()

    # Handle --list-providers
    if args.list_providers:
        list_providers()
        sys.exit(0)

    # Handle --config (set default provider and model)
    if args.config:
        set_default_config(args.config[0], args.config[1])
        sys.exit(0)

    # Handle --show-config
    if args.show_config:
        config = get_config()
        print(config.show())
        # Validate and show warnings if any
        errors = config.validate()
        if errors:
            print("\n⚠ Configuration Warnings:")
            for error in errors:
                print(f"  - {error}")
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
    # Use --model argument if provided, otherwise use provider's default
    model = args.model if args.model else provider.model

    # Show provider info
    print(f"Using: {provider.name} ({model})", file=sys.stderr)

    # ==========================================================================
    # Phase 0: Planner Analysis (Dynamic Prompt Construction)
    # ==========================================================================
    plan: Plan | None = None
    system_prompt = SYSTEM_PROMPT  # Default to static prompt

    if PLANNER_ENABLED:
        # Quick bypass for trivial queries
        if is_trivial_query(args.query):
            print("Planner: Trivial query detected, using static prompt", file=sys.stderr)
            plan = create_default_plan(intent="simple_chat", skip_planning=True)
        else:
            timer.start("Planner Analysis")
            # Get planner-specific model and client
            planner_model = PLANNER_MODEL or model  # Use planner-specific model or fall back to coder model
            planner_client = create_client(get_planner_provider_config())
            plan = run_planner(planner_client, args.query, planner_model, timeout=PLANNER_TIMEOUT)
            timer.stop()

            # Build dynamic system prompt based on plan
            system_prompt = build_coder_prompt(plan)

    # ==========================================================================
    # Phase 1: Code Generation with Security Retry Loop
    # ==========================================================================
    print("Thinking...", file=sys.stderr, end="", flush=True)

    # Use separate timers for nested operations
    llm_timer = Timer()
    security_timer = Timer()
    code_extract_timer = Timer()

    code = None
    response = None
    conversation_history = None
    error_feedback = None

    # Track security retry statistics
    security_retry_data = {
        "retry_count": 0,
        "violations": [],
    }

    for attempt in range(MAX_SECURITY_RETRIES):
        # Generate code (with error feedback on retry)
        llm_timer.start("LLM Generate")
        response, conversation_history = generate_code(
            client,
            args.query,
            model,
            error_feedback=error_feedback,
            conversation_history=conversation_history,
            system_prompt=system_prompt,  # Use dynamic prompt from planner
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
                security_retry_data["retry_count"] = attempt + 1
                security_retry_data["violations"] = violations
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

    # Clear the "Thinking..." status
    print("\r\033[K", end="", file=sys.stderr, flush=True)

    # Show code if requested
    if args.show_code:
        print("--- Generated Code ---", file=sys.stderr)
        print(code, file=sys.stderr)
        print("--- Execution Result ---", file=sys.stderr)

    # ==========================================================================
    # Phase 2: Execute Code with Self-Healing Retry Loop
    # ==========================================================================
    output = ""
    error = ""
    execution_error = None

    # Track self-healing statistics
    self_heal_attempts = 0
    self_heal_errors = []
    final_code = code

    for exec_attempt in range(MAX_EXECUTION_RETRIES):
        timer.start("Code Execute")
        output, error = execute_code(code, client=client, provider=provider)
        timer.stop()

        if not error:
            break  # Execution successful

        # Execution failed, attempt self-healing
        execution_error = error
        if exec_attempt < MAX_EXECUTION_RETRIES - 1:
            self_heal_attempts += 1
            # Extract first line of error for summary
            error_summary = error.split('\n')[0][:100] if error else "Unknown error"
            self_heal_errors.append(error_summary)

            print(f"\n  Execution error, attempting self-heal ({exec_attempt + 1}/{MAX_EXECUTION_RETRIES})...", file=sys.stderr)

            # Build error feedback for LLM to fix
            error_feedback = f"""代码执行时发生错误：
{error}

请修复上述错误，确保：
1. 正确处理所有异常情况（如除零、索引越界、变量未定义等）
2. 变量在使用前已定义
3. 语法和逻辑正确

只输出修复后的代码，不要解释。"""

            # Generate new code with error feedback
            llm_timer.start("LLM Generate (Self-Heal)")
            response, conversation_history = generate_code(
                client,
                args.query,
                model,
                error_feedback=error_feedback,
                conversation_history=conversation_history,
                system_prompt=system_prompt,  # Use same dynamic prompt for self-healing
            )
            llm_timer.stop()

            # Extract code from healing response
            code_extract_timer.start("Code Extract (Self-Heal)")
            code = extract_code(response)
            code_extract_timer.stop()

            if not code:
                print("  Failed to extract code from healing response", file=sys.stderr)
                continue

            # Security check for healed code
            security_timer.start("Security Check (Self-Heal)")
            violations = check_code_safety(code)
            security_timer.stop()

            if violations:
                print(f"  Security violation in healed code: {violations[0]}", file=sys.stderr)
                continue

            print("  Healed code generated, retrying execution...", file=sys.stderr)
            final_code = code  # Track the latest code version

    # After all attempts, check if we still have an error
    if execution_error and error:
        print(f"\n经过 {MAX_EXECUTION_RETRIES} 次自愈尝试，仍无法执行成功:", file=sys.stderr)
        print(error, file=sys.stderr)
        print(f"\n问题类型: 代码逻辑错误（非安全问题）", file=sys.stderr)
        print(f"建议: 检查代码逻辑或重新表述您的需求", file=sys.stderr)
        if args.show_code:
            print("\n最终执行的代码:", file=sys.stderr)
            print(code, file=sys.stderr)
        sys.exit(1)

    # ==========================================================================
    # Phase 3: Post-Processing (Optional)
    # ==========================================================================
    # Determine if post-processing is needed
    # Priority: CLI --no-post-process > CLI --post-process > Planner suggestion > Config default
    config = get_config()
    should_post_process = False
    if args.no_post_process:
        should_post_process = False
    elif args.post_process:
        should_post_process = True
    elif plan and plan.requires_post_processing:
        should_post_process = True
    elif config.post_process_enabled:
        should_post_process = True

    if should_post_process and output.strip():
        print("Formatting output...", file=sys.stderr)
        timer.start("Post-Process")
        output = post_process_output(
            client,
            args.query,
            output,
            model,
            format_hint=plan.output_format_hint if plan else "",
        )
        timer.stop()

    # Print result
    print(output, end="")

    # Show timing report if requested
    if args.timing:
        timer.print_report()

    # JSON output for benchmarking
    if args.json_output:
        import json as json_module
        # Extract planner info from stderr if available
        planner_info = {}
        planner_match = re.search(r'Planner: (intent=\w+, complexity=\w+, tools=[^,]+(?:,\s*\w+)*, steps=\d+, confidence=[\d.]+)', sys.stderr.getvalue() if hasattr(sys, '_stderr_content') else "")
        # Alternative: check if we can access stderr content directly
        # We'll use a different approach - write planner info to stderr before JSON output
        report = {
            "generated_code": final_code,
            "self_heal_attempts": self_heal_attempts,
            "self_heal_errors": self_heal_errors,
            "security_violations": security_retry_data.get("violations", []),
            "security_retry_count": security_retry_data.get("retry_count", 0),
            "timing_ms": timer.to_dict(),
            "planner": {
                "enabled": PLANNER_ENABLED,
                "intent": plan.intent if plan else None,
                "complexity": plan.complexity if plan else None,
                "required_tools": plan.required_tools if plan else [],
                "relevant_modules": plan.relevant_modules if plan else [],
                "steps_count": len(plan.steps) if plan else 0,
                "confidence": plan.confidence if plan else None,
                "skip_planning": plan.skip_planning if plan else True,
                "timing_ms": timer.to_dict().get("Planner Analysis", 0),
            } if plan and PLANNER_ENABLED else None,
        }
        # Output as a compact JSON line to stderr
        print(f"__UPA_JSON__{json_module.dumps(report)}", file=sys.stderr)


if __name__ == "__main__":
    main()
