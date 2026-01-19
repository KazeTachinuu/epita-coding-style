"""Tests for control structure rules."""

import pytest
from textwrap import dedent


@pytest.mark.parametrize("code,should_fail", [
    ("int x = 1;\n", False),
    ('asm("nop");\n', True),
    ('__asm__("nop");\n', True),
])
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
])
def test_ctrl_empty(check, code, should_fail):
    assert check(code, "ctrl.empty") == should_fail
