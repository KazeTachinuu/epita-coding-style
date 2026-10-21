"""C-only checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .common import definitions

if TYPE_CHECKING:
    from tree_sitter import Node

    from ..config import Config
    from ..model import Source, Violation


def _has_storage(src: Source, decl: Node, keyword: str) -> bool:
    return any(
        src.text_of(c) == keyword for c in decl.children if c.type == "storage_class_specifier"
    )


def check_export_fun(src: Source, cfg: Config) -> list[Violation]:
    """Limit exported functions in a .c file."""
    if not src.path.endswith(".c"):
        return []
    count = sum(1 for func, *_ in definitions(src) if not _has_storage(src, func, "static"))
    if count <= cfg.max_funcs:
        return []
    return [src.violation("export.fun", f"{count} exported functions (max {cfg.max_funcs})")]


def check_export_other(src: Source, cfg: Config) -> list[Violation]:
    """Limit exported globals in a .c file."""
    if not src.path.endswith(".c"):
        return []
    globals_found = [
        decl.start_point[0] + 1
        for decl in src.nodes.root.children
        if decl.type == "declaration"
        and not any(c.type == "function_declarator" for c in decl.children)
        and not _has_storage(src, decl, "static")
        and not _has_storage(src, decl, "extern")
        and src.id_of(decl)
    ]
    if len(globals_found) <= cfg.max_globals:
        return []
    return [
        src.violation(
            "export.other",
            f"{len(globals_found)} exported globals (max {cfg.max_globals})",
            globals_found[cfg.max_globals],
        )
    ]


CHECKS = (check_export_fun, check_export_other)
