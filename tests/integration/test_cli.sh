#!/bin/bash
# Integration tests for uv run epita-coding-style CLI
# Can run standalone or with bats

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TMP_DIR=$(mktemp -d)
trap "rm -rf $TMP_DIR" EXIT

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

PASS=0
FAIL=0

check() {
    local name="$1"
    local expected="$2"
    shift 2

    if eval "$@" > /dev/null 2>&1; then
        result=0
    else
        result=1
    fi

    if [ "$result" -eq "$expected" ]; then
        echo -e "${GREEN}PASS${NC}: $name"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}FAIL${NC}: $name (expected exit $expected, got $result)"
        FAIL=$((FAIL + 1))
    fi
}

# Create test files
cat > "$TMP_DIR/clean.c" << 'EOF'
#include <stdio.h>

int main(void)
{
    printf("Hello\n");
    return 0;
}
EOF

cat > "$TMP_DIR/bad_goto.c" << 'EOF'
void f(void)
{
label:
    goto label;
}
EOF

cat > "$TMP_DIR/bad_cast.c" << 'EOF'
void f(void)
{
    void *p = 0;
    int x = (int)p;
}
EOF

cat > "$TMP_DIR/bad_lines.c" << 'EOF'
void f(void)
{
    int x = 1;
    x++;
    x++;
    x++;
    x++;
    x++;
    x++;
    x++;
    x++;
    x++;
    x++;
    x++;
    x++;
    x++;
    x++;
    x++;
    x++;
    x++;
    x++;
    x++;
    x++;
    x++;
    x++;
    x++;
    x++;
    x++;
    x++;
    x++;
    x++;
    x++;
    x++;
    x++;
}
EOF

cat > "$TMP_DIR/bad_args.c" << 'EOF'
void f(int a, int b, int c, int d, int e)
{
    return;
}
EOF

cat > "$TMP_DIR/config.toml" << 'EOF'
max_lines = 50

[rules]
"keyword.goto" = false
"cast" = false
EOF

echo "=== CLI Integration Tests ==="
echo ""

# Basic functionality
check "clean file passes" 0 "uv run epita-coding-style $TMP_DIR/clean.c"
check "no files found fails" 1 "uv run epita-coding-style $TMP_DIR/nonexistent/"
check "list-rules works" 0 "uv run epita-coding-style --list-rules"
check "help works" 0 "uv run epita-coding-style --help"

# Rule detection (default = strict EPITA)
check "goto detected (default)" 1 "uv run epita-coding-style $TMP_DIR/bad_goto.c"
check "cast detected (default)" 1 "uv run epita-coding-style $TMP_DIR/bad_cast.c"
check "too many lines detected" 1 "uv run epita-coding-style $TMP_DIR/bad_lines.c"
check "too many args detected" 1 "uv run epita-coding-style $TMP_DIR/bad_args.c"

# Preset
check "42sh preset allows goto" 0 "uv run epita-coding-style --preset 42sh $TMP_DIR/bad_goto.c"
check "42sh preset allows cast" 0 "uv run epita-coding-style --preset 42sh $TMP_DIR/bad_cast.c"

# Config file
check "config file disables goto" 0 "uv run epita-coding-style --config $TMP_DIR/config.toml $TMP_DIR/bad_goto.c"
check "config file disables cast" 0 "uv run epita-coding-style --config $TMP_DIR/config.toml $TMP_DIR/bad_cast.c"

# CLI overrides
check "max-lines override" 0 "uv run epita-coding-style --max-lines 50 $TMP_DIR/bad_lines.c"
check "max-args override" 0 "uv run epita-coding-style --max-args 10 $TMP_DIR/bad_args.c"

# Output options
check "quiet mode works" 0 "uv run epita-coding-style -q $TMP_DIR/clean.c"
check "no-color works" 0 "uv run epita-coding-style --no-color $TMP_DIR/clean.c"

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

[ "$FAIL" -eq 0 ]
