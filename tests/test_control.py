"""Tests for control structure rules."""

from textwrap import dedent

import pytest


@pytest.mark.parametrize("code,should_fail", [
    ("int x = 1;\n", False),
    ('asm("nop");\n', True),
    ('__asm__("nop");\n', True),
], ids=["no-asm", "asm", "__asm__"])
def test_stat_asm(rules, code, should_fail):
    assert ("stat.asm" in rules(code)) == should_fail


CTRL_OK = dedent("""\
    void f(void)
    {
        while (x)
        {
            continue;
        }
    }
""")

CTRL_WHILE_FAIL = dedent("""\
    void f(void)
    {
        while (x)
            ;
    }
""")

CTRL_FOR_FAIL = dedent("""\
    void f(void)
    {
        for (;;)
            ;
    }
""")


@pytest.mark.parametrize("code,should_fail", [
    (CTRL_OK, False),
    (CTRL_WHILE_FAIL, True),
    (CTRL_FOR_FAIL, True),
], ids=["while-body-ok", "while-empty", "for-empty"])
def test_ctrl_empty(rules, code, should_fail):
    assert ("ctrl.empty" in rules(code)) == should_fail


@pytest.mark.parametrize("code,rule,should_fail", [
    ('char *s = "goto out";\n', "keyword.goto", False),
    ("void f(void)\n{\n    goto out;\nout:\n    return;\n}\n", "keyword.goto", True),
    ("void f(int x)\n{\n    int y = (x);\n}\n", "cast", False),
    ("int g(int a, int b);\nvoid f(int a, int b)\n{\n    g((a) + b, b);\n}\n", "cast", False),
    ("int g(void);\nvoid f(void)\n{\n    (void)g();\n}\n", "cast", True),
], ids=["goto-in-string", "goto-real", "parenthesized-not-cast",
        "paren-expr-arg", "void-discard-is-cast"])
def test_goto_cast_edges(rules, code, rule, should_fail):
    assert (rule in rules(code)) == should_fail


@pytest.mark.parametrize("code,should_fail", [
    ('char *s = "asm(nop)";\n', False),
    ('void f(void)\n{\n    __asm__("nop");\n}\n', True),
], ids=["asm-in-string", "asm-real"])
def test_stat_asm_edges(rules, code, should_fail):
    assert ("stat.asm" in rules(code)) == should_fail


def test_ctrl_empty_braced_body(rules):
    assert "ctrl.empty" in rules("void f(void)\n{\n    while (1)\n    {\n    }\n}\n")
