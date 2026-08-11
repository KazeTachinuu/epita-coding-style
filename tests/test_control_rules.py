"""Tests for control structure rules."""

import pytest
from textwrap import dedent


@pytest.mark.parametrize("code,should_fail", [
    ("int x = 1;\n", False),
    ('asm("nop");\n', True),
    ('__asm__("nop");\n', True),
], ids=["no-asm", "asm", "__asm__"])
def test_stat_asm(check, code, should_fail):
    assert check(code, "stat.asm") == should_fail


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
def test_ctrl_empty(check, code, should_fail):
    assert check(code, "ctrl.empty") == should_fail


@pytest.mark.parametrize("code,rule,should_fail", [
    ('char *s = "goto out";\n', "keyword.goto", False),
    ("void f(void)\n{\n    goto out;\nout:\n    return;\n}\n", "keyword.goto", True),
    ("void f(int x)\n{\n    int y = (x);\n}\n", "cast", False),
    ("int g(int a, int b);\nvoid f(int a, int b)\n{\n    g((a) + b, b);\n}\n", "cast", False),
    ("int g(void);\nvoid f(void)\n{\n    (void)g();\n}\n", "cast", True),
], ids=["goto-in-string", "goto-real", "parenthesized-not-cast",
        "paren-expr-arg", "void-discard-is-cast"])
def test_goto_cast_edges(check, code, rule, should_fail):
    assert check(code, rule, preset=None) == should_fail


@pytest.mark.parametrize("code,should_fail", [
    ('char *s = "asm(nop)";\n', False),
    ('void f(void)\n{\n    __asm__("nop");\n}\n', True),
], ids=["asm-in-string", "asm-real"])
def test_stat_asm_edges(check, code, should_fail):
    assert check(code, "stat.asm") == should_fail


def test_ctrl_empty_braced_body(check):
    assert check("void f(void)\n{\n    while (1)\n    {\n    }\n}\n", "ctrl.empty")
