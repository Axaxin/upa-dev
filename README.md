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
├── benchmark_upa.py    # Performance benchmark suite
├── test_upa.py         # Functional test suite
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
# Run functional tests
uv run python test_upa.py

# Run performance benchmarks
uv run python benchmark_upa.py

# Run specific complexity
uv run python benchmark_upa.py -c 中等
uv run python benchmark_upa.py -c 复杂
uv run python benchmark_upa.py -c 边缘案例

# Export benchmark results
uv run python benchmark_upa.py -j results.json
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
User Query → LLM (Always-Code Prompt) → Python Code → AST Check → Execute → stdout
                                      ↓ (blocked)
                                  Security Violation
```

## Benchmark Results

| Complexity | Tests | Pass Rate | Avg Time |
|------------|-------|-----------|----------|
| Simple     | 5     | 100%      | ~9s      |
| Medium     | 8     | 100%      | ~26s     |
| Complex    | 7     | 100%      | ~20s     |
| Edge Cases | 5     | 100%      | ~41s     |

## License

MIT
