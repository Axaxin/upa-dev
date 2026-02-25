"""
Core UPA Test Suite
Tests core code generation and execution capabilities.
"""

from benchmarks.suites.base import (
    TestCase, TestSuite, Complexity, register_suite
)


# =============================================================================
# Test Cases (extracted from benchmark_upa.py)
# =============================================================================

CORE_CASES: list[TestCase] = [
    # ---- Simple Tests ----
    TestCase("基础问候", "你好，请简单介绍一下你自己。输出格式：用print()输出一句话", Complexity.SIMPLE),
    TestCase("整数加法", "计算 123 + 456。输出格式：print(579)", Complexity.SIMPLE, expect_numeric=(579, 0)),
    TestCase("整数乘法", "计算 25 乘以 4。输出格式：print(100)", Complexity.SIMPLE, expect_numeric=(100, 0)),
    TestCase("浮点除法", "计算 22 除以 7，保留4位小数。输出格式：print(3.1428)", Complexity.SIMPLE, expect_numeric=(3.1428, 0.001)),
    TestCase("幂运算", "计算 2 的 10 次方。输出格式：print(1024)", Complexity.SIMPLE, expect_numeric=(1024, 0)),
    TestCase("绝对值", "计算 |-15|。输出格式：print(15)", Complexity.SIMPLE, expect_numeric=(15, 0)),
    TestCase("余数计算", "计算 17 除以 5 的余数。输出格式：print(2)", Complexity.SIMPLE, expect_numeric=(2, 0)),

    # ---- Medium Tests ----
    TestCase("列表排序", "将列表 [5, 2, 8, 1, 9, 3] 排序。输出格式：print([1,2,3,5,8,9])", Complexity.MEDIUM, expect_pattern=r"\[1,\s*2,\s*3,\s*5,\s*8,\s*9\]"),
    TestCase("列表去重", "去除 [1, 2, 2, 3, 3, 3, 4] 中的重复元素。输出格式：print([1,2,3,4])", Complexity.MEDIUM, expect_pattern=r"\[1,\s*2,\s*3,\s*4\]"),
    TestCase("字符串反转", "反转字符串 'Hello World'。输出格式：print('dlroW olleH')", Complexity.MEDIUM, expect_contains="dlroW olleH"),
    TestCase("素数判断", "判断 97 是否是素数。如果是素数输出'是'，否则输出'否'", Complexity.MEDIUM, expect_contains="是"),
    TestCase("斐波那契", "计算斐波那契数列的第15个数。输出格式：print(610)", Complexity.MEDIUM, expect_numeric=(610, 0)),
    TestCase("阶乘计算", "计算 10 的阶乘。输出格式：print(3628800)", Complexity.MEDIUM, expect_numeric=(3628800, 0)),
    TestCase("日期计算", "计算从今天开始30天后的日期。输出格式：print('YYYY-MM-DD')", Complexity.MEDIUM),
    TestCase("星期计算", "计算2024年1月1日是星期几。输出格式：print('星期X')", Complexity.MEDIUM, expect_contains="一"),
    TestCase("最大公约数", "计算 48 和 18 的最大公约数。输出格式：print(6)", Complexity.MEDIUM, expect_numeric=(6, 0)),
    TestCase("字符串拼接", "将 ['Hello', 'World', 'UPA'] 用空格连接。输出格式：print('Hello World UPA')", Complexity.MEDIUM, expect_contains="Hello World UPA"),
    TestCase("列表求和", "计算 [1, 3, 5, 7, 9] 的和。输出格式：print(25)", Complexity.MEDIUM, expect_numeric=(25, 0)),
    TestCase("判断回文", "判断 'radar' 是否是回文字符串。如果是输出'是'，否则输出'否'", Complexity.MEDIUM, expect_contains="是"),

    # ---- Complex Tests ----
    TestCase("统计词频", "统计 'the quick brown fox jumps over the lazy dog' 中the的出现次数。输出格式：print(2)", Complexity.COMPLEX, expect_numeric=(2, 0)),
    TestCase("JSON解析", "从JSON {\"users\":[{\"name\":\"Alice\"},{\"name\":\"Bob\"}]} 中提取所有用户名。输出格式：包含'Alice'", Complexity.COMPLEX, expect_contains="Alice"),
    TestCase("正则提取", "从 '电话13812345678' 中提取手机号。输出格式：print('13812345678')", Complexity.COMPLEX, expect_contains="13812345678"),
    TestCase("数学序列", "找出1到100中能被3整除但不能被5整除的数的个数。输出格式：print(27)", Complexity.COMPLEX, expect_numeric=(27, 0)),
    TestCase("字符串处理", "将 'hello_world_example' 转换为驼峰命名。输出格式：print('helloWorldExample')", Complexity.COMPLEX, expect_contains="helloWorldExample"),
    TestCase("数组交集", "找出 [1,2,3,4,5] 和 [4,5,6,7,8] 的交集。输出格式：print([4,5])", Complexity.COMPLEX, expect_pattern=r"\[4,\s*5\]"),
    TestCase("统计计算", "计算列表 [1,2,3,4,5,6,7,8,9,10] 的平均值。输出格式：print(5.5)", Complexity.COMPLEX, expect_numeric=(5.5, 0.1)),
    TestCase("冒泡排序", "用冒泡排序对 [64, 34, 25, 12, 22, 11, 90] 排序。输出格式：print([升序排列的列表])", Complexity.COMPLEX),
    TestCase("二分查找", "判断 17 是否在有序列表 [2,5,8,12,16,23,38,56,72,91] 中。如果是输出True，否则输出False", Complexity.COMPLEX, expect_contains="False"),
    TestCase("矩阵转置", "将矩阵 [[1,2,3],[4,5,6]] 转置。输出格式：print([[1,4],[2,5],[3,6]])", Complexity.COMPLEX),
    TestCase("生成密码", "生成一个包含大小写字母和数字的8位随机密码。输出格式：print('生成的密码')", Complexity.COMPLEX),
    TestCase("凯撒密码", "用凯撒密码加密 'hello'，偏移量为3。输出格式：print('khoor')", Complexity.COMPLEX, expect_contains="khoor"),
    TestCase("水仙花数", "找出100-999之间的所有水仙花数。输出格式：print([153, 370, 371, 407])", Complexity.COMPLEX, expect_contains="153"),
    TestCase("最长公共子串", "找出 'abcdefg' 和 'xcdey' 的最长公共子串。输出格式：print('cde')", Complexity.COMPLEX, expect_contains="cde"),

    # ---- Edge Cases ----
    TestCase("大数计算", "计算 999999 * 999999。输出格式：print(999998000001)", Complexity.EDGE_CASE, expect_numeric=(999998000001, 0)),
    TestCase("负数运算", "计算 -5 * -3 + -10。输出格式：print(5)", Complexity.EDGE_CASE, expect_numeric=(5, 0)),
    TestCase("边界值", "判断0是正数还是负数还是零。如果是零输出'零'，正数输出'正数'，负数输出'负数'", Complexity.EDGE_CASE, expect_contains="零"),
    TestCase("中文数字", "将中文数字 '三百五十六' 转换为阿拉伯数字。输出格式：print(356)", Complexity.EDGE_CASE, expect_numeric=(356, 0)),
    TestCase("Emoji统计", "统计字符串 '🎉🎊🎁' 中emoji的数量。输出格式：print(3)", Complexity.EDGE_CASE, expect_numeric=(3, 0)),
    TestCase("空列表处理", "对空列表 [] 求和。输出格式：print(0)", Complexity.EDGE_CASE, expect_numeric=(0, 0)),
    TestCase("除零处理", "计算 1/0。如果发生错误，输出包含'Error'或'错误'", Complexity.EDGE_CASE, expect_contains="Error"),
    TestCase("科学计数法", "将 0.0000123 转为科学计数法。输出格式：包含'1.23'", Complexity.EDGE_CASE, expect_contains="1.23"),
    TestCase("罗马数字", "将罗马数字 'MMXXIV' 转为阿拉伯数字。输出格式：print(2024)", Complexity.EDGE_CASE, expect_numeric=(2024, 10)),
    TestCase("Unicode处理", "输出字符串 '你好🌍世界' 的长度。输出格式：print(5)", Complexity.EDGE_CASE, expect_numeric=(5, 1)),
]


# =============================================================================
# Register Test Suite
# =============================================================================

@register_suite
def _register_core_suite() -> TestSuite:
    """Register the core UPA test suite."""
    return TestSuite(
        name="core",
        description="Core UPA functionality tests (code generation & execution)",
        version="1.0.0",
        cases=CORE_CASES,
    )


# Export for direct access
__all__ = ["CORE_CASES"]
