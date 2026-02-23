"""Tests for CXX control flow rules."""

import pytest
from textwrap import dedent


# ── ctrl.switch ──────────────────────────────────────────────────────────

SWITCH_NO_DEFAULT = "void foo(int x) { switch (x) { case 1: break; } }\n"

SWITCH_WITH_DEFAULT = "void foo(int x) { switch (x) { case 1: break; default: break; } }\n"


@pytest.mark.parametrize("code,should_fail", [
    (SWITCH_WITH_DEFAULT, False),
    (SWITCH_NO_DEFAULT, True),
], ids=["with-default", "without-default"])
def test_ctrl_switch(check_cxx, code, should_fail):
    assert check_cxx(code, "ctrl.switch") == should_fail


# ── ctrl.switch.padding ─────────────────────────────────────────────────

SWITCH_SPACE_BEFORE_COLON = dedent("""\
    void foo(int x)
    {
        switch (x)
        {
        case 1 :
            break;
        default:
            break;
        }
    }
""")

SWITCH_NO_SPACE_BEFORE_COLON = dedent("""\
    void foo(int x)
    {
        switch (x)
        {
        case 1:
            break;
        default:
            break;
        }
    }
""")


@pytest.mark.parametrize("code,should_fail", [
    (SWITCH_NO_SPACE_BEFORE_COLON, False),
    (SWITCH_SPACE_BEFORE_COLON, True),
], ids=["no-space", "space-before-colon"])
def test_ctrl_switch_padding(check_cxx, code, should_fail):
    assert check_cxx(code, "ctrl.switch.padding") == should_fail


# ── ctrl.empty ───────────────────────────────────────────────────────────

EMPTY_WHILE_BODY = dedent("""\
    void foo()
    {
        while (true)
            ;
    }
""")

WHILE_WITH_CONTINUE = dedent("""\
    void foo()
    {
        while (true)
        {
            continue;
        }
    }
""")


@pytest.mark.parametrize("code,should_fail", [
    (WHILE_WITH_CONTINUE, False),
    (EMPTY_WHILE_BODY, True),
], ids=["continue-ok", "empty-while"])
def test_ctrl_empty(check_cxx, code, should_fail):
    assert check_cxx(code, "ctrl.empty") == should_fail
