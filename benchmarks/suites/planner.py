"""
Planner Validation Test Suite

This suite validates Planner (Phase 5) decisions:
- Intent classification accuracy (Phase 13 simplified)
- Tool selection correctness
- skip_planning decision appropriateness

Phase 13: Intent recognition simplified to only identify "obviously no planner needed" cases:
- simple_chat: greetings, thanks, small talk
- trivial_computation: simple math expressions like "2+2", "100/5"
- need_planner: everything else (default)
"""

from benchmarks.suites.base import (
    TestCase, TestSuite, Complexity, register_suite
)


# ============================================================================
# Intent Classification Tests (Phase 13 Simplified)
# ============================================================================

INTENT_TESTS = [
    # Simple chat - should skip planning
    # Phase 13: Added expect_planner_intent to validate intent recognition
    # even when planner is skipped
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

    # Trivial computation - should skip planning
    TestCase(
        name="Intent-TrivialComputation-Add",
        query="2+2",
        complexity=Complexity.SIMPLE,
        description="Simple math expression should skip planning",
        expect_planner_intent="trivial_computation",
        expect_planner_skip=True,
    ),
    TestCase(
        name="Intent-TrivialComputation-Multiply",
        query="100/5",
        complexity=Complexity.SIMPLE,
        description="Simple math expression should skip planning",
        expect_planner_intent="trivial_computation",
        expect_planner_skip=True,
    ),

    # Everything else should need planner
    # Translation - should use planner
    TestCase(
        name="Intent-Semantic-Translate",
        query="把 Hello 翻译成中文",
        complexity=Complexity.SIMPLE,
        description="Translation needs planner",
        expect_planner_intent="semantic",
        expect_planner_tools=["ask_semantic"],
    ),
    TestCase(
        name="Intent-Semantic-Summarize",
        query="总结这段文字的主旨：人工智能正在改变世界",
        complexity=Complexity.SIMPLE,
        description="Summarization needs planner",
        expect_planner_intent="semantic",
        expect_planner_tools=["ask_semantic"],
    ),

    # Hybrid - should use planner
    TestCase(
        name="Intent-Hybrid-TranslateCount",
        query="把 Hello 翻译成中文，然后计算中文字符数量",
        complexity=Complexity.MEDIUM,
        description="Translation + computation needs planner",
        expect_planner_intent="hybrid",
        expect_planner_tools=["ask_semantic"],
    ),

    # Multi-step - should use planner
    TestCase(
        name="Intent-MultiStep-Weather",
        query="先搜索北京天气，然后判断是否适合出门",
        complexity=Complexity.COMPLEX,
        description="Search + analysis needs planner",
        expect_planner_intent="multi_step",
        expect_planner_tools=["web_search"],
    ),

    # Knowledge query - should use planner
    TestCase(
        name="Intent-Knowledge-Question",
        query="谁发明了电话？",
        complexity=Complexity.SIMPLE,
        description="Knowledge query needs planner",
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
        expect_planner_intent="simple_chat",
        expect_planner_skip=True,
    ),
    TestCase(
        name="Skip-PureMath",
        query="2^10",
        complexity=Complexity.SIMPLE,
        description="Pure math expression should skip planning",
        expect_planner_intent="trivial_computation",
        expect_planner_skip=True,
    ),
    TestCase(
        name="Skip-Thanks",
        query="thanks",
        complexity=Complexity.SIMPLE,
        description="Thanks should skip planning",
        expect_planner_intent="simple_chat",
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
# Logic Steps / Logic Contract Tests (Phase 9)
# ============================================================================

LOGIC_STEPS_TESTS = [
    # Web search + semantic should generate logic_steps with variable binding
    TestCase(
        name="LogicSteps-SearchAndAnalyze",
        query="支架式教学的概念最早由谁提出？",
        complexity=Complexity.MEDIUM,
        description="Search + analysis should use logic_steps with variable binding",
        expect_planner_intent="semantic",
        expect_planner_tools=["web_search", "ask_semantic"],
        expect_logic_steps=True,
        expect_uses_logic_contract=True,
    ),

    # Multi-step task should decompose into logic_steps
    TestCase(
        name="LogicSteps-MultiStep",
        query="搜索Python最新版本特性，然后总结主要改进",
        complexity=Complexity.COMPLEX,
        description="Multi-step task should generate logic_steps",
        expect_planner_intent="multi_step",
        expect_planner_tools=["web_search", "ask_semantic"],
        expect_logic_steps=True,
        expect_uses_logic_contract=True,
    ),

    # Pure computation may skip logic_steps
    TestCase(
        name="LogicSteps-PureComputation",
        query="计算100的阶乘",
        complexity=Complexity.SIMPLE,
        description="Pure computation may not need logic_steps",
        expect_planner_intent="trivial_computation",
        expect_planner_skip=True,  # Pure computation should skip planner
    ),

    # Simple translation should use ask_semantic in logic_steps
    TestCase(
        name="LogicSteps-Translation",
        query="将'Hello World'翻译成中文",
        complexity=Complexity.SIMPLE,
        description="Translation should have ask_semantic step",
        expect_planner_intent="semantic",
        expect_planner_tools=["ask_semantic"],
        expect_logic_steps=True,
    ),
]


# ============================================================================
# Combine all tests
# ============================================================================

PLANNER_TEST_CASES = (
    INTENT_TESTS +
    TOOL_TESTS +
    SKIP_PLANNING_TESTS +
    LOGIC_STEPS_TESTS  # Add Phase 9 tests
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
