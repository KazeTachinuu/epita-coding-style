"""Tests for config loading, discovery, validation and the rule registry."""

import pytest

from epita_coding_style import RULES, Config, ConfigError, load_config

# RULES registry invariants


def test_rules_table_well_formed():
    for name, (desc, category, lang) in RULES.items():
        assert desc, name
        assert category, name
        assert lang in ("c", "cxx", "both"), name


def test_default_rules_match_registry():
    cfg = Config()
    assert set(cfg.rules) == set(RULES)
    for name, (_, _, lang) in RULES.items():
        assert cfg.rules[name] == (lang != "cxx"), name


# config validation


def test_config_unknown_rule_errors(tmp_path):
    (tmp_path / ".epita-style.toml").write_text('[rules]\n"keyword.gotoo" = false\n')
    with pytest.raises(ConfigError, match="unknown rule"):
        load_config()


def test_config_unknown_key_errors(tmp_path):
    (tmp_path / ".epita-style.toml").write_text("max_linez = 40\n")
    with pytest.raises(ConfigError, match="unknown key"):
        load_config()


def test_config_malformed_toml_errors(tmp_path):
    (tmp_path / ".epita-style.toml").write_text("[rules\nbad")
    with pytest.raises(ConfigError, match="invalid TOML"):
        load_config()


def test_config_string_limit_errors(tmp_path):
    (tmp_path / ".epita-style.toml").write_text('max_lines = "40"\n')
    with pytest.raises(ConfigError, match="must be a non-negative integer"):
        load_config()


def test_config_missing_explicit_path_errors(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(config_path=tmp_path / "nope.toml")


def test_config_directory_errors(tmp_path):
    with pytest.raises(ConfigError, match="cannot read"):
        load_config(config_path=tmp_path)


def test_config_autodetect_skips_directories(tmp_path):
    (tmp_path / ".epita-style").mkdir()
    (tmp_path / ".epita-style.toml").write_text("max_lines = 5\n")
    assert load_config().max_lines == 5


def test_unknown_preset_errors():
    with pytest.raises(ConfigError, match="unknown preset"):
        load_config(preset="nope")


def test_config_found_from_subdirectory(tmp_path, monkeypatch):
    (tmp_path / ".epita-style.toml").write_text("max_lines = 5\n")
    sub = tmp_path / "src"
    sub.mkdir()
    monkeypatch.chdir(sub)
    assert load_config().max_lines == 5


# --show-config output is a loadable config


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--preset", "42sh"],
        ["--preset", "ppex1", "--max-lines", "12", "--max-casts", "3"],
    ],
)
def test_show_config_round_trips(cli, tmp_path, args):
    shown = cli("--no-color", *args, "--show-config").out
    (tmp_path / ".epita-style.toml").write_text(shown)
    assert cli("--no-color", "--show-config").out == shown
    # Regression: the old output listed C++ rules as false, disabling them once loaded
    assert load_config().with_cxx().is_enabled("naming.class")
