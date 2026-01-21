"""Core types and utilities for the coding style checker."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Severity(Enum):
    MAJOR = "MAJOR"
    MINOR = "MINOR"


@dataclass
class Violation:
    file: str
    line: int
    rule: str
    message: str
    severity: Severity = Severity.MAJOR
    line_content: str | None = None
    column: int | None = None


# Lazy-loaded parser
_parser = None


def _get_parser():
    """Get or create the tree-sitter parser."""
    global _parser
    if _parser is None:
        from tree_sitter import Language, Parser
        import tree_sitter_c as tsc
        _parser = Parser(Language(tsc.language()))
    return _parser


def parse(content: bytes):
    """Parse C code and return AST root."""
    return _get_parser().parse(content).root_node


class NodeCache:
    """Caches AST nodes by type to avoid repeated traversals."""

    def __init__(self, root):
        self.root = root
        self._cache: dict[str, list] = {}

    def get(self, *types) -> list:
        """Get all nodes of given types (cached)."""
        key = types
        if key not in self._cache:
            self._cache[key] = list(_find_nodes(self.root, *types))
        return self._cache[key]


def _find_nodes(node, *types):
    """Yield all descendant nodes matching given types."""
    if node.type in types:
        yield node
    for child in node.children:
        yield from _find_nodes(child, *types)


def find_nodes(node, *types):
    """Yield all descendant nodes matching given types."""
    return _find_nodes(node, *types)


def text(node, content: bytes) -> str:
    """Get text content of a node."""
    return content[node.start_byte:node.end_byte].decode()


def find_id(node, content: bytes) -> str | None:
    """Recursively find first identifier in a node."""
    if node.type == 'identifier':
        return text(node, content)
    for child in node.children:
        if name := find_id(child, content):
            return name
    return None
