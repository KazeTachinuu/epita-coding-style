"""Tests for export rules."""

import pytest
from check import Severity


def _make_exported_funcs(n, allman=False, multiline_params=False):
    """Generate n exported functions (K&R, Allman, or multi-line params)."""
    if multiline_params:
        return "\n".join(
            f"int func{i}(int a,\n           int b)\n{{\n    return {i};\n}}"
            for i in range(n)
        ) + "\n"
    if allman:
        return "\n".join(f"int func{i}(void)\n{{\n    return {i};\n}}" for i in range(n)) + "\n"
    return "\n".join(f"int func{i}(void) {{ return {i}; }}" for i in range(n)) + "\n"


def _make_static_funcs(n):
    """Generate n static functions."""
    return "\n".join(f"static int func{i}(void) {{ return {i}; }}" for i in range(n)) + "\n"


# export.fun: max 10 exported functions per .c file
@pytest.mark.parametrize("code,should_fail", [
    (_make_exported_funcs(10), False),
    (_make_exported_funcs(11), True),
    (_make_static_funcs(15), False),  # all static, no limit
])
def test_export_fun(check, code, should_fail):
    assert check(code, "export.fun") == should_fail


# export.fun: Allman style (brace on own line)
@pytest.mark.parametrize("code,should_fail", [
    (_make_exported_funcs(10, allman=True), False),
    (_make_exported_funcs(11, allman=True), True),
])
def test_export_fun_allman(check, code, should_fail):
    assert check(code, "export.fun") == should_fail


# export.fun: Multi-line parameters
@pytest.mark.parametrize("code,should_fail", [
    (_make_exported_funcs(10, multiline_params=True), False),
    (_make_exported_funcs(11, multiline_params=True), True),
])
def test_export_fun_multiline_params(check, code, should_fail):
    assert check(code, "export.fun") == should_fail


def test_export_fun_header_not_checked(check):
    """export.fun rule should not apply to .h files."""
    code = _make_exported_funcs(11)
    assert not check(code, "export.fun", suffix=".h")


def test_export_fun_is_major(check_result):
    """export.fun violations should be MAJOR severity."""
    code = _make_exported_funcs(11)
    result = check_result(code)
    violations = [v for v in result.violations if v.rule == "export.fun"]
    assert len(violations) > 0
    assert all(v.severity == Severity.MAJOR for v in violations)


# Character literals with parens/braces should not throw off function counting
CODE_CHAR_LITERAL_PARENS = """\
int func1(void)
{
    if (c == '(')
        return 1;
    return 0;
}
int func2(void)
{
    if (c == ')')
        return 1;
    return 0;
}
"""

CODE_CHAR_LITERAL_BRACES_IN_FUNC = """\
int func1(void)
{
    if (c == '{')
        return 1;
    return 0;
}
int func2(void)
{
    if (c == '}')
        return 1;
    return 0;
}
"""


def test_export_fun_char_literal_parens(check_result):
    """Parenthesis in char literals like '(' or ')' should not affect function counting."""
    result = check_result(CODE_CHAR_LITERAL_PARENS)
    # Should detect exactly 2 exported functions, not be confused by '(' and ')'
    export_violations = [v for v in result.violations if v.rule == "export.fun"]
    assert len(export_violations) == 0  # 2 functions is under the limit of 10


def test_export_fun_char_literal_braces(check_result):
    """Braces in char literals like '{' or '}' should not affect function counting."""
    result = check_result(CODE_CHAR_LITERAL_BRACES_IN_FUNC)
    # Should detect exactly 2 exported functions, not be confused by '{' and '}'
    export_violations = [v for v in result.violations if v.rule == "export.fun"]
    assert len(export_violations) == 0  # 2 functions is under the limit of 10


# Edge case: brace char literal that could confuse brace depth tracking
CODE_11_FUNCS_WITH_BRACE_CHAR = """\
int f1(void) { return 0; }
int f2(void) { return 0; }
int f3(void) { return 0; }
int f4(void) { return 0; }
int f5(void) { return 0; }
int f6(void) { return 0; }
int f7(void) { return 0; }
int f8(void) { return 0; }
int f9(void) { return 0; }
int f10(void) { return 0; }
int f11(void)
{
    if (c == '}')
        return 1;
    return 0;
}
"""


def test_export_fun_brace_char_depth_tracking(check):
    """11 functions with '}' char literal - should still count as 11 exported functions."""
    # This should trigger export.fun violation (> 10 exported functions)
    assert check(CODE_11_FUNCS_WITH_BRACE_CHAR, "export.fun") == True


# export.other: max 1 non-function exported symbol per .c file
@pytest.mark.parametrize("code,should_fail", [
    ("int global_var;\n", False),
    ("int global_var1;\nint global_var2;\n", True),
])
def test_export_other(check, code, should_fail):
    assert check(code, "export.other") == should_fail


# ===========================================================================
# export.other: Additional tests for robustness
# ===========================================================================

# --- Tests that should NOT trigger (false positive prevention) ---

@pytest.mark.parametrize("code", [
    # Static variables are not exported
    "static int a;\nstatic int b;\nstatic int c;\n",
    # Extern declarations don't define symbols
    "extern int a;\nextern int b;\n",
    # Local variables inside functions
    "void func(void)\n{\n    int i;\n    int endptr;\n}\n",
    # Struct definitions are not variables
    "struct foo {\n    int a;\n    int b;\n};\n",
    # Typedef is not a variable
    "typedef int myint;\ntypedef char mychar;\n",
    # Function prototypes are not variables
    "int func1(void);\nint func2(void);\n",
    # Enum definitions
    "enum color {\n    RED,\n    GREEN,\n    BLUE\n};\n",
    # Preprocessor macros
    "#define A 1\n#define B 2\n",
])
def test_export_other_no_false_positives(check, code):
    """These should NOT trigger export.other violations."""
    assert check(code, "export.other") == False


# --- Tests that SHOULD trigger (false negative prevention) ---

@pytest.mark.parametrize("code,description", [
    ("const int a = 1;\nconst int b = 2;\n", "const globals"),
    ("int *a;\nint *b;\n", "pointer globals"),
    ("int a[10];\nint b[20];\n", "array globals"),
    ("int a = 1;\nint b = 2;\n", "initialized globals"),
])
def test_export_other_basic_detection(check, code, description):
    """Basic cases that must trigger export.other."""
    assert check(code, "export.other") == True, f"Failed to detect: {description}"


# --- Edge cases: char/string literals with braces ---

CODE_CHAR_BRACE_GLOBAL = """\
char c = '{';
int a;
int b;
"""

CODE_STRING_BRACE_GLOBAL = """\
char *s = "{";
int a;
int b;
"""

CODE_COMMENT_BRACE_GLOBAL = """\
/* { */
int a;
int b;
"""

CODE_FUNC_WITH_CHAR_BRACE_THEN_GLOBALS = """\
void func(void)
{
    char c = '}';
}
int a;
int b;
"""

# Critical: '}' in char literal should NOT cause local vars to be seen as global
CODE_FUNC_WITH_CLOSING_BRACE_CHAR_LOCAL_VARS = """\
void func(void)
{
    char c = '}';
    int i;
    int j;
}
"""

# Multiple '}' chars could compound the depth tracking error
CODE_FUNC_WITH_MULTIPLE_BRACE_CHARS = """\
void func(void)
{
    char a = '}';
    char b = '}';
    char c = '}';
    int local1;
    int local2;
}
"""

# String with multiple braces
CODE_FUNC_WITH_BRACE_STRING_LOCAL_VARS = """\
void func(void)
{
    char *s = "}}}{{{";
    int i;
    int j;
}
"""


def test_export_other_char_literal_brace(check):
    """Char literal '{' should not confuse brace depth tracking."""
    assert check(CODE_CHAR_BRACE_GLOBAL, "export.other") == True


def test_export_other_string_literal_brace(check):
    """String literal with brace should not confuse brace depth tracking."""
    assert check(CODE_STRING_BRACE_GLOBAL, "export.other") == True


def test_export_other_comment_brace(check):
    """Comment with brace should not confuse brace depth tracking."""
    assert check(CODE_COMMENT_BRACE_GLOBAL, "export.other") == True


def test_export_other_func_char_brace_then_globals(check):
    """Char '}' in function should not affect global detection after function."""
    assert check(CODE_FUNC_WITH_CHAR_BRACE_THEN_GLOBALS, "export.other") == True


def test_export_other_closing_brace_char_no_false_positive(check):
    """'}' char literal must NOT cause local vars to be misidentified as global."""
    # If brace tracking is broken, '}' would decrement depth to 0,
    # and i, j would be wrongly detected as global
    assert check(CODE_FUNC_WITH_CLOSING_BRACE_CHAR_LOCAL_VARS, "export.other") == False


def test_export_other_multiple_brace_chars_no_false_positive(check):
    """Multiple '}' char literals must NOT compound brace depth errors."""
    # If broken, 3x '}' would make depth = -2, causing false positives
    assert check(CODE_FUNC_WITH_MULTIPLE_BRACE_CHARS, "export.other") == False


def test_export_other_brace_string_no_false_positive(check):
    """String with braces must NOT affect local variable detection."""
    assert check(CODE_FUNC_WITH_BRACE_STRING_LOCAL_VARS, "export.other") == False


# --- Edge cases: various C types ---

@pytest.mark.parametrize("code,description", [
    ("void *a;\nvoid *b;\n", "void pointer"),
    ("int **a;\nint **b;\n", "double pointer"),
    ("long long a;\nlong long b;\n", "long long"),
    ("unsigned long long a;\nunsigned long long b;\n", "unsigned long long"),
    ("_Bool a;\n_Bool b;\n", "_Bool type"),
    ("int8_t a;\nint8_t b;\n", "int8_t"),
    ("uint64_t a;\nuint64_t b;\n", "uint64_t"),
])
def test_export_other_various_types(check, code, description):
    """Various C types must be detected as exported symbols."""
    assert check(code, "export.other") == True, f"Failed to detect: {description}"


# --- Edge case: custom types ---

def test_export_other_custom_type(check):
    """Custom types (without _t suffix) should be detected."""
    code = "MyStruct a;\nMyStruct b;\n"
    assert check(code, "export.other") == True


# --- Edge case: static with qualifiers ---

@pytest.mark.parametrize("code", [
    "const static int a = 1;\nconst static int b = 2;\n",
    "static const int a = 1;\nstatic const int b = 2;\n",
    "volatile static int a;\nvolatile static int b;\n",
])
def test_export_other_static_with_qualifiers(check, code):
    """Static variables with qualifiers should NOT trigger (not exported)."""
    assert check(code, "export.other") == False


# --- Verify severity and file type ---

def test_export_other_is_major(check_result):
    """export.other violations should be MAJOR severity."""
    code = "int a;\nint b;\n"
    result = check_result(code)
    violations = [v for v in result.violations if v.rule == "export.other"]
    assert len(violations) > 0
    assert all(v.severity == Severity.MAJOR for v in violations)


def test_export_other_header_not_checked(check):
    """export.other rule should not apply to .h files."""
    code = "int a;\nint b;\n"
    assert not check(code, "export.other", suffix=".h")
