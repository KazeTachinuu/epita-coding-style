"""Checks shared by C and C++."""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

from ..model import Severity, Source, Violation, child, find_nodes
from .clang_format import clang_format_active

if TYPE_CHECKING:
    from tree_sitter import Node

    from ..config import Config

_CHAR_LITERAL = re.compile(r"'(?:\\.|[^'\\])'")
_STRING_LITERAL = re.compile(r'"(?:\\.|[^"\\])*"')
_INIT_ASSIGN = re.compile(r"(?<![!=<>])=(?!=)")
_DIGRAPHS = ("??=", "??/", "??'", "??(", "??)", "??!", "??<", "??>", "??-", "<%", "%>", "<:", ":>")


def check_file_format(src: Source, cfg: Config) -> list[Violation]:
    """Check file formatting rules."""
    v = []
    lines = src.lines

    if cfg.is_enabled("file.dos") and "\r\n" in src.text:
        v.append(src.violation("file.dos", "Use Unix LF, not DOS CRLF", show_line=True))

    if cfg.is_enabled("file.terminate") and src.text and not src.text.endswith("\n"):
        v.append(
            src.violation(
                "file.terminate", "File must end with newline", len(lines), show_line=True
            )
        )

    if cfg.is_enabled("file.spurious"):
        if not lines[0].strip():
            v.append(
                src.violation("file.spurious", "No blank lines at start of file", show_line=True)
            )
        end_idx = len(lines) - 2 if lines[-1] == "" else len(lines) - 1
        if end_idx >= 0 and not lines[end_idx].strip():
            v.append(
                src.violation(
                    "file.spurious", "No blank lines at end of file", end_idx + 1, show_line=True
                )
            )

    if cfg.is_enabled("lines.empty"):
        # The final '' from a trailing newline is an artifact, not a line
        last = len(lines) - 1 if lines[-1] == "" else len(lines)
        v.extend(
            src.violation("lines.empty", "No consecutive empty lines", i, show_line=True)
            for i in range(2, last + 1)
            if not lines[i - 1].strip() and not lines[i - 2].strip()
        )

    if cfg.is_enabled("file.trailing"):
        for i, line in enumerate(lines, 1):
            if line != line.rstrip():
                v.append(
                    src.violation(
                        "file.trailing",
                        "Trailing whitespace",
                        i,
                        column=len(line.rstrip()),
                        severity=Severity.MINOR,
                        show_line=True,
                    )
                )

    return v


def check_braces(src: Source, cfg: Config) -> list[Violation]:
    """Check Allman brace style."""
    if not cfg.is_enabled("braces"):
        return []
    # clang-format owns brace layout when available
    if clang_format_active(cfg):
        return []

    v = []
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

        clean = _STRING_LITERAL.sub(lambda m: " " * len(m.group()), _CHAR_LITERAL.sub("   ", s))

        if "{" in clean:
            before = clean[: clean.find("{")].strip()
            is_init = bool(_INIT_ASSIGN.search(before))
            if (
                before
                and not is_init
                and clean.strip() not in ("{}", "{ }")
                and before != "do"
                and not line.rstrip().endswith("\\")
            ):
                v.append(
                    src.violation(
                        "braces",
                        "Opening brace must be on its own line",
                        i,
                        column=line.find("{"),
                        show_line=True,
                    )
                )

        if "}" in clean and not line.rstrip().endswith("\\"):
            after = clean[clean.find("}") + 1 :].strip()
            if (
                after
                and not after.startswith(("while", "//", "/*"))
                and after not in (";", ",", ");")
            ):
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


def check_functions(src: Source, cfg: Config) -> list[Violation]:
    """Check function rules using AST."""
    v = []
    chk_void = cfg.is_enabled("fun.proto.void")
    chk_args = cfg.is_enabled("fun.arg.count")
    chk_len = cfg.is_enabled("fun.length")
    max_args = cfg.max_args
    max_lines = cfg.max_lines

    def check_params(node: Node, name: str, plist: list[Node] | None, void_msg: str) -> None:
        # (void) parses as a parameter_declaration, so empty params means ()
        if chk_void and plist == []:
            v.append(src.at(node, "fun.proto.void", f"'{name}' {void_msg}", column=False))
        if chk_args and plist and len(plist) > max_args:
            v.append(
                src.at(
                    node,
                    "fun.arg.count",
                    f"'{name}' has {len(plist)} args (max {max_args})",
                    column=False,
                )
            )

    for func in src.nodes.get("function_definition"):
        name = None
        plist = None
        body = None

        for part in func.children:
            func_decl = function_declarator(part)
            if func_decl:
                name = src.id_of(func_decl)
                plist = params(func_decl)
            elif part.type == "compound_statement":
                body = part

        if not name:
            continue

        check_params(func, name, plist, "should use (void) for empty params")

        if chk_len and body:
            count = _count_function_lines(body, src.lines)
            if count > max_lines:
                v.append(
                    src.at(
                        func,
                        "fun.length",
                        f"Function has {count} lines (max {max_lines})",
                        column=False,
                    )
                )

    if src.path.endswith((".h", ".hh", ".hxx")):
        for decl in src.nodes.get("declaration"):
            for func_decl in decl.children:
                if func_decl.type != "function_declarator":
                    continue
                ident = child(func_decl, "identifier")
                if ident is not None:
                    check_params(
                        func_decl, src.text_of(ident), params(func_decl), "should use (void)"
                    )

    return v


def check_preprocessor(src: Source, cfg: Config) -> list[Violation]:
    """Check preprocessor and comment rules."""
    v = []
    lines = src.lines

    if cfg.is_enabled("cpp.guard") and src.path.endswith(".h"):
        guard = os.path.basename(src.path).upper().replace(".", "_").replace("-", "_")
        if not any("#ifndef" in line and guard in line for line in lines):
            v.append(
                src.violation(
                    "cpp.guard", f"Missing include guard (#ifndef {guard})", show_line=True
                )
            )

    if cfg.is_enabled("comment.multi"):
        v.extend(_check_comment_multi(src))

    check_mark = cfg.is_enabled("cpp.mark")
    check_if = cfg.is_enabled("cpp.if")
    check_digraphs = cfg.is_enabled("cpp.digraphs")
    if not (check_mark or check_if or check_digraphs):
        return v

    comments = [(n.start_byte, n.end_byte) for n in src.nodes.get("comment")]

    def in_comment(pos: int) -> bool:
        for start, end in comments:
            if start <= pos < end:
                return True
            if start > pos:
                break
        return False

    offset = 0
    for i, line in enumerate(lines, 1):
        line_start, offset = offset, offset + len(line) + 1
        s = line.strip()

        if s.startswith("#") and in_comment(line_start + line.find("#")):
            continue

        if check_mark and s.startswith("#") and line[0] != "#":
            v.append(
                src.violation("cpp.mark", "# must be on first column", i, column=0, show_line=True)
            )

        if check_if and s.startswith(("#endif", "#else")) and "//" not in s and "/*" not in s:
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

        if check_digraphs:
            for d in _DIGRAPHS:
                col = line.find(d)
                while col != -1:
                    if not in_comment(line_start + col):
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


def _check_comment_multi(src: Source) -> list[Violation]:
    """Check multi-line comments (spec 4.7).

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


def check_misc(src: Source, cfg: Config) -> list[Violation]:
    """Check misc rules (declarations, asm, goto, cast, comma operator)."""
    v = []
    nodes = src.nodes

    if cfg.is_enabled("decl.single"):
        for decl in nodes.get("declaration"):
            if any(c.type == "function_declarator" for c in decl.children):
                continue
            declarators = [
                c
                for c in decl.children
                if c.type
                in ("init_declarator", "pointer_declarator", "identifier", "array_declarator")
            ]
            if len(declarators) > 1:
                v.append(src.at(decl, "decl.single", "One declaration per line"))

    if cfg.is_enabled("stat.asm"):
        v.extend(
            src.at(node, "stat.asm", "asm not allowed")
            for node in nodes.get("gnu_asm_expression", "gnu_asm_statement")
        )

    if cfg.is_enabled("keyword.goto"):
        v.extend(
            src.at(node, "keyword.goto", "goto not allowed") for node in nodes.get("goto_statement")
        )

    if cfg.is_enabled("cast"):
        v.extend(
            src.at(node, "cast", "Explicit cast not allowed")
            for node in nodes.get("cast_expression")
        )

    # stat.sep: comma operator allowed only in 'for' clauses (spec 5.25)
    if cfg.is_enabled("stat.sep"):
        for node in nodes.get("comma_expression"):
            parent = node.parent
            if parent is not None and parent.type == "comma_expression":
                continue  # report only the outermost expression
            while parent is not None and parent.type == "parenthesized_expression":
                parent = parent.parent
            if parent is not None and parent.type != "for_statement":
                v.append(src.at(node, "stat.sep", "Comma operator only allowed in 'for'"))

    return v


def check_vla(src: Source, cfg: Config) -> list[Violation]:
    """Check for variable-length arrays."""
    if not cfg.is_enabled("decl.vla"):
        return []
    v = []
    for decl in src.nodes.get("declaration"):
        for arr in find_nodes(decl, "array_declarator"):
            # The size expression sits between [ and ]
            size = None
            for part in arr.children:
                if part.type == "[":
                    size = None
                elif part.type == "]":
                    break
                else:
                    size = part
            if size and size.type == "identifier" and not src.text_of(size).isupper():
                v.append(src.at(arr, "decl.vla", "VLA not allowed"))
    return v


def check_ctrl_empty(src: Source, cfg: Config) -> list[Violation]:
    """Check for empty loop bodies."""
    if not cfg.is_enabled("ctrl.empty"):
        return []
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


CHECKS = (
    check_file_format,
    check_braces,
    check_functions,
    check_preprocessor,
    check_misc,
    check_vla,
    check_ctrl_empty,
)
