# UPA Benchmark Framework

模块化基准测试系统，支持灵活添加新的测试集。

## 目录结构

```
benchmarks/
├── __init__.py          # 模块入口
├── __main__.py          # python -m benchmarks 入口
├── cli.py               # CLI 参数解析和路由
├── runner.py            # 核心执行引擎
├── display.py           # 终端显示工具
├── suites/
│   ├── __init__.py      # 导出所有数据类
│   ├── base.py          # 基础数据类 (TestCase, TestSuite, 等)
│   ├── core_upa.py      # 核心 UPA 测试集 (43 个测试)
│   └── semantic.py      # 语义混合测试集 (17 个测试)
└── examples/
    ├── __init__.py
    └── custom_suite.py  # 自定义测试集示例
```

## 快速开始

```bash
# 列出所有可用测试集
uv run python -m benchmarks --list-suites

# 运行核心测试集
uv run python -m benchmarks core

# 运行语义混合测试集
uv run python -m benchmarks semantic

# 查看帮助
uv run python -m benchmarks --help
```

## CLI 参数

```
positional arguments:
  suite                  测试集名称 (core, semantic, 或自定义)

options:
  -h, --help            显示帮助
  -c, --complexity      按复杂度过滤 (core 专用)
  -t, --type            按任务类型过滤 (semantic 专用)
  -n, --limit N         限制测试数量
  -l, --list            列出测试集内的测试用例
  --list-suites         列出所有可用测试集
  -j, --json FILE       导出结果到 JSON
  -w, --workers N       并发 worker 数量 (默认: 4)
```

## 创建自定义测试集

### 方法 1: 创建独立的 Python 模块

```python
# benchmarks/suites/my_custom.py
from benchmarks.suites.base import (
    TestCase, TestSuite, Complexity, register_suite
)

MY_CASES: list[TestCase] = [
    TestCase(
        "测试名称",
        "查询文本",
        Complexity.SIMPLE,
        expect_numeric=(42, 0)
    ),
    # 添加更多测试...
]

@register_suite
def _my_custom_suite() -> TestSuite:
    return TestSuite(
        name="my_custom",
        description="我的自定义测试集",
        version="1.0.0",
        cases=MY_CASES,
    )
```

运行:
```bash
uv run python -m benchmarks my_custom
```

### 方法 2: 使用语义混合测试 (HybridTest)

```python
from benchmarks.suites.base import (
    HybridTest, TestSuite, TaskType, register_suite
)

HYBRID_CASES: list[HybridTest] = [
    HybridTest(
        "翻译测试",
        "用 ask_sub_agent 把 'Hello' 翻译成中文",
        TaskType.TRANSLATE_LOGIC,
        "Translation example",
        expected_contains="你好"
    ),
]

@register_suite
def _my_hybrid_suite() -> TestSuite:
    return TestSuite(
        name="my_hybrid",
        description="我的语义混合测试集",
        version="1.0.0",
        cases=HYBRID_CASES,
    )
```

## 测试用例类型

### TestCase (基础测试)

用于测试核心 UPA 功能：

```python
TestCase(
    name="测试名称",           # 显示名称
    query="查询文本",          # 发送给 UPA 的查询
    complexity=Complexity.SIMPLE,  # 复杂度
    expect_contains="文本",    # 期望输出包含的文本
    expect_pattern=r"\d+",     # 期望匹配的正则表达式
    expect_numeric=(42, 0),    # 期望数值 (值, 容差)
    description="描述",
)
```

### HybridTest (语义混合测试)

用于测试 sub-agent 集成：

```python
HybridTest(
    name="测试名称",
    query="查询文本",
    task_type=TaskType.TRANSLATE_LOGIC,  # 任务类型
    description="描述",
    expected_contains="文本",    # 期望输出包含的文本
    expected_pattern=r"\d+",     # 期望匹配的正则表达式
    expected_numeric=(42, 0),    # 期望数值 (值, 容差)
)
```

## 内置测试集

### core (核心 UPA)

测试基本的代码生成和执行能力。

- **测试数量**: 43
- **复杂度分级**: 简单、中等、复杂、边缘案例
- **测试类型**: 数学运算、字符串处理、数据结构、算法等

### semantic (语义混合)

测试语义理解 (sub-agent) 与逻辑处理的混合任务。

- **测试数量**: 17
- **任务类型**: 翻译+逻辑、总结+分析、情感+计算、提取+处理、递归调用

## 示例

```bash
# 运行简单复杂度的测试
uv run python -m benchmarks core -c 简单

# 运行翻译类测试
uv run python -m benchmarks semantic -t "翻译+逻辑"

# 运行 5 个测试并导出结果
uv run python -m benchmarks core -n 5 -j results.json

# 使用 8 个并发 worker
uv run python -m benchmarks core -w 8
```
