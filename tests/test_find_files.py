"""Tests for directory traversal: hidden paths and git ignore rules."""

import os
import shutil
import subprocess

import pytest

from epita_coding_style.files import find_files

needs_git = pytest.mark.skipif(not shutil.which("git"), reason="git not installed")

HIDDEN = [".venv/a.c", "src/.cache/a.c", "src/.hidden.c"]


def found(root, *args):
    """Create .c files at the given relative paths, return what find_files keeps."""
    for rel in args:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("int x;\n")
    return sorted(os.path.relpath(f, root) for f in find_files([str(root)]))


def git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def test_hidden_skipped_without_git(tmp_path):
    assert found(tmp_path, "src/a.c", "node_modules/a.c", *HIDDEN) \
        == ["node_modules/a.c", "src/a.c"]


@needs_git
def test_hidden_skipped_in_git_repo_even_when_tracked(tmp_path):
    git(tmp_path, "init")
    found(tmp_path, "src/a.c", *HIDDEN)
    git(tmp_path, "add", "-f", ".")
    assert found(tmp_path) == ["src/a.c"]


def test_explicit_hidden_dir_is_walked(tmp_path):
    found(tmp_path, ".hidden/a.c")
    assert find_files([str(tmp_path / ".hidden")]) == [str(tmp_path / ".hidden/a.c")]


@needs_git
def test_gitignore_root_and_nested(tmp_path):
    git(tmp_path, "init")
    (tmp_path / "src").mkdir()
    (tmp_path / ".gitignore").write_text("node_modules/\nbuild/\n")
    (tmp_path / "src/.gitignore").write_text("gen.c\n")
    assert found(tmp_path, "src/a.c", "src/gen.c", "build/b.c", "node_modules/n.c", "gen.c") \
        == ["gen.c", "src/a.c"]
    # Walking a subdirectory still applies the repo's .gitignore files
    assert find_files([str(tmp_path / "src")]) == [str(tmp_path / "src/a.c")]


@needs_git
def test_git_info_exclude(tmp_path):
    git(tmp_path, "init")
    (tmp_path / ".git/info/exclude").write_text("b.c\n")
    assert found(tmp_path, "a.c", "b.c") == ["a.c"]


@needs_git
def test_explicit_ignored_file_is_checked(tmp_path):
    git(tmp_path, "init")
    (tmp_path / ".gitignore").write_text("*.c\n")
    assert found(tmp_path, "a.c") == []
    assert find_files([str(tmp_path / "a.c")]) == [str(tmp_path / "a.c")]


@needs_git
def test_tracked_file_deleted_from_worktree(tmp_path):
    git(tmp_path, "init")
    found(tmp_path, "a.c", "gone.c")
    git(tmp_path, "add", ".")
    (tmp_path / "gone.c").unlink()
    assert found(tmp_path) == ["a.c"]


@needs_git
def test_explicit_ignored_dir_is_walked(tmp_path):
    git(tmp_path, "init")
    (tmp_path / ".gitignore").write_text("build/\n")
    found(tmp_path, "build/b.c")
    assert find_files([str(tmp_path / "build")]) == [str(tmp_path / "build/b.c")]


@needs_git
def test_nested_repo_is_walked(tmp_path):
    git(tmp_path, "init")
    found(tmp_path, "a.c", "sub/nested.c")
    git(tmp_path / "sub", "init")
    assert found(tmp_path) == ["a.c", "sub/nested.c"]


def test_extension_only_name_skipped(tmp_path):
    assert found(tmp_path, ".c", "a.c") == ["a.c"]
    assert find_files([str(tmp_path / ".c")]) == []


def test_duplicate_paths_deduped(tmp_path):
    (tmp_path / "a.c").write_text("int x;\n")
    assert find_files([str(tmp_path), str(tmp_path / "a.c"), "a.c"]) \
        == [str(tmp_path / "a.c")]


@needs_git
def test_repo_config_cannot_run_commands(tmp_path):
    """A scanned repo's .git/config must not make git execute anything."""
    git(tmp_path, "init")
    marker = tmp_path / "pwned"
    git(tmp_path, "config", "core.fsmonitor", f"touch '{marker}'; false")
    assert found(tmp_path, "a.c") == ["a.c"]
    assert not marker.exists()
