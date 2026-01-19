"""Core types and utilities for the coding style checker."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from tree_sitter import Language, Parser
import tree_sitter_c as tsc

# Tree-sitter parser (singleton)
_parser = Parser(Language(tsc.language()))


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


def parse(content: bytes):
    """Parse C code and return AST root."""
    return _parser.parse(content).root_node


def find_nodes(node, *types):
    """Yield all descendant nodes matching given types."""
    if node.type in types:
        yield node
    for child in node.children:
        yield from find_nodes(child, *types)


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
