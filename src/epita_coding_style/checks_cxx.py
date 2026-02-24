"""C++ (CXX) specific check functions for the EPITA coding style checker."""

from __future__ import annotations

import re

from .config import Config
from .core import Violation, Severity, NodeCache, text, find_id, find_nodes, line_at
from .checks import check_vla, check_ctrl_empty, count_function_lines

# C standard headers that should be replaced with C++ equivalents
_C_HEADERS = {
    "assert.h", "complex.h", "ctype.h", "errno.h", "fenv.h", "float.h",
    "inttypes.h", "iso646.h", "limits.h", "locale.h", "math.h", "setjmp.h",
    "signal.h", "stdalign.h", "stdarg.h", "stdatomic.h", "stdbool.h",
    "stddef.h", "stdint.h", "stdio.h", "stdlib.h", "stdnoreturn.h",
    "string.h", "tgmath.h", "threads.h", "time.h", "uchar.h", "wchar.h",
    "wctype.h",
}

# C functions that have std:: equivalents
_C_FUNCTIONS = {"printf", "scanf", "malloc", "calloc", "realloc", "free",
                "memcpy", "memset", "memmove", "strlen", "strcmp", "strncmp",
                "strcpy", "strncpy", "strcat", "strncat", "atoi", "atof",
                "atol", "strtol", "strtoul", "strtod", "abs", "exit",
                "qsort", "bsearch"}

# Memory allocation functions forbidden in C++
_MALLOC_FUNCS = {"malloc", "calloc", "realloc", "free"}

# Forbidden operator overloads
_FORBIDDEN_OPS = {"operator,", "operator||", "operator&&"}

_CAMEL_CASE = re.compile(r'^[A-Z][a-zA-Z0-9]*$')
_LOWER_NS = re.compile(r'^[a-z_][a-z0-9_]*$')

# Source file extensions that should not be #included
_SOURCE_EXTS = {".cc", ".cpp", ".cxx", ".c"}


def check_cxx_preprocessor(path: str, lines: list[str], content_bytes: bytes,
                           nodes: NodeCache, cfg: Config) -> list[Violation]:
    """Check CXX preprocessor rules: pragma.once, include.filetype, include.order, constexpr."""
    v = []

    # pragma.once: header files must use #pragma once
    if cfg.is_enabled("cpp.pragma.once") and path.endswith(('.hh', '.hxx')):
        has_pragma = any(line.strip() == '#pragma once' for line in lines)
        if not has_pragma:
            v.append(Violation(path, 1, "cpp.pragma.once",
                               "Use #pragma once instead of include guards",
                               line_content=lines[0] if lines else None))

    # include.filetype: only .hh/.hxx includes (no source files)
    if cfg.is_enabled("cpp.include.filetype"):
        for inc in nodes.get('preproc_include'):
            inc_text = text(inc, content_bytes)
            # Extract the included filename
            for child in inc.children:
                if child.type == 'string_literal':
                    fname = text(child, content_bytes).strip('"')
                    for ext in _SOURCE_EXTS:
                        if fname.endswith(ext):
                            line_num = inc.start_point[0] + 1
                            v.append(Violation(path, line_num, "cpp.include.filetype",
                                               f"Don't include source file '{fname}'",
                                               line_content=line_at(lines, inc.start_point[0])))
                            break

    # include.order: same-name header first, then system, then local
    if cfg.is_enabled("cpp.include.order"):
        v.extend(_check_include_order(path, lines, nodes, content_bytes))

    # constexpr: compile-time constants should use constexpr
    if cfg.is_enabled("cpp.constexpr"):
        for decl in nodes.root.children:
            if decl.type != 'declaration':
                continue
            has_const = any(text(c, content_bytes) == 'const'
                           for c in decl.children if c.type == 'type_qualifier')
            if not has_const:
                continue
            # Check if it's a simple literal init that could be constexpr
            for child in decl.children:
                if child.type == 'init_declarator':
                    for c in child.children:
                        if c.type in ('number_literal', 'string_literal', 'true', 'false', 'char_literal'):
                            line_num = decl.start_point[0] + 1
                            v.append(Violation(path, line_num, "cpp.constexpr",
                                               "Consider using constexpr for compile-time constant",
                                               Severity.MINOR,
                                               line_content=line_at(lines, decl.start_point[0])))
                            break

    return v


def _check_include_order(path: str, lines: list[str], nodes: NodeCache,
                         content_bytes: bytes) -> list[Violation]:
    """Check that includes are ordered: same-name header, system, local."""
    import os
    v = []
    base = os.path.splitext(os.path.basename(path))[0]

    includes = []
    for inc in nodes.get('preproc_include'):
        line_num = inc.start_point[0] + 1
        for child in inc.children:
            if child.type == 'system_lib_string':
                includes.append((line_num, 'system', text(child, content_bytes)))
            elif child.type == 'string_literal':
                fname = text(child, content_bytes).strip('"')
                fname_base = os.path.splitext(fname)[0]
                if fname_base == base:
                    includes.append((line_num, 'self', fname))
                else:
                    includes.append((line_num, 'local', fname))

    if not includes:
        return v

    # Check self-include is first
    self_incs = [i for i in includes if i[1] == 'self']
    if self_incs:
        first_non_self = next((i for i in includes if i[1] != 'self'), None)
        if first_non_self and self_incs[0][0] > first_non_self[0]:
            v.append(Violation(path, self_incs[0][0], "cpp.include.order",
                               "Same-name header should be included first",
                               line_content=lines[self_incs[0][0] - 1] if self_incs[0][0] <= len(lines) else None))

    # Find first local that comes before a system include
    for i, (line_num, kind, _) in enumerate(includes):
        if kind == 'local':
            for line_num2, kind2, _ in includes[i + 1:]:
                if kind2 == 'system':
                    v.append(Violation(path, line_num, "cpp.include.order",
                                       "System includes should come before local includes",
                                       line_content=lines[line_num - 1] if line_num <= len(lines) else None))
                    return v  # Report only once

    return v


def check_cxx_globals(path: str, lines: list[str], content_bytes: bytes,
                      nodes: NodeCache, cfg: Config) -> list[Violation]:
    """Check CXX global rules: casts, memory, nullptr, extern C, C headers, C functions."""
    v = []

    # global.casts: no C-style casts
    if cfg.is_enabled("global.casts"):
        for node in nodes.get('cast_expression'):
            line_num = node.start_point[0] + 1
            line_content = line_at(lines, node.start_point[0])
            v.append(Violation(path, line_num, "global.casts",
                               "Use C++ casts (static_cast, etc.) instead of C-style casts",
                               line_content=line_content, column=node.start_point[1]))

    # global.memory.no_malloc: no malloc/calloc/realloc/free
    if cfg.is_enabled("global.memory.no_malloc"):
        for node in nodes.get('call_expression'):
            func_node = node.children[0] if node.children else None
            if func_node and func_node.type == 'identifier':
                fname = text(func_node, content_bytes)
                if fname in _MALLOC_FUNCS:
                    line_num = node.start_point[0] + 1
                    line_content = line_at(lines, node.start_point[0])
                    v.append(Violation(path, line_num, "global.memory.no_malloc",
                                       f"Don't use {fname}(), use new/delete or smart pointers",
                                       line_content=line_content, column=node.start_point[1]))
        # Also catch free() which may not be a call_expression if used as free(ptr)
        # Already handled above since free(ptr) is a call_expression

    # global.nullptr: use nullptr, not NULL
    if cfg.is_enabled("global.nullptr"):
        for node in nodes.get('null'):
            node_text = text(node, content_bytes)
            if node_text == 'NULL':
                line_num = node.start_point[0] + 1
                line_content = line_at(lines, node.start_point[0])
                v.append(Violation(path, line_num, "global.nullptr",
                                   "Use nullptr instead of NULL",
                                   line_content=line_content, column=node.start_point[1]))

    # c.extern: no extern "C"
    if cfg.is_enabled("c.extern"):
        for node in nodes.get('linkage_specification'):
            line_num = node.start_point[0] + 1
            line_content = line_at(lines, node.start_point[0])
            v.append(Violation(path, line_num, "c.extern",
                               'No extern "C" in C++ code',
                               line_content=line_content, column=node.start_point[1]))

    # c.headers: no C headers
    if cfg.is_enabled("c.headers"):
        for inc in nodes.get('preproc_include'):
            for child in inc.children:
                if child.type == 'system_lib_string':
                    header = text(child, content_bytes).strip('<>')
                    if header in _C_HEADERS:
                        line_num = inc.start_point[0] + 1
                        cxx_header = 'c' + header.replace('.h', '')
                        line_content = line_at(lines, inc.start_point[0])
                        v.append(Violation(path, line_num, "c.headers",
                                           f"Use <{cxx_header}> instead of <{header}>",
                                           line_content=line_content))

    # c.std_functions: use std:: equivalents
    if cfg.is_enabled("c.std_functions"):
        for node in nodes.get('call_expression'):
            func_node = node.children[0] if node.children else None
            if func_node and func_node.type == 'identifier':
                fname = text(func_node, content_bytes)
                if fname in _C_FUNCTIONS and fname not in _MALLOC_FUNCS:
                    line_num = node.start_point[0] + 1
                    line_content = line_at(lines, node.start_point[0])
                    v.append(Violation(path, line_num, "c.std_functions",
                                       f"Use std::{fname} instead of {fname}",
                                       line_content=line_content, column=node.start_point[1]))

    return v


def check_cxx_naming(path: str, lines: list[str], content_bytes: bytes,
                     nodes: NodeCache, cfg: Config) -> list[Violation]:
    """Check CXX naming rules: class/struct names (CamelCase), namespace (lowercase + closing comment)."""
    v = []

    # naming.class: CamelCase class/struct names
    if cfg.is_enabled("naming.class"):
        for node in nodes.get('class_specifier', 'struct_specifier'):
            for child in node.children:
                if child.type == 'type_identifier':
                    name = text(child, content_bytes)
                    if not _CAMEL_CASE.match(name):
                        line_num = child.start_point[0] + 1
                        line_content = line_at(lines, child.start_point[0])
                        v.append(Violation(path, line_num, "naming.class",
                                           f"Class/struct '{name}' should be CamelCase",
                                           line_content=line_content, column=child.start_point[1]))
                    break

    # naming.namespace: lowercase namespaces + closing comment
    if cfg.is_enabled("naming.namespace"):
        for node in nodes.get('namespace_definition'):
            for child in node.children:
                if child.type == 'namespace_identifier':
                    name = text(child, content_bytes)
                    if not _LOWER_NS.match(name):
                        line_num = child.start_point[0] + 1
                        line_content = line_at(lines, child.start_point[0])
                        v.append(Violation(path, line_num, "naming.namespace",
                                           f"Namespace '{name}' should be lowercase",
                                           line_content=line_content, column=child.start_point[1]))

            # Check closing comment: } // namespace <name>
            end_line = node.end_point[0]
            if end_line < len(lines):
                closing = lines[end_line].strip()
                ns_name = None
                for child in node.children:
                    if child.type == 'namespace_identifier':
                        ns_name = text(child, content_bytes)
                        break
                if ns_name and closing.startswith('}'):
                    expected = f'// namespace {ns_name}'
                    if expected not in closing:
                        v.append(Violation(path, end_line + 1, "naming.namespace",
                                           f"Closing brace should have comment '// namespace {ns_name}'",
                                           Severity.MINOR,
                                           line_content=lines[end_line]))

    return v


def check_cxx_declarations(path: str, lines: list[str], content_bytes: bytes,
                           nodes: NodeCache, cfg: Config) -> list[Violation]:
    """Check CXX declaration rules: ref/pointer placement, explicit constructors, VLA."""
    v = []

    # decl.ref / decl.point: & and * should be next to type, not variable
    if cfg.is_enabled("decl.ref") or cfg.is_enabled("decl.point"):
        v.extend(_check_ref_pointer_placement(path, lines, content_bytes, nodes, cfg))

    # decl.ctor.explicit: single-arg constructors should be explicit
    if cfg.is_enabled("decl.ctor.explicit"):
        v.extend(_check_explicit_ctors(path, lines, content_bytes, nodes))

    # decl.vla: no variable-length arrays (shared helper)
    v.extend(check_vla(path, nodes, content_bytes, lines, cfg))

    return v


def _check_ref_pointer_placement(path: str, lines: list[str], content_bytes: bytes,
                                 nodes: NodeCache, cfg: Config) -> list[Violation]:
    """Check that & and * are next to type, not variable name."""
    v = []
    # Use regex on lines for this - AST doesn't capture whitespace well
    # Pattern: type <space(s)> &varname or type <space(s)> *varname
    ref_pattern = re.compile(r'(\w)\s+&(\w)')
    ptr_pattern = re.compile(r'(\w)\s+\*(\w)')

    for i, line in enumerate(lines, 1):
        s = line.strip()
        # Skip preprocessor, comments, string literals in a basic way
        if s.startswith(('#', '//', '/*', '*')):
            continue

        if cfg.is_enabled("decl.ref"):
            for m in ref_pattern.finditer(line):
                # Avoid matching && (logical and) or &= etc.
                pos = m.start(0)
                # Check it's not inside a string or preceded by another &
                amp_pos = line.index('&', pos)
                if amp_pos + 1 < len(line) and line[amp_pos + 1] == '&':
                    continue  # It's && operator
                # Check context: should be in a declaration context
                if _is_declaration_context(line):
                    v.append(Violation(path, i, "decl.ref",
                                       "& should be next to type, not variable",
                                       line_content=line, column=amp_pos))

        if cfg.is_enabled("decl.point"):
            for m in ptr_pattern.finditer(line):
                pos = m.start(0)
                star_pos = line.index('*', pos)
                # Skip if inside a comment or multiplication
                if _is_declaration_context(line):
                    v.append(Violation(path, i, "decl.point",
                                       "* should be next to type, not variable",
                                       line_content=line, column=star_pos))

    return v


def _is_declaration_context(line: str) -> bool:
    """Heuristic: check if a line looks like a declaration (has a type)."""
    s = line.strip()
    # Common type keywords that suggest declaration context
    type_keywords = {'int', 'char', 'float', 'double', 'long', 'short', 'unsigned',
                     'signed', 'void', 'bool', 'auto', 'const', 'static', 'volatile',
                     'extern', 'virtual', 'inline', 'explicit', 'mutable'}
    words = s.split()
    if not words:
        return False
    # Function parameters or variable declarations
    if any(w in type_keywords for w in words[:3]):
        return True
    # CamelCase type name (class type)
    if words[0][0].isupper() and words[0].isalpha():
        return True
    # std:: prefixed type
    if words[0].startswith('std::'):
        return True
    return False


def _check_explicit_ctors(path: str, lines: list[str], content_bytes: bytes,
                          nodes: NodeCache) -> list[Violation]:
    """Check that single-argument constructors are marked explicit."""
    v = []

    for cls in nodes.get('class_specifier', 'struct_specifier'):
        class_name = None
        for child in cls.children:
            if child.type == 'type_identifier':
                class_name = text(child, content_bytes)
                break
        if not class_name:
            continue

        # Look at field declarations / declarations inside the class
        for child in cls.children:
            if child.type != 'field_declaration_list':
                continue
            for decl in child.children:
                if decl.type not in ('declaration', 'field_declaration', 'function_definition'):
                    continue
                # Check if this is a constructor
                func_decl = None
                is_explicit = False
                for c in decl.children:
                    if c.type == 'function_declarator':
                        func_decl = c
                    elif c.type == 'explicit_function_specifier':
                        is_explicit = True

                if not func_decl:
                    continue

                # Check the function name matches class name (constructor)
                func_name = find_id(func_decl, content_bytes)
                if func_name != class_name:
                    continue

                # Count parameters
                params = []
                for c in func_decl.children:
                    if c.type == 'parameter_list':
                        params = [p for p in c.children if p.type == 'parameter_declaration']

                # Single-arg constructors need explicit (unless already explicit)
                if len(params) == 1 and not is_explicit:
                    line_num = decl.start_point[0] + 1
                    line_content = line_at(lines, decl.start_point[0])
                    v.append(Violation(path, line_num, "decl.ctor.explicit",
                                       f"Single-argument constructor '{class_name}' should be explicit",
                                       Severity.MINOR,
                                       line_content=line_content))

    return v


def check_cxx_control(path: str, lines: list[str], content_bytes: bytes,
                      nodes: NodeCache, cfg: Config) -> list[Violation]:
    """Check CXX control flow rules: switch/default, label padding, empty bodies."""
    v = []

    # ctrl.switch: default case must be present
    if cfg.is_enabled("ctrl.switch"):
        for sw in nodes.get('switch_statement'):
            has_default = False
            for child in find_nodes(sw, 'case_statement'):
                case_text = text(child.children[0], content_bytes) if child.children else ''
                if case_text == 'default':
                    has_default = True
                    break
            if not has_default:
                line_num = sw.start_point[0] + 1
                line_content = line_at(lines, sw.start_point[0])
                v.append(Violation(path, line_num, "ctrl.switch",
                                   "Switch statement should have a default case",
                                   line_content=line_content))

    # ctrl.switch.padding: no space before colon in case/default labels
    if cfg.is_enabled("ctrl.switch.padding"):
        for node in nodes.get('case_statement'):
            # Find the colon
            for child in node.children:
                if child.type == ':':
                    col = child.start_point[1]
                    line_idx = child.start_point[0]
                    if line_idx < len(lines) and col > 0 and lines[line_idx][col - 1] == ' ':
                        v.append(Violation(path, line_idx + 1, "ctrl.switch.padding",
                                           "No space before colon in case/default label",
                                           line_content=lines[line_idx], column=col))
                    break

    # ctrl.empty: empty loop bodies should use continue (shared helper)
    v.extend(check_ctrl_empty(path, lines, cfg))

    return v


def check_cxx_writing(path: str, lines: list[str], content_bytes: bytes,
                      nodes: NodeCache, cfg: Config) -> list[Violation]:
    """Check CXX writing rules: braces, throw, operators, enum class, etc."""
    v = []

    # braces.empty: {} on same line for empty bodies
    if cfg.is_enabled("braces.empty"):
        v.extend(_check_empty_braces(path, lines, content_bytes, nodes))

    # braces.single_exp: prefer braces for single-expression blocks
    if cfg.is_enabled("braces.single_exp"):
        v.extend(_check_single_exp_braces(path, lines, content_bytes, nodes))

    # err.throw: don't throw literals
    if cfg.is_enabled("err.throw"):
        for node in nodes.get('throw_statement'):
            for child in node.children:
                if child.type in ('number_literal', 'string_literal', 'char_literal',
                                  'true', 'false', 'null', 'nullptr'):
                    line_num = node.start_point[0] + 1
                    line_content = line_at(lines, node.start_point[0])
                    v.append(Violation(path, line_num, "err.throw",
                                       "Don't throw literals, throw exception objects",
                                       line_content=line_content, column=node.start_point[1]))

    # err.throw.catch: catch by reference
    if cfg.is_enabled("err.throw.catch"):
        for node in nodes.get('catch_clause'):
            for child in node.children:
                if child.type == 'parameter_list':
                    for param in child.children:
                        if param.type == 'parameter_declaration':
                            param_text = text(param, content_bytes)
                            if '&' not in param_text and param_text != '...':
                                line_num = param.start_point[0] + 1
                                line_content = line_at(lines, param.start_point[0])
                                v.append(Violation(path, line_num, "err.throw.catch",
                                                   "Catch exceptions by reference",
                                                   Severity.MINOR,
                                                   line_content=line_content))

    # err.throw.paren: no parentheses after throw
    if cfg.is_enabled("err.throw.paren"):
        for node in nodes.get('throw_statement'):
            for child in node.children:
                if child.type == 'parenthesized_expression':
                    line_num = node.start_point[0] + 1
                    line_content = line_at(lines, node.start_point[0])
                    v.append(Violation(path, line_num, "err.throw.paren",
                                       "No parentheses after throw",
                                       line_content=line_content, column=node.start_point[1]))

    # exp.padding: no space in operator keyword (operator++ not operator ++)
    if cfg.is_enabled("exp.padding"):
        v.extend(_check_operator_padding(path, lines))

    # exp.linebreak: line breaks before binary operators
    if cfg.is_enabled("exp.linebreak"):
        v.extend(_check_linebreak_operators(path, lines, root=nodes.root))

    # fun.proto.void.cxx: MUST NOT use void in C++ empty params
    if cfg.is_enabled("fun.proto.void.cxx"):
        v.extend(_check_no_void_params(path, lines, content_bytes, nodes))

    # fun.length: max 50 lines per function (CXX uses 50)
    if cfg.is_enabled("fun.length"):
        for func in nodes.get('function_definition'):
            body = None
            for child in func.children:
                if child.type == 'compound_statement':
                    body = child
            if body:
                count = count_function_lines(body, lines)
                if count > cfg.max_lines:
                    line_num = func.start_point[0] + 1
                    v.append(Violation(path, line_num, "fun.length",
                                       f"Function has {count} lines (max {cfg.max_lines})",
                                       line_content=line_at(lines, func.start_point[0])))

    # op.assign: assignment operators should return Class& and *this
    if cfg.is_enabled("op.assign"):
        v.extend(_check_op_assign(path, lines, content_bytes, nodes))

    # op.overload: don't overload operator,, operator||, operator&&
    if cfg.is_enabled("op.overload"):
        v.extend(_check_forbidden_overloads(path, lines, content_bytes, nodes, _FORBIDDEN_OPS, "op.overload"))

    # op.overload.binand: don't overload operator&
    if cfg.is_enabled("op.overload.binand"):
        v.extend(_check_forbidden_overloads(path, lines, content_bytes, nodes, {"operator&"}, "op.overload.binand",
                                            severity=Severity.MINOR))

    # enum.class: prefer enum class over plain enum
    if cfg.is_enabled("enum.class"):
        for node in nodes.get('enum_specifier'):
            has_class = any(child.type == 'class' for child in node.children)
            if not has_class:
                line_num = node.start_point[0] + 1
                line_content = line_at(lines, node.start_point[0])
                v.append(Violation(path, line_num, "enum.class",
                                   "Prefer 'enum class' over plain 'enum'",
                                   Severity.MINOR,
                                   line_content=line_content))

    return v


def _check_empty_braces(path: str, lines: list[str], content_bytes: bytes,
                        nodes: NodeCache) -> list[Violation]:
    """Check that empty bodies use {} on the same line."""
    v = []
    for node in nodes.get('compound_statement'):
        # Empty body: only { and } children, no statements
        real_children = [c for c in node.children if c.type not in ('{', '}', 'comment')]
        if not real_children:
            # Check if { and } are on different lines
            if node.start_point[0] != node.end_point[0]:
                line_num = node.start_point[0] + 1
                line_content = line_at(lines, node.start_point[0])
                v.append(Violation(path, line_num, "braces.empty",
                                   "Empty body should use {} on the same line",
                                   line_content=line_content))
    return v


def _check_single_exp_braces(path: str, lines: list[str], content_bytes: bytes,
                             nodes: NodeCache) -> list[Violation]:
    """Check that single-expression blocks have braces."""
    v = []
    for node in nodes.get('if_statement', 'while_statement', 'for_statement'):
        # Find the body (last significant child)
        body = None
        for child in node.children:
            if child.type in ('expression_statement', 'return_statement', 'break_statement',
                              'continue_statement', 'throw_statement'):
                body = child

        if body and body.type != 'compound_statement':
            line_num = body.start_point[0] + 1
            line_content = line_at(lines, body.start_point[0])
            v.append(Violation(path, line_num, "braces.single_exp",
                               "Single-expression block should have braces",
                               Severity.MINOR,
                               line_content=line_content))
    return v


def _check_operator_padding(path: str, lines: list[str]) -> list[Violation]:
    """Check no space in operator keyword (operator++ not operator ++)."""
    v = []
    pattern = re.compile(r'\boperator\s+[^\s(]')
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if s.startswith(('#', '//', '/*', '*')):
            continue
        if m := pattern.search(line):
            v.append(Violation(path, i, "exp.padding",
                               "No space between 'operator' and the operator symbol",
                               line_content=line, column=m.start()))
    return v


def _collect_non_binary_op_lines(root) -> set[tuple[int, str]]:
    """Use tree-sitter AST to find lines where >, >>, &, or * are NOT binary operators.

    Returns a set of (0-based line number, operator string) pairs that should be
    excluded from the binary operator line-break check.
    """
    excluded = set()

    def _walk(node):
        # Template parameter lists: template<...> — the > is not a binary op
        if node.type == 'template_parameter_list':
            end_line = node.end_point[0]
            excluded.add((end_line, '>'))
            excluded.add((end_line, '>>'))

        # Template argument lists: vector<int> — the > is not a binary op
        elif node.type == 'template_argument_list':
            end_line = node.end_point[0]
            excluded.add((end_line, '>'))
            excluded.add((end_line, '>>'))

        # Reference declarators: const int& x, auto f() -> const T&
        elif node.type in ('reference_declarator', 'abstract_reference_declarator',
                           'type_descriptor'):
            for child in node.children:
                if child.type == '&' or child.type == '&&':
                    excluded.add((child.start_point[0], child.type))

        # Pointer declarators: int* p
        elif node.type in ('pointer_declarator', 'abstract_pointer_declarator'):
            for child in node.children:
                if child.type == '*':
                    excluded.add((child.start_point[0], '*'))

        # Trailing return type: auto f() -> const T&
        elif node.type == 'trailing_return_type':
            end_line = node.end_point[0]
            # The & or * at end of a trailing return type is a type qualifier
            excluded.add((end_line, '&'))
            excluded.add((end_line, '*'))
            excluded.add((end_line, '>'))
            excluded.add((end_line, '>>'))

        for child in node.children:
            _walk(child)

    _walk(root)
    return excluded


def _check_linebreak_operators(path: str, lines: list[str],
                               root=None) -> list[Violation]:
    """Check that line breaks come before binary operators, not after."""
    v = []
    # Binary operators that should not start a continuation line
    bin_ops = {'&&', '||', '+', '-', '*', '/', '%', '&', '|', '^', '<<', '>>',
               '==', '!=', '<', '>', '<=', '>='}

    # Use tree-sitter to find lines where ambiguous operators are NOT binary
    excluded = _collect_non_binary_op_lines(root) if root else set()

    for i, line in enumerate(lines, 1):
        s = line.strip()
        if not s or s.startswith(('#', '//', '/*', '*')):
            continue
        # Check if line ends with a binary operator (bad: break after operator)
        for op in sorted(bin_ops, key=len, reverse=True):
            if s.endswith(op) and not s.endswith(f'//{op}'):
                # Verify it's not a unary or part of something else
                before = s[:-len(op)].rstrip()
                if before and not before.endswith(('(', ',', '=')):
                    # Skip if tree-sitter says this is not a binary operator
                    if (i - 1, op) in excluded:
                        break
                    v.append(Violation(path, i, "exp.linebreak",
                                       f"Line break should come before '{op}', not after",
                                       line_content=line))
                    break

    return v


def _check_no_void_params(path: str, lines: list[str], content_bytes: bytes,
                          nodes: NodeCache) -> list[Violation]:
    """In C++, empty parameter lists should use () not (void)."""
    v = []
    seen = set()

    def _check_unique(func_decl):
        key = (func_decl.start_point, func_decl.end_point)
        if key not in seen:
            seen.add(key)
            _check_void_in_func_decl(path, lines, content_bytes, func_decl, v)

    for func in nodes.get('function_definition'):
        for fd in find_nodes(func, 'function_declarator'):
            _check_unique(fd)

    # Check declarations too (prototypes)
    for decl in nodes.get('declaration', 'field_declaration'):
        for fd in find_nodes(decl, 'function_declarator'):
            _check_unique(fd)

    return v


def _check_void_in_func_decl(path: str, lines: list[str], content_bytes: bytes,
                             func_decl, v: list[Violation]):
    """Check a single function_declarator for (void) params."""
    for child in func_decl.children:
        if child.type == 'parameter_list':
            params = [p for p in child.children if p.type == 'parameter_declaration']
            if len(params) == 1:
                param_text = text(params[0], content_bytes).strip()
                if param_text == 'void':
                    line_num = func_decl.start_point[0] + 1
                    name = find_id(func_decl, content_bytes)
                    line_content = line_at(lines, func_decl.start_point[0])
                    v.append(Violation(path, line_num, "fun.proto.void.cxx",
                                       f"'{name or '?'}' should use () not (void) in C++",
                                       line_content=line_content))


def _check_op_assign(path: str, lines: list[str], content_bytes: bytes,
                     nodes: NodeCache) -> list[Violation]:
    """Check that assignment operators return Class& and *this."""
    v = []
    for func in nodes.get('function_definition'):
        func_text = text(func, content_bytes)
        if 'operator=' not in func_text:
            continue

        # Check return type includes & (reference)
        has_ref_return = False
        for child in func.children:
            if child.type == 'reference_declarator':
                has_ref_return = True
                break

        if not has_ref_return:
            line_num = func.start_point[0] + 1
            line_content = line_at(lines, func.start_point[0])
            v.append(Violation(path, line_num, "op.assign",
                               "Assignment operator should return Class&",
                               line_content=line_content))
            continue

        # Check body contains "return *this"
        body = None
        for child in func.children:
            if child.type == 'compound_statement':
                body = child
                break
        if body:
            body_text = text(body, content_bytes)
            if 'return *this' not in body_text and 'return *this;' not in body_text:
                line_num = func.start_point[0] + 1
                line_content = line_at(lines, func.start_point[0])
                v.append(Violation(path, line_num, "op.assign",
                                   "Assignment operator should return *this",
                                   line_content=line_content))

    return v


def _check_forbidden_overloads(path: str, lines: list[str], content_bytes: bytes,
                               nodes: NodeCache, forbidden: set[str], rule: str,
                               severity: Severity = Severity.MAJOR) -> list[Violation]:
    """Check for forbidden operator overloads."""
    v = []
    for node in nodes.get('function_definition', 'function_declarator',
                          'field_declaration', 'declaration'):
        node_text = text(node, content_bytes)
        for op in forbidden:
            if op in node_text:
                # Find the actual function_declarator
                for fd in find_nodes(node, 'function_declarator'):
                    fd_text = text(fd, content_bytes)
                    # Check the operator name precisely
                    if op + '(' in fd_text or op + ' (' in fd_text:
                        line_num = fd.start_point[0] + 1
                        line_content = line_at(lines, fd.start_point[0])
                        v.append(Violation(path, line_num, rule,
                                           f"Don't overload {op}",
                                           severity,
                                           line_content=line_content))
    return v
