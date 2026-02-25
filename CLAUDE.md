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
uv run python benchmark_upa.py --workers 8
uv run python benchmark_semantic.py --workers 8
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
- **Sub-Agent Recursive Calls**: `ask_sub_agent()` allows LLM-generated code to call LLM for semantic tasks
- **Security Guardrails**: AST-based blocking of dangerous modules (os, subprocess, exec, eval, etc.)
- **Error Recovery**: Automatic retry with security feedback when violations detected

### Sub-Agent System

The `ask_sub_agent(query: str) -> str` function is injected into the sandbox and allows:
- Semantic tasks (translation, sentiment analysis, summarization)
- Recursive calls up to MAX_SUB_AGENT_DEPTH=3
- 60-second timeout per sub-agent call
- Automatic provider propagation to sub-agents

```python
# Example: Using sub-agent in generated code
translation = ask_sub_agent("Translate 'Hello' to Chinese")
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

### UPA Performance Benchmark (`benchmark_upa.py`)
Tests core code generation and execution across 43 test cases covering 4 complexity levels.

```bash
# Run all tests
uv run python benchmark_upa.py --workers 8

# Filter by complexity
uv run python benchmark_upa.py --complexity simple --workers 4

# Limit tests
uv run python benchmark_upa.py --limit 10

# Export results
uv run python benchmark_upa.py --workers 8 --json results.json
```

### Semantic-Logic Hybrid Benchmark (`benchmark_semantic.py`)
Tests hybrid tasks combining semantic understanding (sub-agent) with logic processing. 17 test cases across 5 task types.

```bash
# Run all tests
uv run python benchmark_semantic.py --workers 8

# Filter by task type
uv run python benchmark_semantic.py --type "翻译+逻辑" --workers 4

# Export results
uv run python benchmark_semantic.py --workers 8 --json results.json
```

### Benchmark Task Types

- **翻译+逻辑**: Translation followed by logical operations
- **总结+分析**: Summarization with analysis
- **情感+计算**: Sentiment analysis with calculations
- **提取+处理**: Information extraction with processing
- **递归调用**: Multi-step recursive sub-agent calls
