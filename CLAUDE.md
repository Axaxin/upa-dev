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

# Add a dev dependency
uv add --dev <package>

# Run Python scripts
uv run python <script.py>

# Run the main module
uv run python -m upa_dev
```

## Architecture

The system follows a single unified workflow:

1. **Input** → Receive user text and context
2. **Code Generation** → LLM outputs Python code wrapped in ```python blocks
3. **Guardrails** → AST-based static analysis to block dangerous imports (os, subprocess, etc.)
4. **Sandbox Execution** → Run code in isolated environment
5. **Output** → Capture stdout as final response; on error, feed traceback back to LLM for auto-repair

### Core Components

- **Unified Orchestrator**: Single entry point with constrained system prompt that forces Python-only output
- **Sandbox Runtime**: Docker or WASM isolated execution with pre-installed libs (pandas, numpy, requests, datetime, re)
- **Sub-Agent Functions**: `ask_sub_agent()` for semantic tasks that can't be solved with pure logic
- **Code Cache**: Stores successful code patterns keyed by task feature vectors for reuse and self-healing

### Key Principle

All LLM responses must be executable Python code. Even casual chat is handled via `print("response")`. This ensures 100% deterministic logic operations and full explainability.
