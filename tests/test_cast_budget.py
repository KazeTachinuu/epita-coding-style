"""max_casts: a budget of explicit casts shared by all files of one run."""

import pytest

from epita_coding_style import Config, ConfigError, check_file, load_config
from epita_coding_style.lint import lint_files

CASTS_3 = "int f(long x)\n{\n    return (int)x + (int)x + (int)x;\n}\n"
CASTS_0 = "int g(long x)\n{\n    return x;\n}\n"


def casts(results):
    return {path: [v for v in vs if v.rule == "cast"] for path, vs in results.items()}


def write(tmp_path, **files):
    for name, code in files.items():
        (tmp_path / name).write_text(code)
    return [str(tmp_path / name) for name in files]


def cfg(**limits):
    c = Config(**limits)
    c.rules["format"] = False
    return c


def test_default_forbids_every_cast(tmp_path):
    [a] = write(tmp_path, **{"a.c": CASTS_3})
    vs = casts(lint_files([a], cfg()))[a]
    assert [v.message for v in vs] == ["Explicit cast not allowed"] * 3


def test_within_budget_reports_nothing(tmp_path):
    a, b = write(tmp_path, **{"a.c": CASTS_3, "b.c": CASTS_3})
    assert casts(lint_files([a, b], cfg(max_casts=6))) == {a: [], b: []}


def test_over_budget_reports_every_cast_in_its_own_file(tmp_path):
    a, b, c = write(tmp_path, **{"a.c": CASTS_3, "b.c": CASTS_3, "c.c": CASTS_0})
    result = casts(lint_files([a, b, c], cfg(max_casts=5)))
    assert [len(result[p]) for p in (a, b, c)] == [3, 3, 0]
    assert all(v.file == p for p in (a, b) for v in result[p])
    assert result[a][0].message == "Explicit cast (6 in total, max 5)"


def test_budget_does_not_depend_on_file_order(tmp_path):
    a, b = write(tmp_path, **{"a.c": CASTS_3, "b.c": CASTS_3})
    forward = casts(lint_files([a, b], cfg(max_casts=5)))
    backward = casts(lint_files([b, a], cfg(max_casts=5)))
    assert forward == backward


def test_cast_rule_disabled_ignores_budget(tmp_path):
    [a] = write(tmp_path, **{"a.c": CASTS_3})
    c = cfg(max_casts=1)
    c.rules["cast"] = False
    assert casts(lint_files([a], c)) == {a: []}


def test_cxx_files_use_their_own_rule(tmp_path):
    [a] = write(tmp_path, **{"a.cc": CASTS_3})
    rules = {v.rule for v in lint_files([a], cfg(max_casts=1))[a]}
    assert "cast" not in rules and "global.casts" in rules


def test_check_file_applies_budget_to_that_file(tmp_path):
    [a] = write(tmp_path, **{"a.c": CASTS_3})
    assert not [v for v in check_file(a, cfg(max_casts=3)) if v.rule == "cast"]


@pytest.mark.parametrize("source", ["preset", "file", "cli"])
def test_max_casts_is_configurable(tmp_path, source):
    if source == "preset":
        c = load_config(preset="ppex1")
    elif source == "file":
        (tmp_path / ".epita-style.toml").write_text("max_casts = 5\n")
        c = load_config()
    else:
        c = load_config(max_casts=5)
    assert c.max_casts == 5


@pytest.mark.parametrize("value", ['"5"', "-1", "true"])
def test_max_casts_must_be_a_non_negative_integer(tmp_path, value):
    (tmp_path / ".epita-style.toml").write_text(f"max_casts = {value}\n")
    with pytest.raises(ConfigError, match="non-negative integer"):
        load_config()


def test_negative_override_rejected():
    with pytest.raises(ConfigError, match="non-negative integer"):
        load_config(max_casts=-1)


def test_cli_flag(cli, tmp_path):
    (tmp_path / "a.c").write_text(CASTS_3)
    assert "[epita-cast]" not in cli("--no-color", "--max-casts", "3", "a.c").out
    assert (
        cli("--no-color", "--max-casts", "2", "a.c").out.count(
            "Explicit cast (3 in total, max 2) [epita-cast]"
        )
        == 3
    )
