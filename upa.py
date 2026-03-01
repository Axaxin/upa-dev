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

from typing import Any

from upa.planner_models import Plan, PlanStep, LogicStep, PlanParseResult


# =============================================================================
# Phase 11: Intent Recognition (Independent Service)
# =============================================================================

@dataclass
class Intent:
    """
    Intent classification result - Phase 11 新增

    用于独立意图识别服务，在 Planner 之前进行快速分类。
    """
    category: str                   # simple_chat, computation, semantic, knowledge, multi_step, complex
    complexity: str                 # trivial, simple, medium, complex
    suggested_model: str | None     # 推荐的 Coder 模型（可选）
    requires_planning: bool         # 是否需要 Planner 分析
    confidence: float = 0.0         # 分类置信度
    reasoning: str | None = None    # 简短推理说明（用于调试）


@dataclass
class ToolDefinition:
    """Definition of an injectable tool."""
    name: str
    description: str
    usage_doc: str
    categories: list[str]
    complexity_score: int


# =============================================================================
# Phase 6: Complexity-Aware Coder Selection
# =============================================================================

@dataclass
class ComplexityModelMapping:
    """Mapping from (intent, complexity) to model configuration."""
    model: str                      # Model identifier
    provider: str | None = None     # Optional provider override
    enable_self_check: bool = False # Enable TDD self-check in prompt


def parse_model_mapping(value: str) -> ComplexityModelMapping:
    """
    Parse 'model[:provider][:self-check]' into ComplexityModelMapping.

    Examples:
        "grok/grok-code-fast-1"
        "kimi-k2.5:dashscope"
        "kimi-k2.5:dashscope:self-check"
        "o3-mini:openai:self-check"
    """
    parts = value.split(":")
    model = parts[0]
    provider = None
    enable_self_check = False

    for part in parts[1:]:
        if part == "self-check":
            enable_self_check = True
        elif part:  # Non-empty string that's not "self-check"
            provider = part

    return ComplexityModelMapping(model, provider, enable_self_check)


def load_complexity_map_from_env() -> dict[tuple[str, str], ComplexityModelMapping]:
    """
    Load complexity model mapping from environment variables.

    Format: UPA_MODEL_MAP_{INTENT}_{COMPLEXITY}=model[:provider][:self-check]

    Examples:
        UPA_MODEL_MAP_computation_simple=grok/grok-code-fast-1
        UPA_MODEL_MAP_computation_medium=kimi-k2.5:dashscope:self-check
        UPA_MODEL_MAP__complex=kimi-k2.5:dashscope:self-check  # wildcard
    """
    mapping = DEFAULT_COMPLEXITY_MODEL_MAP.copy()

    for key, value in os.environ.items():
        if key.startswith("UPA_MODEL_MAP_"):
            # Parse: UPA_MODEL_MAP_computation_complex=...
            suffix = key[len("UPA_MODEL_MAP_"):]  # "computation_complex"
            parts = suffix.rsplit("_", 1)  # Split from right: ["computation", "complex"]

            if len(parts) == 2:
                intent, complexity = parts
                intent = intent.lower()
                complexity = complexity.lower()

                # Handle wildcard intent: UPA_MODEL_MAP__complex
                if intent == "":
                    intent = "*"

                # Validate complexity level
                if complexity in ("trivial", "simple", "medium", "complex"):
                    mapping[(intent, complexity)] = parse_model_mapping(value)

    return mapping


# Default complexity-to-model mapping registry
DEFAULT_COMPLEXITY_MODEL_MAP: dict[tuple[str, str], ComplexityModelMapping] = {
    # Fast models for trivial/simple tasks
    ("computation", "trivial"): ComplexityModelMapping("grok/grok-code-fast-1"),
    ("computation", "simple"):  ComplexityModelMapping("grok/grok-code-fast-1"),
    ("simple_chat", "trivial"): ComplexityModelMapping("grok/grok-code-fast-1"),
    ("simple_chat", "simple"):  ComplexityModelMapping("grok/grok-code-fast-1"),

    # kimi-k2.5 for medium/complex tasks (with self-check)
    # Note: kimi-k2.5 requires DashScope provider
    ("computation", "medium"): ComplexityModelMapping("kimi-k2.5", provider="dashscope", enable_self_check=True),
    ("computation", "complex"): ComplexityModelMapping("kimi-k2.5", provider="dashscope", enable_self_check=True),
    ("hybrid", "medium"):       ComplexityModelMapping("kimi-k2.5", provider="dashscope", enable_self_check=True),
    ("hybrid", "complex"):      ComplexityModelMapping("kimi-k2.5", provider="dashscope", enable_self_check=True),
    ("multi_step", "medium"):   ComplexityModelMapping("kimi-k2.5", provider="dashscope", enable_self_check=True),
    ("multi_step", "complex"):  ComplexityModelMapping("kimi-k2.5", provider="dashscope", enable_self_check=True),
    ("semantic", "medium"):     ComplexityModelMapping("kimi-k2.5", provider="dashscope", enable_self_check=True),
    ("semantic", "complex"):    ComplexityModelMapping("kimi-k2.5", provider="dashscope", enable_self_check=True),

    # Wildcard fallback for any medium/complex task
    ("*", "medium"):  ComplexityModelMapping("kimi-k2.5", provider="dashscope", enable_self_check=True),
    ("*", "complex"): ComplexityModelMapping("kimi-k2.5", provider="dashscope", enable_self_check=True),
}


# Tool Registry
TOOL_REGISTRY: dict[str, ToolDefinition] = {
    "set_output": ToolDefinition(
        name="set_output",
        description="Return final result (preserves data type)",
        usage_doc="""- set_output(data): 返回最终结果，保持原始数据类型（dict, list, number, string等）。
  必须调用一次，否则报错。

  示例:
    result = {"total": 100, "items": [1, 2, 3]}
    set_output(result)

    # 简单计算
    set_output(42)

    # 文本结果
    set_output("Hello, World!")
""",
        categories=["output"],
        complexity_score=0,
    ),
    "get_output": ToolDefinition(
        name="get_output",
        description="Get current output result (for chained processing)",
        usage_doc="""- get_output(): 获取当前输出结果，用于链式处理。

  示例:
    data = get_output()  # 获取之前设置的结果
    processed = data * 2
    set_output(processed)
""",
        categories=["output"],
        complexity_score=0,
    ),
    "ask_semantic": ToolDefinition(
        name="ask_semantic",
        description="Process semantic tasks (translation, summary, sentiment)",
        usage_doc="""- ask_semantic(query: str) -> str: 用于处理语义理解、翻译、总结等需要 AI 的任务。
  直接返回文本结果，无需代码生成。
  示例: result = ask_semantic("请总结这段文本的主旨")""",
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
        set_output({"error": data['error']})
    else:
        set_output(data["results"])

    # 复杂任务可加 assert 自检
    assert data.get("results"), "搜索无结果"
    assert len(data["results"]) > 0, "未找到相关信息"
""",
        categories=["search", "fact-checking"],
        complexity_score=2,
    ),
    "safe_semantic": ToolDefinition(
        name="safe_semantic",
        description="Decorator syntax sugar for semantic calls",
        usage_doc="""- safe_semantic(query): 装饰器，简化 ask_semantic 调用的语法糖。

  使用方式 1 - 装饰空函数:
  ```python
@safe_semantic("将 'Hello' 翻译成中文")
def translation(result):
    print(result)

translation()
```

  使用方式 2 - 装饰带参数的函数:
  ```python
@safe_semantic("总结文字")
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
# Phase 10: Modular Prompt Architecture
# =============================================================================

# -----------------------------------------------------------------------------
# 10.1 Core Rules Layer (~800 chars)
# -----------------------------------------------------------------------------

CORE_RULES_PROMPT = """你是一个 Python 逻辑单元。你的回答必须仅包含一个 Python 代码块。

【预定义函数】直接调用，不要重新定义：
- set_output(data): 返回最终结果（必须调用一次）
- get_output(): 获取当前输出结果（用于链式处理）
- web_search(query, num_results=5) -> dict: 网络搜索，返回 {"results": [...], "error": null}
- ask_semantic(query) -> str: 语义处理（翻译、总结、情感分析），直接返回文本

【核心规则】
1. 必须调用 set_output(data) 一次来返回最终结果
2. 可以用 print() 输出调试信息（显示在日志中，不影响结果）
3. 禁止重新定义预定义函数
4. 如果调用工具，必须解析并利用其返回结果，禁止忽略

数据处理：可使用 datetime, json, re, math 等标准库

重要：只输出 ```python ... ``` 格式的代码，不要其他文字。"""

# -----------------------------------------------------------------------------
# 10.2 Task Rules Registry (Dynamic Injection)
# -----------------------------------------------------------------------------

# 多选题检测规则
MULTIPLE_CHOICE_RULES = """
【多选题输出规则】如果题目有选项（A/B/C/D），必须输出选项字母，而非计算结果本身：
- 错误：计算 12 × 8 = 96，set_output(96) ❌
- 正确：计算 12 × 8 = 96，对应选项 B，set_output("B") ✅
- 必须将计算结果/事实与选项进行映射，输出正确选项字母
- 数值选项示例：
  ```python
  result = 0.5 * 2 * 10**2  # 计算得 100
  options = {50: "A", 100: "B", 150: "C", 200: "D"}
  answer = options.get(result, str(result))
  set_output(answer)  # 输出 "B"
  ```
- 文本选项示例：
  ```python
  if result == "氧化反应": answer = "B"
  elif result == "分解反应": answer = "A"
  set_output(answer)
  ```"""

# 工具使用规范
TOOL_USAGE_RULES = """
【工具使用规范】
- web_search: 用于查询实时信息、事实核查。返回 dict，需解析 data["results"]
- ask_semantic: 用于翻译、总结、情感分析等语义任务。直接返回文本
- 禁止调用工具后用"基于知识"等借口忽略结果"""

# 思维链推理规则
COT_REASONING_RULES = """
【思维链 CoT】对于需要推理的问题，要求 ask_semantic 先分析再结论：
- "请先分析每个选项与搜索结果的匹配程度，然后得出结论"
- "先逐步推理，最后只返回选项字母：A/B/C/D"
"""

# 自检规则 (medium/complex 任务)
SELF_CHECK_RULES = """
【自检要求】在 set_output() 前，添加 assert 语句校验关键结果：
- 数值：assert isinstance(result, (int, float))
- 范围：assert 0 <= result <= 1000000
- 非空：assert len(results) > 0
- 格式：assert re.match(r'\\d{4}-\\d{2}-\\d{2}', date_str)"""


def detect_multiple_choice(query: str) -> bool:
    """
    检测问题是否为多选题格式。

    Args:
        query: 用户输入的问题文本

    Returns:
        True 如果检测到多选题格式，False 否则
    """
    patterns = [
        # A. B. C. D. 格式（中英文句号、括号）
        r'[A-D][\.、\)）]\s*[\u4e00-\u9fa5\w]',  # A. xxx B. xxx
        # 连续选项格式
        r'[A-D][\.、\)）][^A-D]*[A-D][\.、\)）]',  # A. ... B. ...
        # 中文选项格式
        r'选项\s*[A-D]',  # 选项A、选项B
        # "A是..." 格式
        r'[A-D]\s*[是为]',  # A是... B为...
        # 多选题明确标记
        r'[A-D]\.\s*[^\n]+\n\s*[A-D]\.',  # 多行选项
        # 括号内选项
        r'\([A-D]\)',  # (A) (B) (C) (D)
        # 题目末尾选项列表
        r'[？?]\s*[A-D][\.、]',  # ...？A. B. C. D.
    ]

    for pattern in patterns:
        if re.search(pattern, query, re.IGNORECASE):
            return True

    # 检查是否有至少2个不同选项出现
    options_found = set(re.findall(r'\b[A-D]\b', query.upper()))
    if len(options_found) >= 2:
        return True

    return False


def detect_intent_features(query: str) -> dict[str, bool]:
    """
    检测查询的意图特征，用于辅助 Planner 分类。

    Returns:
        特征字典，包含各意图的正负特征检测结果
    """
    features = {
        # computation 特征
        "has_math_expr": bool(re.search(r'\d+\s*[\+\-\*/\^=]', query)),
        "has_calc_keyword": bool(re.search(r'计算|求.*值|等于|斐波那契|素数|阶乘', query)),
        "is_pure_math": bool(re.match(r'^[\d\s\+\-\*/\^\.\(\)]+$', query.strip())),

        # semantic 特征
        "has_translate": bool(re.search(r'翻译|translate', query, re.IGNORECASE)),
        "has_summarize": bool(re.search(r'总结|摘要|概括|summarize', query, re.IGNORECASE)),
        "has_sentiment": bool(re.search(r'情感|态度|sentiment', query, re.IGNORECASE)),
        "has_polish": bool(re.search(r'润色|改写|优化.*文字', query)),

        # multi_step / web_search 特征
        "needs_fact_check": bool(re.search(r'是谁|什么是|哪个|哪里|首都|提出者|发明者', query)),
        "needs_realtime": bool(re.search(r'最新|今天|今年|近期|当前|现在', query)),
        "has_question_word": bool(re.search(r'谁|什么|哪|如何|为什么|怎样', query)),

        # simple_chat 特征
        "is_greeting": bool(re.match(r'^[你好吗嗨嘿嗯]+[！!？?。.，,]*$', query.strip())),
        "is_thanks": bool(re.match(r'^(谢谢|感谢|thanks|thank you)', query.strip(), re.IGNORECASE)),
        "is_short": len(query.strip()) <= 3,

        # multiple_choice 特征
        "is_multiple_choice": detect_multiple_choice(query),
    }

    return features


def infer_intent_from_features(features: dict[str, bool], query: str) -> tuple[str, str]:
    """
    根据特征推断意图和复杂度。

    Returns:
        (intent, complexity) 元组
    """
    # simple_chat: 问候、感谢、超短输入
    if features["is_greeting"] or features["is_thanks"] or features["is_short"]:
        return "simple_chat", "trivial"

    # computation: 数学表达式、计算关键词
    if features["has_math_expr"] or features["has_calc_keyword"]:
        # 检查是否混合语义任务
        if features["has_translate"] or features["has_summarize"]:
            return "hybrid", "medium"
        return "computation", "simple"

    # semantic: 翻译、总结、情感分析
    if features["has_translate"] or features["has_summarize"] or features["has_sentiment"]:
        return "semantic", "simple"

    # multi_step: 需要事实核查或实时信息
    if features["needs_fact_check"] or features["needs_realtime"]:
        if features["is_multiple_choice"]:
            return "multi_step", "medium"
        return "multi_step", "simple"

    # hybrid: 混合特征
    if features["has_question_word"] and features["has_math_expr"]:
        return "hybrid", "medium"

    # 默认
    return "unknown", "simple"


# -----------------------------------------------------------------------------
# 10.3 Intent Rules for Planner Enhancement
# -----------------------------------------------------------------------------

INTENT_CLASSIFICATION_RULES = {
    "computation": {
        "positive": [
            r'\d+\s*[\+\-\*/\^]',  # 数学表达式
            r'计算', r'求.*值', r'等于',
            r'斐波那契', r'素数', r'阶乘', r'排序', r'统计',
            r'最大值', r'最小值', r'平均值', r'方差',
        ],
        "negative": [
            r'翻译', r'总结', r'情感', r'是谁', r'什么是',
            r'润色', r'改写', r'润色',
        ],
    },
    "semantic": {
        "positive": [
            r'翻译', r'translate',
            r'总结', r'摘要', r'概括', r'summarize',
            r'情感', r'态度', r'sentiment',
            r'润色', r'改写', r'优化.*文字',
        ],
        "negative": [
            r'\d+\s*[\+\-\*/\^]', r'计算', r'等于',
        ],
    },
    "multi_step": {
        "positive": [
            r'是谁', r'是谁提出', r'发明者', r'提出者',
            r'什么是.*概念', r'首都是哪', r'哪里是',
            r'最新', r'今天', r'今年', r'近期',
            r'哪个.*正确', r'下列.*说法',
        ],
        "requires_tools": ["web_search"],
    },
    "simple_chat": {
        "positive": [
            r'^[你好吗嗨嘿嗯]+[！!？?。.，,]*$',
            r'^(谢谢|感谢|thanks)',
        ],
        "negative": [
            r'\?', r'？',  # 包含问号
        ],
    },
}

# -----------------------------------------------------------------------------
# 10.4 Tool Selection Rules for Planner
# -----------------------------------------------------------------------------

TOOL_SELECTION_RULES = {
    "web_search": {
        "use_when": [
            "查询实时信息（新闻、股价、天气）",
            "事实核查（历史事件、人物、地点）",
            "概念解释（专业术语、科学概念）",
            "需要最新知识的场景",
        ],
        "avoid_when": [
            "纯数学计算",
            "翻译、总结等语义任务",
            "简单问候闲聊",
            "逻辑推理（不涉及外部事实）",
        ],
    },
    "ask_semantic": {
        "use_when": [
            "翻译任务",
            "文本总结、摘要",
            "情感分析、态度判断",
            "文本润色、改写",
            "需要语义理解的场景",
        ],
        "avoid_when": [
            "纯数学计算",
            "简单问候闲聊",
            "事实查询（应用 web_search）",
        ],
    },
    "none": {
        "use_when": [
            "简单问候、感谢",
            "纯数学表达式",
            "直接可回答的问题",
        ],
    },
}


# Planner System Prompt
PLANNER_SYSTEM_PROMPT = """你是一个任务规划器。分析用户查询并输出结构化的执行计划。

你的职责：
1. 识别用户意图（闲聊、计算、语义处理、多步骤任务）
2. 评估任务复杂度
3. 确定需要哪些工具（ask_semantic, web_search）
4. **输出逻辑契约（logic_steps）**：带变量绑定的执行步骤，强制数据流

【重要】输出严格 JSON，且字段类型必须正确：
- 数组字段：required_tools, relevant_modules, logic_steps, input_vars 必须是 JSON 数组 [...]，不能是字符串 "[]"
- 对象字段：args 必须是 JSON 对象 {...}，不能是字符串 "{}"
- 布尔字段：requires_post_processing, skip_planning 必须是 true/false，不能是 "true"/"false"
- 数字字段：confidence 必须是数字 0.95，不能是字符串 "0.95"

输出格式模板：
{
  "intent": "simple_chat|computation|semantic|hybrid|multi_step",
  "complexity": "trivial|simple|medium|complex",
  "required_tools": [],
  "relevant_modules": [],
  "steps": [],
  "logic_steps": [],
  "expected_output_type": "string",
  "requires_post_processing": false,
  "output_format_hint": "",
  "confidence": 0.95,
  "skip_planning": false
}

【修复模式】如果收到错误反馈（如"JSON 解析失败"），必须：
1. 检查输出是否为 valid JSON
2. 确保数组/对象/布尔/数字字段类型正确
3. 重新输出完整的 JSON，不要解释
"""

# Planner Repair Prompt - 用于 JSON 解析失败时的修复请求
PLANNER_REPAIR_PROMPT = """【JSON 格式修复】你的上一次输出解析失败。

错误信息：{error}
原始输出：{original_output}

请修正 JSON 格式问题，重新输出。注意：
- 数组必须是 [...] 格式，不能是字符串
- 对象必须是 {{...}} 格式，不能是字符串
- 布尔值必须是 true/false，不能是 "true"/"false"
- 数字必须是 0.95 格式，不能是 "0.95"

只输出修正后的 JSON，不要其他内容。"""

PLANNER_LOGIC_STEPS_FORMAT = """
logic_steps 数组元素格式（当需要时使用）：
[
  {"id": "S1", "action": "web_search", "args": {"query": "关键词"}, "input_vars": [], "output_var": "data", "description": "描述"},
  {"id": "S2", "action": "ask_semantic", "args": {"query": "问题：{data}"}, "input_vars": ["data"], "output_var": "answer", "description": "分析"},
  {"id": "S3", "action": "set_output", "args": {"value": "{answer}"}, "input_vars": ["answer"], "output_var": "_final", "description": "返回结果"}
]
"""

# Append additional prompt content to PLANNER_SYSTEM_PROMPT
PLANNER_SYSTEM_PROMPT += """

工具说明：
- ask_semantic: 用于翻译、总结、情感分析等语义任务，返回文本
- web_search: 用于查询实时信息、事实核查，返回 {"answer": "...", "results": [...], "error": null}
- set_output: 返回最终结果（必须调用一次）
- logic: 纯逻辑/计算操作

logic_steps 规则：
1. 每个步骤必须有 id（S1, S2, ...）和 output_var（变量名）
2. 使用 {var_name} 语法引用前面步骤的输出变量
3. 工具结果必须通过变量传递，禁止跳过步骤
4. 最后必须有一个 action="set_output" 的步骤

requires_post_processing 判断规则：
- true: 需要整理格式化输出的场景（web_search 结果整理、多步骤综合、数值结果解释）
- false: 简单直接的输出（纯代码执行结果、简单问候、单值结果如翻译）

意图判断规则：
- simple_chat: 简单问候、闲聊、感谢 → skip_planning=true
- computation: 纯数学计算、逻辑推理
- semantic: 翻译、总结、情感分析等纯语义任务
- hybrid: 语义 + 计算混合任务
- multi_step: 需要多步骤协作（如先搜索后分析）

示例 1：需要网络搜索的问题
用户问题："支架式教学的概念最早由谁提出？A.皮亚杰 B.维果茨基 C.布鲁纳 D.斯金纳"
输出:
{"intent": "multi_step", "complexity": "medium", "required_tools": ["web_search", "ask_semantic"], "relevant_modules": ["json"], "logic_steps": [{"id": "S1", "action": "web_search", "args": {"query": "支架式教学概念最早提出者"}, "input_vars": [], "output_var": "search_data", "description": "搜索相关信息"}, {"id": "S2", "action": "ask_semantic", "args": {"query": "根据搜索结果 {search_data} 回答：支架式教学最早由谁提出？只返回选项字母 A/B/C/D"}, "input_vars": ["search_data"], "output_var": "answer", "description": "分析结果"}, {"id": "S3", "action": "set_output", "args": {"value": "{answer}"}, "input_vars": ["answer"], "output_var": "_final", "description": "返回最终答案"}], "requires_post_processing": false, "confidence": 0.95, "skip_planning": false}

示例 2：纯计算任务
用户问题："计算斐波那契数列第 10 项"
输出:
{"intent": "computation", "complexity": "simple", "required_tools": [], "relevant_modules": [], "logic_steps": [{"id": "S1", "action": "logic", "args": {}, "input_vars": [], "output_var": "result", "description": "计算斐波那契数列"}, {"id": "S2", "action": "set_output", "args": {"value": "{result}"}, "input_vars": ["result"], "output_var": "_final", "description": "返回结果"}], "requires_post_processing": false, "confidence": 0.99, "skip_planning": false}

示例 3：简单闲聊
用户问题："你好"
输出:
{"intent": "simple_chat", "complexity": "trivial", "required_tools": [], "relevant_modules": [], "logic_steps": [], "requires_post_processing": false, "confidence": 0.99, "skip_planning": true}

示例 4：翻译任务
用户问题："把 'Hello' 翻译成中文"
输出:
{"intent": "semantic", "complexity": "simple", "required_tools": ["ask_semantic"], "relevant_modules": [], "logic_steps": [{"id": "S1", "action": "ask_semantic", "args": {"query": "把 'Hello' 翻译成中文"}, "input_vars": [], "output_var": "translation", "description": "翻译"}, {"id": "S2", "action": "set_output", "args": {"value": "{translation}"}, "input_vars": ["translation"], "output_var": "_final", "description": "返回结果"}], "requires_post_processing": false, "confidence": 0.99, "skip_planning": false}

只输出 JSON，不要其他文字。
"""

# =============================================================================
# Phase 11: Intent Recognition Prompts
# =============================================================================

INTENT_CLASSIFICATION_PROMPT = """
你是一个意图分类器。分析用户查询并输出分类结果。

## 类别定义（互斥，选最匹配的）

- **simple_chat**: 问候、闲聊、感谢
  - 例："你好"、"谢谢"、"早上好"、"Hi"

- **computation**: 纯数学计算、公式求解、数值运算
  - 例："2+2=?"、"求积分∫x²dx"、"解方程 2x+3=7"、"计算组合数 C(5,3)"
  - 特征：有明确数值答案，可通过编程直接计算

- **semantic**: 语言相关的语义任务
  - 例："翻译成英文"、"总结这篇文章"、"分析这句话的情感"
  - 特征：输入输出都是自然语言，不需要外部知识

- **knowledge**: 事实/概念/理论查询（新增）
  - 例："什么是 Porter 五力"、"维果茨基是谁"、"社会契约论的观点"、"文艺复兴的背景"
  - 特征：需要特定领域知识（历史、政治、经济、管理、物理、化学、生物等）

- **multi_step**: 需要多步骤协作或外部工具
  - 例："先搜索 X 概念，然后分析它与 Y 的关系"
  - 特征：明确需要 web_search 或 ask_semantic 工具

- **complex**: 复杂推理，需要深度分析或多步推导
  - 例："证明 X 定理"、"分析 X 现象的多个影响因素"
  - 特征：推理链条长，需要多步逻辑推导

## 复杂度分级

- **trivial**: 条件反射式回答（<5 秒）
- **simple**: 一步处理（<30 秒）
- **medium**: 2-3 步处理（<2 分钟）
- **complex**: 4 步以上或深度推理（>2 分钟）

## requires_planning 判断规则（重要）

输出 `true` 的情况：
1. 类别是 knowledge 或 multi_step
2. 类别是 complex（无论什么领域）
3. 类别是 computation 但复杂度是 medium 或 complex
4. 涉及专业领域知识（物理、化学、生物、历史、政治、经济、管理等）

输出 `false` 的情况：
1. 类别是 simple_chat
2. 类别是 computation 且复杂度是 trivial 或 simple（纯数学计算）
3. 类别是 semantic 且复杂度是 trivial 或 simple（简单翻译/总结）

## 输出格式

严格 JSON：
{
  "category": "simple_chat|computation|semantic|knowledge|multi_step|complex",
  "complexity": "trivial|simple|medium|complex",
  "requires_planning": true|false,
  "confidence": 0.0-1.0,
  "reasoning": "一句话说明分类依据"
}

只输出 JSON，不要其他内容。
"""

# =============================================================================
# Phase 11: Intent Recognition Functions
# =============================================================================

def recognize_intent(
    client: OpenAI,
    query: str,
    model: str,
    timeout: float = 10.0,
    max_retries: int = 2,
    base_delay: float = 0.5,
) -> Intent:
    """
    使用快速模型进行意图分类 - Phase 11 新增

    Args:
        client: OpenAI 客户端
        query: 用户查询
        model: 模型名称
        timeout: 超时时间
        max_retries: 重试次数
        base_delay: 基础延迟

    Returns:
        Intent 对象
    """
    import random
    import signal
    from httpx import ProxyError
    from openai import APIConnectionError, APIStatusError

    def timeout_handler(signum, frame):
        raise TimeoutError("Intent recognition call timed out")

    # Set timeout (works on Unix systems)
    if hasattr(signal, 'SIGALRM'):
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(timeout))

    try:
        # Build request parameters
        request_params = {
            "model": model,
            "messages": [
                {"role": "system", "content": INTENT_CLASSIFICATION_PROMPT},
                {"role": "user", "content": query}
            ],
            "temperature": 0.0,  # Deterministic classification
            "max_tokens": 200,   # Concise JSON output
        }

        # Add JSON mode for models that support it
        if model:
            model_lower = model.lower()
            if any(x in model_lower for x in ['gpt-4o', 'gpt4o', 'qwen', 'deepseek', 'grok', 'gemini']):
                request_params["response_format"] = {"type": "json_object"}

        # Retry loop with exponential backoff
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                response = client.chat.completions.create(**request_params)
                break  # Success, exit retry loop

            except (APIConnectionError, ProxyError, APIStatusError) as e:
                last_exception = e
                status_code = getattr(e, 'status_code', None)

                # Check if this is a rate limit or service unavailable error
                is_retryable = (
                    status_code in (429, 503, 502, 504) or
                    "rate limit" in str(e).lower() or
                    "throttl" in str(e).lower() or
                    "service unavailable" in str(e).lower() or
                    "connection error" in str(e).lower()
                )

                if is_retryable and attempt < max_retries:
                    # Exponential backoff with jitter
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 0.2)
                    print(f"Intent API error, retrying in {delay:.1f}s... ({attempt+1}/{max_retries})", file=sys.stderr)
                    time.sleep(delay)
                else:
                    print(f"Intent recognition failed after {attempt+1} attempts: {type(e).__name__}", file=sys.stderr)
                    # Return low-confidence default intent
                    return Intent(
                        category="unknown",
                        complexity="simple",
                        suggested_model=None,
                        requires_planning=False,
                        confidence=0.0,
                        reasoning=f"API error: {type(e).__name__}",
                    )

            except Exception as e:
                # Non-retryable error, return default
                return Intent(
                    category="unknown",
                    complexity="simple",
                    suggested_model=None,
                    requires_planning=False,
                    confidence=0.0,
                    reasoning=f"Unexpected error: {type(e).__name__}",
                )

        # Parse response
        content = response.choices[0].message.content.strip()

        # Attempt JSON parsing
        try:
            data = json.loads(content)
            return Intent(
                category=data.get("category", "unknown"),
                complexity=data.get("complexity", "simple"),
                suggested_model=data.get("suggested_model"),
                requires_planning=data.get("requires_planning", False),
                confidence=float(data.get("confidence", 0.0)),
                reasoning=data.get("reasoning"),
            )
        except json.JSONDecodeError as e:
            # Try to extract JSON from text
            json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    return Intent(
                        category=data.get("category", "unknown"),
                        complexity=data.get("complexity", "simple"),
                        suggested_model=data.get("suggested_model"),
                        requires_planning=data.get("requires_planning", False),
                        confidence=float(data.get("confidence", 0.0)),
                        reasoning=data.get("reasoning"),
                    )
                except json.JSONDecodeError:
                    pass

            # JSON parsing failed, return low-confidence intent
            return Intent(
                category="unknown",
                complexity="simple",
                suggested_model=None,
                requires_planning=False,
                confidence=0.0,
                reasoning=f"JSON parse error: {str(e)}",
            )

    finally:
        # Cancel alarm
        if hasattr(signal, 'SIGALRM'):
            signal.alarm(0)


def is_trivial_query(query: str) -> bool:
    """Detect queries that don't need planning (Phase 10 enhanced)."""
    query = query.strip()

    # Use feature detection for more accurate trivial detection
    features = detect_intent_features(query)

    # Trivial if: greeting, thanks, or very short non-question
    if features["is_greeting"] or features["is_thanks"]:
        return True

    # Very short queries (<=3 chars) that are not questions
    if features["is_short"] and not features["has_question_word"]:
        return True

    # Pure math expressions (no semantic content)
    if features["is_pure_math"]:
        return True

    # Legacy patterns for edge cases
    legacy_patterns = [
        r'^[你好吗嗨嘿嗯]+[！!？?。.，,]*$',  # Simple greetings
        r'^(谢谢|感谢|thanks|thank you)',  # Thank you
        r'^[0-9+\-*/\s().^]+$',  # Pure math expression
    ]

    for pattern in legacy_patterns:
        if re.match(pattern, query, re.IGNORECASE):
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
        required_tools=["ask_semantic"],  # Include most common tool
        relevant_modules=["datetime", "json", "re", "math"],
        coding_hints=[],
        expected_output_type="string",
        confidence=confidence,
        skip_planning=skip_planning,
    )


def create_plan_from_intent(intent: Intent) -> Plan:
    """
    根据 Intent 创建简化的 Plan - Phase 11 新增.

    用于简单任务跳过 Planner 时，基于意图分类结果快速构建 Plan。

    Args:
        intent: Intent 分类结果

    Returns:
        Plan 对象
    """
    # Map intent category to required tools
    tool_map = {
        "simple_chat": [],
        "computation": [],
        "semantic": ["ask_semantic"],
        "multi_step": ["web_search"],
        "complex": ["web_search", "ask_semantic"],
    }

    return Plan(
        intent=intent.category,
        complexity=intent.complexity,
        steps=[],
        logic_steps=[],
        required_tools=tool_map.get(intent.category, []),
        relevant_modules=["datetime", "json", "re", "math"],
        coding_hints=[],
        expected_output_type="string",
        confidence=intent.confidence,
        skip_planning=not intent.requires_planning,
    )
def validate_plan(plan: Plan) -> Plan:
    """
    Validate and sanitize plan output.

    Note: Most validation is now handled by Pydantic in the Plan model.
    This function provides additional runtime validation and sanitization.
    """
    # Pydantic already validates:
    # - intent (valid values)
    # - complexity (valid values)
    # - confidence (0.0-1.0 range)
    # - required_tools (filtered to valid tools)
    # - steps (capped at 5)

    # Additional runtime validation can be added here if needed
    return plan


def parse_plan_from_json(json_str: str) -> Plan | None:
    """
    Parse Plan from JSON string with layered parsing strategy.
    Uses Pydantic models for type-safe validation.

    Layer 1: Fast path - direct parsing with Pydantic
    Layer 2: String repair path - handle stringified JSON fields
    Layer 3: Smart extraction path - regex-based field extraction
    """

    def extract_with_regex(content: str) -> dict:
        """
        Extract fields using regex as fallback.
        Handles cases where JSON structure is broken but fields are recognizable.
        """
        extracted = {}

        # Extract intent
        intent_match = re.search(r'"intent"\s*:\s*"([^"]+)"', content)
        if intent_match:
            extracted['intent'] = intent_match.group(1)

        # Extract complexity
        complexity_match = re.search(r'"complexity"\s*:\s*"([^"]+)"', content)
        if complexity_match:
            extracted['complexity'] = complexity_match.group(1)

        # Extract skip_planning
        skip_match = re.search(r'"skip_planning"\s*:\s*(true|false)', content, re.IGNORECASE)
        if skip_match:
            extracted['skip_planning'] = skip_match.group(1).lower() == 'true'

        # Extract confidence
        confidence_match = re.search(r'"confidence"\s*:\s*([\d.]+)', content)
        if confidence_match:
            extracted['confidence'] = float(confidence_match.group(1))

        # Extract required_tools (handles both array and stringified array)
        tools_match = re.search(r'"required_tools"\s*:\s*\[([^\]]*)\]', content)
        if tools_match:
            tools_str = tools_match.group(1).strip()
            if tools_str:
                # Extract individual tool names from the array
                tool_names = re.findall(r'"([^"]+)"', tools_str)
                extracted['required_tools'] = tool_names
            else:
                extracted['required_tools'] = []

        # Extract relevant_modules
        modules_match = re.search(r'"relevant_modules"\s*:\s*\[([^\]]*)\]', content)
        if modules_match:
            modules_str = modules_match.group(1).strip()
            if modules_str:
                module_names = re.findall(r'"([^"]+)"', modules_str)
                extracted['relevant_modules'] = module_names
            else:
                extracted['relevant_modules'] = []

        # Extract requires_post_processing
        post_match = re.search(r'"requires_post_processing"\s*:\s*(true|false)', content, re.IGNORECASE)
        if post_match:
            extracted['requires_post_processing'] = post_match.group(1).lower() == 'true'

        # Extract output_format_hint
        format_match = re.search(r'"output_format_hint"\s*:\s*"([^"]+)"', content)
        if format_match:
            extracted['output_format_hint'] = format_match.group(1)

        return extracted

    # Try parsing as JSON first
    try:
        data = json.loads(json_str)
        print(f"Planner: JSON parse succeeded (Layer 1: Fast path)", file=sys.stderr)
    except json.JSONDecodeError as e:
        # Log the error for debugging
        print(f"Planner: JSON parse failed - {str(e)[:200]}", file=sys.stderr)
        print(f"Planner: Raw JSON (first 500 chars): {json_str[:500]}...", file=sys.stderr)

        # Layer 3: Try regex extraction as last resort
        extracted = extract_with_regex(json_str)
        if extracted:
            print(f"Planner: Regex extraction succeeded for: {list(extracted.keys())}", file=sys.stderr)
            try:
                return Plan.model_validate(extracted)
            except Exception as e:
                print(f"Planner: Pydantic validation failed after regex: {e}", file=sys.stderr)
                return None
        print(f"Planner: Regex extraction also failed, returning None", file=sys.stderr)
        return None

    # Layer 1/2: Use Pydantic to parse the data directly
    # Pydantic will handle type coercion and validation automatically
    try:
        return Plan.model_validate(data)
    except Exception as e:
        print(f"Planner: Pydantic validation failed - {e}", file=sys.stderr)
        # Try to repair and re-validate
        try:
            # Handle stringified JSON fields (Layer 2 repair)
            for key in ['steps', 'logic_steps', 'required_tools', 'relevant_modules', 'coding_hints']:
                value = data.get(key)
                if isinstance(value, str):
                    try:
                        parsed = json.loads(value)
                        data[key] = parsed
                        print(f"Planner: Layer 2 repair - {key} was stringified JSON", file=sys.stderr)
                    except json.JSONDecodeError:
                        pass

            # Handle nested objects (steps and logic_steps)
            for step_data in data.get('steps', []):
                if isinstance(step_data, dict):
                    for dep_key in ['dependencies']:
                        dep_value = step_data.get(dep_key)
                        if isinstance(dep_value, str):
                            try:
                                step_data[dep_key] = json.loads(dep_value)
                            except json.JSONDecodeError:
                                pass

            for ls_data in data.get('logic_steps', []):
                if isinstance(ls_data, dict):
                    for list_key in ['args', 'input_vars']:
                        list_value = ls_data.get(list_key)
                        if isinstance(list_value, str):
                            try:
                                ls_data[list_key] = json.loads(list_value)
                            except json.JSONDecodeError:
                                pass

            return Plan.model_validate(data)
        except Exception as e2:
            print(f"Planner: Repair failed - {e2}", file=sys.stderr)
            # Return a default plan on validation failure
            return create_default_plan()


def run_planner(
    client: OpenAI,
    query: str,
    model: str,
    timeout: float = 5.0,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_repair_attempts: int = 2,  # Phase 10.5: Multi-round repair
) -> Plan:
    """
    Run planner with comprehensive fallback handling.

    Args:
        client: OpenAI client
        query: User query
        model: Model to use for planning
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts for rate limit errors (default 3)
        base_delay: Base delay in seconds for exponential backoff (default 1.0)

    Returns:
        Plan object (may be a default plan on failure)
    """
    import random
    import signal
    from httpx import ProxyError
    from openai import APIConnectionError, APIStatusError

    def timeout_handler(signum, frame):
        raise TimeoutError("Planner call timed out")

    # Set timeout (works on Unix systems)
    if hasattr(signal, 'SIGALRM'):
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(timeout))

    try:
        # Build request parameters
        request_params = {
            "model": model,
            "messages": [
                {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                {"role": "user", "content": query}
            ],
            "temperature": 0.3,  # Lower for more deterministic planning
            "max_tokens": 500,   # Plans should be concise
        }

        # Add structured output format for models that support JSON Schema
        # Support for: GPT-4o, Qwen, and other models with JSON mode
        if model:
            model_lower = model.lower()
            # GPT-4o series
            if 'gpt-4o' in model_lower or 'gpt4o' in model_lower:
                request_params["response_format"] = {"type": "json_object"}
            # Qwen series (DashScope)
            elif 'qwen' in model_lower:
                request_params["response_format"] = {"type": "json_object"}
            # DeepSeek series
            elif 'deepseek' in model_lower:
                request_params["response_format"] = {"type": "json_object"}
            # Grok series (via Cloudflare)
            elif 'grok' in model_lower:
                request_params["response_format"] = {"type": "json_object"}
            # Gemini series
            elif 'gemini' in model_lower:
                request_params["response_format"] = {"type": "json_object"}

        # Retry loop with exponential backoff (Phase 10.5: Rate limit handling)
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                response = client.chat.completions.create(**request_params)
                break  # Success, exit retry loop

            except (APIConnectionError, ProxyError, APIStatusError) as e:
                last_exception = e
                status_code = getattr(e, 'status_code', None)

                # Check if this is a rate limit or service unavailable error
                is_retryable = (
                    status_code in (429, 503, 502, 504) or
                    "rate limit" in str(e).lower() or
                    "throttl" in str(e).lower() or
                    "service unavailable" in str(e).lower() or
                    "connection error" in str(e).lower()
                )

                if is_retryable and attempt < max_retries:
                    # Exponential backoff with jitter
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                    print(f"Planner API rate limit/connection error, retrying in {delay:.1f}s... ({attempt+1}/{max_retries})", file=sys.stderr)
                    time.sleep(delay)
                else:
                    print(f"Planner API error after {attempt+1} attempts: {type(e).__name__}: {str(e)[:100]}", file=sys.stderr)
                    # Fall back to default plan
                    return create_default_plan(skip_planning=True)

            except Exception as e:
                # Non-retryable error, use default plan
                print(f"Planner unexpected error: {type(e).__name__}: {e}", file=sys.stderr)
                return create_default_plan(skip_planning=True)

        # If all retries failed but no exception was raised, use default plan
        if last_exception and attempt == max_retries:
            return create_default_plan(skip_planning=True)

        content = response.choices[0].message.content or ""

        # Log raw response for debugging
        print(f"Planner Raw JSON: {content[:500]}...", file=sys.stderr)

        # Try to extract JSON from response (in case there's extra text)
        json_match = re.search(r'\{[^{}]*\{.*\}[^{}]*\}|\{[^{}]+\}', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)

        plan = parse_plan_from_json(content)

        # Layer 4: LLM Repair - Multi-round repair for better reliability (Phase 10.5)
        if plan is None:
            print(f"Planner Parse Error: JSON parsing failed, requesting LLM repair (max {max_repair_attempts} attempts)...", file=sys.stderr)
            print(f"  Raw response: {content[:200]}...", file=sys.stderr)

            # Keep track of repair history for multi-round repair
            repair_history = [content]
            repair_succeeded = False

            for repair_attempt in range(max_repair_attempts):
                # Build repair prompt with escalating urgency
                if repair_attempt == 0:
                    error_msg = "无法解析为有效 JSON 或字段类型错误"
                else:
                    error_msg = f"第{repair_attempt+1}次修复仍然失败！请仔细检查 JSON 格式，确保：数组是 [...]、对象是{{...}}、布尔值是 true/false、数字不加引号"

                repair_prompt = PLANNER_REPAIR_PROMPT.format(
                    error=error_msg,
                    original_output=repair_history[-1][:800]  # Show last failed attempt
                )

                # Build conversation history with all previous attempts
                repair_messages = [
                    {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                    {"role": "user", "content": query},
                ]
                # Add all failed attempts as context
                for i, failed_output in enumerate(repair_history):
                    repair_messages.append({"role": "assistant", "content": failed_output})
                    if i == len(repair_history) - 1:
                        repair_messages.append({"role": "user", "content": repair_prompt})

                # Use lower temperature for more deterministic repair
                request_params["messages"] = repair_messages
                request_params["temperature"] = 0.1  # More deterministic for repair
                repair_response = client.chat.completions.create(**request_params)
                repair_content = repair_response.choices[0].message.content or ""

                print(f"Planner Repair attempt {repair_attempt+1}/{max_repair_attempts}: Received {len(repair_content)} chars", file=sys.stderr)

                # Try to extract JSON from repair response
                repair_json_match = re.search(r'\{[^{}]*\{.*\}[^{}]*\}|\{[^{}]+\}', repair_content, re.DOTALL)
                if repair_json_match:
                    repair_content = repair_json_match.group(0)

                # Try parsing the repaired content
                plan = parse_plan_from_json(repair_content)

                if plan is not None:
                    print(f"Planner Repair: Success on attempt {repair_attempt+1}!", file=sys.stderr)
                    repair_succeeded = True
                    break
                else:
                    print(f"Planner Repair: Attempt {repair_attempt+1} failed, trying again..." if repair_attempt < max_repair_attempts - 1 else "All repair attempts failed", file=sys.stderr)
                    repair_history.append(repair_content)  # Add to history for next attempt context

            if not repair_succeeded:
                print(f"Planner Repair: All {max_repair_attempts} attempts failed, using default plan", file=sys.stderr)
                return create_default_plan(skip_planning=True, confidence=0.0)

        # Validate the plan
        plan = validate_plan(plan)

        # Log to stderr
        print(f"Planner: intent={plan.intent}, complexity={plan.complexity}, "
              f"tools={plan.required_tools}, logic_steps={len(plan.logic_steps)}, "
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
- set_output(data): 返回最终结果（保持原始数据类型）
- get_output(): 获取当前输出结果（用于链式处理）
- web_search(query, num_results=5) -> dict: 网络搜索函数，返回结构化数据
- ask_semantic(query) -> str: 语义处理函数，直接返回文本结果
- safe_semantic(query): 装饰器

规则：
1. 必须调用 set_output(data) 一次来返回最终结果
2. 可以用 print() 输出调试信息（会显示在日志中，不影响结果）
3. 【绝对不要重新定义 set_output、web_search、ask_semantic 等预定义函数】
4. 【关键】如果调用了工具，必须解析并利用其返回结果来得出最终答案：
   - 解析 data["results"] 或返回值中的具体信息
   - 从中提取关键事实，基于这些事实得出结论
   - 禁止调用工具后用"基于知识"等借口忽略结果
5. 【多选题输出规则】如果题目有选项（A/B/C/D），必须输出选项字母，而非计算结果本身：
   - 错误示例：计算 12 × 8 = 96，set_output(96) ❌
   - 正确示例：计算 12 × 8 = 96，对应选项 B，set_output("B") ✅
   - 必须将计算结果/事实与选项进行映射，输出正确选项字母
6. 闲聊场景：set_output("回复内容")
7. 计算场景：计算后 set_output(result) 或 set_output("选项字母")
8. 数据处理：可以使用 datetime, json, re, math 等标准库

核心API：
- set_output(data): 返回最终结果，保持原始数据类型（dict, list, number, string等）
  必须调用一次，否则报错。
  示例:
    result = {"total": 100, "items": [1, 2, 3]}
    set_output(result)

- get_output(): 获取当前输出结果，用于链式处理。
  示例:
    data = get_output()  # 获取之前设置的结果
    processed = data * 2
    set_output(processed)

辅助函数：
- ask_semantic(query: str) -> str: 用于处理语义理解、翻译、总结等需要 AI 的任务。
  直接返回文本结果。
  示例:
    result = ask_semantic("请总结这段文本的主旨")
    set_output(result)

- web_search(query: str, num_results: int = 5) -> dict: 网络搜索获取实时信息。
  返回结构化数据: {"answer": "...", "results": [{"title": "...", "content": "...", "url": "..."}], "error": None}
  示例:
    data = web_search("今天的科技新闻")
    if data.get("error"):
        set_output({"error": data['error']})
    else:
        set_output(data["results"])

使用场景：
- 纯逻辑/计算任务：直接用 Python 代码，最后 set_output(result)
- 需要语义理解/翻译/总结：使用 ask_semantic()，然后 set_output(result)
- 需要查资料/事实信息：使用 web_search()，处理返回的 dict 数据
- 混合任务：先获取信息，再做逻辑处理，最后 set_output(result)

【工具使用正确/错误示例】

❌ 错误：调用工具后忽略结果
```python
data = web_search("支架式教学最早由谁提出")
print(data)  # 只打印，没使用
# 基于知识：布鲁纳提出的
set_output("C")  # 错误：直接用训练数据的知识
```

✅ 正确：解析并利用工具结果
```python
data = web_search("支架式教学最早由谁提出")
results = data.get("results", [])
# 从搜索结果中提取关键信息
answer_text = results[0]["content"] if results else ""
if "维果茨基" in answer_text or "Vygotsky" in answer_text:
    set_output("B")
elif "布鲁纳" in answer_text or "Bruner" in answer_text:
    set_output("C")
else:
    # 没找到时才用其他方式
    set_output(ask_semantic("支架式教学最早由谁提出？"))
```

✅ 正确：多步骤工具链（web_search + ask_semantic）
```python
# 先获取信息，再用语义理解提取答案
data = web_search("澳大利亚首都是哪个城市")
if data.get("error"):
    # 搜索失败时用 ask_semantic 直接回答
    answer = ask_semantic("澳大利亚首都是哪个城市？只返回选项字母 A/B/C/D")
    set_output(answer)
else:
    # 整理搜索结果，让 ask_semantic 基于此分析
    search_content = "\\n".join([r["title"] + ": " + r["content"] for r in data.get("results", [])])
    answer = ask_semantic(f"根据以下搜索结果，回答问题并只返回选项字母 A/B/C/D：\\n{search_content}\\n问题：澳大利亚首都是哪个城市？A. 悉尼 B. 墨尔本 C. 堪培拉 D. 珀斯")
    set_output(answer)
```

✅ 正确：带思维链 (CoT) 的分析（推荐用于复杂推理）
```python
# 要求 ask_semantic 先分析每个选项，再得出结论
data = web_search("燃烧属于什么类型的化学反应")
search_content = "\\n".join([f"{r['title']}: {r['content']}" for r in data.get("results", [])])
prompt = '''根据以下搜索结果分析问题：
{search_content}

问题：燃烧属于什么类型的化学反应？
A. 分解反应
B. 氧化反应
C. 置换反应
D. 复分解反应

请先分析每个选项与搜索结果的匹配程度，然后得出结论。
最后只返回选项字母：A/B/C/D
'''.format(search_content=search_content)
answer = ask_semantic(prompt)
set_output(answer)
```

【多选题正确/错误示例】

❌ 错误：计算正确但未映射到选项
```python
# 题目：12 × 8 等于多少？A. 86 B. 96 C. 106 D. 116
result = 12 * 8
set_output(result)  # 错误：输出 96，应该输出 "B"
```

✅ 正确：计算后映射到选项字母
```python
# 题目：12 × 8 等于多少？A. 86 B. 96 C. 106 D. 116
result = 12 * 8
# 将计算结果映射到选项
options = {"86": "A", "96": "B", "106": "C", "116": "D"}
set_output(options[str(result)])  # 正确：输出 "B"
```

✅ 正确：使用条件判断映射
```python
# 题目：12 × 8 等于多少？A. 86 B. 96 C. 106 D. 116
result = 12 * 8
if result == 86:
    set_output("A")
elif result == 96:
    set_output("B")  # 正确
elif result == 106:
    set_output("C")
elif result == 116:
    set_output("D")
```

重要：
- 不要输出任何代码块之外的文字
- 只输出 ```python ... ``` 格式的代码"""


def build_coder_prompt(plan: Plan, enable_self_check: bool | None = None, query: str = "") -> str:
    """Build optimized SYSTEM_PROMPT based on plan using modular architecture (Phase 10).

    Args:
        plan: Planner's output with intent, complexity, etc.
        enable_self_check: Override for self-check requirement.
            If None, uses plan.complexity to determine.
        query: Original user query for multiple-choice detection.
    """
    # If skip_planning, use static prompt (backward compatibility)
    if plan.skip_planning:
        return STATIC_CODER_PROMPT

    # Check if logic_steps are provided (Phase 9: Logic Contract)
    if plan.logic_steps:
        return build_logic_contract_prompt(plan, enable_self_check, query)

    # Phase 10: Modular prompt construction
    prompt_parts = [CORE_RULES_PROMPT]

    # Detect multiple choice from query or plan
    is_multiple_choice = detect_multiple_choice(query) if query else False

    # Inject multiple choice rules if detected
    if is_multiple_choice:
        prompt_parts.append(MULTIPLE_CHOICE_RULES)

    # Inject tool usage rules if tools are required
    if plan.required_tools:
        prompt_parts.append(TOOL_USAGE_RULES)

        # Add specific tool documentation
        tool_docs = "\n【工具详情】\n"
        for tool_name in plan.required_tools:
            if tool_name in TOOL_REGISTRY:
                tool_docs += TOOL_REGISTRY[tool_name].usage_doc + "\n"
        prompt_parts.append(tool_docs)

    # Inject self-check rules for medium/complex tasks
    should_check = enable_self_check if enable_self_check is not None else plan.complexity in ("medium", "complex")
    if should_check:
        prompt_parts.append(SELF_CHECK_RULES)

    # Add relevant module hints
    if plan.relevant_modules:
        prompt_parts.append(f"\n推荐标准库：{', '.join(plan.relevant_modules)}")

    # Add coding hints
    if plan.coding_hints:
        hints = "\n编码提示：\n" + "\n".join(f"- {h}" for h in plan.coding_hints)
        prompt_parts.append(hints)

    # Add step breakdown for complex tasks
    if plan.steps and len(plan.steps) > 1:
        steps_str = "\n执行步骤：\n" + "\n".join(f"{s.order}. {s.description}" for s in plan.steps)
        prompt_parts.append(steps_str)

    return "\n".join(prompt_parts)


def build_logic_contract_prompt(plan: Plan, enable_self_check: bool | None = None, query: str = "") -> str:
    """
    Build prompt for Logic Contract mode (Phase 9 + Phase 10 optimization).

    Coder acts as a "compiler" that translates logic_steps into Python code.
    This ensures tool results are properly used, not ignored.
    """
    # Use modular core rules
    base_prompt = """你是代码编译器。将以下逻辑步骤编译为 Python 代码。

【预定义函数】不要重新定义：
- set_output(data): 返回最终结果（必须调用一次）
- web_search(query, num_results=5) -> dict: 网络搜索
  返回: {"answer": "...", "results": [{"title": "...", "content": "..."}], "error": null}
- ask_semantic(query) -> str: 语义处理，直接返回文本

【编译规则】
1. 变量名必须与 output_var 一致
2. {var} 表示变量插值，必须替换为 f-string 格式，如：f"...{var}..."
3. 严禁跳过步骤或忽略变量
4. 所有事实信息必须来源于变量，禁止使用训练数据中的知识"""

    # Inject multiple choice rules if detected (Phase 10)
    is_multiple_choice = detect_multiple_choice(query) if query else False
    if is_multiple_choice:
        base_prompt += """
5. 【多选题输出规则】必须将计算结果/事实与选项进行映射，输出选项字母 (A/B/C/D)，而非原始数值：
   - 错误：result = 0.5 * 2 * 10**2; set_output(result)  # 输出 100.0 ❌
   - 正确：
     result = 0.5 * 2 * 10**2  # 计算得 100
     options = {50: "A", 100: "B", 150: "C", 200: "D"}
     answer = options.get(result, str(result))
     set_output(answer)  # 输出 "B" ✅
   - 对于非数值选项，直接比较：if result == "氧化反应": answer = "B"
"""

    base_prompt += """
6. 【重要】当传递复杂数据（如 web_search 结果）给 ask_semantic 时，必须先格式化：
   - 错误：ask_semantic(f"根据搜索结果 {data}...")  # 直接传 dict，格式混乱
   - 正确：先提取关键信息，如：
     content = "\\n".join([r["title"] + ": " + r["content"][:100] for r in data.get("results", [])])
     ask_semantic(f"根据以下搜索结果：\\n{content}\\n问题：...")
7. 【思维链 CoT】对于需要推理的问题，要求 ask_semantic 先分析再结论：
   - "请先分析每个选项与搜索结果的匹配程度，然后得出结论"
   - "先逐步推理，最后只返回选项字母：A/B/C/D"

【变量插值示例】
- 错误：ask_semantic(query="答案：{answer}")  # 普通字符串，{answer} 不会被替换
- 正确：ask_semantic(query=f"答案：{answer}")  # f-string，{answer} 会被替换为变量值
- 正确：处理 dict 数据：
  ```python
  data = web_search("问题")
  # 格式化搜索结果
  search_text = "\\n".join([f"{r['title']}: {r['content'][:100]}" for r in data.get("results", [])])
  answer = ask_semantic(f"根据以下信息回答问题，只返回选项字母：\\n{search_text}\\n问题：...")
  ```
- 正确：带思维链 (CoT) 的推理：
  ```python
  data = web_search("燃烧属于什么类型的化学反应")
  search_text = "\\n".join([f"{r['title']}: {r['content']}" for r in data.get("results", [])])
  prompt = '''根据以下搜索结果分析问题：
  {search_text}

  问题：燃烧属于什么类型的化学反应？
  A. 分解反应 B. 氧化反应 C. 置换反应 D. 复分解反应

  请先分析每个选项，再得出结论。最后只返回选项字母：A/B/C/D'''.format(search_text=search_text)
  answer = ask_semantic(prompt)
  set_output(answer)
  ```

"""

    # Compile logic_steps to pseudo-code with f-string hints
    base_prompt += "【逻辑契约】\n"
    var_pattern = re.compile(r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}')

    for step in plan.logic_steps:
        # Check if any arg value contains variable interpolation pattern
        def format_arg_value(v):
            if isinstance(v, str) and var_pattern.search(v):
                # Contains {var}, mark as f-string required
                return f"f{repr(v)}  [注意：包含变量插值，必须使用f-string]"
            return repr(v)

        args_str = ", ".join(f"{k}={format_arg_value(v)}" for k, v in step.args.items())
        if step.action == "set_output":
            base_prompt += f"{step.id}: set_output({step.args.get('value', '')})\n"
        elif step.action == "logic":
            base_prompt += f"{step.id}: # {step.description}\n"
            base_prompt += f"    {step.output_var} = ...  # 计算逻辑\n"
        else:
            base_prompt += f"{step.id}: {step.output_var} = {step.action}({args_str})\n"

    base_prompt += "\n【生成的代码】\n"
    base_prompt += "将上述逻辑契约编译为完整的 Python 代码。\n"
    base_prompt += "只输出 ```python ... ``` 格式的代码，不要其他文字。\n"

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

    # Semantic provider and model (optional - defaults to coder)
    semantic_provider: str | None = None  # None = use same as coder
    semantic_model: str | None = None
    semantic_max_depth: int = 3
    semantic_timeout: float = 60.0

    # Phase 11: Intent Recognition
    intent_provider: str | None = None   # None = use same as coder
    intent_model: str | None = None      # Default: grok/grok-4-1-fast-non-reasoning
    intent_timeout: float = 10.0
    intent_enabled: bool = True

    # Feature flags
    web_search_enabled: bool = True
    post_process_enabled: bool = False  # Default to disabled for backward compatibility

    # Phase 6: Complexity-aware coder selection
    complexity_selection_enabled: bool = True
    complexity_model_map: dict[tuple[str, str], "ComplexityModelMapping"] = field(
        default_factory=dict  # Loaded from env in from_env()
    )

    # Retry settings
    max_security_retries: int = 3
    max_execution_retries: int = 3

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        # Coder provider: UPA_CODER_PROVIDER > UPA_PROVIDER (backward compatible)
        provider = os.getenv("UPA_CODER_PROVIDER") or os.getenv("UPA_PROVIDER", "dashscope")

        # Build provider-specific env var names for coder
        url_key = f"{provider.upper()}_URL"
        key_key = f"{provider.upper()}_API_KEY"
        model_key = f"{provider.upper()}_MODEL"

        # Get defaults from presets if provider exists
        preset = PROVIDER_PRESETS.get(provider, {})
        default_url = preset.get("url", "")
        default_model = preset.get("default_model", "")

        # Coder model: UPA_CODER_MODEL > {PROVIDER}_MODEL > default
        coder_model = os.getenv("UPA_CODER_MODEL") or os.getenv(model_key, default_model)

        # Get planner provider/model
        planner_provider = os.getenv("UPA_PLANNER_PROVIDER", None)
        planner_model = os.getenv("UPA_PLANNER_MODEL", None)

        # Get semantic provider/model (support legacy UPA_SUB_AGENT_* env vars)
        semantic_provider = os.getenv("UPA_SEMANTIC_PROVIDER") or os.getenv("UPA_SUB_AGENT_PROVIDER", None)
        semantic_model = os.getenv("UPA_SEMANTIC_MODEL") or os.getenv("UPA_SUB_AGENT_MODEL", None)

        # Load intent provider/model (Phase 11)
        intent_provider = os.getenv("UPA_INTENT_PROVIDER", None)
        intent_model = os.getenv("UPA_INTENT_MODEL", None)

        # Load complexity model map from environment
        complexity_model_map = load_complexity_map_from_env()

        return cls(
            # Coder config
            provider=provider,
            url=os.getenv(url_key, default_url),
            api_key=os.getenv(key_key, ""),
            model=coder_model,
            # Planner config
            planner_provider=planner_provider,
            planner_model=planner_model,
            planner_timeout=float(os.getenv("UPA_PLANNER_TIMEOUT", "5.0")),
            # Semantic config
            semantic_provider=semantic_provider,
            semantic_model=semantic_model,
            semantic_max_depth=int(os.getenv("UPA_SEMANTIC_DEPTH") or os.getenv("UPA_SUB_AGENT_DEPTH", "3")),
            semantic_timeout=float(os.getenv("UPA_SEMANTIC_TIMEOUT") or os.getenv("UPA_SUB_AGENT_TIMEOUT", "60.0")),
            # Phase 11: Intent Recognition
            intent_provider=intent_provider,
            intent_model=intent_model or "grok/grok-4-1-fast-non-reasoning",
            intent_timeout=float(os.getenv("UPA_INTENT_TIMEOUT", "10.0")),
            intent_enabled=os.getenv("UPA_INTENT_ENABLED", "true").lower() == "true",
            # Feature flags
            web_search_enabled=os.getenv("UPA_WEB_SEARCH", "true").lower() == "true",
            post_process_enabled=os.getenv("UPA_POST_PROCESS", "false").lower() == "true",
            # Phase 6
            complexity_selection_enabled=os.getenv("UPA_COMPLEXITY_SELECTION", "true").lower() == "true",
            complexity_model_map=complexity_model_map,
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
            "  Semantic:",
            f"    Provider:        {self.semantic_provider or '(same as coder)'}",
            f"    Model:           {self.semantic_model or '(same as coder)'}",
            f"    Max Depth:       {self.semantic_max_depth}",
            f"    Timeout:         {self.semantic_timeout}s",
            "",
            "  Intent Recognition (Phase 11):",
            f"    Enabled:         {self.intent_enabled}",
            f"    Provider:        {self.intent_provider or '(same as coder)'}",
            f"    Model:           {self.intent_model or 'grok/grok-4-1-fast-non-reasoning'}",
            f"    Timeout:         {self.intent_timeout}s",
            "",
            "  Features:",
            f"    Web Search:           {self.web_search_enabled}",
            f"    Post-Process:         {self.post_process_enabled}",
            f"    Complexity Selection: {self.complexity_selection_enabled}",
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
# Semantic Context (for recursive calls)
# =============================================================================

class SemanticContext:
    """Context for tracking semantic recursion depth."""
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
        """Check if semantic calls are enabled."""
        return cls._enabled

    @classmethod
    def disable(cls):
        """Disable semantic calls (for security)."""
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
# System Prompt: Always-Code (alias for STATIC_CODER_PROMPT)
# =============================================================================

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




def get_planner_provider_config() -> ProviderConfig:
    """Get the provider configuration for planner."""
    config = get_config()

    # If planner has its own provider
    if config.planner_provider:
        return get_provider(config.planner_provider)

    # Otherwise use coder's provider
    return get_provider(config.provider)


def get_intent_provider_config() -> ProviderConfig:
    """
    Get the provider configuration for intent recognition - Phase 11 新增.

    Priority:
      1. UPA_INTENT_PROVIDER (if set)
      2. Fall back to coder provider
    """
    config = get_config()

    # If intent has its own provider
    if config.intent_provider:
        return get_provider(config.intent_provider)

    # Otherwise use coder's provider
    return get_provider(config.provider)


# =============================================================================
# Phase 6: Complexity-Aware Coder Model Selection
# =============================================================================

def select_coder_model(
    plan: Plan,
    config: Config,
    cli_model: str | None = None,
    cli_provider: str | None = None,
    complexity_selection_disabled: bool = False,
) -> tuple[ProviderConfig, str, bool]:
    """
    Select Coder model based on plan complexity.

    Priority:
      1. CLI --model (user explicit override)
      2. Complexity mapping (with cross-provider support)
      3. Default provider model

    Args:
        plan: Planner's output with intent and complexity
        config: Current configuration
        cli_model: Model specified via --model CLI flag
        cli_provider: Provider specified via --provider CLI flag
        complexity_selection_disabled: If True, skip complexity-based selection

    Returns:
        (provider_config, model_name, enable_self_check)
    """
    # CLI override takes highest priority
    if cli_model:
        provider = get_provider(cli_provider or config.provider)
        self_check = plan.complexity in ("medium", "complex")
        print(f"Coder: CLI override model={cli_model}, self_check={self_check}", file=sys.stderr)
        return provider, cli_model, self_check

    # Complexity-based selection
    if config.complexity_selection_enabled and not complexity_selection_disabled:
        # Use config's map (loaded from env) instead of global DEFAULT
        model_map = config.complexity_model_map or DEFAULT_COMPLEXITY_MODEL_MAP

        # Try exact match, then wildcard
        key = (plan.intent, plan.complexity)
        if key not in model_map:
            key = ("*", plan.complexity)

        if key in model_map:
            mapping = model_map[key]

            # Handle cross-provider selection
            if mapping.provider:
                target_provider = get_provider(mapping.provider)
                # Check if API key is configured
                if target_provider.api_key:
                    print(f"Coder: complexity={plan.complexity} → model={mapping.model}, "
                          f"provider={mapping.provider}, self_check={mapping.enable_self_check}",
                          file=sys.stderr)
                    return target_provider, mapping.model, mapping.enable_self_check
                else:
                    # Fallback to default provider with mapped model
                    print(f"  Warning: Provider '{mapping.provider}' not configured, "
                          f"using default provider with model '{mapping.model}'", file=sys.stderr)
                    provider = get_provider(config.provider)
                    return provider, mapping.model, mapping.enable_self_check

            # Same provider, different model
            provider = get_provider(config.provider)
            print(f"Coder: complexity={plan.complexity} → model={mapping.model}, "
                  f"self_check={mapping.enable_self_check}", file=sys.stderr)
            return provider, mapping.model, mapping.enable_self_check

    # Fallback
    provider = get_provider(cli_provider or config.provider)
    self_check = plan.complexity in ("medium", "complex")
    print(f"Coder: fallback model={provider.model}, self_check={self_check}", file=sys.stderr)
    return provider, provider.model, self_check


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


def ask_semantic(query: str, client: OpenAI | None = None, model: str = None) -> str:
    """
    Semantic processing function - returns text directly without code generation.
    This function is injected into the sandbox for LLM-generated code to call.

    Args:
        query: The semantic query to process (translation, summary, sentiment, etc.)
        client: OpenAI client (will be created if not provided)
        model: Model name to use (defaults to semantic model from config)

    Returns:
        The direct text response from the LLM

    Example usage in sandbox:
        translation = ask_semantic("Translate to Chinese: Hello")
        summary = ask_semantic("Summarize this text: ...")
    """
    # Check if semantic calls are enabled
    if not SemanticContext.is_enabled():
        return "[Error: Semantic calls disabled]"

    # Get config for semantic settings
    config = get_config()

    # Check recursion depth
    current_depth = SemanticContext.depth()
    if current_depth >= config.semantic_max_depth:
        return f"[Error: Maximum semantic depth ({config.semantic_max_depth}) reached]"

    # Increment depth for this call
    SemanticContext.increment()
    depth = SemanticContext.depth()

    # Output semantic call info to stderr for tracking
    print(f"Semantic Call (L{depth}): {query[:50]}...", file=sys.stderr)

    # Get semantic model if not specified
    if model is None:
        # Use semantic's provider config (may be different from coder)
        semantic_config = get_semantic_provider_config()
        model = get_semantic_model(semantic_config.model)

    try:
        # Create client if not provided
        if client is None:
            # Use semantic's provider config (may be different from coder)
            client = create_client(get_semantic_provider_config())

        # Semantic system prompt - direct response, no code generation
        semantic_prompt = """你是一个语义处理助手。直接回答用户的问题，不要生成代码。

适用于以下任务：
- 翻译：输出翻译结果
- 总结：输出总结内容
- 情感分析：输出分析结果
- 文本理解：输出理解结果

直接回答，简洁明了。"""

        # Call LLM with timeout
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError("Semantic call timed out")

        # Set timeout (works on Unix systems)
        if hasattr(signal, 'SIGALRM'):
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(config.semantic_timeout))

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": semantic_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.7,
            )
        finally:
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)  # Cancel alarm

        # Direct text response
        result = response.choices[0].message.content or ""
        if not result:
            return "[Error: LLM returned empty response]"
        return result

    except TimeoutError:
        return f"[Error: Semantic call timed out after {config.semantic_timeout}s]"
    except Exception as e:
        return f"[Error: Semantic call failed: {str(e)}]"
    finally:
        # Always decrement depth when done
        SemanticContext.decrement()


def get_semantic_provider_config() -> ProviderConfig:
    """Get the provider configuration for semantic calls."""
    config = get_config()
    # If semantic has independent provider, use it
    if config.semantic_provider:
        return get_provider(config.semantic_provider)
    # Otherwise use coder's provider
    return get_provider(config.provider)


def get_semantic_model(model: str) -> str:
    """Get the model name for semantic calls."""
    config = get_config()
    if config.semantic_model:
        return config.semantic_model
    return model


# Web Search configuration
WEB_SEARCH_TIMEOUT = 30    # Timeout for web search calls in seconds
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
    # Check if web search is enabled (from config)
    config = get_config()
    if not config.web_search_enabled:
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
    max_retries: int = 3,
    base_delay: float = 1.0,
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
        max_retries: Maximum retry attempts for rate limit errors (default 3)
        base_delay: Base delay in seconds for exponential backoff (default 1.0)

    Returns:
        (response_content, updated_conversation_history)
    """
    import random
    from httpx import ProxyError
    from openai import APIConnectionError, APIStatusError

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

    # Retry loop with exponential backoff (Phase 10.5: Rate limit handling)
    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
            )
            return response.choices[0].message.content or "", messages

        except (APIConnectionError, ProxyError, APIStatusError) as e:
            last_exception = e
            status_code = getattr(e, 'status_code', None)

            # Check if this is a rate limit or service unavailable error
            is_retryable = (
                status_code in (429, 503, 502, 504) or
                "rate limit" in str(e).lower() or
                "throttl" in str(e).lower() or
                "service unavailable" in str(e).lower() or
                "connection error" in str(e).lower()
            )

            if is_retryable and attempt < max_retries:
                # Exponential backoff with jitter
                delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                print(f"API rate limit/connection error, retrying in {delay:.1f}s... ({attempt+1}/{max_retries})", file=sys.stderr)
                time.sleep(delay)
            else:
                print(f"API error after {attempt+1} attempts: {type(e).__name__}: {str(e)[:100]}", file=sys.stderr)
                raise

        except Exception as e:
            # Non-retryable error, re-raise immediately
            print(f"Unexpected error during API call: {type(e).__name__}: {e}", file=sys.stderr)
            raise

    # Should not reach here, but just in case
    print(f"Max retries exceeded, last error: {last_exception}", file=sys.stderr)
    raise last_exception


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


# =============================================================================
# Phase 8: Structured Output (set_output API)
# =============================================================================

class OutputCollector:
    """
    Collect structured output from sandbox execution.

    Replaces stdout interception with explicit set_output() API.
    This preserves data types and enables thread-safe concurrent execution.
    """

    def __init__(self):
        self._result = None
        self._has_result = False
        self._call_count = 0

    def set_output(self, data) -> None:
        """
        Set the final output result (preserves data type).

        Can only be called once. Raises RuntimeError if called multiple times.

        Args:
            data: Any Python data structure (dict, list, number, string, etc.)
        """
        self._call_count += 1
        if self._call_count > 1:
            raise RuntimeError("set_output() can only be called once per execution")
        self._result = data
        self._has_result = True

    def get_output(self):
        """
        Get the current output result.

        Useful for chained processing within the sandbox code.

        Returns:
            The data passed to set_output(), or None if not yet called.
        """
        return self._result

    def has_output(self) -> bool:
        """Check if set_output() has been called."""
        return self._has_result


def execute_code(code: str, client: OpenAI | None = None, provider: ProviderConfig | None = None) -> tuple[str, str]:
    """
    Execute Python code in a sandbox-like environment.
    Returns (stdout, error_message).

    Note: For structured output, use execute_code_with_output() instead.
    """
    result = execute_code_with_output(code, client, provider)
    return result.stdout, result.error


class ExecutionResult:
    """Result of code execution with structured output support."""

    def __init__(self):
        self.output: any = None  # Structured output from set_output()
        self.stdout: str = ""     # Captured stdout
        self.stderr: str = ""     # Captured stderr
        self.error: str = ""      # Error message if execution failed
        self.has_output: bool = False  # Whether set_output() was called


def execute_code_with_output(
    code: str,
    client: OpenAI | None = None,
    provider: ProviderConfig | None = None
) -> ExecutionResult:
    """
    Execute Python code with structured output support.

    Returns ExecutionResult with:
    - output: Data from set_output() (preserves type)
    - stdout: Captured stdout (debug logs)
    - stderr: Captured stderr
    - error: Error message if execution failed
    - has_output: Whether set_output() was called
    """
    result = ExecutionResult()

    # Capture stdout and stderr
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()

    # Get provider for model name (use passed provider or default)
    if provider is None:
        provider = get_provider()

    # Create OutputCollector for structured output
    collector = OutputCollector()

    # Create a partial function for ask_semantic with the client and model
    def make_ask_semantic(llm_client: OpenAI, model_name: str):
        def ask_semantic_wrapper(query: str) -> str:
            return ask_semantic(query, client=llm_client, model=model_name)
        return ask_semantic_wrapper

    # Create safe_semantic decorator (syntax sugar for ask_semantic)
    def create_safe_semantic(ask_sem_fn):
        def safe_semantic(query: str):
            """Decorator factory for semantic calls (syntax sugar)."""
            def decorator(func):
                def wrapper(*args, **kwargs):
                    sem_result = ask_sem_fn(query)
                    return func(sem_result, *args, **kwargs)
                return wrapper
            return decorator
        return safe_semantic

    # Get model name for semantic calls
    if client:
        ask_semantic_fn = make_ask_semantic(client, provider.model)
        safe_semantic_decorator = create_safe_semantic(ask_semantic_fn)
    else:
        ask_semantic_fn = lambda q: "[Error: No LLM client]"
        safe_semantic_decorator = lambda q: lambda f: f

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
        # Inject structured output API
        "set_output": collector.set_output,
        "get_output": collector.get_output,
        # Inject ask_semantic and safe_semantic
        "ask_semantic": ask_semantic_fn,
        "safe_semantic": safe_semantic_decorator,
        # Inject web_search for fact-checking
        "web_search": web_search,
    }

    try:
        exec(code, sandbox_globals)
        result.stdout = sys.stdout.getvalue()
        result.stderr = sys.stderr.getvalue()

        # Check for structured output (strict mode)
        if collector.has_output():
            result.output = collector.get_output()
            result.has_output = True
        else:
            # Strict mode: set_output() must be called
            result.error = "Error: set_output() was never called. You must call set_output(data) once to return the result."

    except Exception:
        result.error = traceback.format_exc()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    return result


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
    parser.add_argument(
        "--no-complexity-selection",
        action="store_true",
        help="Disable complexity-based model selection",
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

    # Reset semantic context for fresh execution
    SemanticContext.reset()

    # Get configuration
    config = get_config()

    # Initialize timer
    timer = Timer()

    # ==========================================================================
    # Phase 11: Intent Recognition (Independent Service)
    # ==========================================================================
    # Run intent classification as a前置 step to decide whether to use Planner
    intent: Intent | None = None
    plan: Plan | None = None
    system_prompt = SYSTEM_PROMPT  # Default to static prompt


    # Get planner provider early for later validation
    planner_provider = get_planner_provider_config()
    if config.intent_enabled:
        timer.start("Intent Recognition")
        intent_provider_cfg = get_intent_provider_config()
        intent_client = create_client(intent_provider_cfg)
        intent_model = config.intent_model or intent_provider_cfg.model

        # Validate intent provider API key
        if not intent_provider_cfg.api_key:
            print(f"Warning: Intent Recognition API key not set, using fallback", file=sys.stderr)
            intent = None
        else:
            intent = recognize_intent(
                intent_client,
                args.query,
                intent_model,
                timeout=config.intent_timeout,
            )
            timer.stop()

            # 低置信度回退：confidence < 0.6 时强制运行 Planner
            if intent and intent.confidence < 0.6:
                print(f"Intent: Low confidence ({intent.confidence:.2f}), running Planner for safety", file=sys.stderr)
                intent.requires_planning = True

            print(f"Intent: {intent.category} ({intent.complexity}, confidence={intent.confidence:.2f})", file=sys.stderr)

    # ==========================================================================
    # Phase 0: Planner Analysis (Dynamic Prompt Construction)
    # ==========================================================================
    # Route based on intent classification
    if intent and not intent.requires_planning:
        # Simple task: skip Planner, create plan from intent
        plan = create_plan_from_intent(intent)
        print("Skipping Planner (intent classification)", file=sys.stderr)
    elif intent and intent.requires_planning:
        # Complex task: run Planner
        timer.start("Planner Analysis")
        planner_model = config.planner_model or planner_provider.model
        planner_client = create_client(planner_provider)
        plan = run_planner(planner_client, args.query, planner_model, timeout=config.planner_timeout)
        timer.stop()
    else:
        # Intent disabled or failed: fall back to original logic
        if is_trivial_query(args.query):
            print("Planner: Trivial query detected (fallback)", file=sys.stderr)
            plan = create_default_plan(intent="simple_chat", skip_planning=True)
        else:
            timer.start("Planner Analysis")
            planner_model = config.planner_model or planner_provider.model
            planner_client = create_client(planner_provider)
            plan = run_planner(planner_client, args.query, planner_model, timeout=config.planner_timeout)
            timer.stop()


    # ==========================================================================
    # Phase 6: Complexity-Aware Coder Model Selection
    # ==========================================================================
    # Select Coder model based on plan complexity (AFTER planner runs)
    coder_provider, coder_model, enable_self_check = select_coder_model(
        plan=plan or create_default_plan(skip_planning=True),
        config=config,
        cli_model=args.model,
        cli_provider=args.provider,
        complexity_selection_disabled=args.no_complexity_selection,
    )

    # Validate coder API key
    if not coder_provider.api_key:
        print(f"Error: API key not set for provider '{coder_provider.name}'", file=sys.stderr)
        sys.exit(1)

    # Create coder client with selected provider
    client = create_client(coder_provider)

    # Show provider info
    print(f"Using: {coder_provider.name} ({coder_model})", file=sys.stderr)

    # Build dynamic system prompt based on plan (Phase 10: pass query for MC detection)
    if plan and not plan.skip_planning:
        system_prompt = build_coder_prompt(plan, enable_self_check=enable_self_check, query=args.query)

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

    for attempt in range(config.max_security_retries):
        # Generate code (with error feedback on retry)
        llm_timer.start("LLM Generate")
        response, conversation_history = generate_code(
            client,
            args.query,
            coder_model,
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
            if attempt < config.max_security_retries - 1:
                error_feedback = "错误：未找到Python代码块。请确保输出格式为 ```python ... ```"
                print(f"  No code block found, retrying... ({attempt + 1}/{config.max_security_retries})", file=sys.stderr)
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
            if attempt < config.max_security_retries - 1:
                # Build error feedback for retry
                error_feedback = "安全违规：\n" + "\n".join(f"  - {v}" for v in violations)
                security_retry_data["retry_count"] = attempt + 1
                security_retry_data["violations"] = violations
                print(f"  Security violations detected, retrying... ({attempt + 1}/{config.max_security_retries})", file=sys.stderr)
                continue
            else:
                print(f"\n经过 {config.max_security_retries} 次尝试，仍无法生成符合安全要求的代码。", file=sys.stderr)
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
    exec_result = None
    execution_error = None

    # Track self-healing statistics
    self_heal_attempts = 0
    self_heal_errors = []
    final_code = code

    for exec_attempt in range(config.max_execution_retries):
        timer.start("Code Execute")
        exec_result = execute_code_with_output(code, client=client, provider=coder_provider)
        timer.stop()

        if not exec_result.error:
            break  # Execution successful

        # Execution failed, attempt self-healing
        execution_error = exec_result.error
        if exec_attempt < config.max_execution_retries - 1:
            self_heal_attempts += 1
            # Extract first line of error for summary
            error_summary = exec_result.error.split('\n')[0][:100] if exec_result.error else "Unknown error"
            self_heal_errors.append(error_summary)

            print(f"\n  Execution error, attempting self-heal ({exec_attempt + 1}/{config.max_execution_retries})...", file=sys.stderr)

            # Build error feedback for LLM to fix
            error_feedback = f"""代码执行时发生错误：
{exec_result.error}

请修复上述错误，确保：
1. 正确处理所有异常情况（如除零、索引越界、变量未定义等）
2. 变量在使用前已定义
3. 必须调用 set_output(data) 一次返回结果
4. 语法和逻辑正确

只输出修复后的代码，不要解释。"""

            # Generate new code with error feedback
            llm_timer.start("LLM Generate (Self-Heal)")
            response, conversation_history = generate_code(
                client,
                args.query,
                coder_model,
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
    if execution_error and exec_result and exec_result.error:
        print(f"\n经过 {config.max_execution_retries} 次自愈尝试，仍无法执行成功:", file=sys.stderr)
        print(exec_result.error, file=sys.stderr)
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

    # Get output from structured result
    output = exec_result.output if exec_result and exec_result.has_output else None
    stdout = exec_result.stdout if exec_result else ""

    # Format output for display
    if output is not None and output != "":
        # Structured output - format appropriately
        if isinstance(output, (dict, list)):
            import json as json_module
            display_output = json_module.dumps(output, ensure_ascii=False, indent=2)
        else:
            display_output = str(output)
    elif stdout.strip():
        # Fallback to stdout if no structured output or output is empty
        display_output = stdout
    else:
        display_output = output if output is not None else ""

    if should_post_process and display_output.strip():
        print("Formatting output...", file=sys.stderr)
        timer.start("Post-Process")
        display_output = post_process_output(
            client,
            args.query,
            display_output,
            coder_model,
            format_hint=plan.output_format_hint if plan else "",
        )
        timer.stop()

    # Print result (ensure newline if empty to avoid terminal showing nothing)
    if not display_output:
        print("(No output)", file=sys.stderr)
        if exec_result and exec_result.has_output and not exec_result.output:
            print("  Note: set_output() was called with empty value", file=sys.stderr)
        elif exec_result and not exec_result.has_output:
            print("  Note: set_output() was never called", file=sys.stderr)
    else:
        print(display_output)  # Added newline for clean terminal display

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
            "structured_output": output,  # Structured output from set_output()
            "output_type": type(output).__name__ if output is not None else None,
            "self_heal_attempts": self_heal_attempts,
            "self_heal_errors": self_heal_errors,
            "security_violations": security_retry_data.get("violations", []),
            "security_retry_count": security_retry_data.get("retry_count", 0),
            "timing_ms": timer.to_dict(),
            "planner": {
                "enabled": True,
                "intent": plan.intent if plan else None,
                "complexity": plan.complexity if plan else None,
                "required_tools": plan.required_tools if plan else [],
                "relevant_modules": plan.relevant_modules if plan else [],
                "steps_count": len(plan.steps) if plan else 0,
                "confidence": plan.confidence if plan else None,
                "skip_planning": plan.skip_planning if plan else True,
                "timing_ms": timer.to_dict().get("Planner Analysis", 0),
                # Phase 9: Logic Contract
                "logic_steps": [
                    {
                        "id": step.id,
                        "action": step.action,
                        "args": step.args,
                        "input_vars": step.input_vars,
                        "output_var": step.output_var,
                        "description": step.description,
                    }
                    for step in plan.logic_steps
                ] if plan and plan.logic_steps else [],
                "logic_steps_count": len(plan.logic_steps) if plan and plan.logic_steps else 0,
                "uses_logic_contract": bool(plan and plan.logic_steps),
            } if plan else None,
        }
        # Output as a compact JSON line to stderr
        print(f"__UPA_JSON__{json_module.dumps(report)}", file=sys.stderr)


if __name__ == "__main__":
    main()
