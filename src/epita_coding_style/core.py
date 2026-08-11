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


_c_parser = None
_cpp_parser = None


def parse(content: bytes):
    """Parse C code and return AST root."""
    global _c_parser
    if _c_parser is None:
        from tree_sitter import Language, Parser
        import tree_sitter_c as tsc
        _c_parser = Parser(Language(tsc.language()))
    return _c_parser.parse(content).root_node


def parse_cpp(content: bytes):
    """Parse C++ code and return AST root."""
    global _cpp_parser
    if _cpp_parser is None:
        from tree_sitter import Language, Parser
        import tree_sitter_cpp as tscpp
        _cpp_parser = Parser(Language(tscpp.language()))
    return _cpp_parser.parse(content).root_node


class NodeCache:
    """Indexes all AST nodes by type in one traversal."""

    def __init__(self, root):
        self.root = root
        self._by_type: dict[str, list] = {}
        stack = [root]
        while stack:
            n = stack.pop()
            self._by_type.setdefault(n.type, []).append(n)
            stack.extend(reversed(n.children))

    def get(self, *types) -> list:
        """All nodes of the given types, document order within each type."""
        if len(types) == 1:
            return self._by_type.get(types[0], [])
        return [n for t in types for n in self._by_type.get(t, [])]


def find_nodes(node, *types):
    """Yield all descendant nodes matching given types."""
    stack = [node]
    while stack:
        n = stack.pop()
        if n.type in types:
            yield n
        stack.extend(reversed(n.children))


def text(node, content: bytes) -> str:
    """Get text content of a node."""
    return content[node.start_byte:node.end_byte].decode()


def line_at(lines: list[str], index: int) -> str | None:
    """Get line content at 0-based index, or None if out of bounds."""
    return lines[index] if index < len(lines) else None


def find_id(node, content: bytes) -> str | None:
    """Find first identifier in a node (iterative)."""
    stack = [node]
    while stack:
        n = stack.pop()
        if n.type == 'identifier':
            return text(n, content)
        stack.extend(reversed(n.children))
    return None
