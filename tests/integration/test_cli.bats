#!/usr/bin/env bats
# Integration tests for epita-coding-style CLI

setup() {
    TMP_DIR=$(mktemp -d)

    # Clean file
    cat > "$TMP_DIR/clean.c" << 'EOF'
#include <stdio.h>

int main(void)
{
    printf("Hello\n");
    return 0;
}
EOF

    # Bad goto
    cat > "$TMP_DIR/bad_goto.c" << 'EOF'
void f(void)
{
label:
    goto label;
}
EOF

    # Bad cast
    cat > "$TMP_DIR/bad_cast.c" << 'EOF'
void f(void)
{
    void *p = 0;
    int x = (int)p;
}
EOF

    # Too many lines (31 lines in body, exceeds 30 limit)
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
}
EOF

    # Too many args
    cat > "$TMP_DIR/bad_args.c" << 'EOF'
void f(int a, int b, int c, int d, int e)
{
    return;
}
EOF

    # Config file
    cat > "$TMP_DIR/config.toml" << 'EOF'
max_lines = 50

[rules]
"keyword.goto" = false
"cast" = false
EOF

    # Bad format (K&R style instead of Allman)
    cat > "$TMP_DIR/bad_format.c" << 'EOF'
int main(void){
    return 0;
}
EOF

    # Too many exported functions (11 functions, exceeds 10 limit)
    cat > "$TMP_DIR/bad_funcs.c" << 'EOF'
void f1(void)
{
}
void f2(void)
{
}
void f3(void)
{
}
void f4(void)
{
}
void f5(void)
{
}
void f6(void)
{
}
void f7(void)
{
}
void f8(void)
{
}
void f9(void)
{
}
void f10(void)
{
}
void f11(void)
{
}
EOF
}

teardown() {
    rm -rf "$TMP_DIR"
}

# === Basic CLI ===

@test "clean file passes" {
    run uv run epita-coding-style "$TMP_DIR/clean.c"
    [ "$status" -eq 0 ]
}

@test "no files found fails" {
    run uv run epita-coding-style "$TMP_DIR/nonexistent/"
    [ "$status" -eq 1 ]
}

@test "--list-rules works" {
    run uv run epita-coding-style --list-rules
    [ "$status" -eq 0 ]
    [[ "$output" == *"keyword.goto"* ]]
    [[ "$output" == *"cast"* ]]
}

@test "--help works" {
    run uv run epita-coding-style --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"EPITA"* ]]
}

# === Rule Detection (default strict) ===

@test "goto detected by default" {
    run uv run epita-coding-style "$TMP_DIR/bad_goto.c"
    [ "$status" -eq 1 ]
    [[ "$output" == *"keyword.goto"* ]]
}

@test "cast detected by default" {
    run uv run epita-coding-style "$TMP_DIR/bad_cast.c"
    [ "$status" -eq 1 ]
    [[ "$output" == *"cast"* ]]
}

@test "fun.length detected (>30 lines)" {
    run uv run epita-coding-style "$TMP_DIR/bad_lines.c"
    [ "$status" -eq 1 ]
    [[ "$output" == *"fun.length"* ]]
}

@test "fun.arg.count detected (>4 args)" {
    run uv run epita-coding-style "$TMP_DIR/bad_args.c"
    [ "$status" -eq 1 ]
    [[ "$output" == *"fun.arg.count"* ]]
}

# === Preset ===

@test "--preset 42sh allows goto" {
    run uv run epita-coding-style --preset 42sh "$TMP_DIR/bad_goto.c"
    [ "$status" -eq 0 ]
}

@test "--preset 42sh allows cast" {
    run uv run epita-coding-style --preset 42sh "$TMP_DIR/bad_cast.c"
    [ "$status" -eq 0 ]
}

@test "--preset 42sh has 40 line limit" {
    run uv run epita-coding-style --preset 42sh "$TMP_DIR/bad_lines.c"
    [ "$status" -eq 0 ]
}

# === Config File ===

@test "--config file works" {
    run uv run epita-coding-style --config "$TMP_DIR/config.toml" "$TMP_DIR/bad_goto.c"
    [ "$status" -eq 0 ]
}

@test "config disables cast check" {
    run uv run epita-coding-style --config "$TMP_DIR/config.toml" "$TMP_DIR/bad_cast.c"
    [ "$status" -eq 0 ]
}

# === CLI Overrides ===

@test "--max-lines override" {
    run uv run epita-coding-style --max-lines 50 "$TMP_DIR/bad_lines.c"
    [ "$status" -eq 0 ]
}

@test "--max-args override" {
    run uv run epita-coding-style --max-args 10 "$TMP_DIR/bad_args.c"
    [ "$status" -eq 0 ]
}

@test "export.fun detected (>10 functions)" {
    run uv run epita-coding-style "$TMP_DIR/bad_funcs.c"
    [ "$status" -eq 1 ]
    [[ "$output" == *"export.fun"* ]]
}

@test "--max-funcs override" {
    run uv run epita-coding-style --max-funcs 15 "$TMP_DIR/bad_funcs.c"
    [ "$status" -eq 0 ]
}

# === Output Options ===

@test "-q quiet mode" {
    run uv run epita-coding-style -q "$TMP_DIR/bad_goto.c"
    [ "$status" -eq 1 ]
    # Should only show summary, not individual violations
    [[ "$output" == *"Files:"* ]]
}

@test "--no-color disables colors" {
    run uv run epita-coding-style --no-color "$TMP_DIR/bad_goto.c"
    [ "$status" -eq 1 ]
    # Should not contain ANSI escape codes
    [[ "$output" != *$'\033'* ]]
}

# === Format Check ===

@test "format rule detects bad formatting" {
    if ! command -v clang-format &> /dev/null; then
        skip "clang-format not installed"
    fi
    run uv run epita-coding-style "$TMP_DIR/bad_format.c"
    [[ "$output" == *"format"* ]]
}

@test "clean file passes format check" {
    if ! command -v clang-format &> /dev/null; then
        skip "clang-format not installed"
    fi
    run uv run epita-coding-style "$TMP_DIR/clean.c"
    [ "$status" -eq 0 ]
}
