"""End-to-end CLI output on a fixed corpus. Regenerate: UPDATE_SNAPSHOTS=1 pytest."""

import os
import shutil
from pathlib import Path

import pytest

SNAPSHOTS = Path(__file__).parent / "snapshots"

SCENARIOS = {
    "default": ["."],
    "preset-42sh": ["--preset", "42sh", "."],
    "preset-ppex1": ["--preset", "ppex1", "."],
    "quiet": ["-q", "."],
    "explicit-files": ["bad.cc", "dos.c", "good.c"],
    "stdin": ["-"],
    "list-rules": ["--list-rules"],
    "show-config": ["--preset", "42sh", "--max-lines", "12", "--show-config"],
}


@pytest.mark.parametrize("name", SCENARIOS)
def test_snapshot(name, cli, tmp_path, monkeypatch):
    shutil.copytree(SNAPSHOTS / "corpus", tmp_path / "corpus")
    monkeypatch.chdir(tmp_path / "corpus")
    r = cli("--no-color", *SCENARIOS[name], stdin="bad.c\nsub/bad.h\n")
    got = f"exit={r.code}\n{r.out}{r.err}"
    expected = SNAPSHOTS / "expected" / f"{name}.txt"
    if os.environ.get("UPDATE_SNAPSHOTS"):
        expected.write_bytes(got.encode())
    else:
        assert got == expected.read_bytes().decode()
