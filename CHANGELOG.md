# Changelog

All notable changes to this project will be documented in this file.

For detailed implementation history and phase documentation, see [DESIGN.md](DESIGN.md).

## [Unreleased]

### Phase 11.5: Intent Recognition Optimization (2026-03-01)

**Enhancements**:
- Added `knowledge` category for fact/concept/theory queries
- Added confidence threshold fallback (< 0.6 forces Planner)
- Reduced temperature to 0.0 for deterministic classification

**Results**:
- MMLU benchmark: 100% pass rate (16/16)
- Skip planning rate: 62.5% (within target 50-70%)

### Phase 10: Prompt Optimization (2026-02-28)

**Enhancements**:
- Dynamic rule injection for multiple-choice questions
- Chain-of-Thought (CoT) prompting for complex reasoning

**Results**:
- MMLU benchmark: 90.6% → 100.0% (32/32)

### Phase 9: Logic Contract (2026-02-28)

**Enhancements**:
- Variable binding for tool result data flow
- AST-based validation for tool result usage

### Phase 8: Structured Output (set_output API)

**Enhancements**:
- Type-preserving output via `set_output()` API
- Separated debug logging from final results

### Phase 7: Self-Check Mechanism

**Enhancements**:
- Auto-generated assertions for logic validation
- Type and range validation templates

### Phase 6: Complexity-Aware Coder Selection

**Enhancements**:
- Dynamic model selection based on task complexity
- Environment-configurable model mapping

### Phase 5: Planner Architecture

**Enhancements**:
- Intent classification system
- Dynamic tool selection (ask_semantic, web_search)
- Task decomposition for multi-step problems

### Earlier Phases

- **Phase 4**: CLI enhancements (--model, --config flags)
- **Phase 3**: Self-healing mechanism (auto-retry on errors)
- **Phase 2**: Semantic integration (ask_semantic function)
- **Phase 1**: MVP (Always-Code Execution, AST guardrails)
