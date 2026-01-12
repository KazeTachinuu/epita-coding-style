"""Tests for control structure rules."""

import pytest


# stat.asm: no asm declarations
@pytest.mark.parametrize("code,should_fail", [
    ("int x = 1;\n", False),
    ("asm(\"nop\");\n", True),
    ("__asm__(\"nop\");\n", True),
])
def test_stat_asm(check, code, should_fail):
    assert check(code, "stat.asm") == should_fail


# ctrl.empty: empty loops should use continue (semicolon on own line)
@pytest.mark.parametrize("code,should_fail", [
    ("void f(void)\n{\n    while (x)\n    {\n        continue;\n    }\n}\n", False),
    ("void f(void)\n{\n    while (x)\n        ;\n}\n", True),
    ("void f(void)\n{\n    for (;;)\n        ;\n}\n", True),
])
def test_ctrl_empty(check, code, should_fail):
    assert check(code, "ctrl.empty") == should_fail
