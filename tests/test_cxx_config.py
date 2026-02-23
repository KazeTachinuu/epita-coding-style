"""Tests for CXX config handling — idempotency, with_cxx(), language detection."""

import pytest
from epita_coding_style import Config, Lang, lang_from_path


# ── lang_from_path ───────────────────────────────────────────────────────


@pytest.mark.parametrize("path,expected", [
    ("foo.c", Lang.C),
    ("foo.h", Lang.C),
    ("foo.cc", Lang.CXX),
    ("foo.hh", Lang.CXX),
    ("foo.hxx", Lang.CXX),
    ("foo.py", None),
    ("/some/dir/foo.cc", Lang.CXX),
], ids=["c-source", "c-header", "cxx-source", "cxx-header", "cxx-hxx", "unknown-ext", "nested-path"])
def test_lang_from_path(path, expected):
    assert lang_from_path(path) == expected


# ── Config.with_cxx() ───────────────────────────────────────────────────


def test_with_cxx_returns_new_config():
    cfg = Config()
    cxx = cfg.with_cxx()
    assert cxx is not cfg


def test_with_cxx_does_not_mutate_original():
    cfg = Config()
    original_rules = dict(cfg.rules)
    cfg.with_cxx()
    assert cfg.rules == original_rules


def test_with_cxx_idempotent():
    """Calling with_cxx() twice should produce equivalent configs."""
    cfg = Config()
    cxx1 = cfg.with_cxx()
    cxx2 = cfg.with_cxx()
    assert cxx1.rules == cxx2.rules
    assert cxx1.max_lines == cxx2.max_lines


@pytest.mark.parametrize("rule", [
    "global.casts", "global.nullptr", "naming.class",
    "cpp.pragma.once", "enum.class", "fun.proto.void.cxx",
], ids=["casts", "nullptr", "naming-class", "pragma-once", "enum-class", "proto-void-cxx"])
def test_with_cxx_enables_cxx_rules(rule):
    assert Config().with_cxx().is_enabled(rule)


@pytest.mark.parametrize("rule", [
    "cpp.guard", "export.fun", "export.other",
    "fun.proto.void", "keyword.goto", "cast",
], ids=["guard", "export-fun", "export-other", "proto-void", "goto", "cast"])
def test_with_cxx_disables_c_only_rules(rule):
    assert not Config().with_cxx().is_enabled(rule)


@pytest.mark.parametrize("rule", [
    "file.dos", "file.trailing", "lines.empty",
], ids=["file-dos", "file-trailing", "lines-empty"])
def test_with_cxx_preserves_shared_rules(rule):
    assert Config().with_cxx().is_enabled(rule)


def test_with_cxx_max_lines_50():
    assert Config().with_cxx().max_lines == 50


def test_with_cxx_overrides_user_disabled_cxx_rule():
    """User disabling a CXX rule should persist through with_cxx()."""
    cfg = Config()
    cfg.rules["global.casts"] = False
    # with_cxx enables all CXX rules, overriding user choice
    # This is intentional — CXX rules are always on for CXX files
    assert cfg.with_cxx().is_enabled("global.casts")


def test_with_cxx_preserves_user_limits():
    """with_cxx sets max_lines=50, but preserves other user limits."""
    cfg = Config()
    cfg.max_args = 6
    cxx = cfg.with_cxx()
    assert cxx.max_args == 6
    assert cxx.max_lines == 50


def test_with_cxx_preserves_user_max_lines():
    """Regression: user-specified max_lines must not be overridden to 50."""
    cfg = Config()
    cfg.max_lines = 25
    cxx = cfg.with_cxx()
    assert cxx.max_lines == 25


# ── CXX defaults disabled ───────────────────────────────────────────────


@pytest.mark.parametrize("rule", [
    "global.casts", "naming.class", "cpp.pragma.once", "enum.class",
], ids=["casts", "naming-class", "pragma-once", "enum-class"])
def test_cxx_rules_disabled_by_default(rule):
    assert not Config().is_enabled(rule)


@pytest.mark.parametrize("rule", [
    "fun.proto.void", "cpp.guard", "export.fun",
], ids=["proto-void", "guard", "export-fun"])
def test_c_rules_enabled_by_default(rule):
    assert Config().is_enabled(rule)
