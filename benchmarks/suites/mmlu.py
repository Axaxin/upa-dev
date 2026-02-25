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
# Additional STEM Subjects
# ============================================================================

MMLU_BIOLOGY_SAMPLES: list[TestCase] = [
    TestCase(
        name="Biology: Cell Structure",
        query="""问题：植物细胞和动物细胞的主要区别是什么？
A. 植物细胞没有细胞核
B. 植物细胞有细胞壁和叶绿体
C. 动物细胞有细胞壁
D. 植物细胞没有线粒体

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Cell biology basics"
    ),

    TestCase(
        name="Biology: DNA",
        query="""问题：DNA的双螺旋结构是由谁发现的？
A. 达尔文
B. 孟德尔
C. 沃森和克里克
D. 巴斯德

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="C",
        description="History of biology"
    ),

    TestCase(
        name="Biology: Photosynthesis",
        query="""问题：光合作用的主要产物是什么？
A. 二氧化碳和水
B. 葡萄糖和氧气
C. 蛋白质和脂肪
D. 淀粉和氮气

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Plant biology"
    ),
]

MMLU_PHYSICS_SAMPLES: list[TestCase] = [
    TestCase(
        name="Physics: Newton's Laws",
        query="""问题：牛顿第一定律也被称为？
A. 万有引力定律
B. 惯性定律
C. 作用力与反作用力定律
D. 动量守恒定律

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Classical mechanics"
    ),

    TestCase(
        name="Physics: Light",
        query="""问题：光在真空中的传播速度约为多少？
A. 3×10⁶ m/s
B. 3×10⁸ m/s
C. 3×10¹⁰ m/s
D. 3×10⁵ m/s

请用 Python 代码验证并输出正确选项的字母。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Speed of light"
    ),

    TestCase(
        name="Physics: Gravity",
        query="""问题：地球表面的重力加速度约为多少？
A. 5 m/s²
B. 9.8 m/s²
C. 15 m/s²
D. 20 m/s²

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Gravitational acceleration"
    ),

    TestCase(
        name="Physics: Thermodynamics",
        query="""问题：热力学第二定律说明热量会自发地从？
A. 低温物体传向高温物体
B. 高温物体传向低温物体
C. 两物体温度相同才会传热
D. 热量不会传递

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Thermodynamics laws"
    ),
]

MMLU_CHEMISTRY_SAMPLES: list[TestCase] = [
    TestCase(
        name="Chemistry: Periodic Table",
        query="""问题：元素周期表中，原子序数为1的元素是？
A. 氦
B. 氢
C. 锂
D. 氧

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Periodic table basics"
    ),

    TestCase(
        name="Chemistry: Molecules",
        query="""问题：水分子(H₂O)中包含几个氢原子？
A. 1 个
B. 2 个
C. 3 个
D. 4 个

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Molecular structure"
    ),

    TestCase(
        name="Chemistry: pH Scale",
        query="""问题：pH值为7的溶液是？
A. 酸性
B. 碱性
C. 中性
D. 强酸性

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="C",
        description="Acid-base chemistry"
    ),

    TestCase(
        name="Chemistry: Reaction",
        query="""问题：燃烧属于什么类型的化学反应？
A. 分解反应
B. 氧化反应
C. 置换反应
D. 复分解反应

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Chemical reaction types"
    ),
]


# ============================================================================
# Additional Humanities
# ============================================================================

MMLU_HISTORY_SAMPLES: list[TestCase] = [
    TestCase(
        name="History: Ancient Civilizations",
        query="""问题：古埃及文明发源于哪条河流沿岸？
A. 底格里斯河
B. 尼罗河
C. 长江
D. 恒河

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Ancient history"
    ),

    TestCase(
        name="History: World War II",
        query="""问题：第二次世界大战结束于哪一年？
A. 1943
B. 1944
C. 1945
D. 1946

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="C",
        description="Modern history"
    ),

    TestCase(
        name="History: Chinese History",
        query="""问题：中国第一个统一的封建王朝是？
A. 周朝
B. 秦朝
C. 汉朝
D. 唐朝

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Chinese history"
    ),

    TestCase(
        name="History: Industrial Revolution",
        query="""问题：工业革命最早起源于哪个国家？
A. 法国
B. 德国
C. 英国
D. 美国

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="C",
        description="Economic history"
    ),
]

MMLU_LITERATURE_SAMPLES: list[TestCase] = [
    TestCase(
        name="Literature: Chinese Classics",
        query="""问题：《红楼梦》的作者是谁？
A. 罗贯中
B. 施耐庵
C. 曹雪芹
D. 吴承恩

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="C",
        description="Chinese classical literature"
    ),

    TestCase(
        name="Literature: Poetry",
        query="""问题：被称为"诗仙"的中国古代诗人是？
A. 杜甫
B. 李白
C. 白居易
D. 王维

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Chinese poetry"
    ),

    TestCase(
        name="Literature: Western Classics",
        query="""问题：《战争与和平》的作者是谁？
A. 狄更斯
B. 巴尔扎克
C. 托尔斯泰
D. 陀思妥耶夫斯基

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="C",
        description="Western literature"
    ),
]

MMLU_PHILOSOPHY_SAMPLES: list[TestCase] = [
    TestCase(
        name="Philosophy: Greek Philosophers",
        query="""问题："我思故我在"是哪位哲学家的名言？
A. 柏拉图
B. 亚里士多德
C. 笛卡尔
D. 康德

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="C",
        description="Western philosophy"
    ),

    TestCase(
        name="Philosophy: Ethics",
        query="""问题：功利主义的核心观点是？
A. 行为的道德性取决于其结果
B. 道德来自神的命令
C. 道德是主观的
D. 道德来自传统

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="A",
        description="Ethics philosophy"
    ),

    TestCase(
        name="Philosophy: Chinese Philosophy",
        query="""问题：老子的代表作是？
A. 《论语》
B. 《道德经》
C. 《孟子》
D. 《庄子》

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Chinese philosophy"
    ),
]


# ============================================================================
# Additional Social Sciences
# ============================================================================

MMLU_ECONOMICS_SAMPLES: list[TestCase] = [
    TestCase(
        name="Economics: GDP",
        query="""问题：GDP是指？
A. 国民生产总值
B. 国内生产总值
C. 国民收入
D. 人均收入

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Macroeconomics basics"
    ),

    TestCase(
        name="Economics: Market",
        query="""问题：在完全竞争市场中，单个企业是？
A. 价格制定者
B. 价格接受者
C. 垄断者
D. 政府监管者

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Market structures"
    ),

    TestCase(
        name="Economics: Inflation",
        query="""问题：通货膨胀通常会导致？
A. 货币购买力上升
B. 货币购买力下降
C. 失业率下降
D. 经济增长加速

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Monetary economics"
    ),

    TestCase(
        name="Economics: Opportunity Cost",
        query="""问题：机会成本是指？
A. 实际支出的成本
B. 放弃的最佳替代选择的收益
C. 沉没成本
D. 边际成本

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Economic concepts"
    ),
]

MMLU_PSYCHOLOGY_SAMPLES: list[TestCase] = [
    TestCase(
        name="Psychology: Brain",
        query="""问题：大脑中负责记忆的重要结构是？
A. 小脑
B. 海马体
C. 脑干
D. 额叶

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Neuropsychology"
    ),

    TestCase(
        name="Psychology: Development",
        query="""问题：皮亚杰的认知发展理论中，第一个阶段是？
A. 前运算阶段
B. 感知运动阶段
C. 具体运算阶段
D. 形式运算阶段

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Developmental psychology"
    ),

    TestCase(
        name="Psychology: Learning",
        query="""问题：斯金纳的操作性条件作用强调？
A. 刺激与反应的联结
B. 行为的后果影响行为
C. 观察学习
D. 认知过程

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Learning theory"
    ),
]

MMLU_GEOGRAPHY_SAMPLES: list[TestCase] = [
    TestCase(
        name="Geography: Continents",
        query="""问题：面积最大的洲是？
A. 非洲
B. 北美洲
C. 亚洲
D. 欧洲

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="C",
        description="Physical geography"
    ),

    TestCase(
        name="Geography: Oceans",
        query="""问题：面积最大的海洋是？
A. 大西洋
B. 印度洋
C. 太平洋
D. 北冰洋

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="C",
        description="Physical geography"
    ),

    TestCase(
        name="Geography: Climate",
        query="""问题：赤道地区主要是什么气候类型？
A. 温带气候
B. 热带雨林气候
C. 沙漠气候
D. 极地气候

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Climate geography"
    ),

    TestCase(
        name="Geography: Countries",
        query="""问题：世界上人口最多的国家是？
A. 美国
B. 印度
C. 中国
D. 印度尼西亚

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Human geography"
    ),
]


# ============================================================================
# Computer Science Extended
# ============================================================================

MMLU_CS_SAMPLES: list[TestCase] = [
    TestCase(
        name="CS: Data Structures",
        query="""问题：栈的特点是？
A. 先进先出
B. 先进后出
C. 随机访问
D. 顺序访问

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Data structures"
    ),

    TestCase(
        name="CS: Sorting",
        query="""问题：快速排序的平均时间复杂度是？
A. O(n)
B. O(n log n)
C. O(n²)
D. O(log n)

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Algorithm analysis"
    ),

    TestCase(
        name="CS: Programming",
        query="""问题：Python中，用于定义函数的关键字是？
A. function
B. def
C. func
D. define

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Programming basics"
    ),

    TestCase(
        name="CS: Networks",
        query="""问题：HTTP协议默认使用的端口号是？
A. 21
B. 22
C. 80
D. 443

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="C",
        description="Computer networks"
    ),

    TestCase(
        name="CS: Databases",
        query="""问题：SQL中用于从数据库检索数据的关键字是？
A. INSERT
B. UPDATE
C. SELECT
D. DELETE

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="C",
        description="Database queries"
    ),

    TestCase(
        name="CS: Boolean Logic",
        query="""问题：在Python中，表达式 `True and False` 返回什么值？
A. True
B. False
C. "True"
D. "False"

请用 Python 代码验证并输出正确选项的字母。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Boolean algebra"
    ),
]


# ============================================================================
# Mathematics Extended
# ============================================================================

MMLU_MATH_SAMPLES: list[TestCase] = [
    TestCase(
        name="Math: Percentage",
        query="""问题：如果一个数增加了20%，变成了120，那么原数是多少？
A. 96
B. 100
C. 108
D. 144

请用 Python 代码计算并输出正确选项的字母。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Percentage calculation"
    ),

    TestCase(
        name="Math: Fractions",
        query="""问题：1/2 + 1/3 等于多少？
A. 2/5
B. 1/5
C. 5/6
D. 2/6

请用 Python 代码计算并输出正确选项的字母。""",
        complexity=Complexity.MEDIUM,
        expect_contains="C",
        description="Fraction arithmetic"
    ),

    TestCase(
        name="Math: Exponents",
        query="""问题：2的10次方等于多少？
A. 512
B. 1000
C. 1024
D. 2048

请用 Python 代码计算并输出正确选项的字母。""",
        complexity=Complexity.MEDIUM,
        expect_contains="C",
        description="Exponentiation"
    ),

    TestCase(
        name="Math: Geometry",
        query="""问题：圆的周长公式是？
A. πr
B. 2πr
C. πr²
D. 2πr²

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Circle geometry"
    ),

    TestCase(
        name="Math: Pythagorean",
        query="""问题：直角三角形的两条直角边分别是3和4，斜边是多少？
A. 5
B. 6
C. 7
D. 8

请用 Python 代码计算并输出正确选项的字母。""",
        complexity=Complexity.MEDIUM,
        expect_contains="A",
        description="Pythagorean theorem"
    ),

    TestCase(
        name="Math: Logarithms",
        query="""问题：log₁₀(100) 等于多少？
A. 1
B. 2
C. 10
D. 100

请用 Python 代码计算并输出正确选项的字母。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Logarithm basics"
    ),
]


# ============================================================================
# Medicine & Health
# ============================================================================

MMLU_MEDICINE_SAMPLES: list[TestCase] = [
    TestCase(
        name="Medicine: Anatomy",
        query="""问题：人体最大的器官是？
A. 肝脏
B. 大脑
C. 皮肤
D. 心脏

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="C",
        description="Human anatomy"
    ),

    TestCase(
        name="Medicine: Blood",
        query="""问题：人体血液中负责运输氧气的是？
A. 白细胞
B. 红细胞
C. 血小板
D. 血浆

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Blood components"
    ),

    TestCase(
        name="Medicine: Vitamins",
        query="""问题：缺乏维生素C会导致什么疾病？
A. 佝偻病
B. 坏血病
C. 贫血
D. 夜盲症

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Nutrition science"
    ),

    TestCase(
        name="Medicine: Organs",
        query="""问题：人体内最大的内脏器官是？
A. 肝脏
B. 肺
C. 肾脏
D. 胃

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="A",
        description="Internal organs"
    ),
]


# ============================================================================
# Astronomy
# ============================================================================

MMLU_ASTRONOMY_SAMPLES: list[TestCase] = [
    TestCase(
        name="Astronomy: Solar System",
        query="""问题：太阳系中最大的行星是？
A. 地球
B. 木星
C. 土星
D. 天王星

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Solar system planets"
    ),

    TestCase(
        name="Astronomy: Moon Phases",
        query="""问题：当月球位于地球和太阳之间时，我们看到的是什么月相？
A. 满月
B. 新月
C. 上弦月
D. 下弦月

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Lunar phases"
    ),

    TestCase(
        name="Astronomy: Stars",
        query="""问题：太阳属于哪类恒星？
A. 红巨星
B. 白矮星
C. 主序星
D. 中子星

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="C",
        description="Stellar classification"
    ),

    TestCase(
        name="Astronomy: Light Year",
        query="""问题：光年是测量什么的单位？
A. 时间
B. 亮度
C. 距离
D. 速度

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="C",
        description="Astronomical units"
    ),
]


# ============================================================================
# Law & Jurisprudence
# ============================================================================

MMLU_LAW_SAMPLES: list[TestCase] = [
    TestCase(
        name="Law: Contract",
        query="""问题：合同成立的三个基本要素是什么？
A. 要约、承诺、价格
B. 要约、承诺、对价
C. 要约、签字、见证
D. 书面、签字、公证

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Contract law basics"
    ),

    TestCase(
        name="Law: Constitution",
        query="""问题：三权分立是指哪三种权力？
A. 立法、行政、司法
B. 立法、执法、监督
C. 决策、执行、监督
D. 立法、行政、监察

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="A",
        description="Constitutional law"
    ),

    TestCase(
        name="Law: Criminal",
        query="""问题：刑法中，"无罪推定"原则意味着？
A. 被告必须证明自己无罪
B. 检方必须证明被告有罪
C. 法官决定被告是否有罪
D. 警察决定是否起诉

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Criminal law"
    ),
]


# ============================================================================
# Art & Music
# ============================================================================

MMLU_ART_SAMPLES: list[TestCase] = [
    TestCase(
        name="Art: Renaissance",
        query="""问题：《蒙娜丽莎》的作者是谁？
A. 米开朗基罗
B. 拉斐尔
C. 达芬奇
D. 波提切利

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="C",
        description="Renaissance art"
    ),

    TestCase(
        name="Art: Music Theory",
        query="""问题：一个八度包含多少个半音？
A. 6个
B. 8个
C. 10个
D. 12个

请用 Python 代码验证并输出正确选项的字母。""",
        complexity=Complexity.MEDIUM,
        expect_contains="D",
        description="Music theory"
    ),

    TestCase(
        name="Art: Impressionism",
        query="""问题：印象派绘画起源于哪个国家？
A. 意大利
B. 荷兰
C. 法国
D. 西班牙

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="C",
        description="Art history"
    ),
]


# ============================================================================
# Advanced Mathematics
# ============================================================================

MMLU_ADV_MATH_SAMPLES: list[TestCase] = [
    TestCase(
        name="Math: Integral",
        query="""问题：∫x²dx 等于多少？（C为常数）
A. x³ + C
B. x³/2 + C
C. x³/3 + C
D. 2x + C

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.COMPLEX,
        expect_contains="C",
        description="Basic integration"
    ),

    TestCase(
        name="Math: Complex Numbers",
        query="""问题：i² 等于多少？（i为虚数单位）
A. 1
B. -1
C. i
D. -i

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Complex numbers"
    ),

    TestCase(
        name="Math: Trigonometry",
        query="""问题：sin(30°) 等于多少？
A. 0
B. 0.5
C. 0.866
D. 1

请用 Python 的 math 模块验证并输出正确选项的字母。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Trigonometric values"
    ),

    TestCase(
        name="Math: Matrix",
        query="""问题：2×2矩阵的行列式公式是什么？
A. ad - bc
B. ad + bc
C. a + d
D. a × d

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.COMPLEX,
        expect_contains="A",
        description="Linear algebra"
    ),

    TestCase(
        name="Math: Probability",
        query="""问题：同时掷两枚硬币，两枚都是正面的概率是多少？
A. 1/4
B. 1/3
C. 1/2
D. 2/3

请用 Python 代码计算并输出正确选项的字母。""",
        complexity=Complexity.MEDIUM,
        expect_contains="A",
        description="Probability calculation"
    ),
]


# ============================================================================
# Technology & Engineering
# ============================================================================

MMLU_TECH_SAMPLES: list[TestCase] = [
    TestCase(
        name="Tech: Binary",
        query="""问题：二进制数 1111 等于十进制的多少？
A. 7
B. 14
C. 15
D. 16

请用 Python 代码计算并输出正确选项的字母。""",
        complexity=Complexity.MEDIUM,
        expect_contains="C",
        description="Binary conversion"
    ),

    TestCase(
        name="Tech: CPU",
        query="""问题：CPU的"时钟频率"通常以什么单位衡量？
A. 字节
B. 赫兹
C. 瓦特
D. 比特

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Computer hardware"
    ),

    TestCase(
        name="Tech: Memory",
        query="""问题：1GB 等于多少 MB？
A. 100 MB
B. 500 MB
C. 1000 MB
D. 1024 MB

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="D",
        description="Memory units"
    ),

    TestCase(
        name="Tech: Algorithm",
        query="""问题：冒泡排序的最坏时间复杂度是？
A. O(n)
B. O(n log n)
C. O(n²)
D. O(log n)

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="C",
        description="Algorithm complexity"
    ),

    TestCase(
        name="Tech: Internet",
        query="""问题：HTTPS 相比 HTTP 增加了什么？
A. 速度
B. 加密
C. 压缩
D. 缓存

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Web protocols"
    ),
]


# ============================================================================
# Linguistics & Language
# ============================================================================

MMLU_LINGUISTICS_SAMPLES: list[TestCase] = [
    TestCase(
        name="Linguistics: Parts of Speech",
        query="""问题：在中文语法中，"很"属于什么词性？
A. 名词
B. 动词
C. 形容词
D. 副词

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="D",
        description="Chinese grammar"
    ),

    TestCase(
        name="Linguistics: Phonetics",
        query="""问题：普通话有几个声调？
A. 3个
B. 4个
C. 5个
D. 6个

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Chinese phonetics"
    ),

    TestCase(
        name="Linguistics: Syntax",
        query="""问题："主语+谓语+宾语"是什么语言的基本语序？
A. 日语
B. 汉语
C. 土耳其语
D. 阿拉伯语

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Language typology"
    ),
]


# ============================================================================
# Additional MMLU Subject Categories (60 new questions)
# ============================================================================

MMLU_BUSINESS_SAMPLES: list[TestCase] = [
    TestCase(
        name="Business: SWOT Analysis",
        query="""问题：SWOT 分析中的 "S" 代表什么？
A. Strengths
B. Strategy
C. Sales
D. Success

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="A",
        description="Business strategy framework"
    ),

    TestCase(
        name="Business: ROI",
        query="""问题：ROI 的全称是什么？
A. Rate of Interest
B. Return on Investment
C. Return on Income
D. Rate of Inflation

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Financial metric"
    ),

    TestCase(
        name="Business: Supply Chain",
        query="""问题：供应链管理的核心目标是？
A. 最大化库存
B. 优化流程、降低成本
C. 增加供应商数量
D. 提高产品价格

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Operations management"
    ),

    TestCase(
        name="Business: Marketing Mix 4P",
        query="""问题：营销组合 4P 不包括以下哪项？
A. Product
B. Price
C. Profit
D. Promotion

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="C",
        description="Marketing fundamentals"
    ),

    TestCase(
        name="Business: Break-even",
        query="""问题：盈亏平衡点是？
A. 收入最大化的点
B. 成本最低的点
C. 收入等于成本的点
D. 利润最高的点

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="C",
        description="Financial analysis"
    ),

    TestCase(
        name="Business: Leadership",
        query="""问题：变革型领导者的核心特征是？
A. 维持现状
B. 激励和激励追随者超越预期
C. 严格控制下属
D. 避免风险

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Organizational behavior"
    ),

    TestCase(
        name="Business: BCG Matrix",
        query="""问题：BCG 矩阵中"现金牛"业务的特点是？
A. 高增长、高市场份额
B. 低增长、高市场份额
C. 高增长、低市场份额
D. 低增长、低市场份额

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.COMPLEX,
        expect_contains="B",
        description="Strategic planning"
    ),

    TestCase(
        name="Business: Porter's Five Forces",
        query="""问题：波特五力模型不包括以下哪项？
A. 供应商议价能力
B. 买方议价能力
C. 政府监管强度
D. 替代品威胁

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.COMPLEX,
        expect_contains="C",
        description="Competitive analysis"
    ),
]

MMLU_POLITICS_SAMPLES: list[TestCase] = [
    TestCase(
        name="Politics: Democracy",
        query="""问题：民主制度的核心原则是？
A. 君主统治
B. 人民主权
C. 军事独裁
D. 神权统治

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Political systems"
    ),

    TestCase(
        name="Politics: Separation of Powers",
        query="""问题：三权分立不包括以下哪项？
A. 立法权
B. 行政权
C. 司法权
D. 监察权

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="D",
        description="Constitutional theory"
    ),

    TestCase(
        name="Politics: Ideology",
        query="""问题：自由主义的核心价值观是？
A. 集体主义高于个人
B. 个人自由和权利
C. 国家干预经济
D. 传统价值至上

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Political ideology"
    ),

    TestCase(
        name="Politics: United Nations",
        query="""问题：联合国安理会常任理事国有几个？
A. 5个
B. 7个
C. 10个
D. 15个

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="A",
        description="International organizations"
    ),

    TestCase(
        name="Politics: Electoral Systems",
        query="""问题：比例代表制的主要特点是？
A. 赢者通吃
B. 席位按投票比例分配
C. 只有两党能获胜
D. 必须获得绝对多数

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Voting systems"
    ),

    TestCase(
        name="Politics: Social Contract",
        query="""问题：社会契约理论的代表人物不包括？
A. 霍布斯
B. 洛克
C. 卢梭
D. 黑格尔

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.COMPLEX,
        expect_contains="D",
        description="Political philosophy"
    ),

    TestCase(
        name="Politics: GDP",
        query="""问题：GDP 的全称是？
A. Gross Domestic Product
B. General Domestic Product
C. Gross Development Product
D. General Development Product

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="A",
        description="Economic indicators"
    ),
]

MMLU_EDUCATION_SAMPLES: list[TestCase] = [
    TestCase(
        name="Education: Bloom's Taxonomy",
        query="""问题：布鲁姆认知目标分类中最高层次是？
A. 应用
B. 分析
C. 评价
D. 创造

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="D",
        description="Educational psychology"
    ),

    TestCase(
        name="Education: Learning Styles",
        query="""问题：VARK 学习风格模型不包括？
A. Visual
B. Auditory
C. Kinesthetic
D. Emotional

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="D",
        description="Learning theories"
    ),

    TestCase(
        name="Education: Constructivism",
        query="""问题：建构主义学习理论的核心观点是？
A. 学生被动接受知识
B. 学习者主动构建知识
C. 教师是唯一的知识来源
D. 记忆是学习的主要方式

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Learning theory"
    ),

    TestCase(
        name="Education: Formative Assessment",
        query="""问题：形成性评价的主要目的是？
A. 给学生最终成绩
B. 改进教学过程
C. 选拔优秀学生
D. 评价教师绩效

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Assessment methods"
    ),

    TestCase(
        name="Education: Scaffolding",
        query="""问题：支架式教学的概念最早由谁提出？
A. 皮亚杰
B. 维果茨基
C. 布鲁纳
D. 斯金纳

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.COMPLEX,
        expect_contains="B",
        description="Educational theory"
    ),

    TestCase(
        name="Education: Multiple Intelligences",
        query="""问题：多元智能理论的提出者是？
A. 加德纳
B. 斯滕伯格
C. 卡特尔
D. 斯皮尔曼

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="A",
        description="Intelligence theory"
    ),

    TestCase(
        name="Education: Andragogy",
        query="""问题：成人教育学的英文名称是？
A. Pedagogy
B. Andragogy
C. Heutagogy
D. Synergogy

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Adult learning"
    ),
]

MMLU_ENVIRONMENT_SAMPLES: list[TestCase] = [
    TestCase(
        name="Environment: Greenhouse Effect",
        query="""问题：温室效应的主要原因是？
A. 氧气增加
B. 温室气体排放
C. 森林砍伐减少
D. 海洋温度下降

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Climate change"
    ),

    TestCase(
        name="Environment: Carbon Footprint",
        query="""问题：碳足迹衡量的是？
A. 身体留下的痕迹
B. 活动产生的二氧化碳排放量
C. 森林覆盖面积
D. 能源消耗总量

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Environmental metrics"
    ),

    TestCase(
        name="Environment: Biodiversity",
        query="""问题：生物多样性 hotspot 的特点是？
A. 物种丰富且受威胁严重
B. 物种稀少且稳定
C. 只存在于极地地区
D. 不受人类活动影响

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="A",
        description="Conservation biology"
    ),

    TestCase(
        name="Environment: Renewable Energy",
        query="""问题：以下哪项不是可再生能源？
A. 太阳能
B. 风能
C. 天然气
D. 水能

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="C",
        description="Energy sources"
    ),

    TestCase(
        name="Environment: Ozone Layer",
        query="""问题：臭氧层的主要作用是？
A. 保持地球温度
B. 吸收有害紫外线
C. 产生氧气
D. 调节降水

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Atmospheric science"
    ),

    TestCase(
        name="Environment: Eutrophication",
        query="""问题：水体富营养化的主要原因是？
A. 重金属污染
B. 氮磷营养物质过多
C. 酸性物质排放
D. 石油泄漏

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Water pollution"
    ),

    TestCase(
        name="Environment: Paris Agreement",
        query="""问题：《巴黎协定》的主要目标是？
A. 禁止所有化石燃料
B. 限制全球平均升温
C. 强制所有国家碳中和
D. 取消所有工业活动

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Climate policy"
    ),
]

MMLU_STATISTICS_SAMPLES: list[TestCase] = [
    TestCase(
        name="Statistics: Mean",
        query="""问题：数据集 [2, 4, 6, 8, 10] 的平均值是？
A. 5
B. 6
C. 7
D. 8

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Descriptive statistics"
    ),

    TestCase(
        name="Statistics: Median",
        query="""问题：数据集 [3, 7, 2, 9, 1] 的中位数是？
A. 2
B. 3
C. 7
D. 9

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Descriptive statistics"
    ),

    TestCase(
        name="Statistics: Standard Deviation",
        query="""问题：标准差衡量的是？
A. 数据的平均值
B. 数据的离散程度
C. 数据的总和
D. 数据的最大值

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Variability measures"
    ),

    TestCase(
        name="Statistics: Correlation",
        query="""问题：相关系数 r 的取值范围是？
A. 0 到 1
B. -1 到 1
C. -∞ 到 +∞
D. 0 到 100

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Correlation analysis"
    ),

    TestCase(
        name="Statistics: Hypothesis Testing",
        query="""问题：p 值小于 0.05 意味着？
A. 接受零假设
B. 拒绝零假设
C. 结果不显著
D. 需要更多样本

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Inferential statistics"
    ),

    TestCase(
        name="Statistics: Normal Distribution",
        query="""问题：正态分布中，约多少数据位于均值±1个标准差内？
A. 50%
B. 68%
C. 95%
D. 99%

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Probability distributions"
    ),

    TestCase(
        name="Statistics: Type I Error",
        query="""问题：第一类错误（Type I）是指？
A. 零假设为真时拒绝了它
B. 零假设为假时接受了它
C. 样本量不足
D. 计算错误

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.COMPLEX,
        expect_contains="A",
        description="Hypothesis testing errors"
    ),
]

MMLU_ACCOUNTING_SAMPLES: list[TestCase] = [
    TestCase(
        name="Accounting: Assets",
        query="""问题：会计基本等式是？
A. 收入 - 费用 = 利润
B. 资产 = 负债 + 所有者权益
C. 借方 = 贷方
D. 现金流入 = 现金流出

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Fundamental accounting equation"
    ),

    TestCase(
        name="Accounting: Debit/Credit",
        query="""问题：资产类账户增加记在？
A. 借方
B. 贷方
C. 双方均可
D. 不记录

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="A",
        description="Double-entry bookkeeping"
    ),

    TestCase(
        name="Accounting: Depreciation",
        query="""问题：折旧是一种？
A. 现金流出
B. 费用分摊
C. 负债增加
D. 收入减少

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Asset valuation"
    ),

    TestCase(
        name="Accounting: Accrual Basis",
        query="""问题：权责发生制与收付实现制的主要区别是？
A. 记账时间不同
B. 货币种类不同
C. 税率不同
D. 报表格式不同

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="A",
        description="Accounting methods"
    ),

    TestCase(
        name="Accounting: Liquidity Ratio",
        query="""问题：流动比率衡量的是？
A. 盈利能力
B. 短期偿债能力
C. 长期偿债能力
D. 资产周转速度

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Financial ratios"
    ),

    TestCase(
        name="Accounting: COGS",
        query="""问题：COGS（销售成本）是指？
A. Cost of Goods Sold
B. Cost of General Sales
C. Cost of Global Standards
D. Cost of Government Services

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="A",
        description="Income statement items"
    ),

    TestCase(
        name="Accounting: Equity",
        query="""问题：所有者权益不包括以下哪项？
A. 实收资本
B. 留存收益
C. 应付账款
D. 资本公积

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="C",
        description="Balance sheet components"
    ),
]

MMLU_MARKETING_SAMPLES: list[TestCase] = [
    TestCase(
        name="Marketing: STP",
        query="""问题：STP 营销中的 T 代表？
A. Targeting
B. Timing
C. Testing
D. Trust

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="A",
        description="Marketing strategy"
    ),

    TestCase(
        name="Marketing: CRM",
        query="""问题：CRM 的全称是？
A. Customer Revenue Management
B. Customer Relationship Management
C. Corporate Resource Management
D. Consumer Research Method

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Customer management"
    ),

    TestCase(
        name="Marketing: Brand Equity",
        query="""问题：品牌资产是指？
A. 品牌的财务价值
B. 品牌的厂房设备
C. 品牌的员工数量
D. 品牌的办公用品

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="A",
        description="Brand management"
    ),

    TestCase(
        name="Marketing: AIDA Model",
        query="""问题：AIDA 模型中的 A 不代表？
A. Attention
B. Action
C. Analysis
D. Interest

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="C",
        description="Consumer behavior"
    ),

    TestCase(
        name="Marketing: Market Segmentation",
        query="""问题：市场细分的基础不包括？
A. 地理因素
B. 人口因素
C. 心理因素
D. 随机分配

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="D",
        description="Market research"
    ),

    TestCase(
        name="Marketing: SEO",
        query="""问题：SEO 的全称是？
A. Search Engine Optimization
B. Social Media Engagement
C. Site Effectiveness Operation
D. Sales Enhancement Option

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="A",
        description="Digital marketing"
    ),

    TestCase(
        name="Marketing: CLV",
        query="""问题：客户生命周期价值（CLV）衡量的是？
A. 客户的单次购买金额
B. 客户在整个关系期间的总价值
C. 客户的年龄
D. 客户的数量

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Customer analytics"
    ),
]

MMLU_SOCILOGY_SAMPLES: list[TestCase] = [
    TestCase(
        name="Sociology: Socialization",
        query="""问题：社会化的主要意思是？
A. 使用社交媒体
B. 学习社会规范和价值观
C. 参加社交活动
D. 扩大人脉关系

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="B",
        description="Social processes"
    ),

    TestCase(
        name="Sociology: Culture",
        query="""问题：文化的核心要素不包括？
A. 符号
B. 价值观
C. 地理位置固定
D. 规范

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="C",
        description="Cultural concepts"
    ),

    TestCase(
        name="Sociology: Social Stratification",
        query="""问题：社会分层的主要依据不包括？
A. 经济收入
B. 教育水平
C. 血型
D. 职业地位

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.SIMPLE,
        expect_contains="C",
        description="Social structure"
    ),

    TestCase(
        name="Sociology: Deviance",
        query="""问题：越轨行为是指？
A. 违反社会规范的行为
B. 犯罪行为
C. 心理疾病
D. 个性表现

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="A",
        description="Social control"
    ),

    TestCase(
        name="Sociology: Social Mobility",
        query="""问题：社会流动性是指？
A. 人口迁徙
B. 社会地位的变化
C. 职业转换
D. 住所搬迁

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.MEDIUM,
        expect_contains="B",
        description="Social change"
    ),

    TestCase(
        name="Sociology: Gemeinschaft",
        query="""问题：滕尼斯提出的"礼俗社会"（Gemeinschaft）特点是？
A. 理性、契约、匿名
B. 情感、传统、紧密
C. 工业化、城市化
D. 个人主义、竞争

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.COMPLEX,
        expect_contains="B",
        description="Classical sociology"
    ),

    TestCase(
        name="Sociology: Labeling Theory",
        query="""问题：标签理论的核心观点是？
A. 犯罪是由基因决定的
B. 越轨是社会标签的结果
C. 贫穷导致犯罪
D. 教育可以消除犯罪

请输出正确选项的字母（A/B/C/D）。""",
        complexity=Complexity.COMPLEX,
        expect_contains="B",
        description="Deviance theories"
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
    MMLU_ADVANCED_SAMPLES +
    MMLU_BIOLOGY_SAMPLES +
    MMLU_PHYSICS_SAMPLES +
    MMLU_CHEMISTRY_SAMPLES +
    MMLU_HISTORY_SAMPLES +
    MMLU_LITERATURE_SAMPLES +
    MMLU_PHILOSOPHY_SAMPLES +
    MMLU_ECONOMICS_SAMPLES +
    MMLU_PSYCHOLOGY_SAMPLES +
    MMLU_GEOGRAPHY_SAMPLES +
    MMLU_CS_SAMPLES +
    MMLU_MATH_SAMPLES +
    MMLU_MEDICINE_SAMPLES +
    MMLU_ASTRONOMY_SAMPLES +
    MMLU_LAW_SAMPLES +
    MMLU_ART_SAMPLES +
    MMLU_ADV_MATH_SAMPLES +
    MMLU_TECH_SAMPLES +
    MMLU_LINGUISTICS_SAMPLES +
    MMLU_BUSINESS_SAMPLES +
    MMLU_POLITICS_SAMPLES +
    MMLU_EDUCATION_SAMPLES +
    MMLU_ENVIRONMENT_SAMPLES +
    MMLU_STATISTICS_SAMPLES +
    MMLU_ACCOUNTING_SAMPLES +
    MMLU_MARKETING_SAMPLES +
    MMLU_SOCILOGY_SAMPLES
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
