# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**upa-dev** implements the Unified Programmatic Architecture (UPA) - an "Always-Code Execution" (ACE) system that treats the LLM as a JIT Code Engine. All user inputs (chat, data processing, logic) are handled through Python code generation and execution.

## Environment & Dependency Management

This project uses **uv** for Python environment and dependency management.

```bash
# Install dependencies
uv sync

# Add a new dependency
uv add <package>

# Run Python scripts
uv run python <script.py>

# Run the UPA CLI
uv run python upa.py "your question"

# Run benchmarks
# Core UPA functionality (43 tests)
uv run python -m benchmarks core -w 8

# Semantic-Logic hybrid (17 tests)
uv run python -m benchmarks semantic -w 8

# All suites: core, semantic, classic, mmlu, planner
uv run python -m benchmarks --list-suites
```

### Environment Configuration

Create a `.env` file in the project root:

```bash
# Default provider (dashscope | cloudflare)
UPA_PROVIDER=cloudflare

# DashScope Configuration
DASHSCOPE_URL=https://coding.dashscope.aliyuncs.com/v1
DASHSCOPE_API_KEY=your_key_here
DASHSCOPE_MODEL=qwen3.5-plus

# Cloudflare Gateway + Grok Configuration
CLOUDFLARE_URL=https://gateway.ai.cloudflare.com/v1/your_account/gemini/compat
CLOUDFLARE_API_KEY=your_key_here
CLOUDFLARE_MODEL=grok/grok-4-1-fast-non-reasoning
```

## Architecture

The system follows a single unified workflow:

1. **Input** → Receive user text and context
2. **Code Generation** → LLM outputs Python code wrapped in ```python blocks
3. **Guardrails** → AST-based static analysis to block dangerous imports (os, subprocess, etc.)
4. **Sandbox Execution** → Run code in isolated environment
5. **Output** → Capture stdout as final response; on error, feed traceback back to LLM for auto-repair

### Core Components

- **Multi-Provider Support**: Switch between DashScope (Qwen) and Cloudflare (Grok) via `--provider` flag
- **Semantic Function**: `ask_semantic()` allows LLM-generated code to call LLM for semantic tasks
- **Security Guardrails**: AST-based blocking of dangerous modules (os, subprocess, exec, eval, etc.)
- **Error Recovery**: Automatic retry with security feedback when violations detected

### Semantic Function

The `ask_semantic(query: str) -> str` function is injected into the sandbox and allows:
- Semantic tasks (translation, sentiment analysis, summarization)
- Recursive calls up to MAX_SEMANTIC_DEPTH=3
- 60-second timeout per call
- Direct text response (no code generation)

```python
# Example: Using semantic in generated code
translation = ask_semantic("Translate 'Hello' to Chinese")
print(f"Translation: {translation}")
```

### Key Principle

All LLM responses must be executable Python code. Even casual chat is handled via `print("response")`. This ensures 100% deterministic logic operations and full explainability.

## CLI Usage

```bash
# Basic usage (uses default provider from .env)
uv run python upa.py "What is 2+2?"

# Specify provider
uv run python upa.py --provider dashscope "Translate hello to Chinese"
uv run python upa.py --provider cloudflare "Analyze sentiment of 'I love this'"

# List available providers
uv run python upa.py --list-providers

# Show timing breakdown
uv run python upa.py --timing "Calculate fibonacci(10)"
```

## Benchmarking

The project uses a unified benchmark framework (`benchmarks/` module):

```bash
# List all available test suites
uv run python -m benchmarks --list-suites

# Run core UPA functionality tests (43 tests)
uv run python -m benchmarks core -w 8

# Run semantic-logic hybrid tests (17 tests)
uv run python -m benchmarks semantic -w 8

# Run classic LLM benchmarks (23 tests)
uv run python -m benchmarks classic -w 8

# Run MMLU academic knowledge benchmarks (147 tests)
uv run python -m benchmarks mmlu -w 8

# Filter by complexity
uv run python -m benchmarks core -c 中等 -w 4

# Export results to JSON
uv run python -m benchmarks core -j results.json -w 8

# Save detailed execution logs
uv run python -m benchmarks core --save-details details.json -w 8
```

**Test Suites**:

| Suite | Tests | Description |
|-------|-------|-------------|
| **core** | 43 | Core UPA functionality (code generation & execution) |
| **semantic** | 17 | Sub-agent integration (semantic-logic hybrid) |
| **classic** | 23 | Classic LLM problems (GSM8K, HumanEval, MATH) |
| **mmlu** | 147 | Academic knowledge across STEM, humanities, social sciences |
| **planner** | 18 | Planner validation (intent classification, task decomposition) |

**Legacy Commands** (still work but deprecated):
- `benchmark_upa.py` → Use `python -m benchmarks core`
- `benchmark_semantic.py` → Use `python -m benchmarks semantic`

## Implementation Status

### ✅ Completed Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | MVP (Always-Code Execution) | ✅ Complete |
| 2 | Semantic Integration | ✅ Complete |
| 3 | Self-Healing | ✅ Complete |
| 4 | CLI Enhancements | ✅ Complete |
| 5 | Planner Architecture | ✅ Complete |
| 6 | Complexity-Aware Coder Selection | ✅ Complete |
| 7 | Self-Check Mechanism | ✅ Complete |
| 8 | Structured Output (set_output API) | ✅ Complete |
| 9 | Logic Contract (variable binding) | ✅ Complete |
| 10 | Prompt Optimization | ✅ Complete |
| 11 | Intent Recognition | ✅ Complete |
| 11.5 | Intent Recognition Optimization | ✅ Complete |
| 12 | Pydantic Planner Validation | ✅ Complete |

### Recent Achievements

- **MMLU Benchmark**: 100% pass rate (32/32 sampling)
- **Intent Recognition Stability**: 100% consistent across 5 consecutive runs
- **Skip Planning Rate**: 62.5% (within target 50-70% range)
- **Pydantic Refactoring**: Type-safe Planner validation with 5-field accuracy reporting

See `DESIGN.md` for detailed architecture and phase documentation.
