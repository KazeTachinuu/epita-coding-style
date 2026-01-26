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


# Test pointer return types (char *, int **, etc.)
@pytest.mark.parametrize("return_type", [
    "char *",
    "int *",
    "void *",
    "char **",
    "int ***",
    "struct foo *",
    "const char *",
    "static char *",
])
def test_func_length_pointer_return_ok(check, return_type):
    """Functions with pointer return types under limit should pass."""
    body = "\n".join(["    x++;"] * 37)
    code = f"{return_type} f(void)\n{{\n    int x = 0;\n{body}\n    return 0;\n}}\n"
    assert not check(code, "fun.length")


@pytest.mark.parametrize("return_type", [
    "char *",
    "int *",
    "void *",
    "char **",
    "int ***",
    "struct foo *",
    "const char *",
    "static char *",
])
def test_func_length_pointer_return_fail(check, return_type):
    """Functions with pointer return types over limit should fail."""
    body = "\n".join(["    x++;"] * 39)
    code = f"{return_type} f(void) {{\n    int x = 0;\n{body}\n    return 0;\n}}\n"
    assert check(code, "fun.length")


@pytest.mark.parametrize("return_type", [
    "char *",
    "int **",
    "void *",
])
def test_arg_count_pointer_return(check, return_type):
    """Arg count check works for functions with pointer return types."""
    # 4 args should pass
    code_ok = f"{return_type} f(int a, int b, int c, int d) {{ return 0; }}\n"
    assert not check(code_ok, "fun.arg.count")
    # 5 args should fail
    code_fail = f"{return_type} f(int a, int b, int c, int d, int e) {{ return 0; }}\n"
    assert check(code_fail, "fun.arg.count")


# Test complex return types (function pointers, array pointers)
@pytest.mark.parametrize("signature,expect_fail", [
    # Function returning pointer to array - over limit
    ("int (*f(void))[10]", True),
    # Function returning function pointer - over limit
    ("int (*f(void))(int)", True),
    # Parenthesized declarator - over limit
    ("int (f)(void)", True),
])
def test_func_length_complex_return_types(check, signature, expect_fail):
    """Function length detection works for complex return types."""
    body = "\n".join(["    x++;"] * 39)
    code = f"{signature} {{\n    int x = 0;\n{body}\n    return 0;\n}}\n"
    assert check(code, "fun.length") == expect_fail


@pytest.mark.parametrize("signature", [
    "int (*f(void))[10]",   # Returns pointer to array
    "int (*f(void))(int)",  # Returns function pointer
])
def test_arg_count_complex_return_types(check, signature):
    """Arg count detection works for complex return types."""
    # Replace (void) with 5 args to trigger violation
    sig_with_args = signature.replace("(void)", "(int a, int b, int c, int d, int e)")
    code = f"{sig_with_args} {{ return 0; }}\n"
    assert check(code, "fun.arg.count")


@pytest.mark.parametrize("code,should_fail", [
    (PROTO_VOID_OK, False),
    (PROTO_EMPTY, True),
])
def test_proto_void(check, code, should_fail):
    assert check(code, "fun.proto.void", suffix=".h") == should_fail
