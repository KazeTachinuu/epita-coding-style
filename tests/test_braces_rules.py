"""Tests for braces rules (Allman style)."""

import pytest


# Allman style code samples
CODE_ALLMAN = """\
void f(void)
{
    if (x)
    {
        y++;
    }
}
"""

CODE_KR_FUNC = """\
void f(void) {
    return;
}
"""

CODE_KR_IF = """\
void f(void)
{
    if (x) {
        y++;
    }
}
"""

CODE_ELSE_SAME_LINE = """\
void f(void)
{
    if (x)
    {
        y++;
    } else {
        z++;
    }
}
"""

CODE_INITIALIZER = """\
int arr[] = {1, 2, 3};
"""

CODE_DO_WHILE = """\
void f(void)
{
    do
    {
        x++;
    } while (x < 10);
}
"""

CODE_MACRO_BRACES = """\
#define MACRO(x) do { \\
    x++; \\
} while (0)
"""

# Character literals containing braces - should NOT trigger violations
CODE_CHAR_LITERAL_OPEN_BRACE = """\
void f(void)
{
    if (input[start] == '{')
    {
        x++;
    }
}
"""

CODE_CHAR_LITERAL_CLOSE_BRACE = """\
void f(void)
{
    while (input[i] && input[i] != '}')
    {
        i++;
    }
    if (input[i] == '}')
    {
        i++;
    }
}
"""

CODE_CHAR_LITERAL_BOTH_BRACES = """\
void f(void)
{
    if (c == '{' || c == '}')
    {
        return 1;
    }
}
"""


# braces: Braces must be on their own line (Allman style)
@pytest.mark.parametrize("code,should_fail", [
    (CODE_ALLMAN, False),
    (CODE_KR_FUNC, True),
    (CODE_KR_IF, True),
    (CODE_ELSE_SAME_LINE, True),
])
def test_braces(check, code, should_fail):
    assert check(code, "braces") == should_fail


# Allowed exceptions to braces rule
@pytest.mark.parametrize("code,should_fail", [
    (CODE_INITIALIZER, False),
    (CODE_DO_WHILE, False),
    (CODE_MACRO_BRACES, False),
])
def test_braces_exceptions(check, code, should_fail):
    assert check(code, "braces") == should_fail


# Character literals containing braces should NOT trigger false positives
@pytest.mark.parametrize("code,should_fail", [
    (CODE_CHAR_LITERAL_OPEN_BRACE, False),
    (CODE_CHAR_LITERAL_CLOSE_BRACE, False),
    (CODE_CHAR_LITERAL_BOTH_BRACES, False),
])
def test_braces_char_literals_not_false_positive(check, code, should_fail):
    """Braces inside character literals like '{' or '}' should not trigger violations."""
    assert check(code, "braces") == should_fail


# Real brace violation on line with '}' char literal - MUST still be caught
CODE_REAL_VIOLATION_WITH_CHAR_LITERAL = """\
void f(void)
{
    if (c == '}') { x++; }
}
"""


def test_braces_real_violation_with_char_literal(check):
    """Real brace violation on same line as '}' char literal must still be caught."""
    assert check(CODE_REAL_VIOLATION_WITH_CHAR_LITERAL, "braces") == True
