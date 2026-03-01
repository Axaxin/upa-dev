"""
Planner validation using Pydantic models for type-safe validation.

This module provides structured validation for Planner decisions, replacing
the previous dict[str, bool] approach with proper type checking and detailed
error reporting.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict


class IntentType(str):
    """Intent types for Planner classification."""
    SIMPLE_CHAT = "simple_chat"
    COMPUTATION = "computation"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    MULTI_STEP = "multi_step"


# Valid intent values as a set for easy reference
VALID_INTENTS = {
    "simple_chat",
    "computation",
    "semantic",
    "hybrid",
    "multi_step",
}


class PlannerExpectation(BaseModel):
    """测试用例的 Planner 预期配置"""
    model_config = ConfigDict(frozen=True)  # 不可变

    intent: str | None = None
    tools: list[str] = Field(default_factory=list)
    skip_planning: bool | None = None
    has_logic_steps: bool | None = None
    uses_logic_contract: bool | None = None

    @field_validator('tools')
    @classmethod
    def validate_tools(cls, v: list[str]) -> list[str]:
        allowed_tools = {"ask_semantic", "web_search", "set_output", "logic"}
        for tool in v:
            if tool not in allowed_tools:
                raise ValueError(f"Unknown tool: {tool}. Allowed: {allowed_tools}")
        return v


class PlannerValidationDetail(BaseModel):
    """单个校验项的详细信息"""
    expected: str | bool | list[str]
    actual: str | bool | list[str]
    correct: bool

    def error_message(self) -> str | None:
        if self.correct:
            return None
        return f"Expected {self.expected!r}, got {self.actual!r}"


class PlannerValidationResult(BaseModel):
    """Planner 校验完整结果"""

    # 校验结果汇总
    intent_correct: bool = True
    tools_correct: bool = True
    skip_correct: bool = True
    logic_steps_correct: bool = True
    logic_contract_correct: bool = True

    # 详细信息（用于调试和报告）
    intent_detail: PlannerValidationDetail | None = None
    tools_detail: PlannerValidationDetail | None = None
    skip_detail: PlannerValidationDetail | None = None
    logic_steps_detail: PlannerValidationDetail | None = None
    logic_contract_detail: PlannerValidationDetail | None = None

    @property
    def all_correct(self) -> bool:
        return all([
            self.intent_correct,
            self.tools_correct,
            self.skip_correct,
            self.logic_steps_correct,
            self.logic_contract_correct,
        ])

    @property
    def error_summary(self) -> list[str]:
        """获取所有错误信息"""
        errors = []
        for detail_attr in ['intent_detail', 'tools_detail',
                           'skip_detail', 'logic_steps_detail',
                           'logic_contract_detail']:
            detail = getattr(self, detail_attr)
            if detail and not detail.correct:
                msg = detail.error_message()
                if msg:
                    errors.append(f"{detail_attr.replace('_detail', '')}: {msg}")
        return errors

    def to_dict(self) -> dict[str, bool]:
        """兼容原有 dict 格式的转换方法"""
        return {
            'intent_correct': self.intent_correct,
            'tools_correct': self.tools_correct,
            'skip_correct': self.skip_correct,
            'logic_steps_correct': self.logic_steps_correct,
            'logic_contract_correct': self.logic_contract_correct,
            'all_correct': self.all_correct,
        }
