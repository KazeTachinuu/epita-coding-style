"""Tests for braces rules (Allman style)."""

import pytest
from textwrap import dedent

# Valid Allman style
ALLMAN = dedent("""\
    void f(void)
    {
        if (x)
        {
            y++;
        }
    }
""")

# K&R violations
KR_FUNC = dedent("""\
    void f(void) {
        return;
    }
""")

KR_IF = dedent("""\
    void f(void)
    {
        if (x) {
            y++;
        }
    }
""")

ELSE_SAME_LINE = dedent("""\
    void f(void)
    {
        if (x)
        {
            y++;
        } else {
            z++;
        }
    }
""")

# Allowed exceptions
DO_WHILE = dedent("""\
    void f(void)
    {
        do
        {
            x++;
        } while (x < 10);
    }
""")

MACRO = dedent("""\
    #define MACRO(x) do { \\
        x++; \\
    } while (0)
""")

# Char literals with braces
CHAR_OPEN = dedent("""\
    void f(void)
    {
        if (input[start] == '{')
        {
            x++;
        }
    }
""")

CHAR_CLOSE = dedent("""\
    void f(void)
    {
        while (input[i] && input[i] != '}')
        {
            i++;
        }
    }
""")

CHAR_BOTH = dedent("""\
    void f(void)
    {
        if (c == '{' || c == '}')
        {
            return 1;
        }
    }
""")

CHAR_WITH_VIOLATION = dedent("""\
    void f(void)
    {
        if (c == '}') { x++; }
    }
""")


@pytest.mark.parametrize("code,should_fail", [
    (ALLMAN, False),
    (KR_FUNC, True),
    (KR_IF, True),
    (ELSE_SAME_LINE, True),
])
def test_braces(check, code, should_fail):
    # Use noformat preset to test braces independently from clang-format
    assert check(code, "braces", preset="noformat") == should_fail


@pytest.mark.parametrize("code", [
    "int arr[] = {1, 2, 3};\n",
    DO_WHILE,
    MACRO,
])
def test_braces_exceptions(check, code):
    assert not check(code, "braces", preset="noformat")


@pytest.mark.parametrize("code", [CHAR_OPEN, CHAR_CLOSE, CHAR_BOTH])
def test_braces_char_literals_no_false_positive(check, code):
    assert not check(code, "braces", preset="noformat")


def test_braces_char_literal_with_violation(check):
    assert check(CHAR_WITH_VIOLATION, "braces", preset="noformat")
