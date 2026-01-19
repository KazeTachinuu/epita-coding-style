"""Tests for export rules."""

import pytest
from textwrap import dedent
from epita_coding_style import Severity


def _make_funcs(n, static=False):
    """Generate n functions."""
    prefix = "static " if static else ""
    return "\n".join(
        f"{prefix}int func{i}(void)\n{{\n    return {i};\n}}"
        for i in range(n)
    ) + "\n"


def _make_mixed_funcs(n_exported, n_static):
    """Generate a mix of exported and static functions."""
    exported = "\n".join(
        f"int exported{i}(void)\n{{\n    return {i};\n}}"
        for i in range(n_exported)
    )
    static = "\n".join(
        f"static int static{i}(void)\n{{\n    return {i};\n}}"
        for i in range(n_static)
    )
    return exported + "\n" + static + "\n"


def _make_multiline_funcs(n):
    """Generate n functions with multi-line signatures."""
    return "\n".join(
        f"int func{i}(int a,\n           int b)\n{{\n    return {i};\n}}"
        for i in range(n)
    ) + "\n"


# =============================================================================
# export.fun: max 10 exported functions per .c file
# =============================================================================

@pytest.mark.parametrize("code,should_fail", [
    (_make_funcs(10), False),
    (_make_funcs(11), True),
    (_make_funcs(15, static=True), False),
    (_make_multiline_funcs(10), False),
    (_make_multiline_funcs(11), True),
    (_make_mixed_funcs(10, 5), False),  # 10 exported + 5 static = OK
    (_make_mixed_funcs(11, 5), True),   # 11 exported + 5 static = fail
])
def test_export_fun(check, code, should_fail):
    assert check(code, "export.fun") == should_fail


def test_export_fun_header_not_checked(check):
    assert not check(_make_funcs(11), "export.fun", suffix=".h")


def test_export_fun_is_major(check_result):
    violations = [v for v in check_result(_make_funcs(11)) if v.rule == "export.fun"]
    assert violations and all(v.severity == Severity.MAJOR for v in violations)


# =============================================================================
# export.other: max 1 exported global per .c file
# =============================================================================

STATIC_VARS = dedent("""\
    static int a;
    static int b;
""")

EXTERN_VARS = dedent("""\
    extern int a;
    extern int b;
""")

LOCAL_VARS = dedent("""\
    void f(void)
    {
        int i;
        int j;
    }
""")

STRUCT_DEF = dedent("""\
    struct foo {
        int a;
        int b;
    };
""")

TYPEDEF_DEF = dedent("""\
    typedef int myint;
    typedef char mychar;
""")

PROTO_DEF = dedent("""\
    int f1(void);
    int f2(void);
""")

CONST_STATIC = dedent("""\
    const static int a = 1;
    const static int b = 2;
""")

CHAR_BRACE_LOCAL = dedent("""\
    void f(void)
    {
        char c = '}';
        int i;
        int j;
    }
""")

STRING_BRACE_LOCAL = dedent("""\
    void f(void)
    {
        char *s = "}}}{{";
        int i;
        int j;
    }
""")


@pytest.mark.parametrize("code,should_fail", [
    ("int global_var;\n", False),
    ("int a;\nint b;\n", True),
])
def test_export_other(check, code, should_fail):
    assert check(code, "export.other") == should_fail


@pytest.mark.parametrize("code", [
    STATIC_VARS,
    EXTERN_VARS,
    LOCAL_VARS,
    STRUCT_DEF,
    TYPEDEF_DEF,
    PROTO_DEF,
    CONST_STATIC,
    CHAR_BRACE_LOCAL,
    STRING_BRACE_LOCAL,
])
def test_export_other_not_exported(check, code):
    assert not check(code, "export.other")


@pytest.mark.parametrize("code", [
    "const int a = 1;\nconst int b = 2;\n",
    "int *a;\nint *b;\n",
    "int a[10];\nint b[20];\n",
    "char c = '{';\nint a;\nint b;\n",
])
def test_export_other_multiple_globals(check, code):
    assert check(code, "export.other")


def test_export_other_header_not_checked(check):
    assert not check("int a;\nint b;\n", "export.other", suffix=".h")


def test_export_other_is_major(check_result):
    violations = [v for v in check_result("int a;\nint b;\n") if v.rule == "export.other"]
    assert violations and all(v.severity == Severity.MAJOR for v in violations)
