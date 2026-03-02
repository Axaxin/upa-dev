"""
UPA Planner Pydantic Models.

This module provides type-safe Plan and LogicStep models using Pydantic,
replacing the previous dataclass-based approach with proper validation.
"""

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import Any


class PlanStep(BaseModel):
    """Single step in a decomposed plan."""
    model_config = ConfigDict(extra='ignore')

    order: int = 0
    description: str = ""
    tool_needed: str | None = None
    expected_output: str = ""
    dependencies: list[int] = Field(default_factory=list)


class LogicStep(BaseModel):
    """
    带变量绑定的逻辑步骤 - 用于强制数据流约束。

    Planner 输出逻辑契约，Coder 作为"编译器"将其编译为 Python 代码。
    这确保工具结果被正确使用，而非被 LLM 忽略。
    """
    model_config = ConfigDict(extra='ignore')

    id: str = ""                           # "S1", "S2", ...
    action: str = ""                       # "web_search" | "ask_semantic" | "logic" | "set_output"
    args: dict[str, Any] = Field(default_factory=dict)  # 工具参数（支持变量插值 {var}）
    input_vars: list[str] = Field(default_factory=list)  # 依赖的变量
    output_var: str = ""                   # 输出变量名
    description: str = ""                  # 步骤描述（用于调试）
    assertion: str | None = None           # 断言条件（可选）

    @field_validator('action')
    @classmethod
    def validate_action(cls, v: str) -> str:
        """Validate action is a known type."""
        valid_actions = {"web_search", "ask_semantic", "logic", "set_output", "get_output"}
        if v and v not in valid_actions:
            # Allow unknown actions but log a warning (handled by caller)
            pass
        return v


class Plan(BaseModel):
    """Structured output from Planner."""
    model_config = ConfigDict(extra='ignore')

    # Intent classification
    intent: str = "unknown"  # "simple_chat" | "computation" | "semantic" | "hybrid" | "multi_step"
    complexity: str = "simple"  # "trivial" | "simple" | "medium" | "complex"

    # Task decomposition (legacy, kept for backward compatibility)
    steps: list[PlanStep] = Field(default_factory=list)

    # Logic Contract: 带变量绑定的逻辑步骤（Phase 9 新增）
    logic_steps: list[LogicStep] = Field(default_factory=list)

    # Dynamic tool selection
    required_tools: list[str] = Field(default_factory=list)
    relevant_modules: list[str] = Field(default_factory=list)

    # Guidance for Coder
    coding_hints: list[str] = Field(default_factory=list)
    expected_output_type: str = "string"

    # Planner confidence
    confidence: float = 0.8

    # Fallback flag
    skip_planning: bool = False

    # Post-processing configuration
    requires_post_processing: bool = False  # 是否需要输出整理
    output_format_hint: str = ""  # 输出格式提示

    @field_validator('intent')
    @classmethod
    def validate_intent(cls, v: str) -> str:
        """Validate intent is a known type.

        Phase 13: simple_chat and trivial_computation are filtered by Intent Recognition.
        Planner only handles: computation, semantic, hybrid, multi_step.
        """
        valid_intents = {"computation", "semantic", "hybrid", "multi_step", "unknown"}
        # Also accept simple_chat and trivial_computation for backward compatibility
        # (in case they bypass intent recognition)
        all_valid = valid_intents | {"simple_chat", "trivial_computation", "need_planner"}
        if v and v not in all_valid:
            # Allow unknown intents to pass through (for flexibility and testing)
            pass
        return v

    @field_validator('complexity')
    @classmethod
    def validate_complexity(cls, v: str) -> str:
        """Validate complexity is a known type."""
        valid_complexities = {"trivial", "simple", "medium", "complex"}
        if v and v not in valid_complexities:
            return "simple"  # Default to simple for unknown complexity
        return v

    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is in valid range [0.0, 1.0]."""
        return max(0.0, min(1.0, v))

    @field_validator('required_tools')
    @classmethod
    def validate_required_tools(cls, v: list[str]) -> list[str]:
        """Filter to only valid tools."""
        # Import TOOL_REGISTRY lazily to avoid circular import
        try:
            from upa import TOOL_REGISTRY
            valid_tools = set(TOOL_REGISTRY.keys())
            return [t for t in v if t in valid_tools]
        except ImportError:
            # If TOOL_REGISTRY is not available, return as-is
            return v

    @model_validator(mode='after')
    def validate_plan(self) -> 'Plan':
        """Validate plan after all fields are set."""
        # Cap steps to prevent runaway decomposition
        if len(self.steps) > 5:
            self.steps = self.steps[:5]
            if self.coding_hints is None:
                self.coding_hints = []
            self.coding_hints.append("任务已简化，专注于核心步骤")
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'Plan':
        """Create Plan from dictionary."""
        return cls.model_validate(data)


class PlanParseResult(BaseModel):
    """Result of parsing plan from JSON with validation details."""
    model_config = ConfigDict(frozen=True)

    plan: Plan | None = None
    parse_method: str = ""  # "layer1_json", "layer2_repair", "layer3_regex", "failed"
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.plan is not None

    def to_plan(self) -> Plan | None:
        """Get the parsed plan or None."""
        return self.plan


# Valid intent values as a set for easy reference
VALID_INTENTS = {"simple_chat", "computation", "semantic", "hybrid", "multi_step", "unknown"}

# Valid complexity values as a set for easy reference
VALID_COMPLEXITIES = {"trivial", "simple", "medium", "complex"}

# Valid tool actions for LogicStep
VALID_LOGIC_ACTIONS = {"web_search", "ask_semantic", "logic", "set_output", "get_output"}
