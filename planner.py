#!/usr/bin/env python3
"""
UPA Planner Module
Analyzes user queries and generates structured execution plans for the Coder.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI


# =============================================================================
# Data Structures
# =============================================================================

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


@dataclass
class ToolDefinition:
    """Definition of an injectable tool."""
    name: str
    description: str
    usage_doc: str
    categories: list[str]
    complexity_score: int


# =============================================================================
# Tool Registry
# =============================================================================

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
        usage_doc="""- web_search(query: str, num_results: int = 5) -> str: 用于网络搜索获取实时信息和事实。
  调用后会返回搜索结果的字符串。适用于需要查资料的问题。
  示例: info = web_search("AIDA 营销模型的组成")""",
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


# =============================================================================
# Planner System Prompt
# =============================================================================

PLANNER_SYSTEM_PROMPT = """你是一个任务规划器。分析用户查询并输出结构化的执行计划。

你的职责：
1. 识别用户意图（闲聊、计算、语义处理、多步骤任务）
2. 评估任务复杂度
3. 确定需要哪些工具（ask_sub_agent, web_search, safe_sub_agent）
4. 为复杂任务分解步骤
5. 提供编码提示

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
  "skip_planning": false
}

工具说明：
- ask_sub_agent: 用于翻译、总结、情感分析等语义任务
- web_search: 用于查询实时信息、事实核查
- safe_sub_agent: 语法糖装饰器，简化 sub-agent 调用

判断规则：
- 简单问候/闲聊 → intent="simple_chat", required_tools=[], skip_planning=true
- 纯数学计算 → intent="computation", required_tools=[], relevant_modules=["math"]
- 需要翻译/总结 → intent="semantic", required_tools=["ask_sub_agent"]
- 翻译+计算等混合 → intent="hybrid", required_tools=["ask_sub_agent"], steps详细分解
- 多步骤复杂任务 → intent="multi_step", 提供完整steps分解
- 需要查资料 → required_tools加入["web_search"]

只输出JSON，不要其他文字。
"""


# =============================================================================
# Utility Functions
# =============================================================================

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
        )
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


# =============================================================================
# Main Planner Function
# =============================================================================

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
        # Find JSON object in the response
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


# =============================================================================
# Dynamic Prompt Builder
# =============================================================================

# Base static prompt for fallback
STATIC_CODER_PROMPT = """你是一个 Python 逻辑单元。你的回答必须仅包含一个 Python 代码块。

规则：
1. 所有输出都必须通过 print() 语句输出
2. 闲聊场景：生成 print("回复内容")
3. 计算场景：生成计算逻辑并 print 结果
4. 数据处理：可以使用 datetime, json, re, math 等标准库

可用的特殊函数：
- ask_sub_agent(query: str) -> str: 用于处理语义理解、翻译、总结等需要 AI 的任务。
  调用后会返回处理结果的字符串。内部有自愈机制，执行失败时会自动修复。
  示例: result = ask_sub_agent("请总结这段文本的主旨")

- web_search(query: str, num_results: int = 5) -> str: 用于网络搜索获取实时信息和事实。
  调用后会返回搜索结果的字符串。适用于需要查资料的问题。
  示例: info = web_search("AIDA 营销模型的组成")

- safe_sub_agent(query): 装饰器，简化 ask_sub_agent 调用的语法糖。
  装饰的函数会自动接收子代理结果作为第一个参数。

使用场景：
- 纯逻辑/计算任务：直接用 Python 代码
- 需要语义理解/翻译/总结：使用 @safe_sub_agent 或 ask_sub_agent()
- 需要查资料/事实信息：使用 web_search()
- 混合任务：先获取信息（搜索或子代理），再做逻辑处理

重要：
- ask_sub_agent 内部有自愈机制，执行失败会自动修复（最多3次）
- web_search 可获取网络信息，用于回答需要最新知识或具体事实的问题
- @safe_sub_agent 只是语法糖，让代码更简洁
- 不要输出任何代码块之外的文字
- 只输出 ```python ... ``` 格式的代码"""


def build_coder_prompt(plan: Plan) -> str:
    """Build optimized SYSTEM_PROMPT based on plan."""
    # If skip_planning, use static prompt
    if plan.skip_planning:
        return STATIC_CODER_PROMPT

    base_prompt = """你是一个 Python 逻辑单元。你的回答必须仅包含一个 Python 代码块。

规则：
1. 所有输出都必须通过 print() 语句输出
2. 闲聊场景：生成 print("回复内容")
3. 计算场景：生成计算逻辑并 print 结果
4. 数据处理：可以使用 datetime, json, re, math 等标准库
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

    base_prompt += """
重要：
- 不要输出任何代码块之外的文字
- 只输出 ```python ... ``` 格式的代码"""

    return base_prompt
