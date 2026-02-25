"""
MMLU (Massive Multitask Language Understanding) Test Suite

This suite contains multiple-choice questions from various academic subjects.
The LLM is asked to reason through the question and output the correct answer.

Reference: https://arxiv.org/abs/2009.03300
Dataset: https://huggingface.co/datasets/cais/mmlu
"""

from benchmarks.suites.base import (
    TestCase, TestSuite, Complexity, register_suite
)


# ============================================================================
# MMLU Sample Questions (Embedded for offline use)
# ============================================================================

# STEM Subjects
MMLU_STEM_SAMPLES: list[TestCase] = [
    TestCase(
        name="Elementary Mathematics: Addition",
        query="""问题：23 + 45 等于多少？
A. 68
B. 78
C. 58
D. 88

请用 Python 代码计算并输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="A",
        description="Basic addition"
    ),

    TestCase(
        name="Elementary Mathematics: Multiplication",
        query="""问题：12 × 8 等于多少？
A. 86
B. 96
C. 106
D. 116

请用 Python 代码计算并输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Basic multiplication"
    ),

    TestCase(
        name="Algebra: Linear Equation",
        query="""问题：如果 3x + 7 = 22，那么 x 等于多少？
A. 3
B. 4
C. 5
D. 6

请用 Python 代码求解并输出正确选项的字母。""",
        complexity=Complexity.MEDIUM,
        expect_contains="C",
        description="Solve linear equation"
    ),

    TestCase(
        name="Geometry: Triangle Area",
        query="""问题：一个三角形的底是 10，高是 6，它的面积是多少？
A. 30
B. 60
C. 15
D. 45

请用 Python 代码计算并输出正确选项的字母。""",
        complexity=Complexity.MEDIUM,
        expect_contains="A",
        description="Triangle area formula: (base * height) / 2"
    ),

    TestCase(
        name="Physics: Kinematics",
        query="""问题：一个物体从静止开始以 5 m/s² 的加速度运动，3 秒后的速度是多少？
A. 10 m/s
B. 15 m/s
C. 20 m/s
D. 25 m/s

请用 Python 代码计算并输出正确选项的字母。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="v = v0 + at, v0=0, a=5, t=3"
    ),

    TestCase(
        name="Chemistry: Atomic Number",
        query="""问题：碳元素的原子序数是多少？
A. 4
B. 6
C. 8
D. 12

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Basic chemistry knowledge"
    ),

    TestCase(
        name="Computer Science: Binary",
        query="""问题：二进制数 1011 等于十进制的多少？
A. 9
B. 10
C. 11
D. 12

请用 Python 代码计算并输出正确选项的字母。""",
        complexity=Complexity.MEDIUM,
        expect_contains="C",
        description="Binary to decimal conversion"
    ),

    TestCase(
        name="Statistics: Mean",
        query="""问题：数据集 [5, 8, 12, 15, 20] 的平均值是多少？
A. 10
B. 11
C. 12
D. 13

请用 Python 代码计算并输出正确选项的字母。""",
        complexity=Complexity.MEDIUM,
        expect_contains="C",
        description="Calculate arithmetic mean"
    ),
]


# Humanities
MMLU_HUMANITIES_SAMPLES: list[TestCase] = [
    TestCase(
        name="History: Renaissance",
        query="""问题：文艺复兴运动起源于哪个国家？
A. 法国
B. 英国
C. 意大利
D. 西班牙

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="C",
        description="Historical knowledge"
    ),

    TestCase(
        name="Literature: Shakespeare",
        query="""问题：剧本《哈姆雷特》的作者是谁？
A. 狄更斯
B. 莎士比亚
C. 歌德
D. 托尔斯泰

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Literature knowledge"
    ),

    TestCase(
        name="Philosophy: Logic",
        query="""问题："所有的人都会死，苏格拉底是人，所以苏格拉底会死。"这是什么推理？
A. 归纳推理
B. 演绎推理
C. 类比推理
D. 反向推理

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Logical reasoning types"
    ),

    TestCase(
        name="Geography: Capitals",
        query="""问题：澳大利亚的首都是哪个城市？
A. 悉尼
B. 墨尔本
C. 堪培拉
D. 珀斯

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="C",
        description="Geographic knowledge"
    ),
]


# Social Sciences
MMLU_SOCIAL_SAMPLES: list[TestCase] = [
    TestCase(
        name="Economics: Supply and Demand",
        query="""问题：当商品价格上升时，通常会出现什么情况？
A. 需求量增加
B. 需求量减少
C. 供给量减少
D. 市场均衡

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Basic economics principle"
    ),

    TestCase(
        name="Psychology: Classical Conditioning",
        query="""问题：巴甫洛夫的狗实验研究的是什么类型的条件作用？
A. 操作性条件作用
B. 经典性条件作用
C. 观察学习
D. 认知学习

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Psychology concepts"
    ),
]


# Complex / Advanced
MMLU_ADVANCED_SAMPLES: list[TestCase] = [
    TestCase(
        name="Calculus: Derivative",
        query="""问题：函数 f(x) = x³ 在 x=2 处的导数值是多少？
A. 6
B. 8
C. 12
D. 16

请用 Python 代码计算 f'(x) = 3x² 在 x=2 的值，并输出正确选项的字母。""",
        complexity=Complexity.COMPLEX,
        expect_contains="C",
        description="Calculus derivative"
    ),

    TestCase(
        name="Probability: Combinations",
        query="""问题：从 10 个人中选 3 个人，有多少种选法？
A. 90
B. 100
C. 120
D. 720

请用 Python 的 math.comb 或组合公式计算并输出正确选项的字母。""",
        complexity=Complexity.COMPLEX,
        expect_contains="C",
        description="C(10,3) = 120"
    ),

    TestCase(
        name="Physics: Energy",
        query="""问题：一个 2kg 的物体以 10m/s 的速度运动，它的动能是多少？(KE = 1/2 mv²)
A. 50 J
B. 100 J
C. 150 J
D. 200 J

请用 Python 代码计算并输出正确选项的字母。""",
        complexity=Complexity.COMPLEX,
        expect_contains="B",
        description="Kinetic energy calculation"
    ),

    TestCase(
        name="Computer Science: Big O",
        query="""问题：对于包含 n 个元素的列表，二分查找的时间复杂度是多少？
A. O(n)
B. O(n²)
C. O(log n)
D. O(1)

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.COMPLEX,
        expect_contains="C",
        description="Algorithm complexity analysis"
    ),

    TestCase(
        name="Number Theory: Prime",
        query="""问题：在 100 到 110 之间有多少个质数？
A. 1 个
B. 2 个
C. 3 个
D. 4 个

请用 Python 代码找出 100-110 之间的质数数量，并输出正确选项的字母。""",
        complexity=Complexity.COMPLEX,
        expect_contains="D",
        description="Primes: 101, 103, 107, 109"
    ),
]


# ============================================================================
# Optional: Load from HuggingFace Dataset
# ============================================================================

# Available MMLU subjects for reference
MMLU_SUBJECTS = [
    'abstract_algebra', 'anatomy', 'astronomy', 'business_ethics',
    'clinical_knowledge', 'college_biology', 'college_chemistry',
    'college_computer_science', 'college_mathematics', 'college_medicine',
    'college_physics', 'computer_security', 'conceptual_physics',
    'econometrics', 'electrical_engineering', 'elementary_mathematics',
    'formal_logic', 'global_facts', 'high_school_biology',
    'high_school_chemistry', 'high_school_computer_science',
    'high_school_european_history', 'high_school_geography',
    'high_school_government_and_politics', 'high_school_macroeconomics',
    'high_school_mathematics', 'high_school_microeconomics',
    'high_school_physics', 'high_school_psychology', 'high_school_statistics',
    'high_school_us_history', 'high_school_world_history', 'human_aging',
    'human_sexuality', 'international_law', 'jurisprudence',
    'logical_fallacies', 'machine_learning', 'management', 'marketing',
    'medical_genetics', 'miscellaneous', 'moral_disputes',
    'moral_scenarios', 'nutrition', 'philosophy', 'prehistory',
    'professional_accounting', 'professional_law', 'professional_medicine',
    'professional_psychology', 'public_relations', 'security_studies',
    'sociology', 'us_foreign_policy', 'virology', 'world_religions'
]


def load_mmlu_from_huggingface(
    subjects: list[str] | None = None,
    split: str = "test",
    limit: int | None = None
) -> list[TestCase]:
    """Load MMLU questions from HuggingFace dataset.

    Args:
        subjects: List of MMLU subject names (e.g., ['elementary_mathematics', 'college_physics'])
                 See MMLU_SUBJECTS for available options. If None, loads 'all'.
        split: Dataset split ('test', 'validation', 'dev')
        limit: Maximum number of questions per subject

    Returns:
        List of TestCase objects

    Examples:
        # Load 50 elementary math questions
        cases = load_mmlu_from_huggingface(subjects=['elementary_mathematics'], limit=50)

        # Load from multiple subjects
        cases = load_mmlu_from_huggingface(subjects=['high_school_mathematics', 'college_physics'])

        # Load all subjects (not recommended - too large)
        cases = load_mmlu_from_huggingface(subjects=['all'])
    """
    import os
    # Use mirror for faster access in China
    os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

    # Use HF Token for faster downloads (set via environment variable)
    # export HF_TOKEN=your_token_here
    # or set in .env file
    hf_token = os.environ.get('HF_TOKEN')
    if hf_token:
        os.environ['HF_TOKEN'] = hf_token

    try:
        from datasets import load_dataset
    except ImportError:
        print("Warning: datasets library not installed. Install with: pip install datasets")
        return []

    try:
        cases = []

        # Load each subject separately
        if subjects:
            for subject_name in subjects:
                dataset = load_dataset("cais/mmlu", subject_name)
                data = dataset[split]

                for i, item in enumerate(data):
                    if limit and i >= limit:
                        break

                    # Format question with choices
                    question = item['question']
                    choices = item['choices']

                    # Map answer index to letter
                    answer_idx = item['answer'] if isinstance(item['answer'], int) else 0
                    answer_letter = chr(ord('A') + answer_idx)

                    # Build query
                    query = f"""问题：{question}
A. {choices[0]}
B. {choices[1]}
C. {choices[2]}
D. {choices[3]}

请用 Python 代码推理并输出正确选项的字母（A/B/C/D）。"""

                    # Determine complexity based on question length
                    if len(question) < 100:
                        complexity = Complexity.SIMPLE
                    elif len(question) < 200:
                        complexity = Complexity.MEDIUM
                    else:
                        complexity = Complexity.COMPLEX

                    cases.append(TestCase(
                        name=f"MMLU_{subject_name}_{i}",
                        query=query,
                        complexity=complexity,
                        expect_contains=answer_letter,
                        description=f"Subject: {subject_name}"
                    ))
        else:
            # Load 'all' config (loads everything - use with caution)
            dataset = load_dataset("cais/mmlu", "all")
            data = dataset[split]

            for i, item in enumerate(data):
                if limit and i >= limit:
                    break

                question = item['question']
                choices = item['choices']
                answer_idx = item['answer'] if isinstance(item['answer'], int) else 0
                answer_letter = chr(ord('A') + answer_idx)

                query = f"""问题：{question}
A. {choices[0]}
B. {choices[1]}
C. {choices[2]}
D. {choices[3]}

请用 Python 代码推理并输出正确选项的字母（A/B/C/D）。"""

                if len(question) < 100:
                    complexity = Complexity.SIMPLE
                elif len(question) < 200:
                    complexity = Complexity.MEDIUM
                else:
                    complexity = Complexity.COMPLEX

                cases.append(TestCase(
                    name=f"MMLU_all_{i}",
                    query=query,
                    complexity=complexity,
                    expect_contains=answer_letter,
                    description="Subject: all"
                ))

        return cases

    except Exception as e:
        print(f"Warning: Failed to load MMLU from HuggingFace: {e}")
        return []


# ============================================================================
# Register the MMLU Suite
# ============================================================================

MMLU_CASES = (
    MMLU_STEM_SAMPLES +
    MMLU_HUMANITIES_SAMPLES +
    MMLU_SOCIAL_SAMPLES +
    MMLU_ADVANCED_SAMPLES
)


@register_suite
def _mmlu_suite() -> TestSuite:
    """MMLU (Massive Multitask Language Understanding) Test Suite."""
    return TestSuite(
        name="mmlu",
        description="MMLU: Multiple-choice academic questions across STEM, humanities, and social sciences",
        version="1.0.0",
        cases=MMLU_CASES,
    )
