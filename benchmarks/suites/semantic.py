"""
Semantic-Logic Hybrid Test Suite
Tests tasks combining semantic understanding with logic processing.
"""

from benchmarks.suites.base import (
    HybridTest, TestSuite, TaskType, register_suite
)


# =============================================================================
# Hybrid Test Cases (extracted from benchmark_semantic.py)
# =============================================================================

HYBRID_CASES: list[HybridTest] = [
    # ---- Translation + Logic ----
    HybridTest(
        "翻译后计数",
        "把 'Hello World' 翻译成中文，然后计算翻译结果的字符数量。输出格式：print(字符数)",
        TaskType.TRANSLATE_LOGIC,
        "Translation followed by character counting",
        expected_numeric=(5, 2)  # "你好，世界" ~5 chars
    ),
    HybridTest(
        "多语言连接",
        "用 ask_semantic 把 'Hello' 翻译成中文，把 'World' 翻译成中文，然后用空格连接输出。输出格式：print('你好 世界')",
        TaskType.TRANSLATE_LOGIC,
        "Multiple translations concatenated",
        expected_contains="你好"
    ),
    HybridTest(
        "翻译长度比较",
        "将 'I love programming' 翻译成中文。如果中文译文更长输出'中文更长'，否则输出'英文更长'",
        TaskType.TRANSLATE_LOGIC,
        "Compare original and translated lengths",
        expected_contains="英文更长"
    ),

    # ---- Summary + Analysis ----
    HybridTest(
        "摘要后提取关键词",
        "用 ask_semantic 总结 'Python是一种广泛使用的高级编程语言'，然后从摘要中提取所有中文词汇的数量。输出格式：print(数量)",
        TaskType.SUMMARIZE_ANALYZE,
        "Summarize then extract keywords",
        expected_numeric=(3, 5)
    ),
    HybridTest(
        "情感分类统计",
        "分析以下句子的情感：'今天太棒了'、'真倒霉'、'还不错'，然后统计积极情感的句子数量。输出格式：print(数量)",
        TaskType.SENTIMENT_CALC,
        "Sentiment analysis and counting",
        expected_numeric=(2, 1)  # 2 positive: 太棒了, 还不错
    ),
    HybridTest(
        "文本摘要评分",
        "总结这段话：'机器学习是人工智能的一个分支。它使计算机能够在没有明确编程的情况下学习。'，然后给摘要打分（每字1分）。输出格式：print(分数)",
        TaskType.SUMMARIZE_ANALYZE,
        "Summarize and score by length",
        expected_numeric=(20, 15)
    ),

    # ---- Sentiment + Calculation ----
    HybridTest(
        "情感加权计算",
        "分析'我很开心'的情感（积极=10分，消极=0分），然后分数乘以2输出。格式：print(20)",
        TaskType.SENTIMENT_CALC,
        "Sentiment score multiplied",
        expected_numeric=(20, 0)
    ),
    HybridTest(
        "多句情感平均分",
        "分析这3句：'天气真好'、'太差了'、'很喜欢'。积极=10分，消极=0分。计算3句的平均分（保留整数）。输出格式：print(平均分)",
        TaskType.SENTIMENT_CALC,
        "Average sentiment score",
        expected_numeric=(5, 1)
    ),
    HybridTest(
        "情感判断转换",
        "判断'今天天气真好'的情感，如果是积极输出1，消极输出0。输出格式：print(1或0)",
        TaskType.SENTIMENT_CALC,
        "Sentiment to binary conversion",
        expected_numeric=(1, 0)
    ),

    # ---- Extract + Process ----
    HybridTest(
        "提取数字求和",
        "从'我有3个苹果和5个橙子'中提取所有数字并求和。输出格式：print(8)",
        TaskType.EXTRACT_PROCESS,
        "Extract numbers and sum",
        expected_numeric=(8, 0)
    ),
    HybridTest(
        "提取邮箱验证",
        "用正则表达式判断'联系我@example.com'是否是有效邮箱格式，如果是输出'valid'，否则输出'invalid'",
        TaskType.EXTRACT_PROCESS,
        "Extract and validate email",
        expected_contains="valid"
    ),
    HybridTest(
        "提取排序",
        "从'分数：85, 92, 78, 95'中提取所有数字，排序后输出。输出格式：print([78,85,92,95])",
        TaskType.EXTRACT_PROCESS,
        "Extract and sort numbers",
        expected_pattern=r"78.*85.*92.*95"
    ),

    # ---- Recursive / Multi-step ----
    HybridTest(
        "链式翻译",
        "用 ask_semantic 把'你好'翻译成英文，再用 ask_semantic 把结果翻译回中文。输出格式：print(翻译结果)",
        TaskType.RECURSIVE,
        "Chain translation (zh->en->zh)",
        expected_contains="你好"
    ),
    HybridTest(
        "嵌套语义调用",
        "用 ask_semantic 问：'5乘以3等于几'，打印返回的答案。输出格式：print(15)",
        TaskType.RECURSIVE,
        "Nested semantic returning number",
        expected_numeric=(15, 1)
    ),
    HybridTest(
        "三级处理链",
        "1) 翻译'Hello'成中文 2) 统计字数 3) 乘以3。只输出最终结果数字。输出格式：print(6)",
        TaskType.RECURSIVE,
        "Three-step processing chain",
        expected_numeric=(6, 1)  # "你好"(2) * 3 = 6
    ),

    # ---- Complex Real-world Scenarios ----
    HybridTest(
        "评论分析系统",
        "分析评论'这个产品很棒，但价格有点贵'。规则：包含'很棒'等积极词+40分，包含'贵'等消极词-20分，基础分50分。输出最终评分。输出格式：print(70)",
        TaskType.SENTIMENT_CALC,
        "Complex sentiment scoring",
        expected_numeric=(70, 20)
    ),
    HybridTest(
        "多语言处理",
        "将'How are you?'翻译成中文，然后翻译成法语（用子Agent），统计总共调用了几次子Agent。输出格式：print(2)",
        TaskType.RECURSIVE,
        "Multi-language processing",
        expected_contains="2"
    ),
]


# =============================================================================
# Register Test Suite
# =============================================================================

@register_suite
def _register_semantic_suite() -> TestSuite:
    """Register the semantic-logic hybrid test suite."""
    return TestSuite(
        name="semantic",
        description="Semantic-Logic hybrid tests (sub-agent integration)",
        version="1.0.0",
        cases=HYBRID_CASES,
    )


# Export for direct access
__all__ = ["HYBRID_CASES"]
