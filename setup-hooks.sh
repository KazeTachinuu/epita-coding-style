#!/bin/bash
set -e

cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: local
    hooks:
      - id: epita-coding-style
        name: epita-coding-style
        entry: epita-coding-style
        language: system
        types: [c++]
EOF

pre-commit install
echo "Pre-commit hook installed."
