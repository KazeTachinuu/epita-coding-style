"""Tests for function-level rules."""

import pytest
from textwrap import dedent
from epita_coding_style import Severity

# Multi-line function signatures
MULTILINE_6_ARGS = dedent("""\
    void handle_unquoted(char **p, struct Ast_node *ast,
                         struct Ast_node **current_cmd,
                         struct Ast_node *merge_target, int *is_first,
                         int *force_new)
    {
        return;
    }
""")

MULTILINE_4_ARGS = dedent("""\
    void foo(int a, int b,
             int c, int d)
    {
        return;
    }
""")

PROTO_VOID_OK = dedent("""\
    #ifndef T_H
    #define T_H
    void f(void);
    #endif /* T_H */
""")

PROTO_EMPTY = dedent("""\
    #ifndef T_H
    #define T_H
    void f();
    #endif /* T_H */
""")


@pytest.mark.parametrize("code,should_fail", [
    ("void f(void) { return; }\n", False),
    ("int f(int a, int b, int c, int d) { return 0; }\n", False),
    ("int f(int a, int b, int c, int d, int e) { return 0; }\n", True),
    (MULTILINE_4_ARGS, False),
    (MULTILINE_6_ARGS, True),
])
def test_arg_count(check, code, should_fail):
    assert check(code, "fun.arg.count") == should_fail


def test_arg_count_is_major(check_result):
    code = "int f(int a, int b, int c, int d, int e) { return 0; }\n"
    violations = [v for v in check_result(code) if v.rule == "fun.arg.count"]
    assert violations and all(v.severity == Severity.MAJOR for v in violations)


def test_func_length_40_ok(check):
    body = "\n".join(["    x++;"] * 37)
    code = f"void f(void)\n{{\n    int x = 0;\n{body}\n    return;\n}}\n"
    assert not check(code, "fun.length")


def test_func_length_41_fail(check):
    body = "\n".join(["    x++;"] * 39)
    code = f"void f(void) {{\n    int x = 0;\n{body}\n    return;\n}}\n"
    assert check(code, "fun.length")


@pytest.mark.parametrize("code,should_fail", [
    (PROTO_VOID_OK, False),
    (PROTO_EMPTY, True),
])
def test_proto_void(check, code, should_fail):
    assert check(code, "fun.proto.void", suffix=".h") == should_fail
