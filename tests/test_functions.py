"""Tests for function-level rules."""

from textwrap import dedent

import pytest

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
], ids=["void-ok", "4-args-ok", "5-args-fail", "multiline-4-ok", "multiline-6-fail"])
def test_arg_count(rules, code, should_fail):
    assert ("fun.arg.count" in rules(code)) == should_fail


def test_arg_count_is_major(lint):
    code = "int f(int a, int b, int c, int d, int e) { return 0; }\n"
    violations = [v for v in lint(code) if v.rule == "fun.arg.count"]
    assert violations and all(v.severity == Severity.MAJOR for v in violations)


def test_func_length_40_ok(rules):
    body = "\n".join(["    x++;"] * 37)
    code = f"void f(void)\n{{\n    int x = 0;\n{body}\n    return;\n}}\n"
    assert "fun.length" not in rules(code, preset="42sh")


def test_func_length_41_fail(rules):
    body = "\n".join(["    x++;"] * 39)
    code = f"void f(void) {{\n    int x = 0;\n{body}\n    return;\n}}\n"
    assert "fun.length" in rules(code, preset="42sh")


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
], ids=["char*", "int*", "void*", "char**", "int***",
        "struct-foo*", "const-char*", "static-char*"])
def test_func_length_pointer_return_ok(rules, return_type):
    """Functions with pointer return types under limit should pass."""
    body = "\n".join(["    x++;"] * 37)
    code = f"{return_type} f(void)\n{{\n    int x = 0;\n{body}\n    return 0;\n}}\n"
    assert "fun.length" not in rules(code, preset="42sh")


@pytest.mark.parametrize("return_type", [
    "char *",
    "int *",
    "void *",
    "char **",
    "int ***",
    "struct foo *",
    "const char *",
    "static char *",
], ids=["char*", "int*", "void*", "char**", "int***",
        "struct-foo*", "const-char*", "static-char*"])
def test_func_length_pointer_return_fail(rules, return_type):
    """Functions with pointer return types over limit should fail."""
    body = "\n".join(["    x++;"] * 39)
    code = f"{return_type} f(void) {{\n    int x = 0;\n{body}\n    return 0;\n}}\n"
    assert "fun.length" in rules(code, preset="42sh")


@pytest.mark.parametrize("return_type", [
    "char *",
    "int **",
    "void *",
], ids=["char*", "int**", "void*"])
def test_arg_count_pointer_return(rules, return_type):
    """Arg count check works for functions with pointer return types."""
    # 4 args should pass
    code_ok = f"{return_type} f(int a, int b, int c, int d) {{ return 0; }}\n"
    assert "fun.arg.count" not in rules(code_ok)
    # 5 args should fail
    code_fail = f"{return_type} f(int a, int b, int c, int d, int e) {{ return 0; }}\n"
    assert "fun.arg.count" in rules(code_fail)


# Test complex return types (function pointers, array pointers)
@pytest.mark.parametrize("signature,expect_fail", [
    # Function returning pointer to array - over limit
    ("int (*f(void))[10]", True),
    # Function returning function pointer - over limit
    ("int (*f(void))(int)", True),
    # Parenthesized declarator - over limit
    ("int (f)(void)", True),
], ids=["ptr-to-array", "func-ptr", "paren-declarator"])
def test_func_length_complex_return_types(rules, signature, expect_fail):
    """Function length detection works for complex return types."""
    body = "\n".join(["    x++;"] * 39)
    code = f"{signature} {{\n    int x = 0;\n{body}\n    return 0;\n}}\n"
    assert ("fun.length" in rules(code, preset="42sh")) == expect_fail


@pytest.mark.parametrize("signature", [
    "int (*f(void))[10]",   # Returns pointer to array
    "int (*f(void))(int)",  # Returns function pointer
], ids=["ptr-to-array", "func-ptr"])
def test_arg_count_complex_return_types(rules, signature):
    """Arg count detection works for complex return types."""
    # Replace (void) with 5 args to trigger violation
    sig_with_args = signature.replace("(void)", "(int a, int b, int c, int d, int e)")
    code = f"{sig_with_args} {{ return 0; }}\n"
    assert "fun.arg.count" in rules(code)


@pytest.mark.parametrize("code,should_fail", [
    (PROTO_VOID_OK, False),
    (PROTO_EMPTY, True),
], ids=["void-ok", "empty-parens-fail"])
def test_proto_void(rules, code, should_fail):
    assert ("fun.proto.void" in rules(code, ".h")) == should_fail


@pytest.mark.parametrize("code,should_fail", [
    ("void f(int);\n", False),
    ("void (*fp)();\n", False),
    ("void f();\n", True),
], ids=["proto-with-arg", "func-pointer", "proto-empty"])
def test_fun_proto_void_header_edges(rules, code, should_fail):
    assert ("fun.proto.void" in rules(code, ".h")) == should_fail
