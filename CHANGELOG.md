# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
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
