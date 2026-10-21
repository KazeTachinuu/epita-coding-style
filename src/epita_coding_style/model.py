"""Core types: languages, violations, and the parsed source every check receives."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from tree_sitter import Node, Parser


class Severity(Enum):
    MAJOR = "MAJOR"
    MINOR = "MINOR"


class Lang(Enum):
    C = "C"
    CXX = "CXX"


_EXT_LANG = {
    ".c": Lang.C,
    ".h": Lang.C,
    ".cc": Lang.CXX,
    ".hh": Lang.CXX,
    ".hxx": Lang.CXX,
    ".cpp": Lang.CXX,
    ".hpp": Lang.CXX,
}


def lang_from_path(path: str) -> Lang | None:
    """Detect language from file extension."""
    return _EXT_LANG.get(Path(path).suffix)


def lang_of(path: str) -> Lang:
    """Language of a path known to be C or C++. Raises ValueError otherwise."""
    if (lang := lang_from_path(path)) is None:
        raise ValueError(f"not a C/C++ file: {path}")
    return lang


@dataclass
class Violation:
    file: str
    line: int
    rule: str
    message: str
    severity: Severity = Severity.MAJOR
    line_content: str | None = None
    column: int | None = None


@cache
def _parser(lang: Lang) -> Parser:
    # Imported lazily: --version, --help and --list-rules never parse
    import tree_sitter_c  # noqa: PLC0415
    import tree_sitter_cpp  # noqa: PLC0415
    from tree_sitter import Language, Parser  # noqa: PLC0415

    grammar = tree_sitter_cpp if lang == Lang.CXX else tree_sitter_c
    return Parser(Language(grammar.language()))


class NodeCache:
    """Indexes all AST nodes by type in one traversal."""

    def __init__(self, root: Node) -> None:
        self.root = root
        self._by_type: dict[str, list[Node]] = {}
        stack = [root]
        while stack:
            n = stack.pop()
            self._by_type.setdefault(n.type, []).append(n)
            stack.extend(reversed(n.children))

    def get(self, *types: str) -> list[Node]:
        """All nodes of the given types, document order within each type."""
        if len(types) == 1:
            return self._by_type.get(types[0], [])
        return [n for t in types for n in self._by_type.get(t, [])]


@dataclass
class Source:
    """A parsed C or C++ file: everything a check needs."""

    path: str
    lang: Lang
    text: str
    lines: list[str]
    data: bytes
    nodes: NodeCache

    @classmethod
    def read(cls, path: str) -> Source:
        """Read and parse path. Raises OSError, or ValueError for a non-C/C++ path."""
        lang = lang_of(path)
        with open(path, encoding="utf-8", errors="replace", newline="") as f:
            text = f.read()
        data = text.encode()
        return cls(
            path, lang, text, text.split("\n"), data, NodeCache(_parser(lang).parse(data).root_node)
        )

    def text_of(self, node: Node) -> str:
        return self.data[node.start_byte : node.end_byte].decode()

    def id_of(self, node: Node) -> str | None:
        """Text of the first identifier in node."""
        n = next(find_nodes(node, "identifier"), None)
        return None if n is None else self.text_of(n)

    def line(self, index: int) -> str | None:
        """Line at 0-based index, or None if out of range."""
        return self.lines[index] if 0 <= index < len(self.lines) else None

    def violation(  # noqa: PLR0913 - mirrors Violation's fields
        self,
        rule: str,
        message: str,
        line: int = 1,
        *,
        column: int | None = None,
        severity: Severity = Severity.MAJOR,
        show_line: bool = False,
    ) -> Violation:
        """Violation at 1-based line; show_line attaches that line's content."""
        return Violation(
            self.path,
            line,
            rule,
            message,
            severity,
            self.line(line - 1) if show_line else None,
            column,
        )

    def at(
        self,
        node: Node,
        rule: str,
        message: str,
        *,
        severity: Severity = Severity.MAJOR,
        column: bool = True,
    ) -> Violation:
        """Violation at node's start, showing its line (and a caret unless column=False)."""
        row, col = node.start_point
        return Violation(
            self.path, row + 1, rule, message, severity, self.line(row), col if column else None
        )


def child(node: Node, *types: str) -> Node | None:
    """First direct child of node matching given types, else None."""
    return next((c for c in node.children if c.type in types), None)


def find_nodes(node: Node, *types: str) -> Iterator[Node]:
    """Yield all descendant nodes matching given types."""
    stack = [node]
    while stack:
        n = stack.pop()
        if n.type in types:
            yield n
        stack.extend(reversed(n.children))
