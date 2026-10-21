"""C-only checks."""

from __future__ import annotations

from ..config import Config
from ..model import Source, Violation
from .common import function_declarator


def _has_storage(src: Source, decl, keyword: str) -> bool:
    return any(src.text_of(c) == keyword for c in decl.children if c.type == 'storage_class_specifier')


def check_exports(src: Source, cfg: Config) -> list[Violation]:
    """Check exported symbols in .c files."""
    if not src.path.endswith('.c'):
        return []

    v = []

    if cfg.is_enabled("export.fun"):
        count = 0
        for func in src.nodes.get('function_definition'):
            if _has_storage(src, func, 'static'):
                continue
            for child in func.children:
                func_decl = function_declarator(child)
                if func_decl and src.id_of(func_decl):
                    count += 1
                    break
        if count > cfg.max_funcs:
            v.append(src.violation("export.fun", f"{count} exported functions (max {cfg.max_funcs})"))

    if cfg.is_enabled("export.other"):
        globals_found = []
        for decl in src.nodes.root.children:
            if decl.type != 'declaration':
                continue
            if any(c.type == 'function_declarator' for c in decl.children):
                continue
            if not _has_storage(src, decl, 'static') and not _has_storage(src, decl, 'extern') \
                    and src.id_of(decl):
                globals_found.append(decl.start_point[0] + 1)

        if len(globals_found) > cfg.max_globals:
            v.append(src.violation("export.other",
                                   f"{len(globals_found)} exported globals (max {cfg.max_globals})",
                                   globals_found[cfg.max_globals]))

    return v


CHECKS = (check_exports,)
