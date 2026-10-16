#!/bin/sh
# Compile the read-only macOS probe once into a stable local path, then run it.
set -eu
if [ "$(uname -s)" != "Darwin" ]; then
  echo "This approval probe requires macOS." >&2
  exit 2
fi
SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
TARGET_DIR="$HOME/.local/bin"
TARGET="$TARGET_DIR/codex-approval-probe"
SOURCE="$SCRIPT_DIR/approval_probe.swift"
if ! command -v xcrun >/dev/null 2>&1 || ! xcrun --find swiftc >/dev/null 2>&1; then
  echo "Install Apple's Xcode Command Line Tools first: xcode-select --install" >&2
  exit 2
fi
mkdir -p "$TARGET_DIR"
if [ ! -x "$TARGET" ] || [ "$SOURCE" -nt "$TARGET" ]; then
  xcrun swiftc -O "$SOURCE" -o "$TARGET"
fi
exec "$TARGET" "$@"