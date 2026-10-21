"""End-to-end tests for the command-line interface."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

FILES = {
    "clean.c": '#include <stdio.h>\n\nint main(void)\n{\n    printf("Hello\\n");\n    return 0;\n}\n',
    "bad_goto.c": "void f(void)\n{\nlabel:\n    goto label;\n}\n",
    "bad_cast.c": "void f(void)\n{\n    void *p = 0;\n    int x = (int)p;\n}\n",
    "bad_lines.c": "void f(void)\n{\n    int x = 1;\n" + "    x++;\n" * 30 + "}\n",
    "bad_args.c": "void f(int a, int b, int c, int d, int e)\n{\n    return;\n}\n",
    "bad_format.c": "int main(void){\n    return 0;\n}\n",
    "bad_funcs.c": "".join(f"void f{i}(void)\n{{\n    return;\n}}\n" for i in range(1, 12)),
    "config.toml": 'max_lines = 50\n\n[rules]\n"keyword.goto" = false\n"cast" = false\n',
    "config_with_preset.toml": 'preset = "42sh"\n',
    "config_preset_override.toml": 'preset = "42sh"\nmax_lines = 25\n\n[rules]\n"cast" = true\n',
}

needs_clang_format = pytest.mark.skipif(not shutil.which("clang-format"),
                                        reason="clang-format not installed")


@pytest.fixture(autouse=True)
def _files(tmp_path):
    for name, content in FILES.items():
        (tmp_path / name).write_text(content)


@pytest.mark.parametrize("args, code, expected", [
    pytest.param(["clean.c"], 0, None, id="clean"),
    pytest.param(["nonexistent/"], 2, None, id="nonexistent-path"),
    pytest.param(["--help"], 0, "EPITA", id="help"),
    pytest.param(["bad_goto.c"], 1, "keyword.goto", id="goto-default"),
    pytest.param(["bad_cast.c"], 1, "cast", id="cast-default"),
    pytest.param(["bad_lines.c"], 1, "fun.length", id="fun-length-default"),
    pytest.param(["bad_args.c"], 1, "fun.arg.count", id="fun-arg-count-default"),
    pytest.param(["bad_funcs.c"], 1, "export.fun", id="export-fun-default"),
    pytest.param(["--preset", "42sh", "bad_goto.c"], 0, None, id="42sh-allows-goto"),
    pytest.param(["--preset", "42sh", "bad_cast.c"], 0, None, id="42sh-allows-cast"),
    pytest.param(["--preset", "42sh", "bad_lines.c"], 0, None, id="42sh-40-lines"),
    pytest.param(["--config", "config.toml", "bad_goto.c"], 0, None, id="config-disables-goto"),
    pytest.param(["--config", "config.toml", "bad_cast.c"], 0, None, id="config-disables-cast"),
    pytest.param(["--config", "config_with_preset.toml", "bad_goto.c"], 0, None,
                 id="config-preset"),
    pytest.param(["--config", "config_preset_override.toml", "bad_lines.c"], 1, "fun.length",
                 id="config-overrides-preset-max-lines"),
    pytest.param(["--config", "config_preset_override.toml", "bad_cast.c"], 1, "cast",
                 id="config-overrides-preset-rules"),
    pytest.param(["--config", "config_preset_override.toml", "bad_goto.c"], 0, None,
                 id="config-inherits-preset-rules"),
    pytest.param(["--config", "config_with_preset.toml", "--max-lines", "20", "bad_lines.c"],
                 1, None, id="cli-flag-overrides-config"),
    pytest.param(["--max-lines", "50", "bad_lines.c"], 0, None, id="max-lines"),
    pytest.param(["--max-args", "10", "bad_args.c"], 0, None, id="max-args"),
    pytest.param(["--max-funcs", "15", "bad_funcs.c"], 0, None, id="max-funcs"),
])
def test_cli(cli, args, code, expected):
    r = cli(*args)
    assert r.code == code
    if expected:
        assert expected in r.out


def test_empty_dir(cli, tmp_path):
    (tmp_path / "emptydir").mkdir()
    assert cli("emptydir/").code == 2


@pytest.mark.parametrize("dotfile, rule, path", [
    (".epita-style", "keyword.goto", "bad_goto.c"),
    (".epita-style.toml", "cast", "bad_cast.c"),
])
def test_autodetect_config(cli, tmp_path, dotfile, rule, path):
    (tmp_path / dotfile).write_text(f'[rules]\n"{rule}" = false\n')
    assert cli(path).code == 0


def test_epita_style_beats_toml(cli, tmp_path):
    (tmp_path / ".epita-style").write_text('[rules]\n"keyword.goto" = false\n')
    (tmp_path / ".epita-style.toml").write_text('[rules]\n"cast" = false\n')
    assert cli("bad_goto.c").code == 0
    assert cli("bad_cast.c").code == 1


def test_no_color(cli, monkeypatch):
    monkeypatch.setenv("FORCE_COLOR", "1")
    r = cli("--no-color", "bad_goto.c")
    assert r.code == 1
    assert "\033" not in r.out + r.err


@needs_clang_format
def test_format_detected(cli):
    assert "format" in cli("bad_format.c").out


def test_console_script():
    exe = Path(sys.executable).with_name("epita-coding-style")
    assert subprocess.run([exe, "clean.c"], capture_output=True).returncode == 0
