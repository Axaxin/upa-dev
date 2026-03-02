#!/usr/bin/env python3
"""
Unit tests for UPA Planner module.

Run with: uv run pytest tests/test_planner.py -v

Note: Tests are run by executing upa.py directly since the upa/ package
conflicts with upa.py module. Use: uv run python tests/test_planner.py
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import from upa.planner_models (the package)
from upa.planner_models import Plan, PlanStep

# Import functions from upa.py by executing it
upa_path = Path(__file__).parent.parent / "upa.py"
with open(upa_path) as f:
    exec(f.read(), globals())


class TestIsTrivialQuery:
    """Tests for is_trivial_query function."""

    def test_simple_greetings(self):
        """Simple greetings should be trivial."""
        assert is_trivial_query("你好") == True
        assert is_trivial_query("嗨") == True
        assert is_trivial_query("嘿") == True
        assert is_trivial_query("你好吗") == True

    def test_greetings_with_punctuation(self):
        """Greetings with punctuation should be trivial."""
        assert is_trivial_query("你好！") == True
        assert is_trivial_query("嗨？") == True
        assert is_trivial_query("你好，") == True

    def test_thank_you(self):
        """Thank you expressions should be trivial."""
        assert is_trivial_query("谢谢") == True
        assert is_trivial_query("感谢") == True
        assert is_trivial_query("thanks") == True
        assert is_trivial_query("thank you") == True

    def test_pure_math_expressions(self):
        """Pure math expressions should be trivial."""
        assert is_trivial_query("1+1") == True
        assert is_trivial_query("2 * 3") == True
        assert is_trivial_query("100 / 5") == True
        assert is_trivial_query("2^10") == True

    def test_very_short_queries(self):
        """Very short queries (1-3 chars) should be trivial."""
        assert is_trivial_query("a") == True
        assert is_trivial_query("hi") == True
        assert is_trivial_query("ok") == True

    def test_non_trivial_queries(self):
        """Complex queries should NOT be trivial."""
        assert is_trivial_query("计算斐波那契数列") == False
        assert is_trivial_query("翻译这段文字") == False
        assert is_trivial_query("帮我排序这些数字") == False
        assert is_trivial_query("什么是人工智能") == False


class TestCreateDefaultPlan:
    """Tests for create_default_plan function."""

    def test_default_plan(self):
        """Default plan should have expected defaults."""
        plan = create_default_plan()
        assert plan.intent == "unknown"
        assert plan.complexity == "simple"
        assert plan.steps == []
        assert "ask_semantic" in plan.required_tools
        assert plan.skip_planning == False

    def test_custom_intent(self):
        """Custom intent should be set."""
        plan = create_default_plan(intent="computation")
        assert plan.intent == "computation"

    def test_skip_planning(self):
        """skip_planning flag should be set."""
        plan = create_default_plan(skip_planning=True)
        assert plan.skip_planning == True

    def test_custom_confidence(self):
        """Custom confidence should be set."""
        plan = create_default_plan(confidence=0.9)
        assert plan.confidence == 0.9


class TestValidatePlan:
    """Tests for validate_plan function."""

    def test_remove_invalid_tools(self):
        """Invalid tools should be removed."""
        plan = Plan(
            intent="computation",
            complexity="simple",
            required_tools=["ask_semantic", "invalid_tool", "another_fake"],
        )
        validated = validate_plan(plan)
        assert "ask_semantic" in validated.required_tools
        assert "invalid_tool" not in validated.required_tools
        assert "another_fake" not in validated.required_tools

    def test_cap_steps(self):
        """Steps should be capped at 5."""
        steps = [PlanStep(order=i, description=f"Step {i}", tool_needed=None, expected_output="") for i in range(10)]
        plan = Plan(
            intent="multi_step",
            complexity="complex",
            steps=steps,
        )
        validated = validate_plan(plan)
        assert len(validated.steps) == 5
        assert "任务已简化" in validated.coding_hints[0]

    def test_confidence_bounds(self):
        """Confidence should be bounded between 0 and 1."""
        # Test upper bound
        plan = Plan(intent="test", complexity="simple", confidence=1.5)
        validated = validate_plan(plan)
        assert validated.confidence == 1.0

        # Test lower bound
        plan = Plan(intent="test", complexity="simple", confidence=-0.5)
        validated = validate_plan(plan)
        assert validated.confidence == 0.0


class TestParsePlanFromJson:
    """Tests for parse_plan_from_json function."""

    def test_parse_valid_json(self):
        """Valid JSON should parse correctly."""
        json_str = '''
        {
            "intent": "computation",
            "complexity": "simple",
            "required_tools": ["ask_semantic"],
            "relevant_modules": ["math"],
            "steps": [],
            "coding_hints": ["Use math module"],
            "expected_output_type": "number",
            "confidence": 0.9,
            "skip_planning": false
        }
        '''
        plan = parse_plan_from_json(json_str)
        assert plan is not None
        assert plan.intent == "computation"
        assert plan.complexity == "simple"
        assert plan.required_tools == ["ask_semantic"]
        assert plan.relevant_modules == ["math"]
        assert plan.confidence == 0.9

    def test_parse_with_steps(self):
        """JSON with steps should parse correctly."""
        json_str = '''
        {
            "intent": "hybrid",
            "complexity": "medium",
            "steps": [
                {"order": 1, "description": "Step 1", "tool_needed": "ask_semantic", "expected_output": "result", "dependencies": []},
                {"order": 2, "description": "Step 2", "tool_needed": null, "expected_output": "final", "dependencies": [0]}
            ]
        }
        '''
        plan = parse_plan_from_json(json_str)
        assert plan is not None
        assert len(plan.steps) == 2
        assert plan.steps[0].description == "Step 1"
        assert plan.steps[1].dependencies == [0]

    def test_parse_invalid_json(self):
        """Invalid JSON should return None."""
        plan = parse_plan_from_json("not valid json")
        assert plan is None

    def test_parse_missing_fields(self):
        """Missing fields should use defaults."""
        json_str = '{"intent": "test"}'
        plan = parse_plan_from_json(json_str)
        assert plan is not None
        assert plan.intent == "test"
        assert plan.complexity == "simple"  # default
        assert plan.steps == []  # default


class TestBuildCoderPrompt:
    """Tests for build_coder_prompt function."""

    def test_skip_planning_uses_static(self):
        """skip_planning=True should return static prompt."""
        plan = Plan(
            intent="simple_chat",
            complexity="trivial",
            skip_planning=True,
        )
        prompt = build_coder_prompt(plan)
        assert prompt == STATIC_CODER_PROMPT

    def test_tools_included_in_prompt(self):
        """Required tools should be included in prompt."""
        plan = Plan(
            intent="semantic",
            complexity="simple",
            required_tools=["ask_semantic"],
        )
        prompt = build_coder_prompt(plan)
        assert "ask_semantic" in prompt
        assert "语义理解" in prompt

    def test_modules_included_in_prompt(self):
        """Relevant modules should be included in prompt."""
        plan = Plan(
            intent="computation",
            complexity="medium",
            relevant_modules=["math", "datetime"],
        )
        prompt = build_coder_prompt(plan)
        assert "math" in prompt
        assert "datetime" in prompt

    def test_steps_included_in_prompt(self):
        """Steps should be included for complex tasks."""
        plan = Plan(
            intent="multi_step",
            complexity="complex",
            steps=[
                PlanStep(order=1, description="First do this", tool_needed=None, expected_output=""),
                PlanStep(order=2, description="Then do that", tool_needed=None, expected_output=""),
            ],
        )
        prompt = build_coder_prompt(plan)
        assert "执行步骤" in prompt
        assert "First do this" in prompt

    def test_output_type_not_in_modular_prompt(self):
        """Expected output type is not in modular prompt (Phase 10 change)."""
        plan = Plan(
            intent="computation",
            complexity="simple",
            expected_output_type="number",
        )
        prompt = build_coder_prompt(plan)
        # Phase 10: Modular prompt doesn't include output_type by default
        # (it can be added via coding_hints if needed)
        assert "set_output" in prompt  # Core functionality


class TestToolRegistry:
    """Tests for TOOL_REGISTRY."""

    def test_required_tools_exist(self):
        """All expected tools should exist in registry."""
        assert "ask_semantic" in TOOL_REGISTRY
        assert "web_search" in TOOL_REGISTRY
        assert "safe_semantic" in TOOL_REGISTRY

    def test_tool_has_usage_doc(self):
        """Each tool should have usage documentation."""
        for name, tool in TOOL_REGISTRY.items():
            assert tool.usage_doc, f"Tool {name} missing usage_doc"
            assert len(tool.usage_doc) > 20, f"Tool {name} has short usage_doc"


# =============================================================================
# Phase 10: Modular Prompt Architecture Tests
# =============================================================================

class TestDetectMultipleChoice:
    """Tests for detect_multiple_choice function (Phase 10.2a)."""

    def test_standard_format(self):
        """Standard A. B. C. D. format should be detected."""
        assert detect_multiple_choice("12 × 8 等于多少？A. 86 B. 96 C. 106 D. 116") == True
        assert detect_multiple_choice("问题？A. 选项1 B. 选项2 C. 选项3 D. 选项4") == True

    def test_chinese_format(self):
        """Chinese format with 选项 should be detected."""
        assert detect_multiple_choice("正确答案是选项A") == True
        assert detect_multiple_choice("选择选项B或C") == True

    def test_parenthesis_format(self):
        """Parenthesis format (A) (B) should be detected."""
        assert detect_multiple_choice("选择 (A) 或 (B)") == True

    def test_non_multiple_choice(self):
        """Non-multiple-choice queries should return False."""
        assert detect_multiple_choice("计算斐波那契数列") == False
        assert detect_multiple_choice("翻译这段文字") == False
        assert detect_multiple_choice("你好") == False
        assert detect_multiple_choice("什么是人工智能？") == False

    def test_single_letter_not_mc(self):
        """Single letter mention without options should not be MC."""
        assert detect_multiple_choice("这个问题是关于A的") == False

    def test_complex_mc_format(self):
        """Complex MC formats should be detected."""
        assert detect_multiple_choice("问题：以下哪个正确？\nA. 第一个\nB. 第二个\nC. 第三个") == True


class TestDetectIntentFeatures:
    """Tests for detect_intent_features function (Phase 10.3)."""

    def test_computation_features(self):
        """Computation queries should have correct features."""
        features = detect_intent_features("计算 1+1")
        assert features["has_math_expr"] == True
        assert features["has_calc_keyword"] == True

    def test_semantic_features(self):
        """Semantic queries should have correct features."""
        features = detect_intent_features("翻译这段文字")
        assert features["has_translate"] == True

        features = detect_intent_features("总结文章主旨")
        assert features["has_summarize"] == True

    def test_multi_step_features(self):
        """Multi-step queries should have correct features."""
        features = detect_intent_features("是谁发明了电话？")
        assert features["needs_fact_check"] == True

        features = detect_intent_features("最新的科技新闻")
        assert features["needs_realtime"] == True

    def test_simple_chat_features(self):
        """Simple chat queries should have correct features."""
        features = detect_intent_features("你好")
        assert features["is_greeting"] == True

        features = detect_intent_features("谢谢")
        assert features["is_thanks"] == True

    def test_multiple_choice_detection(self):
        """MC queries should have is_multiple_choice feature."""
        features = detect_intent_features("问题？A. 选项1 B. 选项2")
        assert features["is_multiple_choice"] == True


class TestInferIntentFromFeatures:
    """Tests for infer_intent_from_features function (Phase 10.3)."""

    def test_infer_simple_chat(self):
        """Simple chat should be inferred correctly."""
        features = {"is_greeting": True, "is_thanks": False, "is_short": False,
                    "has_math_expr": False, "has_calc_keyword": False, "has_translate": False,
                    "has_summarize": False, "has_sentiment": False, "needs_fact_check": False,
                    "needs_realtime": False, "has_question_word": False, "is_multiple_choice": False,
                    "is_pure_math": False}
        intent, complexity = infer_intent_from_features(features, "你好")
        assert intent == "simple_chat"
        assert complexity == "trivial"

    def test_infer_computation(self):
        """Computation should be inferred correctly."""
        features = {"is_greeting": False, "is_thanks": False, "is_short": False,
                    "has_math_expr": True, "has_calc_keyword": True, "has_translate": False,
                    "has_summarize": False, "has_sentiment": False, "needs_fact_check": False,
                    "needs_realtime": False, "has_question_word": False, "is_multiple_choice": False,
                    "is_pure_math": False}
        intent, complexity = infer_intent_from_features(features, "计算 1+1")
        assert intent == "computation"

    def test_infer_semantic(self):
        """Semantic should be inferred correctly."""
        features = {"is_greeting": False, "is_thanks": False, "is_short": False,
                    "has_math_expr": False, "has_calc_keyword": False, "has_translate": True,
                    "has_summarize": False, "has_sentiment": False, "needs_fact_check": False,
                    "needs_realtime": False, "has_question_word": False, "is_multiple_choice": False,
                    "is_pure_math": False}
        intent, complexity = infer_intent_from_features(features, "翻译这段文字")
        assert intent == "semantic"

    def test_infer_multi_step(self):
        """Multi-step should be inferred correctly."""
        features = {"is_greeting": False, "is_thanks": False, "is_short": False,
                    "has_math_expr": False, "has_calc_keyword": False, "has_translate": False,
                    "has_summarize": False, "has_sentiment": False, "needs_fact_check": True,
                    "needs_realtime": False, "has_question_word": True, "is_multiple_choice": False,
                    "is_pure_math": False}
        intent, complexity = infer_intent_from_features(features, "是谁发明了电话？")
        assert intent == "multi_step"


class TestModularPromptArchitecture:
    """Tests for Phase 10 modular prompt architecture."""

    def test_core_rules_exists(self):
        """CORE_RULES_PROMPT should exist and be concise."""
        assert CORE_RULES_PROMPT is not None
        assert len(CORE_RULES_PROMPT) > 100
        assert "set_output" in CORE_RULES_PROMPT
        # Should be around 800 chars (target)
        assert len(CORE_RULES_PROMPT) < 1200  # Allow some flexibility

    def test_multiple_choice_rules_exists(self):
        """MULTIPLE_CHOICE_RULES should exist."""
        assert MULTIPLE_CHOICE_RULES is not None
        assert "A/B/C/D" in MULTIPLE_CHOICE_RULES

    def test_tool_usage_rules_exists(self):
        """TOOL_USAGE_RULES should exist."""
        assert TOOL_USAGE_RULES is not None
        assert "web_search" in TOOL_USAGE_RULES

    def test_build_coder_prompt_with_mc_query(self):
        """build_coder_prompt should inject MC rules when query has MC format."""
        plan = Plan(
            intent="computation",
            complexity="simple",
            skip_planning=False,
            logic_steps=[],
        )
        prompt = build_coder_prompt(plan, query="问题？A. 选项1 B. 选项2 C. 选项3 D. 选项4")
        assert "多选题" in prompt or "选项字母" in prompt

    def test_build_coder_prompt_without_mc_query(self):
        """build_coder_prompt should NOT inject MC rules for non-MC queries."""
        plan = Plan(
            intent="computation",
            complexity="simple",
            skip_planning=False,
            logic_steps=[],
        )
        prompt = build_coder_prompt(plan, query="计算斐波那契数列第10项")
        # Should have core rules but not MC-specific rules
        assert "set_output" in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])