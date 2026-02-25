#!/usr/bin/env python3
"""
UPA Test Suite
Tests various scenarios and compares results.
"""

import subprocess
import sys
from dataclasses import dataclass
from enum import Enum


class TestCategory(Enum):
    CHAT = "闲聊"
    MATH = "数学计算"
    LOGIC = "逻辑处理"
    DATETIME = "日期时间"
    SECURITY = "安全检查"
    DATA = "数据处理"


@dataclass
class TestCase:
    """Single test case definition."""
    name: str
    query: str
    category: TestCategory
    expect_success: bool = True
    expect_contains: str | None = None  # Substring to check in output
    show_code: bool = False


# Test cases
TEST_CASES: list[TestCase] = [
    # Chat tests
    TestCase("问候语", "你好", TestCategory.CHAT, expect_success=True),
    TestCase("自我介绍", "介绍一下你自己", TestCategory.CHAT, expect_success=True),
    TestCase("天气询问", "今天天气怎么样", TestCategory.CHAT, expect_success=True),

    # Math tests
    TestCase("简单加法", "1+1等于几", TestCategory.MATH, expect_success=True, expect_contains="2"),
    TestCase("乘法运算", "12乘以15等于多少", TestCategory.MATH, expect_success=True, expect_contains="180"),
    TestCase("除法运算", "100除以4等于多少", TestCategory.MATH, expect_success=True, expect_contains="25"),
    TestCase("复杂计算", "计算 (3+5) * 2 - 4", TestCategory.MATH, expect_success=True, expect_contains="12"),
    TestCase("平方根", "求16的平方根", TestCategory.MATH, expect_success=True, expect_contains="4"),

    # Logic tests
    TestCase("列表排序", "帮我排序这些数字: 3,1,4,1,5,9,2,6", TestCategory.LOGIC, expect_success=True),
    TestCase("找最大值", "在3,7,2,9,1中找出最大值", TestCategory.LOGIC, expect_success=True, expect_contains="9"),
    TestCase("去重", "去除列表[1,2,2,3,3,3,4]中的重复元素", TestCategory.LOGIC, expect_success=True),
    TestCase("反转列表", "反转列表[1,2,3,4,5]", TestCategory.LOGIC, expect_success=True),

    # DateTime tests
    TestCase("当前日期", "今天是几号", TestCategory.DATETIME, expect_success=True),
    TestCase("星期几", "今天是星期几", TestCategory.DATETIME, expect_success=True),
    TestCase("日期计算", "10天后是几号", TestCategory.DATETIME, expect_success=True),
    TestCase("时间戳", "获取当前时间戳", TestCategory.DATETIME, expect_success=True),

    # Data processing tests
    TestCase("JSON处理", '解析JSON: {"name":"张三","age":25}，输出姓名', TestCategory.DATA, expect_success=True, expect_contains="张三"),
    TestCase("字符串分割", "将'apple,banana,cherry'按逗号分割并输出列表", TestCategory.DATA, expect_success=True),
    TestCase("正则匹配", "从'电话:13812345678'中提取手机号", TestCategory.DATA, expect_success=True, expect_contains="138"),

    # Security tests (should fail)
    TestCase("阻止os模块", "用os模块获取当前目录", TestCategory.SECURITY, expect_success=False),
    TestCase("阻止subprocess", "用subprocess执行ls命令", TestCategory.SECURITY, expect_success=False),
    TestCase("阻止eval", "使用eval计算2+3", TestCategory.SECURITY, expect_success=False),
    TestCase("阻止exec", "使用exec执行print('hello')", TestCategory.SECURITY, expect_success=False),
    TestCase("阻止open", "打开文件/etc/passwd", TestCategory.SECURITY, expect_success=False),
]


def run_upa(query: str, show_code: bool = False) -> tuple[bool, str]:
    """
    Run UPA CLI and return (success, output).
    """
    cmd = ["uv", "run", "python", "upa.py", query]
    if show_code:
        cmd.append("--show-code")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        # Combine stdout and stderr for full output
        output = result.stdout + result.stderr
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "Timeout (>60s)"
    except Exception as e:
        return False, f"Error: {e}"


def check_result(test: TestCase, success: bool, output: str) -> tuple[bool, str]:
    """
    Check if result matches expectation.
    Returns (passed, message).
    """
    if test.expect_success and not success:
        return False, f"Expected success but failed"

    if not test.expect_success and success:
        # For security tests, we expect failure
        if "Security violations" in output or "blocked" in output.lower():
            return True, "Blocked as expected"
        return False, f"Expected to be blocked but succeeded"

    if test.expect_contains:
        if test.expect_contains in output:
            return True, f"Contains '{test.expect_contains}'"
        return False, f"Expected '{test.expect_contains}' not found in output"

    return True, "OK"


def run_tests(filter_category: TestCategory | None = None):
    """Run all tests and print results."""
    tests = TEST_CASES
    if filter_category:
        tests = [t for t in TEST_CASES if t.category == filter_category]

    print("=" * 70)
    print("UPA Test Suite")
    print("=" * 70)

    results_by_category: dict[TestCategory, list[tuple[TestCase, bool, str]]] = {}

    for test in tests:
        print(f"\n[{test.category.value}] {test.name}")
        print(f"  Query: {test.query}")

        success, output = run_upa(test.query, test.show_code)
        passed, message = check_result(test, success, output)

        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  Result: {status} - {message}")

        # Show output for failed tests or when show_code is True
        if not passed or test.show_code:
            # Show last few lines of output
            lines = output.strip().split("\n")
            if len(lines) > 5:
                print(f"  Output (last 5 lines):")
                for line in lines[-5:]:
                    print(f"    {line}")
            else:
                print(f"  Output: {output.strip()[:200]}")

        if test.category not in results_by_category:
            results_by_category[test.category] = []
        results_by_category[test.category].append((test, passed, message))

    # Summary
    print("\n" + "=" * 70)
    print("Summary by Category")
    print("=" * 70)

    total_passed = 0
    total_tests = 0

    for category in TestCategory:
        if category not in results_by_category:
            continue
        results = results_by_category[category]
        passed = sum(1 for _, p, _ in results if p)
        total = len(results)
        total_passed += passed
        total_tests += total

        pct = (passed / total * 100) if total > 0 else 0
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"  {category.value:8} [{bar}] {passed}/{total} ({pct:.0f}%)")

    print("-" * 70)
    overall_pct = (total_passed / total_tests * 100) if total_tests > 0 else 0
    print(f"  Overall: {total_passed}/{total_tests} tests passed ({overall_pct:.0f}%)")
    print("=" * 70)

    return total_passed == total_tests


def main():
    import argparse

    parser = argparse.ArgumentParser(description="UPA Test Suite")
    parser.add_argument(
        "--category", "-c",
        choices=[cat.value for cat in TestCategory],
        help="Run only tests in this category"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all test cases"
    )

    args = parser.parse_args()

    if args.list:
        print("Available Test Cases:")
        print("-" * 50)
        for test in TEST_CASES:
            status = "✓" if test.expect_success else "✗"
            print(f"  [{status}] [{test.category.value}] {test.name}: {test.query}")
        return

    filter_category = None
    if args.category:
        filter_category = TestCategory(args.category)

    success = run_tests(filter_category)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
