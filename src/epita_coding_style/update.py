"""Daily check for a newer release on PyPI."""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.request
from pathlib import Path

from . import __version__

_URL = "https://pypi.org/pypi/epita-coding-style/json"
_newer: str | None = None
_thread: threading.Thread | None = None


def _version(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.strip().split('.'))


def _check(stamp: Path) -> None:
    global _newer
    try:
        req = urllib.request.Request(_URL, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=1) as resp:
            latest = json.loads(resp.read())["info"]["version"]
        if _version(latest) > _version(__version__):
            _newer = latest
    except Exception:
        pass
    try:
        stamp.parent.mkdir(parents=True, exist_ok=True)
        stamp.touch()
    except OSError:
        pass


def start_update_check() -> None:
    """Check PyPI in a background thread: interactive runs only, at most daily."""
    global _thread
    if (not sys.stderr.isatty() or os.environ.get("CI")
            or os.environ.get("EPITA_STYLE_NO_UPDATE_CHECK")):
        return
    stamp = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache",
                 "epita-coding-style", "last-update-check")
    try:
        if time.time() - stamp.stat().st_mtime < 86400:
            return
    except OSError:
        pass
    _thread = threading.Thread(target=_check, args=(stamp,), daemon=True)
    _thread.start()


def print_update_msg() -> None:
    """Print the update notice if the check finishes within a second."""
    if _thread is None:
        return
    _thread.join(timeout=1)
    if _newer and not _thread.is_alive():
        print(f"A new version is available: {__version__} -> {_newer}\n"
              f"Update: https://pypi.org/project/epita-coding-style/", file=sys.stderr)
