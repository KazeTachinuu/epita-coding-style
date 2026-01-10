#!/usr/bin/env python3
"""
EPITA C Coding Style Checker
Checks C code against EPITA coding style rules.
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ============================================================================
# ANSI Colors for terminal output
# ============================================================================

class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    @classmethod
    def disable(cls):
        cls.RED = cls.GREEN = cls.YELLOW = cls.BLUE = ""
        cls.MAGENTA = cls.CYAN = cls.WHITE = cls.BOLD = cls.DIM = cls.RESET = ""


# ============================================================================
# Data structures
# ============================================================================

class Severity(Enum):
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    INFO = "INFO"


@dataclass
class Violation:
    file: str
    line: int
    column: int
    rule: str
    message: str
    severity: Severity = Severity.MAJOR

    def format(self, use_colors: bool = True) -> str:
        C = Colors if use_colors else type('NoColor', (), {k: '' for k in dir(Colors)})()

        sev_color = {
            Severity.MAJOR: Colors.RED,
            Severity.MINOR: Colors.YELLOW,
            Severity.INFO: Colors.CYAN
        }.get(self.severity, Colors.WHITE)

        return (
            f"{Colors.WHITE}{self.file}{Colors.RESET}:"
            f"{Colors.CYAN}{self.line}{Colors.RESET}:"
            f"{Colors.CYAN}{self.column}{Colors.RESET}: "
            f"{sev_color}{Colors.BOLD}[{self.severity.value}]{Colors.RESET} "
            f"{Colors.MAGENTA}{self.rule}{Colors.RESET}: {self.message}"
        )


@dataclass
class CheckResult:
    file: str
    violations: list[Violation] = field(default_factory=list)
    major_count: int = 0
    minor_count: int = 0


# ============================================================================
# Main checker class
# ============================================================================

class CodingStyleChecker:
    """Checks C source files against EPITA coding style rules."""

    def __init__(self, max_func_lines: int = 40, max_func_args: int = 4,
                 max_exported_funcs: int = 10):
        self.max_func_lines = max_func_lines
        self.max_func_args = max_func_args
        self.max_exported_funcs = max_exported_funcs

    def check_file(self, filepath: str) -> CheckResult:
        """Check a single file for coding style violations."""
        result = CheckResult(file=filepath)

        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace', newline='') as f:
                content = f.read()
        except Exception as e:
            result.violations.append(Violation(
                filepath, 0, 0, "file.read", f"Cannot read file: {e}"
            ))
            result.major_count = 1
            return result

        lines = content.split('\n')

        # Run all checks
        checks = [
            self._check_file_rules,
            self._check_line_rules,
            self._check_braces_rules,
            self._check_function_rules,
            self._check_export_rules,
            self._check_naming_rules,
            self._check_preprocessor_rules,
            self._check_declaration_rules,
            self._check_control_rules,
        ]

        for check in checks:
            check(filepath, content, lines, result)

        # Count by severity
        result.major_count = sum(1 for v in result.violations if v.severity == Severity.MAJOR)
        result.minor_count = sum(1 for v in result.violations if v.severity == Severity.MINOR)

        return result

    # ========================================================================
    # File-level checks
    # ========================================================================

    def _check_file_rules(self, filepath: str, content: str, lines: list[str], result: CheckResult):
        """Check file-level rules (DOS endings, trailing whitespace, etc.)."""

        # file.dos: No CRLF line endings
        if '\r\n' in content:
            result.violations.append(Violation(
                filepath, 1, 1, "file.dos",
                "DOS CR+LF line terminator not allowed (use Unix LF only)"
            ))

        # file.terminate: Last character must be newline
        if content and not content.endswith('\n'):
            result.violations.append(Violation(
                filepath, len(lines), len(lines[-1]) if lines else 1,
                "file.terminate", "File must end with a newline"
            ))

        # file.spurious: No blank lines at start of file
        if lines and lines[0].strip() == '':
            result.violations.append(Violation(
                filepath, 1, 1, "file.spurious",
                "No blank lines allowed at the beginning of file"
            ))

        # file.spurious: No blank lines at end of file
        if len(lines) >= 2:
            idx = len(lines) - 1
            if lines[-1] == '':
                idx -= 1
            if idx >= 0 and lines[idx].strip() == '':
                result.violations.append(Violation(
                    filepath, idx + 1, 1, "file.spurious",
                    "No blank lines allowed at the end of file"
                ))

        # lines.empty: No two consecutive empty lines
        prev_empty = False
        for i, line in enumerate(lines):
            is_empty = line.strip() == ''
            if is_empty and prev_empty:
                result.violations.append(Violation(
                    filepath, i + 1, 1, "lines.empty",
                    "Two consecutive empty lines not allowed"
                ))
            prev_empty = is_empty

    def _check_line_rules(self, filepath: str, content: str, lines: list[str], result: CheckResult):
        """Check line-level rules (trailing whitespace)."""
        for i, line in enumerate(lines):
            # file.trailing: No trailing whitespace
            stripped = line.rstrip()
            if line != stripped:
                result.violations.append(Violation(
                    filepath, i + 1, len(stripped) + 1,
                    "file.trailing", "Trailing whitespace not allowed",
                    Severity.MINOR
                ))

    # ========================================================================
    # Braces and indentation checks
    # ========================================================================

    def _check_braces_rules(self, filepath: str, content: str, lines: list[str], result: CheckResult):
        """Check braces rules (Allman style, 4-space indentation, no tabs)."""

        # Track context to avoid false positives
        in_string = False
        in_comment = False
        in_multiline_comment = False

        for i, line in enumerate(lines):
            # Check for tabs (braces.indent: no tabs allowed)
            if '\t' in line:
                col = line.index('\t') + 1
                result.violations.append(Violation(
                    filepath, i + 1, col, "braces.indent",
                    "Tabs not allowed, use 4 spaces for indentation"
                ))

            stripped = line.strip()

            # Skip empty lines
            if not stripped:
                continue

            # Skip preprocessor directives
            if stripped.startswith('#'):
                continue

            # Track multiline comments
            if '/*' in stripped and '*/' not in stripped:
                in_multiline_comment = True
                continue
            if in_multiline_comment:
                if '*/' in stripped:
                    in_multiline_comment = False
                continue

            # Skip single-line comments
            if stripped.startswith('//'):
                continue

            # braces: Opening brace must be on its own line (Allman style)
            # Exception: array/struct initializers like "int arr[] = { 1, 2 };"
            # Exception: do-while: "} while"
            if '{' in stripped:
                # Check if brace is NOT alone or at start of line
                brace_pos = stripped.find('{')
                before_brace = stripped[:brace_pos].strip()

                # Skip initializers (has '=' before brace)
                if '=' in before_brace:
                    continue

                # Skip empty braces on same line like "{ }"
                if stripped == '{}' or stripped == '{ }':
                    continue

                # If there's code before the brace (not just whitespace), it's K&R style
                if before_brace and before_brace not in ['do']:
                    # Check it's not a string containing brace
                    if '"' not in before_brace and "'" not in before_brace:
                        result.violations.append(Violation(
                            filepath, i + 1, brace_pos + 1, "braces",
                            "Opening brace must be on its own line (Allman style)"
                        ))

            # braces: Closing brace must be on its own line
            # Exception: do-while: "} while (...)"
            # Exception: else: "} else"  - but in Allman these should be separate
            if '}' in stripped:
                brace_pos = stripped.find('}')
                after_brace = stripped[brace_pos + 1:].strip()

                # "} while" is allowed for do-while
                if after_brace.startswith('while'):
                    continue

                # Check if there's non-comment content after the brace
                if after_brace and not after_brace.startswith('//') and not after_brace.startswith('/*'):
                    # Skip struct/enum definitions ending with "};"
                    if after_brace == ';':
                        continue
                    # Skip array initializer endings like "},"
                    if after_brace in [',', ');', ');,']:
                        continue

                    result.violations.append(Violation(
                        filepath, i + 1, brace_pos + 1, "braces",
                        "Closing brace must be on its own line (Allman style)"
                    ))

        # braces.indent: Check 4-space indentation
        self._check_indentation(filepath, lines, result)

    def _check_indentation(self, filepath: str, lines: list[str], result: CheckResult):
        """Check that indentation uses 4 spaces per level."""
        expected_indent = 0
        in_multiline_comment = False

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Skip empty lines
            if not stripped:
                continue

            # Track multiline comments
            if '/*' in line and '*/' not in line:
                in_multiline_comment = True
            if in_multiline_comment:
                if '*/' in line:
                    in_multiline_comment = False
                continue

            # Skip preprocessor (always at column 0)
            if stripped.startswith('#'):
                continue

            # Calculate leading spaces
            leading_spaces = len(line) - len(line.lstrip(' \t'))

            # Adjust expected indent based on braces
            # Decrease indent for closing braces before checking
            if stripped.startswith('}') or stripped.startswith('case ') or stripped.startswith('default:'):
                pass  # These can be at various indent levels
            else:
                # Check if indentation is a multiple of 4
                if leading_spaces % 4 != 0 and leading_spaces > 0:
                    # Allow continuation lines (might not be multiple of 4)
                    # Heuristic: if previous line ends with operator or comma, it's continuation
                    if i > 0:
                        prev_stripped = lines[i - 1].strip()
                        # Skip check for continuation lines
                        if (prev_stripped.endswith(',') or
                            prev_stripped.endswith('(') or
                            prev_stripped.endswith('&&') or
                            prev_stripped.endswith('||') or
                            prev_stripped.endswith('+')):
                            continue

                    result.violations.append(Violation(
                        filepath, i + 1, 1, "braces.indent",
                        f"Indentation must be a multiple of 4 spaces (found {leading_spaces})",
                        Severity.MINOR
                    ))

    # ========================================================================
    # Function-level checks
    # ========================================================================

    def _check_function_rules(self, filepath: str, content: str, lines: list[str], result: CheckResult):
        """Check function rules (length, argument count, prototypes)."""

        # Regex for function definition (can end with ) or { for single-line)
        func_def_pattern = re.compile(
            r'^(?:static\s+)?(?:inline\s+)?'
            r'(?:const\s+)?(?:unsigned\s+|signed\s+)?'
            r'(?:void|int|char|short|long|float|double|size_t|ssize_t|'
            r'struct\s+\w+|union\s+\w+|enum\s+\w+|\w+_t|\w+)'
            r'(?:\s*\*+|\s+)'
            r'(\w+)\s*'
            r'\(([^)]*)\)\s*(?:\{.*)?$'
        )

        # Regex for function declaration (ends with semicolon)
        func_decl_pattern = re.compile(
            r'^(?:extern\s+)?(?:static\s+)?(?:inline\s+)?'
            r'(?:const\s+)?(?:unsigned\s+|signed\s+)?'
            r'(?:void|int|char|short|long|float|double|size_t|ssize_t|'
            r'struct\s+\w+|union\s+\w+|enum\s+\w+|\w+_t|\w+)'
            r'(?:\s*\*+|\s+)'
            r'(\w+)\s*'
            r'\(([^)]*)\)\s*;'
        )

        func_pattern = func_def_pattern

        in_function = False
        func_name = ""
        func_start = 0
        brace_depth = 0
        func_lines = 0
        pending_function = False  # True when we matched a function signature

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Check function declarations in header files
            if filepath.endswith('.h'):
                decl_match = func_decl_pattern.match(stripped)
                if decl_match:
                    func_name = decl_match.group(1)
                    params = decl_match.group(2).strip()

                    # fun.proto.void: Empty params should be 'void'
                    if params == '':
                        result.violations.append(Violation(
                            filepath, i + 1, 1, "fun.proto.void",
                            f"Function '{func_name}' should use 'void' for empty parameters"
                        ))

                    # fun.arg.count: Max 4 arguments
                    if params and params != 'void':
                        arg_count = self._count_args(params)
                        if arg_count > self.max_func_args:
                            result.violations.append(Violation(
                                filepath, i + 1, 1, "fun.arg.count",
                                f"Function '{func_name}' has {arg_count} arguments "
                                f"(maximum is {self.max_func_args})"
                            ))

            # Try to match function definition
            if not in_function and brace_depth == 0:
                match = func_pattern.match(stripped)
                if match:
                    func_name = match.group(1)
                    params = match.group(2).strip()
                    pending_function = True  # Mark that next '{' is a function

                    # fun.proto.void: Empty params should be 'void' (for .c files too)
                    if params == '':
                        result.violations.append(Violation(
                            filepath, i + 1, 1, "fun.proto.void",
                            f"Function '{func_name}' should use 'void' for empty parameters"
                        ))

                    # fun.arg.count: Max 4 arguments
                    if params and params != 'void':
                        arg_count = self._count_args(params)
                        if arg_count > self.max_func_args:
                            result.violations.append(Violation(
                                filepath, i + 1, 1, "fun.arg.count",
                                f"Function '{func_name}' has {arg_count} arguments "
                                f"(maximum is {self.max_func_args})"
                            ))

            # Track brace depth for function body
            open_braces = stripped.count('{')
            close_braces = stripped.count('}')

            if open_braces > 0:
                if brace_depth == 0 and pending_function:
                    # This is the start of a function body
                    in_function = True
                    func_start = i + 1
                    func_lines = 0
                    pending_function = False
                elif brace_depth == 0:
                    # This is some other block (enum, struct, etc.) - skip it
                    pending_function = False
                brace_depth += open_braces

            if close_braces > 0:
                brace_depth -= close_braces
                if brace_depth == 0 and in_function:
                    # fun.length: Check function length
                    if func_lines > self.max_func_lines:
                        result.violations.append(Violation(
                            filepath, func_start, 1, "fun.length",
                            f"Function body has {func_lines} lines "
                            f"(maximum is {self.max_func_lines})"
                        ))
                    in_function = False
                    func_name = ""

            # Count lines inside function (skip braces, blanks, comments)
            if in_function and brace_depth > 0:
                if stripped and stripped not in ['{', '}']:
                    if not self._is_comment_line(stripped):
                        func_lines += 1

    def _count_args(self, params: str) -> int:
        """Count function arguments handling nested parentheses."""
        if not params or params == 'void':
            return 0
        depth = 0
        count = 1
        for c in params:
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
            elif c == ',' and depth == 0:
                count += 1
        return count

    def _is_comment_line(self, line: str) -> bool:
        """Check if line is a comment."""
        return (line.startswith('//') or line.startswith('/*') or
                line.startswith('**') or line.startswith('*') or line == '*/')

    # ========================================================================
    # Export rules
    # ========================================================================

    def _check_export_rules(self, filepath: str, content: str, lines: list[str], result: CheckResult):
        """Check export rules (max exported functions per file)."""

        # export.fun only applies to .c files (not headers)
        if not filepath.endswith('.c'):
            return

        # Pattern for function definition (not declaration)
        # Matches: "type name(...) {" or "type name(...) { ... }" (single-line)
        # Exported = not static
        func_def_pattern = re.compile(
            r'^(static\s+)?(?:inline\s+)?'
            r'(?:const\s+)?(?:unsigned\s+|signed\s+)?'
            r'(?:void|int|char|short|long|float|double|size_t|ssize_t|'
            r'struct\s+\w+|union\s+\w+|enum\s+\w+|\w+_t|\w+)'
            r'(?:\s*\*+|\s+)'
            r'(\w+)\s*'
            r'\([^)]*\)\s*\{'
        )

        exported_functions = []
        brace_depth = 0

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Skip if we're inside a function body
            if brace_depth > 0:
                brace_depth += stripped.count('{') - stripped.count('}')
                continue

            # Skip preprocessor lines
            if stripped.startswith('#'):
                continue

            # Skip typedef, struct, union, enum definitions
            if stripped.startswith(('typedef', 'struct ', 'union ', 'enum ')):
                if '{' in stripped:
                    brace_depth += stripped.count('{') - stripped.count('}')
                continue

            # Check for function definition
            match = func_def_pattern.match(stripped)
            if match:
                is_static = match.group(1) is not None
                func_name = match.group(2)

                # Only count non-static functions as exported
                if not is_static:
                    exported_functions.append((func_name, i + 1))

                # Track brace depth
                brace_depth += stripped.count('{') - stripped.count('}')
            else:
                # Track brace depth for other constructs
                brace_depth += stripped.count('{') - stripped.count('}')

        # export.fun: Max 10 exported functions per source file
        if len(exported_functions) > self.max_exported_funcs:
            func_names = [f[0] for f in exported_functions]
            result.violations.append(Violation(
                filepath, 1, 1, "export.fun",
                f"File has {len(exported_functions)} exported functions "
                f"(maximum is {self.max_exported_funcs}): {', '.join(func_names)}"
            ))

        # export.other: Max 1 non-function exported symbol per source file
        self._check_exported_symbols(filepath, lines, result)

    def _check_exported_symbols(self, filepath: str, lines: list[str], result: CheckResult):
        """Check for max 1 non-function exported symbol (global variable)."""

        # Pattern for global variable declaration (not function)
        # Exported = not static
        global_var_pattern = re.compile(
            r'^(?!static\b)'  # NOT starting with static
            r'(?:const\s+)?'
            r'(?:volatile\s+)?'
            r'(?:unsigned\s+|signed\s+)?'
            r'(?:int|char|short|long|float|double|size_t|ssize_t|'
            r'struct\s+\w+|union\s+\w+|enum\s+\w+|\w+_t)\s*'
            r'\*?\s*(\w+)\s*[;=\[]'
        )

        exported_symbols = []
        brace_depth = 0

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Track brace depth
            brace_depth += stripped.count('{') - stripped.count('}')

            # Only check at file scope (brace_depth == 0)
            if brace_depth != 0:
                continue

            # Skip preprocessor, typedef, struct/union/enum definitions
            if (stripped.startswith('#') or
                stripped.startswith('typedef') or
                stripped.startswith('struct ') or
                stripped.startswith('union ') or
                stripped.startswith('enum ')):
                continue

            # Skip function declarations/definitions (have parentheses)
            if '(' in stripped:
                continue

            # Skip extern declarations (they don't define the symbol)
            if stripped.startswith('extern'):
                continue

            match = global_var_pattern.match(stripped)
            if match:
                var_name = match.group(1)
                exported_symbols.append((var_name, i + 1))

        # export.other: Max 1 non-function exported symbol
        if len(exported_symbols) > 1:
            var_names = [f[0] for f in exported_symbols]
            result.violations.append(Violation(
                filepath, exported_symbols[1][1], 1, "export.other",
                f"File has {len(exported_symbols)} exported non-function symbols "
                f"(maximum is 1): {', '.join(var_names)}"
            ))

    # ========================================================================
    # Naming convention checks
    # ========================================================================

    def _check_naming_rules(self, filepath: str, content: str, lines: list[str], result: CheckResult):
        """Check naming conventions (macros, global variables)."""

        macro_pattern = re.compile(r'^\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)')

        for i, line in enumerate(lines):
            # name.case.macro: Macros must be UPPER_CASE
            match = macro_pattern.match(line)
            if match:
                name = match.group(1)
                # Skip include guards
                if name.endswith('_H') or name.endswith('_H_'):
                    continue
                if not name.isupper() and '_' in name:
                    result.violations.append(Violation(
                        filepath, i + 1, match.start(1) + 1,
                        "name.case.macro",
                        f"Macro '{name}' should be UPPER_CASE",
                        Severity.MINOR
                    ))

        # name.prefix.global: Global variables must start with g_
        self._check_global_variables(filepath, lines, result)

    def _check_global_variables(self, filepath: str, lines: list[str], result: CheckResult):
        """Check global variable naming (must start with g_)."""
        brace_depth = 0

        global_pattern = re.compile(
            r'^(?:extern\s+)?'
            r'(?:static\s+)?'
            r'(?:const\s+)?'
            r'(?:unsigned\s+|signed\s+)?'
            r'(?:int|char|short|long|float|double|size_t|\w+_t|struct\s+\w+)\s*'
            r'\*?\s*(\w+)\s*[;=]'
        )

        for i, line in enumerate(lines):
            brace_depth += line.count('{') - line.count('}')

            if brace_depth == 0:
                stripped = line.strip()
                if stripped.startswith('#') or stripped.startswith('typedef'):
                    continue

                match = global_pattern.match(stripped)
                if match and '(' not in stripped:
                    var_name = match.group(1)
                    if 'extern' in stripped and not var_name.startswith('g_'):
                        result.violations.append(Violation(
                            filepath, i + 1, 1, "name.prefix.global",
                            f"Global variable '{var_name}' should start with 'g_'",
                            Severity.MINOR
                        ))

    # ========================================================================
    # Preprocessor checks
    # ========================================================================

    def _check_preprocessor_rules(self, filepath: str, content: str, lines: list[str], result: CheckResult):
        """Check preprocessor rules (guards, includes, directives)."""

        filename = os.path.basename(filepath)

        # cpp.guard: Header files need include guards
        if filepath.endswith('.h'):
            guard = filename.upper().replace('.', '_').replace('-', '_').replace('+', '_')
            has_guard = any(f'#ifndef' in l and guard in l for l in lines)
            if not has_guard:
                result.violations.append(Violation(
                    filepath, 1, 1, "cpp.guard",
                    f"Header file should have include guard (e.g., #ifndef {guard})"
                ))

        for i, line in enumerate(lines):
            stripped = line.strip()

            # cpp.mark: # must be on first column
            if stripped.startswith('#') and line[0] != '#':
                result.violations.append(Violation(
                    filepath, i + 1, 1, "cpp.mark",
                    "Preprocessor '#' must be on the first column"
                ))

            # cpp.if: #endif should have comment
            if stripped.startswith('#endif') and '/*' not in stripped and '//' not in stripped:
                result.violations.append(Violation(
                    filepath, i + 1, 1, "cpp.if",
                    "#endif should have a comment describing the condition",
                    Severity.MINOR
                ))

            # cpp.digraphs: No digraphs/trigraphs
            digraphs = ['??=', '??/', "??'", '??(', '??)', '??!', '??<', '??>', '??-',
                        '<%', '%>', '<:', ':>']
            for d in digraphs:
                if d in line:
                    result.violations.append(Violation(
                        filepath, i + 1, line.find(d) + 1, "cpp.digraphs",
                        f"Digraph/trigraph '{d}' not allowed"
                    ))

    # ========================================================================
    # Declaration checks
    # ========================================================================

    def _check_declaration_rules(self, filepath: str, content: str, lines: list[str], result: CheckResult):
        """Check declaration rules (single per line, no VLA)."""

        # decl.single: One declaration per line
        # Match: "int a, b" but not "int a, int b" (function params)
        multi_decl = re.compile(
            r'^\s*(?:const\s+)?(?:unsigned\s+|signed\s+)?'
            r'(?:int|char|short|long|float|double)\s+'
            r'\*?\s*\w+\s*,\s*\*?\s*\w+'
        )

        # Types that indicate function parameters, not variable declarations
        type_keywords = {'int', 'char', 'short', 'long', 'float', 'double',
                         'void', 'unsigned', 'signed', 'const', 'struct', 'union', 'enum'}

        brace_depth = 0
        for i, line in enumerate(lines):
            brace_depth += line.count('{') - line.count('}')
            stripped = line.strip()

            # Skip for loops (multiple declarations allowed)
            if 'for' in stripped:
                continue

            # Skip function parameter lines (end with ) or contain closing paren)
            if stripped.endswith(')') or stripped.endswith(') {') or stripped.endswith('){'):
                continue

            # Skip lines that are clearly function parameter continuations
            # (have type keyword after the comma, like "int *a, int *b")
            if ',' in stripped:
                after_comma = stripped.split(',', 1)[1].strip()
                first_word = after_comma.split()[0].lstrip('*') if after_comma.split() else ''
                if first_word in type_keywords:
                    continue

            if multi_decl.match(stripped):
                result.violations.append(Violation(
                    filepath, i + 1, 1, "decl.single",
                    "Only one declaration per line is allowed"
                ))

            # decl.vla: No variable-length arrays
            # Check if inside function or single-line function
            in_block = brace_depth > 0 or ('{' in stripped and '}' in stripped)
            if in_block:
                vla_match = re.search(
                    r'\b(?:int|char|short|long|float|double|\w+_t)\s+(\w+)\s*\[\s*([a-zA-Z_]\w*)\s*\]',
                    stripped
                )
                if vla_match and '=' not in stripped:
                    size_expr = vla_match.group(2)
                    # Only flag if size is lowercase (variables), not UPPER_CASE (macros)
                    # Macro constants should be UPPER_CASE per name.case.macro rule
                    if not size_expr.isupper():
                        result.violations.append(Violation(
                            filepath, i + 1, 1, "decl.vla",
                            f"Variable-length array (VLA) not allowed"
                        ))

    # ========================================================================
    # Control structure checks
    # ========================================================================

    def _check_control_rules(self, filepath: str, content: str, lines: list[str], result: CheckResult):
        """Check control structure rules."""

        for i, line in enumerate(lines):
            stripped = line.strip()

            # stat.asm: No asm
            if re.search(r'\b(?:asm|__asm__|__asm)\b', stripped):
                result.violations.append(Violation(
                    filepath, i + 1, 1, "stat.asm",
                    "asm declarations not allowed"
                ))

            # ctrl.empty: Empty loop must use continue
            if stripped == ';' and i > 0:
                prev = lines[i - 1].strip()
                if prev.startswith('for') or prev.startswith('while'):
                    result.violations.append(Violation(
                        filepath, i + 1, 1, "ctrl.empty",
                        "Empty loop body should use 'continue' statement"
                    ))


# ============================================================================
# Utility functions
# ============================================================================

def find_c_files(path: str) -> list[str]:
    """Recursively find all C source and header files."""
    files = []
    if os.path.isfile(path):
        if path.endswith(('.c', '.h')):
            files.append(path)
    elif os.path.isdir(path):
        for root, _, filenames in os.walk(path):
            for f in filenames:
                if f.endswith(('.c', '.h')):
                    files.append(os.path.join(root, f))
    return sorted(files)


def print_header(text: str):
    """Print a section header."""
    width = 60
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'=' * width}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{text.center(width)}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'=' * width}{Colors.RESET}\n")


def print_summary(results: list[CheckResult]):
    """Print summary of all checks."""
    total_files = len(results)
    total_major = sum(r.major_count for r in results)
    total_minor = sum(r.minor_count for r in results)
    total_violations = total_major + total_minor
    files_with_errors = sum(1 for r in results if r.violations)

    print_header("SUMMARY")

    print(f"  {Colors.CYAN}Files checked:{Colors.RESET}     {total_files}")
    print(f"  {Colors.CYAN}Files with issues:{Colors.RESET} {files_with_errors}")
    print(f"  {Colors.CYAN}Total violations:{Colors.RESET}  {total_violations}")
    print(f"    {Colors.RED}Major:{Colors.RESET} {total_major}")
    print(f"    {Colors.YELLOW}Minor:{Colors.RESET} {total_minor}")
    print()

    if total_major > 0:
        print(f"  {Colors.RED}{Colors.BOLD}Status: FAILED{Colors.RESET}")
        return 1
    elif total_minor > 0:
        print(f"  {Colors.YELLOW}{Colors.BOLD}Status: PASSED (with warnings){Colors.RESET}")
        return 0
    else:
        print(f"  {Colors.GREEN}{Colors.BOLD}Status: PASSED{Colors.RESET}")
        return 0


# ============================================================================
# Main entry point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='EPITA C Coding Style Checker',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Rules checked:
  - fun.length      Function body max lines (default: 40)
  - fun.arg.count   Function max arguments (default: 4)
  - fun.proto.void  Empty params should be 'void'
  - export.fun      Max exported functions per file (default: 10)
  - export.other    Max 1 non-function exported symbol per file
  - braces          Braces must be on their own line (Allman style)
  - braces.indent   4-space indentation, no tabs
  - file.trailing   No trailing whitespace
  - file.dos        No CRLF line endings
  - file.terminate  File must end with newline
  - file.spurious   No blank lines at start/end
  - lines.empty     No consecutive empty lines
  - cpp.guard       Header files need include guards
  - cpp.mark        Preprocessor # on first column
  - decl.single     One declaration per line
  - decl.vla        No variable-length arrays
  - name.case.macro Macros must be UPPER_CASE
  - And more...

Examples:
  %(prog)s src/
  %(prog)s main.c utils.h
  %(prog)s --max-lines 30 src/
'''
    )

    parser.add_argument('paths', nargs='*', metavar='PATH', default=['.'],
                        help='Files or directories to check (default: current directory)')
    parser.add_argument('--max-lines', type=int, default=40,
                        help='Max lines per function body (default: 40)')
    parser.add_argument('--max-args', type=int, default=4,
                        help='Max arguments per function (default: 4)')
    parser.add_argument('--max-exported', type=int, default=10,
                        help='Max exported functions per file (default: 10)')
    parser.add_argument('--no-color', action='store_true',
                        help='Disable colored output')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='Only show summary')

    args = parser.parse_args()

    if args.no_color:
        Colors.disable()

    # Collect files
    files = []
    for path in args.paths:
        found = find_c_files(path)
        if not found:
            print(f"{Colors.YELLOW}Warning:{Colors.RESET} No C files found in '{path}'",
                  file=sys.stderr)
        files.extend(found)

    if not files:
        print(f"{Colors.RED}Error:{Colors.RESET} No C files to check", file=sys.stderr)
        return 1

    # Run checks
    checker = CodingStyleChecker(
        max_func_lines=args.max_lines,
        max_func_args=args.max_args,
        max_exported_funcs=args.max_exported
    )

    print_header("EPITA C CODING STYLE CHECKER")
    print(f"  {Colors.DIM}Max function lines:    {args.max_lines}{Colors.RESET}")
    print(f"  {Colors.DIM}Max function args:     {args.max_args}{Colors.RESET}")
    print(f"  {Colors.DIM}Max exported funcs:    {args.max_exported}{Colors.RESET}")
    print(f"  {Colors.DIM}Checking {len(files)} file(s)...{Colors.RESET}")

    results = []
    for filepath in files:
        result = checker.check_file(filepath)
        results.append(result)

        if not args.quiet and result.violations:
            print(f"\n{Colors.WHITE}{Colors.BOLD}{filepath}{Colors.RESET}")
            for v in result.violations:
                print(f"  {v.format()}")

    return print_summary(results)


if __name__ == '__main__':
    sys.exit(main())
