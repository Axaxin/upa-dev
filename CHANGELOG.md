# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
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

## [2026-02-26] - Phase 5 Complete

### Added
- Planner Architecture for dynamic prompt construction
- Intent classification system
- Dynamic tool selection (ask_sub_agent, web_search)
- Benchmark framework integration with Planner tracking
