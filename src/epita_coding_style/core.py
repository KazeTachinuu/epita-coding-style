"""Core types and utilities for the coding style checker."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Severity(Enum):
    MAJOR = "MAJOR"
    MINOR = "MINOR"


class Lang(Enum):
    C = "C"
    CXX = "CXX"


# File extension to language mapping
_EXT_LANG = {
    '.c': Lang.C, '.h': Lang.C,
    '.cc': Lang.CXX, '.hh': Lang.CXX, '.hxx': Lang.CXX,
    '.cpp': Lang.CXX, '.hpp': Lang.CXX,
}

C_EXTS = ('.c', '.h')
CXX_EXTS = ('.cc', '.hh', '.hxx')
CXX_BAD_EXTS = ('.cpp', '.hpp')
ALL_EXTS = C_EXTS + CXX_EXTS + CXX_BAD_EXTS


def lang_from_path(path: str) -> Lang | None:
    """Detect language from file extension."""
    return _EXT_LANG.get(Path(path).suffix)


@dataclass
class Violation:
    file: str
    line: int
    rule: str
    message: str
    severity: Severity = Severity.MAJOR
    line_content: str | None = None
    column: int | None = None


# Lazy-loaded parsers
_c_parser = None
_cpp_parser = None


def _get_c_parser():
    """Get or create the C tree-sitter parser."""
    global _c_parser
    if _c_parser is None:
        from tree_sitter import Language, Parser
        import tree_sitter_c as tsc
        _c_parser = Parser(Language(tsc.language()))
    return _c_parser


def _get_cpp_parser():
    """Get or create the C++ tree-sitter parser."""
    global _cpp_parser
    if _cpp_parser is None:
        from tree_sitter import Language, Parser
        import tree_sitter_cpp as tscpp
        _cpp_parser = Parser(Language(tscpp.language()))
    return _cpp_parser


def parse(content: bytes):
    """Parse C code and return AST root."""
    return _get_c_parser().parse(content).root_node


def parse_cpp(content: bytes):
    """Parse C++ code and return AST root."""
    return _get_cpp_parser().parse(content).root_node


class NodeCache:
    """Caches AST nodes by type to avoid repeated traversals."""

    def __init__(self, root):
        self.root = root
        self._cache: dict[str, list] = {}

    def get(self, *types) -> list:
        """Get all nodes of given types (cached)."""
        key = types
        if key not in self._cache:
            self._cache[key] = list(find_nodes(self.root, *types))
        return self._cache[key]


def find_nodes(node, *types):
    """Yield all descendant nodes matching given types."""
    if node.type in types:
        yield node
    for child in node.children:
        yield from find_nodes(child, *types)


def text(node, content: bytes) -> str:
    """Get text content of a node."""
    return content[node.start_byte:node.end_byte].decode()


def line_at(lines: list[str], index: int) -> str | None:
    """Get line content at 0-based index, or None if out of bounds."""
    return lines[index] if index < len(lines) else None


def find_id(node, content: bytes) -> str | None:
    """Recursively find first identifier in a node."""
    if node.type == 'identifier':
        return text(node, content)
    for child in node.children:
        if name := find_id(child, content):
            return name
    return None
