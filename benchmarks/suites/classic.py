"""
Classic LLM Benchmark Test Cases

This suite contains sample problems from well-known LLM benchmarks:
- GSM8K: Grade school math word problems (OpenAI, 2021)
- HumanEval: Python code generation (OpenAI, 2021)
- MATH: Advanced mathematics problems

References:
- https://github.com/openai/human-eval
- https://github.com/openai/grade-school-math
"""

from benchmarks.suites.base import (
    TestCase, TestSuite, Complexity, register_suite
)


# ============================================================================
# GSM8K: Grade School Math 8K - Math Word Problems
# ============================================================================

GSM8K_CASES: list[TestCase] = [
    TestCase(
        name="Olivia's Bagels (GSM8K)",
        query="Olivia has $23. She bought five bagels for $3 each. How much money does she have left? "
              "请用 Python 代码计算并输出剩余金额，只输出数字。",
        complexity=Complexity.SIMPLE,
        expect_numeric=(8, 0),
        description="Basic arithmetic: multiplication and subtraction"
    ),

    TestCase(
        name="Michael's Golf Balls (GSM8K)",
        query="Michael had 58 golf balls. On Tuesday, he lost 23 golf balls. "
              "On Wednesday, he lost 2 more. How many golf balls did he have at the end of Wednesday? "
              "请用代码计算并输出结果。",
        complexity=Complexity.SIMPLE,
        expect_numeric=(33, 0),
        description="Multi-step subtraction"
    ),

    TestCase(
        name="Server Room Computers (GSM8K)",
        query="There were nine computers in the server room. Five more computers were installed each day, "
              "from Monday to Thursday. How many computers are now in the server room? "
              "请用代码计算并输出最终数量。",
        complexity=Complexity.MEDIUM,
        expect_numeric=(29, 0),
        description="Multiplication and addition"
    ),

    TestCase(
        name="Leah's Chocolates (GSM8K)",
        query="Leah had 32 chocolates and her sister had 42. If they ate 35, "
              "how many pieces do they have left in total? 请用代码计算。",
        complexity=Complexity.SIMPLE,
        expect_numeric=(39, 0),
        description="Sum then subtract"
    ),

    TestCase(
        name="Jason's Lollipops (GSM8K)",
        query="Jason had 20 lollipops. He gave Denny some lollipops. "
              "Now Jason has 12 lollipops. How many lollipops did Jason give to Denny? "
              "请用代码计算。",
        complexity=Complexity.SIMPLE,
        expect_numeric=(8, 0),
        description="Subtraction to find difference"
    ),

    TestCase(
        name="Complex Train Problem (GSM8K)",
        query="A train leaves New York for Chicago at the same time a train leaves Chicago for New York. "
              "The distance between the two cities is 800 miles. The trains are heading toward each other "
              "at speeds of 40 mph and 60 mph respectively. How many miles will the train from New York "
              "have traveled when they meet? 请用代码计算。",
        complexity=Complexity.MEDIUM,
        expect_numeric=(320, 1),
        description="Rate problem: relative speed and distance"
    ),
]


# ============================================================================
# HumanEval: Python Code Generation Problems
# ============================================================================

HUMANEVAL_CASES: list[TestCase] = [
    TestCase(
        name="Truncate Number (HumanEval)",
        query="Write a function truncate_number that returns the decimal part of a positive float. "
              "For example, truncate_number(3.5) should return 0.5. "
              "请实现这个函数并用 print(truncate_number(3.5)) 输出结果。",
        complexity=Complexity.SIMPLE,
        expect_numeric=(0.5, 0.01),
        description="Float modulo operation"
    ),

    TestCase(
        name="Make Palindrome (HumanEval)",
        query="Write a function that finds the closest palindrome to a string. "
              "If the string is already a palindrome, return it. "
              "Test with 'abc' - the closest palindrome is 'aba'. "
              "请实现并测试这个函数。",
        complexity=Complexity.COMPLEX,
        expect_pattern=r"aba",
        description="String manipulation: palindrome generation"
    ),

    TestCase(
        name="Separate Parenthesis (HumanEval)",
        query="Write a function separate_paren_groups that takes a string with multiple parenthesis groups "
              "and returns a list of the groups. For example, '(()) ((()))' should return ['(())', '((()))']. "
              "请实现并测试。",
        complexity=Complexity.COMPLEX,
        expect_contains="['(())', '((()))']",
        description="String parsing and grouping"
    ),

    TestCase(
        name="Fibonacci (HumanEval style)",
        query="Write a function to compute the nth Fibonacci number. "
              "fibonacci(10) should return 55. 请实现并测试。",
        complexity=Complexity.MEDIUM,
        expect_numeric=(55, 0),
        description="Classic recursion/iteration"
    ),

    TestCase(
        name="Prime Numbers (HumanEval style)",
        query="Write a function is_prime(n) that returns True if n is prime, False otherwise. "
              "Test: is_prime(17) should be True, is_prime(10) should be False. "
              "请实现并打印测试结果。",
        complexity=Complexity.MEDIUM,
        expect_contains="True",
        description="Number theory: primality test"
    ),

    TestCase(
        name="Factorial (HumanEval style)",
        query="Implement a factorial function. factorial(5) should return 120. "
              "请实现并打印 factorial(5) 的结果。",
        complexity=Complexity.SIMPLE,
        expect_numeric=(120, 0),
        description="Basic recursion or iteration"
    ),
]


# ============================================================================
# MATH: Advanced Mathematics Problems
# ============================================================================

MATH_CASES: list[TestCase] = [
    TestCase(
        name="Quadratic Equation",
        query="Solve the quadratic equation x² - 5x + 6 = 0. "
              "Find all real solutions and print them as a list. 请用代码求解。",
        complexity=Complexity.MEDIUM,
        expect_pattern=r"[23]",
        description="Solving quadratic equations"
    ),

    TestCase(
        name="Sum of Series",
        query="Calculate the sum of the first 100 natural numbers: 1 + 2 + 3 + ... + 100. "
              "请用代码计算并输出结果。",
        complexity=Complexity.SIMPLE,
        expect_numeric=(5050, 0),
        description="Arithmetic series sum"
    ),

    TestCase(
        name="Greatest Common Divisor",
        query="Find the greatest common divisor (GCD) of 48 and 18. "
              "请用欧几里得算法或 Python 内置函数计算。",
        complexity=Complexity.MEDIUM,
        expect_numeric=(6, 0),
        description="Number theory: GCD"
    ),

    TestCase(
        name="Prime Sum",
        query="Find the sum of all prime numbers less than 20. "
              "Primes less than 20 are: 2, 3, 5, 7, 11, 13, 17, 19. "
              "请用代码计算总和。",
        complexity=Complexity.COMPLEX,
        expect_numeric=(77, 0),
        description="Prime generation and summation"
    ),

    TestCase(
        name="Binomial Coefficient",
        query="Calculate C(10, 3) - the number of ways to choose 3 items from 10. "
              "请用数学公式或 Python 计算。",
        complexity=Complexity.MEDIUM,
        expect_numeric=(120, 0),
        description="Combinatorics: n choose k"
    ),

    TestCase(
        name="Modular Arithmetic",
        query="What is 2^100 mod 7? 请用 Python 的 pow 函数计算并输出结果。",
        complexity=Complexity.MEDIUM,
        expect_numeric=(2, 0),
        description="Modular exponentiation"
    ),
]


# ============================================================================
# Edge Cases and Tricky Problems
# ============================================================================

EDGE_CASES: list[TestCase] = [
    TestCase(
        name="Division by Zero Handling",
        query="Write code that safely calculates 10/0 and handles the division by zero error, "
              "printing 'Division by zero!' instead of crashing.",
        complexity=Complexity.EDGE_CASE,
        expect_contains="Division by zero",
        description="Exception handling"
    ),

    TestCase(
        name="Empty List Processing",
        query="Calculate the average of an empty list []. Handle the case gracefully "
              "and print a message about empty input.",
        complexity=Complexity.EDGE_CASE,
        expect_contains="empty",
        description="Edge case: empty collection"
    ),

    TestCase(
        name="Large Number Sum",
        query="Calculate the sum of all integers from 1 to 1000000. "
              "请用高效的方法计算并输出结果。",
        complexity=Complexity.MEDIUM,
        expect_numeric=(500000500000, 100),
        description="Large scale arithmetic"
    ),

    TestCase(
        name="String to Number Conversion",
        query="Convert the string '123.45' to a number and verify it equals 123.45. "
              "请用 Python 类型转换并验证。",
        complexity=Complexity.SIMPLE,
        expect_numeric=(123.45, 0.01),
        description="Type conversion"
    ),

    TestCase(
        name="List Comprehension",
        query="Create a list of squares for numbers 1-10: [1, 4, 9, 16, 25, 36, 49, 64, 81, 100]. "
              "请用列表推导式生成并打印。",
        complexity=Complexity.SIMPLE,
        expect_pattern=r"100",
        description="Python idioms: list comprehension"
    ),
]


# ============================================================================
# Register the Classic Suite
# ============================================================================

CLASSIC_CASES = GSM8K_CASES + HUMANEVAL_CASES + MATH_CASES + EDGE_CASES


@register_suite
def _classic_suite() -> TestSuite:
    """Classic LLM Benchmark Test Suite."""
    return TestSuite(
        name="classic",
        description="Classic LLM benchmark problems (GSM8K, HumanEval, MATH)",
        version="1.0.0",
        cases=CLASSIC_CASES,
    )
