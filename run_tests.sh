#!/bin/sh
# Runs the Lua unit tests and the Python suite (which also syntax-checks all Lua and compares SHA-256 with hashlib).
set -e
cd "$(dirname "$0")"
lua5.4 tests/lua/test_core.lua
QT_QPA_PLATFORM=offscreen python3 -m pytest
