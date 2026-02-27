#!/usr/bin/env python3
"""
Unit tests for UPA Planner module.

Run with: uv run pytest tests/test_planner.py -v
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from upa import (
    is_trivial_query,
    create_default_plan,
    validate_plan,
    parse_plan_from_json,
    Plan,
    PlanStep,
    TOOL_REGISTRY,
    STATIC_CODER_PROMPT,
    build_coder_prompt,
)


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

    def test_output_type_included(self):
        """Expected output type should be included."""
        plan = Plan(
            intent="computation",
            complexity="simple",
            expected_output_type="number",
        )
        prompt = build_coder_prompt(plan)
        assert "期望输出类型：number" in prompt


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])