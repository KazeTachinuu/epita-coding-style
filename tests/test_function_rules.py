"""Tests for function-level rules."""

import pytest
from check import Severity


# fun.arg.count: max 4 arguments
@pytest.mark.parametrize("code,should_fail", [
    ("void f(void) { return; }\n", False),
    ("int f(int a, int b, int c, int d) { return 0; }\n", False),
    ("int f(int a, int b, int c, int d, int e) { return 0; }\n", True),
])
def test_arg_count(check, code, should_fail):
    assert check(code, "fun.arg.count") == should_fail


def test_arg_count_is_major(check_result):
    code = "int f(int a, int b, int c, int d, int e) { return 0; }\n"
    result = check_result(code)
    violations = [v for v in result.violations if v.rule == "fun.arg.count"]
    assert all(v.severity == Severity.MAJOR for v in violations)


# fun.length: max 40 lines
def test_func_length_40_passes(check):
    body = "\n".join(["    x++;"] * 37)
    code = f"void f(void)\n{{\n    int x = 0;\n{body}\n    return;\n}}\n"
    assert not check(code, "fun.length")


def test_func_length_41_fails(check):
    body = "\n".join(["    x++;"] * 39)
    code = f"void f(void) {{\n    int x = 0;\n{body}\n    return;\n}}\n"
    assert check(code, "fun.length")


# fun.proto.void: empty params should be 'void'
@pytest.mark.parametrize("code,should_fail", [
    ("#ifndef T_H\n#define T_H\nvoid f(void);\n#endif /* T_H */\n", False),
    ("#ifndef T_H\n#define T_H\nvoid f();\n#endif /* T_H */\n", True),
])
def test_proto_void(check, code, should_fail):
    assert check(code, "fun.proto.void", suffix=".h") == should_fail
