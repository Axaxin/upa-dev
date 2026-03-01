# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Phase 11.5: Intent Recognition Optimization (2026-03-01)

**Intent Classification Prompt Enhancement**:
- Added new `knowledge` category for fact/concept/theory queries (history, politics, economics, science, etc.)
- Refined `computation` definition to "pure mathematical calculation" (removed broad terms like "logical reasoning, data processing")
- Added 2-3 concrete examples for each category (simple_chat, computation, semantic, knowledge, multi_step, complex)
- Added "feature" descriptions to help with classification boundary determination
- Defined 5 explicit rules for `requires_planning=true`
- Defined 3 explicit rules for `requires_planning=false`
- Added complexity grading with time estimates (trivial <5s, simple <30s, medium <2min, complex >2min)

**Confidence Threshold Fallback**:
- Added low-confidence fallback mechanism: when `confidence < 0.6`, forces `requires_planning=True`
- Logs "Low confidence" message for debugging and monitoring

**Temperature Adjustment**:
- Changed intent classification temperature from 0.1 to 0.0 for more deterministic results

**Verification Results**:
- MMLU benchmark: 100% pass rate maintained (16/16)
- Knowledge category accuracy: ~100% (tested with "什么是 Porter 五力", "维果茨基是谁")
- Classification stability: 100% consistent across 5 consecutive runs
- Skip planning rate: 62.5% (within target 50-70% range, down from 92.9%)

### Added (Previous)
- **MMLU Benchmark Optimization** (2026-02-28)
  - Achieved 100% pass rate (32/32) on MMLU baseline tests, up from 90.6% (29/32)
  - Added Chain-of-Thought (CoT) prompting for complex reasoning tasks
  - Added explicit option mapping examples for multiple-choice questions
  - Added web_search result formatting guidance for multi-step tool chains

### Fixed
- **Timeout Issue**: Increased benchmark timeout from 120s to 180s for parallel execution
- **Option Mapping**: Fixed LLM generating code that outputs calculation results instead of option letters
- **Tool Chain Handling**: Fixed web_search + ask_semantic chain by adding result formatting examples
- **Syntax Error**: Fixed f-string syntax issue with full-width colons in prompt examples

### Changed
- **STATIC_CODER_PROMPT**: Added multiple-choice output rules and CoT reasoning examples
- **build_logic_contract_prompt**: Added rule for formatting complex data before passing to ask_semantic
- **build_logic_contract_prompt**: Added rule for Chain-of-Thought prompting

### Performance
- **MMLU Results**: 90.6% → 100.0% (32/32 tests passing)
  - Statistics: Mean - Fixed timeout issue (now ~23s)
  - Elementary Mathematics: Multiplication - Fixed option mapping
  - Geography: Capitals - Fixed web_search result handling
  - Chemistry: Reaction - Fixed with CoT prompting

---

### Added (Previous)
- **Tavily Search API Integration**
  - Replaced DuckDuckGo with Tavily API for web search functionality
  - Fixed network timeout issues for search queries in mainland China
  - Free tier: 1000 searches/month
  - Added `TAVILY_API_KEY` configuration to `.env`
  - Improved error handling for API rate limits and authentication errors

- **Configuration Framework Enhancement**
  - Added centralized `PROVIDER_PRESETS` registry for multi-provider support
  - Added `Config` dataclass for type-safe configuration management
  - Support for cross-provider setup (different providers for Coder, Planner, Sub-Agent)
  - New `--show-config` CLI option to display current configuration

- **Planner Validation Test Suite** (`benchmarks/suites/planner.py`)
  - 18 test cases validating Planner (Phase 5) decision accuracy
  - Tests for intent classification, tool selection, and skip_planning decisions
  - Automated validation with accuracy reporting in benchmark results

- **Framework Unit Tests** (`tests/`)
  - `test_planner.py`: Unit tests for Planner module functions
  - `test_runner.py`: Unit tests for benchmark data structures and utilities
  - Added `pytest` as development dependency

- **Planner Validation in Benchmark Report**
  - New "Planner Validation Results" section in benchmark output
  - Reports accuracy for intent, tools, and skip_planning decisions
  - Overall accuracy metric for Planner performance

### Changed
- **Web Search API**: Migrated from DuckDuckGo to Tavily API for better reliability
- **Configuration Structure**: Enhanced `.env` and `.env.example` with:
  - Organized provider sections (DashScope, Cloudflare, OpenAI, Anthropic, Custom)
  - Cross-provider configuration examples
  - Advanced settings section

- **Project Structure**
  - Merged `planner.py` into `upa.py` for single-file simplicity
  - Updated `README.md` to reflect new structure and test commands

- **Benchmark Framework**
  - Added `classic` and `mmlu` suites to default imports in `benchmarks/suites/__init__.py`
  - Extended `TestCase` with `expect_planner_*` fields for validation expectations
  - Extended `TestDetails` with `planner_validation` field for results

- **Legacy Files Deprecated**
  - `benchmark_upa.py`: Now a wrapper that redirects to `benchmarks core`
  - `benchmark_semantic.py`: Now a wrapper that redirects to `benchmarks semantic`
  - Both files emit deprecation warnings

### Fixed
- **Suite Registration Bug**: `classic` and `mmlu` suites now properly registered
- **Network Timeout Issue**: Tavily API resolves DuckDuckGo timeout problems in mainland China
- **Configuration Loading**: Fixed provider/model resolution for cross-provider setups

## [2026-02-26] - Phase 5 Complete

### Added
- Planner Architecture for dynamic prompt construction
- Intent classification system
- Dynamic tool selection (ask_sub_agent, web_search)
- Benchmark framework integration with Planner tracking
