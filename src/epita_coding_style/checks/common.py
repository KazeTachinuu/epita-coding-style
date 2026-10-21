"""Checks shared by C and C++."""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

from ..model import Severity, Source, Violation, child, find_nodes
from .clang_format import clang_format_active

if TYPE_CHECKING:
    from collections.abc import Iterator

    from tree_sitter import Node

    from ..config import Config

_CHAR_LITERAL = re.compile(r"'(?:\\.|[^'\\])'")
_STRING_LITERAL = re.compile(r'"(?:\\.|[^"\\])*"')
_INIT_ASSIGN = re.compile(r"(?<![!=<>])=(?!=)")
_DIGRAPHS = ("??=", "??/", "??'", "??(", "??)", "??!", "??<", "??>", "??-", "<%", "%>", "<:", ":>")


def check_file_dos(src: Source, _cfg: Config) -> list[Violation]:
    if "\r\n" not in src.text:
        return []
    return [src.violation("file.dos", "Use Unix LF, not DOS CRLF", show_line=True)]


def check_file_terminate(src: Source, _cfg: Config) -> list[Violation]:
    if not src.text or src.text.endswith("\n"):
        return []
    return [
        src.violation(
            "file.terminate", "File must end with newline", len(src.lines), show_line=True
        )
    ]


def check_file_spurious(src: Source, _cfg: Config) -> list[Violation]:
    v = []
    lines = src.lines
    if not lines[0].strip():
        v.append(src.violation("file.spurious", "No blank lines at start of file", show_line=True))
    end_idx = len(lines) - 2 if lines[-1] == "" else len(lines) - 1
    if end_idx >= 0 and not lines[end_idx].strip():
        v.append(
            src.violation(
                "file.spurious", "No blank lines at end of file", end_idx + 1, show_line=True
            )
        )
    return v


def check_lines_empty(src: Source, _cfg: Config) -> list[Violation]:
    lines = src.lines
    # The final '' from a trailing newline is an artifact, not a line
    last = len(lines) - 1 if lines[-1] == "" else len(lines)
    return [
        src.violation("lines.empty", "No consecutive empty lines", i, show_line=True)
        for i in range(2, last + 1)
        if not lines[i - 1].strip() and not lines[i - 2].strip()
    ]


def check_file_trailing(src: Source, _cfg: Config) -> list[Violation]:
    return [
        src.violation(
            "file.trailing",
            "Trailing whitespace",
            i,
            column=len(line.rstrip()),
            severity=Severity.MINOR,
            show_line=True,
        )
        for i, line in enumerate(src.lines, 1)
        if line != line.rstrip()
    ]


def _brace_lines(src: Source) -> Iterator[tuple[int, str, str]]:
    """Yield (number, line, stripped line with literals blanked) outside comments."""
    in_comment = False
    for i, line in enumerate(src.lines, 1):
        s = line.strip()
        if "/*" in s and "*/" not in s:
            in_comment = True
            continue
        if in_comment:
            if "*/" in s:
                in_comment = False
            continue
        if not s or s.startswith(("#", "//")):
            continue
        yield (
            i,
            line,
            _STRING_LITERAL.sub(lambda m: " " * len(m.group()), _CHAR_LITERAL.sub("   ", s)),
        )


def _opening_misplaced(line: str, clean: str) -> bool:
    if "{" not in clean:
        return False
    before = clean[: clean.find("{")].strip()
    return bool(
        before
        and not _INIT_ASSIGN.search(before)
        and clean.strip() not in ("{}", "{ }")
        and before != "do"
        and not line.rstrip().endswith("\\")
    )


def _closing_misplaced(line: str, clean: str) -> bool:
    if "}" not in clean or line.rstrip().endswith("\\"):
        return False
    after = clean[clean.find("}") + 1 :].strip()
    return bool(
        after and not after.startswith(("while", "//", "/*")) and after not in (";", ",", ");")
    )


def check_braces(src: Source, cfg: Config) -> list[Violation]:
    """Allman brace style."""
    # clang-format owns brace layout when available
    if clang_format_active(cfg):
        return []
    v = []
    for i, line, clean in _brace_lines(src):
        if _opening_misplaced(line, clean):
            v.append(
                src.violation(
                    "braces",
                    "Opening brace must be on its own line",
                    i,
                    column=line.find("{"),
                    show_line=True,
                )
            )
        if _closing_misplaced(line, clean):
            v.append(
                src.violation(
                    "braces",
                    "Closing brace must be on its own line",
                    i,
                    column=line.find("}"),
                    show_line=True,
                )
            )
    return v


def function_declarator(node: Node) -> Node | None:
    """Innermost function_declarator under node: the one naming the function.

    For function pointer returns like int (*f(void))(int), declarators nest.
    """
    if node.type == "function_declarator":
        for part in node.children:
            if inner := function_declarator(part):
                return inner
        return node
    if node.type in ("pointer_declarator", "array_declarator", "parenthesized_declarator"):
        for part in node.children:
            if result := function_declarator(part):
                return result
    return None


def params(func_decl: Node) -> list[Node] | None:
    """Parameter declarations of a function_declarator, None without a parameter list."""
    plist = child(func_decl, "parameter_list")
    return (
        None if plist is None else [p for p in plist.children if p.type == "parameter_declaration"]
    )


def _count_function_lines(body: Node, lines: list[str]) -> int:
    """Count non-trivial lines in a function body."""
    count = 0
    for ln in range(body.start_point[0], body.end_point[0] + 1):
        if ln < len(lines):
            s = lines[ln].strip()
            if s and s not in ("{", "}") and not s.startswith(("//", "/*", "*")):
                count += 1
    return count


def definitions(src: Source) -> Iterator[tuple[Node, str, list[Node] | None, Node | None]]:
    """(node, name, parameters, body) of each named function definition."""
    for func in src.nodes.get("function_definition"):
        name = None
        plist = None
        body = None
        for part in func.children:
            if func_decl := function_declarator(part):
                name = src.id_of(func_decl)
                plist = params(func_decl)
            elif part.type == "compound_statement":
                body = part
        if name:
            yield func, name, plist, body


def _prototypes(src: Source) -> Iterator[tuple[Node, str, list[Node] | None, str, Node | None]]:
    """(node, name, parameters, how to write empty ones, body) of definitions and prototypes."""
    for func, name, plist, body in definitions(src):
        yield func, name, plist, "should use (void) for empty params", body
    if not src.path.endswith((".h", ".hh", ".hxx")):
        return
    for decl in src.nodes.get("declaration"):
        for func_decl in decl.children:
            if func_decl.type != "function_declarator":
                continue
            if (ident := child(func_decl, "identifier")) is not None:
                yield func_decl, src.text_of(ident), params(func_decl), "should use (void)", None


def check_functions(src: Source, cfg: Config) -> list[Violation]:
    """Prototype and length rules, one function at a time: same-line ties keep this order."""
    v = []
    for node, name, plist, void_msg, body in _prototypes(src):
        # (void) parses as a parameter_declaration, so empty params means ()
        if plist == []:
            v.append(src.at(node, "fun.proto.void", f"'{name}' {void_msg}", column=False))
        if plist and len(plist) > cfg.max_args:
            v.append(
                src.at(
                    node,
                    "fun.arg.count",
                    f"'{name}' has {len(plist)} args (max {cfg.max_args})",
                    column=False,
                )
            )
        if body and (count := _count_function_lines(body, src.lines)) > cfg.max_lines:
            v.append(
                src.at(
                    node,
                    "fun.length",
                    f"Function has {count} lines (max {cfg.max_lines})",
                    column=False,
                )
            )
    return v


def check_cpp_guard(src: Source, _cfg: Config) -> list[Violation]:
    if not src.path.endswith(".h"):
        return []
    guard = os.path.basename(src.path).upper().replace(".", "_").replace("-", "_")
    if any("#ifndef" in line and guard in line for line in src.lines):
        return []
    return [src.violation("cpp.guard", f"Missing include guard (#ifndef {guard})", show_line=True)]


def check_comment_multi(src: Source, _cfg: Config) -> list[Violation]:
    """Multi-line comments (spec 4.7).

    Bare '/*' or '/**' opener, '**' continuations, '*/' alone on the closing line.
    """
    v = []
    for n in src.nodes.get("comment"):
        txt = src.text_of(n)
        if not txt.startswith("/*") or "\n" not in txt:
            continue
        line = n.start_point[0] + 1
        first, *rest = txt.split("\n")
        if first not in ("/*", "/**"):
            v.append(
                src.violation(
                    "comment.multi",
                    "Multi-line comment must open with '/*' on its own line",
                    line,
                    show_line=True,
                )
            )
        for off, cont in enumerate(rest[:-1], 1):
            if not cont.strip().startswith("**"):
                v.append(
                    src.violation(
                        "comment.multi",
                        "Comment continuation must start with '**'",
                        line + off,
                        show_line=True,
                    )
                )
        if rest[-1].strip() != "*/":
            v.append(
                src.violation(
                    "comment.multi",
                    "'*/' must be on its own line",
                    line + len(rest),
                    show_line=True,
                )
            )
    return v


def _lines_with_offsets(src: Source) -> Iterator[tuple[int, str, int]]:
    """Yield (number, line, offset) of lines, except those opening with a commented-out '#'."""
    offset = 0
    for i, line in enumerate(src.lines, 1):
        line_start, offset = offset, offset + len(line) + 1
        if not (line.strip().startswith("#") and src.in_comment(line_start + line.find("#"))):
            yield i, line, line_start


def check_cpp_mark(src: Source, _cfg: Config) -> list[Violation]:
    return [
        src.violation("cpp.mark", "# must be on first column", i, column=0, show_line=True)
        for i, line, _ in _lines_with_offsets(src)
        if line.strip().startswith("#") and line[0] != "#"
    ]


def check_cpp_if(src: Source, _cfg: Config) -> list[Violation]:
    v = []
    for i, line, _ in _lines_with_offsets(src):
        s = line.strip()
        if s.startswith(("#endif", "#else")) and "//" not in s and "/*" not in s:
            directive = "#else" if s.startswith("#else") else "#endif"
            v.append(
                src.violation(
                    "cpp.if",
                    f"{directive} should have comment",
                    i,
                    severity=Severity.MINOR,
                    show_line=True,
                )
            )
    return v


def check_cpp_digraphs(src: Source, _cfg: Config) -> list[Violation]:
    v = []
    for i, line, line_start in _lines_with_offsets(src):
        for d in _DIGRAPHS:
            col = line.find(d)
            while col != -1:
                if not src.in_comment(line_start + col):
                    v.append(
                        src.violation(
                            "cpp.digraphs",
                            f"Digraph '{d}' not allowed",
                            i,
                            column=col,
                            show_line=True,
                        )
                    )
                col = line.find(d, col + 1)
    return v


def check_decl_single(src: Source, _cfg: Config) -> list[Violation]:
    v = []
    for decl in src.nodes.get("declaration"):
        if any(c.type == "function_declarator" for c in decl.children):
            continue
        declarators = [
            c
            for c in decl.children
            if c.type in ("init_declarator", "pointer_declarator", "identifier", "array_declarator")
        ]
        if len(declarators) > 1:
            v.append(src.at(decl, "decl.single", "One declaration per line"))
    return v


def check_stat_asm(src: Source, _cfg: Config) -> list[Violation]:
    return [
        src.at(node, "stat.asm", "asm not allowed")
        for node in src.nodes.get("gnu_asm_expression", "gnu_asm_statement")
    ]


def check_keyword_goto(src: Source, _cfg: Config) -> list[Violation]:
    return [
        src.at(node, "keyword.goto", "goto not allowed") for node in src.nodes.get("goto_statement")
    ]


def check_cast(src: Source, _cfg: Config) -> list[Violation]:
    return [
        src.at(node, "cast", "Explicit cast not allowed")
        for node in src.nodes.get("cast_expression")
    ]


def check_stat_sep(src: Source, _cfg: Config) -> list[Violation]:
    """Comma operator allowed only in 'for' clauses (spec 5.25)."""
    v = []
    for node in src.nodes.get("comma_expression"):
        parent = node.parent
        if parent is not None and parent.type == "comma_expression":
            continue  # report only the outermost expression
        while parent is not None and parent.type == "parenthesized_expression":
            parent = parent.parent
        if parent is not None and parent.type != "for_statement":
            v.append(src.at(node, "stat.sep", "Comma operator only allowed in 'for'"))
    return v


def _array_size(arr: Node) -> Node | None:
    """Return the size expression of an array_declarator: what sits between [ and ]."""
    size = None
    for part in arr.children:
        if part.type == "[":
            size = None
        elif part.type == "]":
            break
        else:
            size = part
    return size


def check_decl_vla(src: Source, _cfg: Config) -> list[Violation]:
    v = []
    for decl in src.nodes.get("declaration"):
        for arr in find_nodes(decl, "array_declarator"):
            size = _array_size(arr)
            if size and size.type == "identifier" and not src.text_of(size).isupper():
                v.append(src.at(arr, "decl.vla", "VLA not allowed"))
    return v


def check_ctrl_empty(src: Source, _cfg: Config) -> list[Violation]:
    """Empty loop bodies."""
    v = []
    for node in src.nodes.get("for_statement", "while_statement"):
        for part in node.children:
            is_bare = part.type == "expression_statement" and all(
                c.type == ";" for c in part.children
            )
            is_braced = part.type == "compound_statement" and all(
                c.type in ("{", "}", "comment") for c in part.children
            )
            if is_bare or is_braced:
                v.append(src.at(part, "ctrl.empty", "Use 'continue' for empty loops", column=False))
    return v


# Order matters: violations at the same position keep this order
CHECKS = (
    check_file_dos,
    check_file_terminate,
    check_file_spurious,
    check_lines_empty,
    check_file_trailing,
    check_braces,
    check_functions,
    check_cpp_guard,
    check_comment_multi,
    check_cpp_mark,
    check_cpp_if,
    check_cpp_digraphs,
    check_decl_single,
    check_stat_asm,
    check_keyword_goto,
    check_cast,
    check_stat_sep,
    check_decl_vla,
    check_ctrl_empty,
)
