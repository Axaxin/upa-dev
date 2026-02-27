"""
Planner Validation Test Suite

This suite validates Planner (Phase 5) decisions:
- Intent classification accuracy
- Tool selection correctness
- skip_planning decision appropriateness

Each test case includes expected Planner behavior via expect_planner_* fields.
"""

from benchmarks.suites.base import (
    TestCase, TestSuite, Complexity, register_suite
)


# ============================================================================
# Intent Classification Tests
# ============================================================================

INTENT_TESTS = [
    # Simple chat - should skip planning
    TestCase(
        name="Intent-SimpleChat-Greeting",
        query="你好",
        complexity=Complexity.SIMPLE,
        description="Simple greeting should skip planning",
        expect_planner_intent="simple_chat",
        expect_planner_skip=True,
    ),
    TestCase(
        name="Intent-SimpleChat-Thanks",
        query="谢谢",
        complexity=Complexity.SIMPLE,
        description="Thank you should skip planning",
        expect_planner_intent="simple_chat",
        expect_planner_skip=True,
    ),

    # Computation - should detect as computation
    TestCase(
        name="Intent-Computation-Add",
        query="计算 123 + 456",
        complexity=Complexity.SIMPLE,
        description="Math computation",
        expect_planner_intent="computation",
    ),
    TestCase(
        name="Intent-Computation-Multiply",
        query="计算 25 乘以 4",
        complexity=Complexity.SIMPLE,
        description="Math computation",
        expect_planner_intent="computation",
    ),

    # Semantic - should use ask_semantic
    TestCase(
        name="Intent-Semantic-Translate",
        query="把 Hello 翻译成中文",
        complexity=Complexity.SIMPLE,
        description="Translation needs semantic",
        expect_planner_intent="semantic",
        expect_planner_tools=["ask_semantic"],
    ),
    TestCase(
        name="Intent-Semantic-Summarize",
        query="总结这段文字的主旨：人工智能正在改变世界",
        complexity=Complexity.SIMPLE,
        description="Summarization needs semantic",
        expect_planner_intent="semantic",
        expect_planner_tools=["ask_semantic"],
    ),

    # Hybrid - should use ask_semantic
    TestCase(
        name="Intent-Hybrid-TranslateCount",
        query="把 Hello 翻译成中文，然后计算中文字符数量",
        complexity=Complexity.MEDIUM,
        description="Translation + computation",
        expect_planner_intent="hybrid",
        expect_planner_tools=["ask_semantic"],
    ),

    # Multi-step - should use web_search
    TestCase(
        name="Intent-MultiStep-Weather",
        query="先搜索北京天气，然后判断是否适合出门",
        complexity=Complexity.COMPLEX,
        description="Search + analysis",
        expect_planner_intent="multi_step",
        expect_planner_tools=["web_search"],
    ),
]


# ============================================================================
# Tool Selection Tests
# ============================================================================

TOOL_TESTS = [
    # Translation needs ask_semantic
    TestCase(
        name="Tool-Translation",
        query="把 'Good morning' 翻译成法语",
        complexity=Complexity.SIMPLE,
        description="Translation needs ask_semantic",
        expect_planner_tools=["ask_semantic"],
    ),

    # Search needs web_search
    TestCase(
        name="Tool-Search-Weather",
        query="今天北京天气怎么样？",
        complexity=Complexity.SIMPLE,
        description="Weather query needs web_search",
        expect_planner_tools=["web_search"],
    ),
    TestCase(
        name="Tool-Search-Fact",
        query="谁发明了电话？",
        complexity=Complexity.SIMPLE,
        description="Fact query needs web_search",
        expect_planner_tools=["web_search"],
    ),

    # Sentiment analysis needs semantic
    TestCase(
        name="Tool-Analysis-Sentiment",
        query="分析 '这部电影太棒了' 的情感",
        complexity=Complexity.MEDIUM,
        description="Sentiment analysis needs ask_semantic",
        expect_planner_tools=["ask_semantic"],
    ),

    # Math-only doesn't need tools
    TestCase(
        name="Tool-None-Math",
        query="计算 100!",
        complexity=Complexity.MEDIUM,
        description="Pure math needs no tools",
        expect_planner_tools=[],
    ),
]


# ============================================================================
# Skip Planning Tests
# ============================================================================

SKIP_PLANNING_TESTS = [
    # Should skip planning
    TestCase(
        name="Skip-Greeting",
        query="嗨",
        complexity=Complexity.SIMPLE,
        description="Greeting should skip planning",
        expect_planner_skip=True,
    ),
    TestCase(
        name="Skip-PureMath",
        query="2^10",
        complexity=Complexity.SIMPLE,
        description="Pure math expression should skip planning",
        expect_planner_skip=True,
    ),
    TestCase(
        name="Skip-Thanks",
        query="thanks",
        complexity=Complexity.SIMPLE,
        description="Thanks should skip planning",
        expect_planner_skip=True,
    ),

    # Should NOT skip planning
    TestCase(
        name="NoSkip-Translate",
        query="翻译 Hello",
        complexity=Complexity.SIMPLE,
        description="Translation should not skip planning",
        expect_planner_skip=False,
    ),
    TestCase(
        name="NoSkip-Search",
        query="搜索北京天气",
        complexity=Complexity.SIMPLE,
        description="Search should not skip planning",
        expect_planner_skip=False,
    ),
]


# ============================================================================
# Combine all tests
# ============================================================================

PLANNER_TEST_CASES = (
    INTENT_TESTS +
    TOOL_TESTS +
    SKIP_PLANNING_TESTS
)


# ============================================================================
# Register the Planner Validation Suite
# ============================================================================

@register_suite
def _planner_suite() -> TestSuite:
    """Planner Validation Test Suite."""
    return TestSuite(
        name="planner",
        description="Validate Planner (Phase 5) decision accuracy",
        version="1.0.0",
        cases=PLANNER_TEST_CASES,
    )
