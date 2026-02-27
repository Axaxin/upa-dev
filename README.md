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

# Configure API keys (copy .env.example to .env and fill in your keys)
cp .env.example .env

# Run UPA
uv run python upa.py "你的问题"

# Show timing report
uv run python upa.py --timing "1+1等于几"

# Show generated code
uv run python upa.py --show-code "帮我排序: 3,1,4,1,5"

# Use specific provider and model
uv run python upa.py --provider dashscope --model qwen3.5-plus "你的问题"

# Set default provider and model
uv run python upa.py --config dashscope qwen3.5-plus
```

## Project Structure

```
upa-dev/
├── upa.py              # Main CLI implementation (MVP + Planner)
├── benchmarks/         # Unified benchmark framework
│   ├── cli.py          # Benchmark CLI entry point
│   ├── runner.py       # Core execution engine
│   ├── display.py      # Terminal display utilities
│   └── suites/         # Test suite definitions
│       ├── base.py     # Base data structures and registry
│       ├── core_upa.py # Core UPA functionality tests (43 tests)
│       ├── semantic.py # Semantic-Logic hybrid tests (17 tests)
│       ├── classic.py  # Classic LLM benchmark problems (23 tests)
│       ├── mmlu.py     # MMLU academic knowledge tests (147 tests)
│       └── planner.py  # Planner validation tests (18 tests)
├── tests/              # Unit tests for framework
│   ├── test_planner.py # Planner module unit tests
│   └── test_runner.py  # Benchmark runner unit tests
├── benchmark_upa.py    # DEPRECATED: Use -m benchmarks core
├── benchmark_semantic.py # DEPRECATED: Use -m benchmarks semantic
├── DESIGN.md           # Architecture design document
├── CLAUDE.md           # Project guidance for Claude Code
├── .env.example        # Configuration template
└── .env                # API configuration (not in git)
```

## Implementation Status

### ✅ Phase 1: MVP (Complete)
- [x] Base Orchestrator with "Always-Code" system prompt
- [x] Local sandbox with stdout capture
- [x] AST-based security guardrails
- [x] CLI with timing support

### ✅ Phase 2: Semantic Integration (Complete)
- [x] `ask_semantic()` function for semantic tasks
- [x] Multi-level LLM calling (main for code, sub for semantics)
- [x] Multi-provider support (DashScope, Cloudflare)

### ✅ Phase 3: Self-Healing (Complete)
- [x] Auto-heal on execution errors (MAX_EXECUTION_RETRIES=3)
- [x] Error feedback to LLM for automatic code repair
- [x] `@safe_semantic` decorator for simplified syntax

### ✅ Phase 4: CLI Enhancements (Complete)
- [x] `--model` flag to override provider's default model
- [x] `--config` flag to set default provider and model
- [x] `.env.example` template for easy configuration

### ✅ Phase 5: Planner Architecture (Complete)
- [x] Dynamic prompt construction based on query analysis
- [x] Task decomposition for complex multi-step problems
- [x] Intent classification (simple_chat, computation, semantic, hybrid, multi_step)
- [x] Dynamic tool selection (ask_semantic, web_search)
- [x] Benchmark framework integration with Planner tracking
- [x] Planner validation test suite with automated accuracy reporting

### 🚧 Phase 6: Complexity-Aware Coder Selection (Planned)
- [ ] Dynamic Coder model selection based on Planner's complexity assessment
- [ ] Reasoning models (o3-mini, R1) for complex tasks
- [ ] Fast models (grok-code-fast-1) for simple/trivial tasks
- [ ] Cost-Quality-Speed balance optimization

### Phase 7: Self-Check Mechanism (Planned)
- [ ] Code-generated assertions for logic validation
- [ ] Type checking and range validation
- [ ] Multi-version code comparison for critical tasks

### Phase 8: Code Memory & Caching (Planned)
- [ ] Code caching with vector similarity matching
- [ ] Code evolution and self-improvement
- [ ] Redis/Postgres storage for successful code

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

# Use specific provider
uv run python upa.py --provider dashscope "你好"

# Override model for a request
uv run python upa.py --provider cloudflare --model grok-4 "你好"

# Set default provider and model (updates .env)
uv run python upa.py --config dashscope qwen3.5-plus

# List all providers with their models
uv run python upa.py --list-providers

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

# Run classic LLM benchmarks
uv run python -m benchmarks classic

# Run MMLU academic knowledge benchmarks
uv run python -m benchmarks mmlu

# Filter by complexity (core suite)
uv run python -m benchmarks core -c 中等
uv run python -m benchmarks mmlu -c 复杂

# Filter by task type (semantic suite)
uv run python -m benchmarks semantic -t "翻译+逻辑"

# Limit test count
uv run python -m benchmarks core -n 10

# Specify worker count (parallelism)
uv run python -m benchmarks core -w 8

# Export results to JSON
uv run python -m benchmarks core -j results.json

# List test cases in a suite
uv run python -m benchmarks core --list
uv run python -m benchmarks mmlu --list

# Save detailed execution logs (auto-saved, or use --no-details to disable)
uv run python -m benchmarks core --save-details core-details.json
uv run python -m benchmarks semantic --save-details semantic-details.json

# Disable LLM validation for failed tests
uv run python -m benchmarks core --no-llm-validation

# Run Planner validation tests (Phase 5)
uv run python -m benchmarks planner

# Run framework unit tests
uv run pytest tests/ -v
```

## Configuration

### Quick Setup

```bash
# Copy the example configuration
cp .env.example .env

# Edit .env and fill in your API keys
# Then run
uv run python upa.py "你好"
```

### CLI Configuration

```bash
# Set default provider and model permanently
uv run python upa.py --config <provider> <model>

# Example: Set DashScope as default
uv run python upa.py --config dashscope qwen3.5-plus
```

### Environment Variables

Edit `.env` file:

```bash
# Default provider (dashscope | cloudflare)
UPA_PROVIDER=dashscope

# Web Search (true | false) - enables fact-checking via DuckDuckGo
UPA_WEB_SEARCH=true

# Planner Configuration (Phase 5)
UPA_PLANNER=true
# UPA_PLANNER_MODEL=qwen-turbo  # Optional: use faster model for planning

# DashScope Configuration (阿里云 Qwen/Kimi)
DASHSCOPE_URL=https://coding.dashscope.aliyuncs.com/v1
DASHSCOPE_API_KEY=your-api-key
DASHSCOPE_MODEL=kimi-k2.5

# Cloudflare Gateway + Grok Configuration
CLOUDFLARE_URL=https://gateway.ai.cloudflare.com/v1/YOUR_ACCOUNT/gemini/compat
CLOUDFLARE_API_KEY=your-api-key
CLOUDFLARE_MODEL=grok/grok-4-1-fast-non-reasoning
```

## Security

Current MVP includes:
- AST static analysis to block dangerous imports (os, subprocess, sys, etc.)
- Blocked functions: eval, exec, compile, open, getattr, etc.
- Blocked dangerous attributes: __subclasses__, __class__, __globals__, etc.

## Architecture

```
User Query → Planner Analysis → Dynamic Prompt Construction
                                      ↓
                            Main LLM (Coder) → Python Code → AST Check → Execute → stdout
                                      ↓ (error)
                                 Self-Heal Loop
                                      ↓ (semantic tasks)
                              ask_sub_agent() → Sub LLM → Code → Execute → stdout
                                                            ↓ (error)
                                                       Sub Self-Heal Loop
                                      ↓ (fact-checking)
                              web_search() → DuckDuckGo → Results
```

**Key Features**:
- **Always-Code**: All outputs are executable Python code
- **Planner (Phase 5)**: Dynamic prompt construction with task decomposition
- **Recursive Self-Healing**: Both main and sub-agents auto-repair on errors
- **Decorator Pattern**: `@safe_sub_agent("query")` simplifies semantic calls
- **Multi-Provider**: Support for DashScope (Qwen/Kimi), Cloudflare (Grok), and more
- **Flexible CLI**: `--model` and `--config` for easy provider/model management
- **Benchmark Integration**: Full Planner tracking in benchmark results

**Planned Features**:
- **Complexity-Aware Coder (Phase 6)**: Dynamic model selection balancing cost/quality/speed
- **Self-Check Mechanism (Phase 7)**: Generated code includes assertions for logic validation
- **Code Memory (Phase 8)**: Vector-based code caching and evolution

## Benchmark Results

### Test Suites

| Suite | Tests | Description |
|-------|-------|-------------|
| **core** | 43 | Core UPA functionality (code generation & execution) |
| **semantic** | 17 | Sub-agent integration (semantic-logic hybrid) |
| **classic** | 23 | Classic LLM problems (GSM8K, HumanEval, MATH) |
| **mmlu** | 147 | Academic knowledge across STEM, humanities, social sciences |

### Recent Results (DashScope + kimi-k2.5)

```
📊 Overall Statistics
Tests Run:       3
Correct Results: 3/3 (100.0%)
Code Generated:  3/3 (100.0%)
Execution OK:    3/3 (100.0%)

🧠 Planner Statistics (Phase 5)
Planner Enabled:  3/3 (100.0%)
Intent Distribution:
  simple_chat     ████░░░░░░░░  1/3
  computation     ████░░░░░░░░  1/3
  Complexity Distribution:
  trivial         ████████████  3/3
Skip Planning:    3/3 (100.0%)
Planner Timing:
  Mean:   4465ms
  Median: 4465ms
```

## License

MIT
