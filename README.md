# UPA - Unified Programmatic Architecture

> **"Always-Code Execution"** - LLM as a JIT Code Engine

UPA is an experimental AI agent architecture where the LLM always outputs Python code that gets executed in a sandbox. The final response is the `stdout` of code execution.

## Vision

- **Unified**: No distinction between chat and tools - everything is code
- **Deterministic**: Logic operations are 100% accurate through actual code execution
- **Evolvable**: Code can be cached and self-healed for edge cases

## Quick Start

```bash
# Install dependencies
uv sync

# Run UPA
uv run python upa.py "你的问题"

# Show timing report
uv run python upa.py --timing "1+1等于几"

# Show generated code
uv run python upa.py --show-code "帮我排序: 3,1,4,1,5"
```

## Project Structure

```
upa-dev/
├── upa.py              # Main CLI implementation (MVP)
├── benchmarks/         # Unified benchmark framework
│   ├── cli.py          # Benchmark CLI entry point
│   ├── runner.py       # Core execution engine
│   ├── display.py      # Terminal display utilities
│   └── suites/         # Test suite definitions
│       ├── core_upa.py # Core UPA functionality tests
│       └── semantic.py # Semantic-Logic hybrid tests
├── benchmark_upa.py    # Legacy: Performance benchmark (deprecated)
├── benchmark_semantic.py # Legacy: Semantic benchmark (deprecated)
├── DESIGN.md           # Architecture design document
├── CLAUDE.md           # Project guidance for Claude Code
└── .env                # API configuration (DashScope)
```

## Implementation Status

### ✅ Phase 1: MVP (Complete)
- [x] Base Orchestrator with "Always-Code" system prompt
- [x] Local sandbox with stdout capture
- [x] AST-based security guardrails
- [x] CLI with timing support

### ✅ Phase 2: Semantic Integration (Complete)
- [x] `ask_sub_agent()` function for semantic tasks
- [x] Multi-level LLM calling (main for code, sub for semantics)
- [x] Multi-provider support (DashScope, Cloudflare)

### ✅ Phase 3: Self-Healing (Complete)
- [x] Auto-heal on execution errors (MAX_EXECUTION_RETRIES=3)
- [x] Error feedback to LLM for automatic code repair
- [x] Sub-agent self-healing (recursive error recovery)
- [x] `@safe_sub_agent` decorator for simplified syntax

## Usage Examples

```bash
# Chat
uv run python upa.py "你好"
# > 你好！有什么我可以帮你的吗？

# Math
uv run python upa.py "1+1等于几"
# > 2

# Logic
uv run python upa.py "帮我排序这些数字: 3,1,4,1,5"
# > [1, 1, 3, 4, 5]

# DateTime
uv run python upa.py "今天是星期几"
# > Tuesday

# With timing
uv run python upa.py --timing "计算 100 的阶乘"
# ⏱  Timing Report
#   LLM Generate     15234.5ms [███████████████████░] 100.0%
#   Code Extract         0.1ms [░░░░░░░░░░░░░░░░░░░░]   0.0%
#   Security Check       0.2ms [░░░░░░░░░░░░░░░░░░░░]   0.0%
#   Code Execute         0.1ms [░░░░░░░░░░░░░░░░░░░░]   0.0%
#   Total            15235.1ms
```

## Testing

```bash
# List all available test suites
uv run python -m benchmarks --list-suites

# Run core UPA benchmarks
uv run python -m benchmarks core

# Run semantic-logic hybrid benchmarks
uv run python -m benchmarks semantic

# Filter by complexity (core suite)
uv run python -m benchmarks core -c 中等

# Filter by task type (semantic suite)
uv run python -m benchmarks semantic -t "翻译+逻辑"

# Limit test count
uv run python -m benchmarks core -n 10

# Export results to JSON
uv run python -m benchmarks core -j results.json

# List test cases in a suite
uv run python -m benchmarks core --list

# Save detailed execution logs (for failed test analysis)
uv run python -m benchmarks core --save-details core-details.json
uv run python -m benchmarks semantic --save-details semantic-details.json
```

## Configuration

Edit `.env` file:

```bash
DASHSCOPE_URL=https://coding.dashscope.aliyuncs.com/v1
DASHSCOPE_API_KEY=your-api-key
DASHSCOPE_MODEL=qwen3.5-plus
```

## Security

Current MVP includes:
- AST static analysis to block dangerous imports (os, subprocess, sys, etc.)
- Blocked functions: eval, exec, compile, open, getattr, etc.
- Blocked dangerous attributes: __subclasses__, __class__, __globals__, etc.

## Architecture

```
User Query → Main LLM → Python Code → AST Check → Execute → stdout
                                      ↓ (error)
                                 Self-Heal Loop
                                      ↓ (semantic tasks)
                              ask_sub_agent() → Sub LLM → Code → Execute → stdout
                                                            ↓ (error)
                                                       Sub Self-Heal Loop
```

**Key Features**:
- **Always-Code**: All outputs are executable Python code
- **Recursive Self-Healing**: Both main and sub-agents auto-repair on errors
- **Decorator Pattern**: `@safe_sub_agent("query")` simplifies semantic calls

## Benchmark Results

| Complexity | Tests | Pass Rate | Avg Time |
|------------|-------|-----------|----------|
| Simple     | 5     | 100%      | ~9s      |
| Medium     | 8     | 100%      | ~26s     |
| Complex    | 7     | 100%      | ~20s     |
| Edge Cases | 5     | 100%      | ~41s     |

## License

MIT
