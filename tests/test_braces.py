"""Tests for braces rules (Allman style)."""

import shutil
from textwrap import dedent

import pytest

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
], ids=["allman-ok", "kr-func", "kr-if", "else-same-line"])
def test_braces(rules, code, should_fail):
    # Use noformat preset to test braces independently from clang-format
    assert ("braces" in rules(code, preset="noformat")) == should_fail


@pytest.mark.parametrize("code", [
    "int arr[] = {1, 2, 3};\n",
    DO_WHILE,
    MACRO,
], ids=["array-init", "do-while", "macro"])
def test_braces_exceptions(rules, code):
    assert "braces" not in rules(code, preset="noformat")


@pytest.mark.parametrize("code", [CHAR_OPEN, CHAR_CLOSE, CHAR_BOTH],
                         ids=["char-open", "char-close", "char-both"])
def test_braces_char_literals_no_false_positive(rules, code):
    assert "braces" not in rules(code, preset="noformat")


def test_braces_char_literal_with_violation(rules):
    assert "braces" in rules(CHAR_WITH_VIOLATION, preset="noformat")


def test_braces_fallback_when_clang_format_missing(rules, monkeypatch):
    """Without clang-format, check_braces takes over instead of silence."""
    monkeypatch.setattr(shutil, "which", lambda _: None)
    found = rules("void f(void) {\n    return;\n}\n")
    assert "braces" in found and "format" not in found
