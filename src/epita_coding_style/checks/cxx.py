"""C++-only checks."""

from __future__ import annotations

import os
import re
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING

from ..model import Severity, Source, Violation, child, find_nodes
from .common import params

if TYPE_CHECKING:
    from collections.abc import Iterator

    from tree_sitter import Node

    from ..config import Config

_C_HEADERS = {
    "assert.h",
    "complex.h",
    "ctype.h",
    "errno.h",
    "fenv.h",
    "float.h",
    "inttypes.h",
    "iso646.h",
    "limits.h",
    "locale.h",
    "math.h",
    "setjmp.h",
    "signal.h",
    "stdalign.h",
    "stdarg.h",
    "stdatomic.h",
    "stdbool.h",
    "stddef.h",
    "stdint.h",
    "stdio.h",
    "stdlib.h",
    "stdnoreturn.h",
    "string.h",
    "tgmath.h",
    "threads.h",
    "time.h",
    "uchar.h",
    "wchar.h",
    "wctype.h",
}

# C functions that have std:: equivalents
_C_FUNCTIONS = {
    "printf",
    "scanf",
    "malloc",
    "calloc",
    "realloc",
    "free",
    "memcpy",
    "memset",
    "memmove",
    "strlen",
    "strcmp",
    "strncmp",
    "strcpy",
    "strncpy",
    "strcat",
    "strncat",
    "atoi",
    "atof",
    "atol",
    "strtol",
    "strtoul",
    "strtod",
    "abs",
    "exit",
    "qsort",
    "bsearch",
}
_MALLOC_FUNCS = {"malloc", "calloc", "realloc", "free"}
_FORBIDDEN_OPS = {"operator,", "operator||", "operator&&"}

_CAMEL_CASE = re.compile(r"^[A-Z][a-zA-Z0-9]*$")
_LOWER_NS = re.compile(r"^[a-z_][a-z0-9_]*$")
_REF_PATTERN = re.compile(r"(\w)\s+&(\w)")
_PTR_PATTERN = re.compile(r"(\w)\s+\*(\w)")

_CONSTEXPR_LITERALS = frozenset(
    ("number_literal", "string_literal", "true", "false", "char_literal")
)
_LITERAL_TYPES = frozenset(
    ("number_literal", "string_literal", "char_literal", "true", "false", "null", "nullptr")
)
_STMT_TYPES = frozenset(
    (
        "expression_statement",
        "return_statement",
        "break_statement",
        "continue_statement",
        "throw_statement",
    )
)
_DECL_TYPES = frozenset(("declaration", "field_declaration", "function_definition"))


def check_file_ext(src: Source, _cfg: Config) -> list[Violation]:
    """C++ files use .cc/.hh, not .cpp/.hpp."""
    ext = Path(src.path).suffix
    expected = {".cpp": ".cc", ".hpp": ".hh"}.get(ext)
    if expected is None:
        return []
    return [src.violation("file.ext", f"Use '{expected}' extension instead of '{ext}'")]


def check_cpp_pragma_once(src: Source, _cfg: Config) -> list[Violation]:
    if not src.path.endswith((".hh", ".hxx")) or any(
        line.strip() == "#pragma once" for line in src.lines
    ):
        return []
    return [
        src.violation(
            "cpp.pragma.once", "Use #pragma once instead of include guards", show_line=True
        )
    ]


def check_cpp_include_filetype(src: Source, _cfg: Config) -> list[Violation]:
    return [
        src.at(
            inc,
            "cpp.include.filetype",
            f"Included file '{fname}' should have .hh or .hxx extension",
            column=False,
        )
        for inc in src.nodes.get("preproc_include")
        for part in inc.children
        if part.type == "string_literal"
        and not (fname := src.text_of(part).strip('"')).endswith((".hh", ".hxx"))
    ]


# (line, kind, name) of an #include; kind is "self" (same-name header), "system" or "local"
_Include = tuple[int, str, str]
# (line, message, severity) of a misordered #include
_Misorder = tuple[int, str, Severity]


def _includes(src: Source) -> list[_Include]:
    base = os.path.splitext(os.path.basename(src.path))[0]
    includes = []
    for inc in src.nodes.get("preproc_include"):
        line = inc.start_point[0] + 1
        for part in inc.children:
            if part.type == "system_lib_string":
                includes.append((line, "system", src.text_of(part)))
            elif part.type == "string_literal":
                fname = src.text_of(part).strip('"')
                kind = "self" if os.path.splitext(fname)[0] == base else "local"
                includes.append((line, kind, fname))
    return includes


def _self_not_first(src: Source, includes: list[_Include]) -> list[_Misorder]:
    self_inc = next((i for i in includes if i[1] == "self"), None)
    # A .hh may include its own .hxx at the end
    if not self_inc or (src.path.endswith(".hh") and self_inc[2].endswith(".hxx")):
        return []
    first_other = next((i for i in includes if i[1] != "self"), None)
    if first_other and self_inc[0] > first_other[0]:
        return [(self_inc[0], "Same-name header should be included first", Severity.MAJOR)]
    return []


def _local_before_system(includes: list[_Include]) -> list[_Misorder]:
    for i, (line, kind, _) in enumerate(includes):
        if kind == "local" and any(k == "system" for _, k, _ in includes[i + 1 :]):
            return [(line, "System includes should come before local includes", Severity.MAJOR)]
    return []


def _not_alphabetical(includes: list[_Include]) -> list[_Misorder]:
    groups: dict[str, list[tuple[int, str]]] = {}
    for line, kind, fname in includes:
        groups.setdefault(kind, []).append((line, fname))
    found = []
    for items in groups.values():
        found += [
            (line, f"Includes not in alphabetical order: '{name}' before '{prev}'", Severity.MINOR)
            for (_, prev), (line, name) in pairwise(items)
            if name.lower() < prev.lower()
        ][:1]
    return found


def _groups_not_separated(src: Source, includes: list[_Include]) -> list[_Misorder]:
    return [
        (line, "Include groups should be separated by a blank line", Severity.MINOR)
        for (prev_line, prev_kind, _), (line, kind, _) in pairwise(includes)
        if kind != prev_kind and all(s.strip() for s in src.lines[prev_line : line - 1])
    ]


def check_cpp_include_order(src: Source, _cfg: Config) -> list[Violation]:
    """Includes come in order: same-name header, system, local."""
    includes = _includes(src)
    return [
        src.violation("cpp.include.order", message, line, severity=severity, show_line=True)
        for line, message, severity in (
            _self_not_first(src, includes)
            + _local_before_system(includes)
            + _not_alphabetical(includes)
            + _groups_not_separated(src, includes)
        )
    ]


def check_cpp_constexpr(src: Source, _cfg: Config) -> list[Violation]:
    return [
        src.at(
            decl,
            "cpp.constexpr",
            "Consider using constexpr for compile-time constant",
            severity=Severity.MINOR,
            column=False,
        )
        for decl in src.nodes.root.children
        if decl.type == "declaration"
        and any(src.text_of(c) == "const" for c in decl.children if c.type == "type_qualifier")
        for part in decl.children
        if part.type == "init_declarator" and child(part, *_CONSTEXPR_LITERALS)
    ]


def check_global_casts(src: Source, _cfg: Config) -> list[Violation]:
    return [
        src.at(node, "global.casts", "Use C++ casts (static_cast, etc.) instead of C-style casts")
        for node in src.nodes.get("cast_expression")
    ]


def _calls(src: Source) -> Iterator[tuple[Node, str]]:
    """Yield (call, function name) of calls to a plain identifier."""
    for node in src.nodes.get("call_expression"):
        func = node.children[0] if node.children else None
        if func and func.type == "identifier":
            yield node, src.text_of(func)


def check_global_memory_no_malloc(src: Source, _cfg: Config) -> list[Violation]:
    return [
        src.at(
            node,
            "global.memory.no_malloc",
            f"Don't use {fname}(), use new/delete or smart pointers",
        )
        for node, fname in _calls(src)
        if fname in _MALLOC_FUNCS
    ]


def check_c_std_functions(src: Source, _cfg: Config) -> list[Violation]:
    return [
        src.at(node, "c.std_functions", f"Use std::{fname} instead of {fname}")
        for node, fname in _calls(src)
        if fname in _C_FUNCTIONS and fname not in _MALLOC_FUNCS
    ]


def check_global_nullptr(src: Source, _cfg: Config) -> list[Violation]:
    return [
        src.at(node, "global.nullptr", "Use nullptr instead of NULL")
        for node in src.nodes.get("null")
        if src.text_of(node) == "NULL"
    ]


def check_c_extern(src: Source, _cfg: Config) -> list[Violation]:
    return [
        src.at(node, "c.extern", 'No extern "C" in C++ code')
        for node in src.nodes.get("linkage_specification")
    ]


def check_c_headers(src: Source, _cfg: Config) -> list[Violation]:
    return [
        src.at(
            inc,
            "c.headers",
            f"Use <c{header.replace('.h', '')}> instead of <{header}>",
            column=False,
        )
        for inc in src.nodes.get("preproc_include")
        for part in inc.children
        if part.type == "system_lib_string"
        and (header := src.text_of(part).strip("<>")) in _C_HEADERS
    ]


def check_naming_class(src: Source, _cfg: Config) -> list[Violation]:
    return [
        src.at(ident, "naming.class", f"Class/struct '{name}' should be CamelCase")
        for node in src.nodes.get("class_specifier", "struct_specifier")
        if (ident := child(node, "type_identifier"))
        and not _CAMEL_CASE.match(name := src.text_of(ident))
    ]


def check_naming_namespace(src: Source, _cfg: Config) -> list[Violation]:
    """Lowercase namespace names, and a '// namespace name' closing comment."""
    v = []
    for node in src.nodes.get("namespace_definition"):
        ident = child(node, "namespace_identifier")
        if not ident:
            continue
        name = src.text_of(ident)
        if not _LOWER_NS.match(name):
            v.append(src.at(ident, "naming.namespace", f"Namespace '{name}' should be lowercase"))
        end = node.end_point[0]
        closing = (src.line(end) or "").strip()
        if closing.startswith("}") and f"// namespace {name}" not in closing:
            v.append(
                src.violation(
                    "naming.namespace",
                    f"Closing brace should have comment '// namespace {name}'",
                    end + 1,
                    severity=Severity.MINOR,
                    show_line=True,
                )
            )
    return v


_TYPE_KEYWORDS = frozenset(
    {
        "int",
        "char",
        "float",
        "double",
        "long",
        "short",
        "unsigned",
        "signed",
        "void",
        "bool",
        "auto",
        "const",
        "static",
        "volatile",
        "extern",
        "virtual",
        "inline",
        "explicit",
        "mutable",
    }
)


def _is_declaration_context(line: str) -> bool:
    """Heuristic: the line looks like a declaration (has a type)."""
    words = line.split()
    if not words:
        return False
    first = words[0]
    if any(w in _TYPE_KEYWORDS for w in words[:3]):
        return True
    if first[0].isupper() and first.isalpha():
        return True
    return first.startswith("std::")


def _misplaced(src: Source, rule: str, pattern: re.Pattern[str], sym: str) -> list[Violation]:
    """Violations where sym sits next to the variable instead of the type."""
    v: list[Violation] = []
    for i, line in enumerate(src.code_lines, 1):
        if line.strip().startswith("#") or not _is_declaration_context(line):
            continue
        v.extend(
            Violation(
                src.path,
                i,
                rule,
                f"{sym} should be next to type, not variable",
                line_content=line,
                column=line.index(sym, m.start()),
            )
            for m in pattern.finditer(line)
        )
    return v


def check_decl_ref(src: Source, _cfg: Config) -> list[Violation]:
    return _misplaced(src, "decl.ref", _REF_PATTERN, "&")


def check_decl_point(src: Source, _cfg: Config) -> list[Violation]:
    return _misplaced(src, "decl.point", _PTR_PATTERN, "*")


def _is_type(src: Source, node: Node, name: str) -> bool:
    return node.type == "type_identifier" and src.text_of(node) == name


def _single_arg_ctors(src: Source, cls: Node, name: str) -> Iterator[tuple[Node, Node]]:
    """Yield (declaration, parameter) of cls's non-explicit constructors taking one argument."""
    for body in cls.children:
        if body.type != "field_declaration_list":
            continue
        for decl in body.children:
            if decl.type not in _DECL_TYPES or child(decl, "explicit_function_specifier"):
                continue
            func = next(
                (c for c in reversed(decl.children) if c.type == "function_declarator"), None
            )
            if func and src.id_of(func) == name and len(plist := params(func) or []) == 1:
                yield decl, plist[0]


def _is_copy_or_move(src: Source, param: Node, name: str) -> bool:
    return bool(child(param, "reference_declarator")) and any(
        _is_type(src, c, name)
        or (c.type == "template_type" and any(_is_type(src, gc, name) for gc in c.children))
        for c in param.children
    )


def check_decl_ctor_explicit(src: Source, _cfg: Config) -> list[Violation]:
    """Single-argument constructors are explicit."""
    v: list[Violation] = []
    for cls in src.nodes.get("class_specifier", "struct_specifier"):
        if not (ident := child(cls, "type_identifier")):
            continue
        name = src.text_of(ident)
        v.extend(
            src.at(
                decl,
                "decl.ctor.explicit",
                f"Single-argument constructor '{name}' should be explicit",
                severity=Severity.MINOR,
                column=False,
            )
            for decl, param in _single_arg_ctors(src, cls, name)
            if not _is_copy_or_move(src, param, name)
        )
    return v


def check_ctrl_switch(src: Source, _cfg: Config) -> list[Violation]:
    """Switch statements have a default case of their own, not one of a nested switch."""
    v = []
    for sw in src.nodes.get("switch_statement"):
        body = child(sw, "compound_statement")
        if not body or not any(
            c.type == "case_statement" and c.children and src.text_of(c.children[0]) == "default"
            for c in body.children
        ):
            v.append(
                src.at(
                    sw, "ctrl.switch", "Switch statement should have a default case", column=False
                )
            )
    return v


def check_ctrl_switch_padding(src: Source, _cfg: Config) -> list[Violation]:
    v = []
    for node in src.nodes.get("case_statement"):
        colon = child(node, ":")
        if not colon:
            continue
        row, col = colon.start_point
        line = src.line(row)
        if line is not None and col > 0 and line[col - 1].isspace():
            v.append(
                src.violation(
                    "ctrl.switch.padding",
                    "No space before colon in case/default label",
                    row + 1,
                    column=col,
                    show_line=True,
                )
            )
    return v


def check_braces_empty(src: Source, _cfg: Config) -> list[Violation]:
    v = []
    for node in src.nodes.get("compound_statement"):
        if any(c.type not in ("{", "}", "comment") for c in node.children):
            continue
        if node.start_point[0] != node.end_point[0]:
            v.append(
                src.at(
                    node, "braces.empty", "Empty body should use {} on the same line", column=False
                )
            )
        elif src.text_of(node) != "{}":
            v.append(
                src.at(node, "braces.empty", "Empty body should be {} with no space", column=False)
            )
    return v


def check_braces_single_exp(src: Source, _cfg: Config) -> list[Violation]:
    bodies = []
    for node in src.nodes.get("if_statement", "while_statement", "for_statement", "do_statement"):
        stmts = [c for c in node.children if c.type in _STMT_TYPES]
        if stmts:
            bodies.append(stmts[-1])
    # else if: the child is an if_statement, not a bare statement
    for node in src.nodes.get("else_clause"):
        bodies.extend(c for c in node.children if c.type in _STMT_TYPES)
    return [
        src.at(
            body,
            "braces.single_exp",
            "Single-expression block should have braces",
            severity=Severity.MINOR,
            column=False,
        )
        for body in bodies
    ]


def check_err_throw(src: Source, _cfg: Config) -> list[Violation]:
    v = []
    for node in src.nodes.get("throw_statement"):
        for part in node.children:
            if part.type in _LITERAL_TYPES:
                v.append(src.at(node, "err.throw", "Don't throw literals, throw exception objects"))
            elif part.type == "new_expression":
                v.append(src.at(node, "err.throw", "Don't throw with new, throw by value"))
    return v


def check_err_throw_paren(src: Source, _cfg: Config) -> list[Violation]:
    return [
        src.at(node, "err.throw.paren", "No parentheses after throw")
        for node in src.nodes.get("throw_statement")
        for part in node.children
        if part.type == "parenthesized_expression"
    ]


def check_err_throw_catch(src: Source, _cfg: Config) -> list[Violation]:
    return [
        src.at(
            param,
            "err.throw.catch",
            "Catch exceptions by reference",
            severity=Severity.MINOR,
            column=False,
        )
        for node in src.nodes.get("catch_clause")
        for part in node.children
        if part.type == "parameter_list"
        for param in part.children
        if param.type == "parameter_declaration"
        and "&" not in (t := src.text_of(param))
        and t != "..."
    ]


def check_exp_padding(src: Source, _cfg: Config) -> list[Violation]:
    return [
        src.at(node, "exp.padding", "No space between 'operator' and the operator symbol")
        for node in src.nodes.get("operator_name")
        if " " in src.text_of(node)[len("operator") :]
    ]


def check_fun_proto_void_cxx(src: Source, _cfg: Config) -> list[Violation]:
    return [
        src.at(
            fd,
            "fun.proto.void.cxx",
            f"'{src.id_of(fd) or '?'}' should use () not (void) in C++",
            column=False,
        )
        for fd in src.nodes.get("function_declarator")
        if (plist := params(fd)) and len(plist) == 1 and src.text_of(plist[0]).strip() == "void"
    ]


def check_op_assign(src: Source, _cfg: Config) -> list[Violation]:
    """operator= returns Class& and ends with return *this."""
    v = []
    for func in src.nodes.get("function_definition"):
        if not any(src.text_of(n) == "operator=" for n in find_nodes(func, "operator_name")):
            continue
        block = child(func, "compound_statement")
        if not child(func, "reference_declarator"):
            msg = "Assignment operator should return Class&"
        elif block and "return *this" not in src.text_of(block):
            msg = "Assignment operator should return *this"
        else:
            continue
        v.append(src.at(func, "op.assign", msg, column=False))
    return v


def check_op_overload(src: Source, _cfg: Config) -> list[Violation]:
    """Forbidden overloads: op.overload, and op.overload.binand for operator&.

    Both rules come from one walk so that violations on one line keep source order.
    """
    v = []
    for node in src.nodes.get("operator_name"):
        op = src.text_of(node).replace(" ", "")
        if op in _FORBIDDEN_OPS:
            v.append(src.at(node, "op.overload", f"Don't overload {op}", column=False))
        elif op == "operator&":
            v.append(
                src.at(
                    node,
                    "op.overload.binand",
                    f"Don't overload {op}",
                    severity=Severity.MINOR,
                    column=False,
                )
            )
    return v


def check_enum_class(src: Source, _cfg: Config) -> list[Violation]:
    return [
        src.at(
            node,
            "enum.class",
            "Prefer 'enum class' over plain 'enum'",
            severity=Severity.MINOR,
            column=False,
        )
        for node in src.nodes.get("enum_specifier")
        if not child(node, "class", "struct")
    ]


_TEMPLATE_TYPES = frozenset(("template_parameter_list", "template_argument_list"))
_REF_TYPES = frozenset(("reference_declarator", "abstract_reference_declarator", "type_descriptor"))
_PTR_TYPES = frozenset(("pointer_declarator", "abstract_pointer_declarator"))


def _non_binary_ops(src: Source) -> set[tuple[int, str]]:
    """(row, op) pairs where >, >>, &, or * are NOT binary operators."""
    excluded: set[tuple[int, str]] = set()
    for node in src.nodes.get(*_TEMPLATE_TYPES, *_REF_TYPES, *_PTR_TYPES, "trailing_return_type"):
        end = node.end_point[0]
        if node.type in _TEMPLATE_TYPES:
            excluded.update(((end, ">"), (end, ">>")))
        elif node.type in _REF_TYPES:
            excluded.update(
                (c.start_point[0], c.type) for c in node.children if c.type in ("&", "&&")
            )
        elif node.type in _PTR_TYPES:
            excluded.update((c.start_point[0], "*") for c in node.children if c.type == "*")
        else:
            excluded.update(((end, "&"), (end, "*"), (end, ">"), (end, ">>")))
    return excluded


# Longest first for greedy matching
_BIN_OPS = (
    "&&",
    "||",
    "<<",
    ">>",
    "==",
    "!=",
    "<=",
    ">=",
    "+",
    "-",
    "*",
    "/",
    "%",
    "&",
    "|",
    "^",
    "<",
    ">",
)


def _trailing_op(s: str) -> str | None:
    """Return the operator s ends with, if it follows an operand."""
    for op in _BIN_OPS:
        before = s[: -len(op)].rstrip()
        if s.endswith(op) and before and not before.endswith(("(", ",", "=")):
            return op
    return None


def check_exp_linebreak(src: Source, _cfg: Config) -> list[Violation]:
    """Line breaks come before binary operators, not after."""
    v = []
    excluded = _non_binary_ops(src)
    for i, line in enumerate(src.code_lines, 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if (op := _trailing_op(s)) and (i - 1, op) not in excluded:
            v.append(
                Violation(
                    src.path,
                    i,
                    "exp.linebreak",
                    f"Line break should come before '{op}', not after",
                    line_content=line,
                )
            )
    return v


# Order matters: violations at the same position keep this order
CHECKS = (
    check_cpp_pragma_once,
    check_cpp_include_filetype,
    check_cpp_include_order,
    check_cpp_constexpr,
    check_global_casts,
    check_global_memory_no_malloc,
    check_c_std_functions,
    check_global_nullptr,
    check_c_extern,
    check_c_headers,
    check_naming_class,
    check_naming_namespace,
    check_decl_ref,
    check_decl_point,
    check_decl_ctor_explicit,
    check_ctrl_switch,
    check_ctrl_switch_padding,
    check_braces_empty,
    check_braces_single_exp,
    check_err_throw,
    check_err_throw_paren,
    check_err_throw_catch,
    check_exp_padding,
    check_exp_linebreak,
    check_fun_proto_void_cxx,
    check_op_assign,
    check_op_overload,
    check_enum_class,
)
