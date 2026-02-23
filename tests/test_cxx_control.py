"""Tests for CXX control flow rules."""


class TestCtrlSwitch:
    """Tests for ctrl.switch rule (default case required)."""

    def test_switch_without_default(self, check_cxx):
        code = "void foo(int x) { switch (x) { case 1: break; } }\n"
        assert check_cxx(code, "ctrl.switch")

    def test_switch_with_default_ok(self, check_cxx):
        code = "void foo(int x) { switch (x) { case 1: break; default: break; } }\n"
        assert not check_cxx(code, "ctrl.switch")


class TestCtrlSwitchPadding:
    """Tests for ctrl.switch.padding rule (no space before colon)."""

    def test_space_before_colon(self, check_cxx):
        code = "void foo(int x) {\n    switch (x) {\n    case 1 :\n        break;\n    default:\n        break;\n    }\n}\n"
        assert check_cxx(code, "ctrl.switch.padding")

    def test_no_space_before_colon_ok(self, check_cxx):
        code = "void foo(int x) {\n    switch (x) {\n    case 1:\n        break;\n    default:\n        break;\n    }\n}\n"
        assert not check_cxx(code, "ctrl.switch.padding")


class TestCtrlEmpty:
    """Tests for ctrl.empty rule (empty loop bodies)."""

    def test_empty_while_body(self, check_cxx):
        code = "void foo() {\n    while (true)\n        ;\n}\n"
        assert check_cxx(code, "ctrl.empty")
