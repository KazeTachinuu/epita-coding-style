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
