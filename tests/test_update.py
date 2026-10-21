"""The daily PyPI update check: when it runs and what it prints. Network is faked."""

import io
import json
import os
import sys
import time

import pytest

from epita_coding_style import __version__, update


@pytest.fixture
def pypi(monkeypatch, tmp_path):
    """Fresh cache, no opt-out; returns pypi(version): fake PyPI's latest, in a terminal."""
    monkeypatch.setattr(update, "_thread", None)
    monkeypatch.setattr(update, "_newer", None)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("EPITA_STYLE_NO_UPDATE_CHECK", raising=False)

    def latest(version):
        # Patched here, in the test body: pytest swaps sys.stderr after fixtures run
        monkeypatch.setattr(sys.stderr, "isatty", lambda: True)
        payload = json.dumps({"info": {"version": version}}).encode()
        monkeypatch.setattr(update.urllib.request, "urlopen", lambda *_, **__: io.BytesIO(payload))

    return latest


def run_check(capsys) -> str:
    update.start_update_check()
    update.print_update_msg()
    return capsys.readouterr().err


def test_newer_release_is_announced(pypi, capsys, tmp_path):
    pypi("999.0.0")
    assert f"{__version__} -> 999.0.0" in run_check(capsys)
    assert (tmp_path / "epita-coding-style" / "last-update-check").exists()


@pytest.mark.parametrize("latest", [__version__, "0.0.1"])
def test_current_or_older_release_is_silent(pypi, capsys, latest):
    pypi(latest)
    assert run_check(capsys) == ""


def test_network_failure_is_silent(pypi, capsys, monkeypatch):
    def offline(*_, **__):
        raise OSError("offline")

    pypi("999.0.0")
    monkeypatch.setattr(update.urllib.request, "urlopen", offline)
    assert run_check(capsys) == ""


@pytest.mark.parametrize("env", ["CI", "EPITA_STYLE_NO_UPDATE_CHECK"])
def test_opt_out(pypi, capsys, monkeypatch, env):
    pypi("999.0.0")
    monkeypatch.setenv(env, "1")
    assert run_check(capsys) == ""


def test_not_a_terminal(pypi, capsys, monkeypatch):
    pypi("999.0.0")
    monkeypatch.setattr(sys.stderr, "isatty", lambda: False)
    assert run_check(capsys) == ""


def test_at_most_daily(pypi, capsys, tmp_path):
    pypi("999.0.0")
    stamp = tmp_path / "epita-coding-style" / "last-update-check"
    stamp.parent.mkdir()
    stamp.touch()
    assert run_check(capsys) == ""
    yesterday = time.time() - 86401
    os.utime(stamp, (yesterday, yesterday))
    assert "999.0.0" in run_check(capsys)
