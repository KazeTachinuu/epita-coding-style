"""Daily check for a newer release on PyPI."""

from __future__ import annotations

import contextlib
import json
import os
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import ClassVar

from . import __version__

_URL = "https://pypi.org/pypi/epita-coding-style/json"
_DAY = 24 * 60 * 60


def _version(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.strip().split("."))


class _Check(threading.Thread):
    """Ask PyPI for the latest release; `newer` holds it if it beats ours."""

    started: ClassVar[_Check | None] = None

    def __init__(self, stamp: Path) -> None:
        super().__init__(daemon=True)
        self.stamp = stamp
        self.newer: str | None = None

    def run(self) -> None:
        with contextlib.suppress(Exception):  # offline, slow or garbled: say nothing
            req = urllib.request.Request(_URL, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=1) as resp:  # noqa: S310 - fixed https URL
                latest = json.loads(resp.read())["info"]["version"]
            if _version(latest) > _version(__version__):
                self.newer = latest
        with contextlib.suppress(OSError):
            self.stamp.parent.mkdir(parents=True, exist_ok=True)
            self.stamp.touch()


def start_update_check() -> None:
    """Check PyPI in a background thread: interactive runs only, at most daily."""
    if (
        not sys.stderr.isatty()
        or os.environ.get("CI")
        or os.environ.get("EPITA_STYLE_NO_UPDATE_CHECK")
    ):
        return
    stamp = Path(
        os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache",
        "epita-coding-style",
        "last-update-check",
    )
    with contextlib.suppress(OSError):
        if time.time() - stamp.stat().st_mtime < _DAY:
            return
    _Check.started = _Check(stamp)
    _Check.started.start()


def print_update_msg() -> None:
    """Print the update notice if the check finishes within a second."""
    check = _Check.started
    if check is None:
        return
    check.join(timeout=1)
    if check.newer and not check.is_alive():
        print(
            f"A new version is available: {__version__} -> {check.newer}\n"
            f"Update: https://pypi.org/project/epita-coding-style/",
            file=sys.stderr,
        )
