"""Tests for CXX config handling: idempotency, with_cxx(), language detection."""

import pytest
from epita_coding_style import Config, Lang, lang_from_path


# lang_from_path


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


# Config.with_cxx()


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


def test_with_cxx_respects_user_disabled_cxx_rule():
    """User disabling a CXX rule via config should persist through with_cxx()."""
    cfg = Config()
    cfg.rules["global.casts"] = False
    cfg._user_rules.add("global.casts")
    assert not cfg.with_cxx().is_enabled("global.casts")


def test_with_cxx_respects_user_enabled_c_only_rule():
    """User enabling a C-only rule via config should persist through with_cxx()."""
    cfg = Config()
    cfg.rules["cpp.guard"] = True
    cfg._user_rules.add("cpp.guard")
    assert cfg.with_cxx().is_enabled("cpp.guard")


def test_with_cxx_enables_cxx_rule_without_user_override():
    """CXX rules are auto-enabled when user hasn't explicitly set them."""
    cfg = Config()
    assert not cfg.is_enabled("global.casts")
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
    cfg._user_limits.add("max_lines")
    cxx = cfg.with_cxx()
    assert cxx.max_lines == 25


# CXX defaults disabled


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


# RULES registry invariants


def test_rules_table_well_formed():
    from epita_coding_style.config import RULES
    for name, (desc, category, lang) in RULES.items():
        assert desc and category, name
        assert lang in ("c", "cxx", "both"), name


def test_default_rules_match_registry():
    from epita_coding_style.config import RULES
    cfg = Config()
    assert set(cfg.rules) == set(RULES)
    for name, (_, _, lang) in RULES.items():
        assert cfg.rules[name] == (lang != "cxx"), name


def test_every_rule_has_a_category_slot():
    from epita_coding_style.config import RULES
    from epita_coding_style.checker import CATEGORY_ORDER
    for name, (_, category, _) in RULES.items():
        assert category in CATEGORY_ORDER, name


def test_readme_rule_count_matches_registry():
    import re
    from pathlib import Path
    from epita_coding_style.config import RULES

    readme = Path(__file__).parent.parent / "README.md"
    m = re.search(r"(\d+) rules across", readme.read_text())
    assert m, "README rule-count sentence missing"
    assert int(m.group(1)) == len(RULES)


# config validation


def test_config_unknown_rule_errors(tmp_path, monkeypatch):
    from epita_coding_style import load_config
    from epita_coding_style.config import ConfigError
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".epita-style.toml").write_text('[rules]\n"keyword.gotoo" = false\n')
    with pytest.raises(ConfigError, match="unknown rule"):
        load_config()


def test_config_unknown_key_errors(tmp_path, monkeypatch):
    from epita_coding_style import load_config
    from epita_coding_style.config import ConfigError
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".epita-style.toml").write_text("max_linez = 40\n")
    with pytest.raises(ConfigError, match="unknown key"):
        load_config()


def test_config_malformed_toml_errors(tmp_path, monkeypatch):
    from epita_coding_style import load_config
    from epita_coding_style.config import ConfigError
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".epita-style.toml").write_text("[rules\nbad")
    with pytest.raises(ConfigError, match="invalid TOML"):
        load_config()


def test_config_string_limit_errors(tmp_path, monkeypatch):
    from epita_coding_style import load_config
    from epita_coding_style.config import ConfigError
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".epita-style.toml").write_text('max_lines = "40"\n')
    with pytest.raises(ConfigError, match="must be an integer"):
        load_config()


def test_config_missing_explicit_path_errors(tmp_path):
    from pathlib import Path
    from epita_coding_style import load_config
    from epita_coding_style.config import ConfigError
    with pytest.raises(ConfigError, match="not found"):
        load_config(config_path=tmp_path / "nope.toml")


def test_explicit_max_lines_survives_cxx(tmp_path, monkeypatch):
    from epita_coding_style import load_config
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".epita-style.toml").write_text("max_lines = 30\n")
    assert load_config().with_cxx().max_lines == 30


def test_default_max_lines_bumps_for_cxx():
    assert Config().with_cxx().max_lines == 50
