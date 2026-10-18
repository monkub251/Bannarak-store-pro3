"""Keeps the Python registry, the Lua handlers and the manifest in step, and runs the Lua unit tests."""
import hashlib
import os
import random
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from app.core.registry import ACTIONS

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "fivem_resource" / "fmcc_control"
LUA = shutil.which("lua5.4") or shutil.which("lua")
LUAC = shutil.which("luac5.4") or shutil.which("luac")


def lua_ids():
    return set(re.findall(r"^A\('([a-z_]+\.[a-z_]+)'", (RES / "server" / "actions.lua").read_text(), re.M))


def test_every_registry_action_has_a_lua_handler_and_vice_versa():
    py = {a.id for a in ACTIONS}
    lua = lua_ids()
    assert py - lua == set(), f"missing in Lua: {py - lua}"
    assert lua - py == set(), f"missing in registry: {lua - py}"


def test_every_dispatched_client_event_has_a_client_handler():
    sent = set(re.findall(r"\bcl\(\w+,\s*'([A-Za-z_]+)'", (RES / "server" / "actions.lua").read_text()))
    handled = set(re.findall(r"RegisterNetEvent\('fmcc:cl:([A-Za-z_]+)'", (RES / "client" / "main.lua").read_text()))
    assert sent and sent <= handled, f"no client handler for: {sent - handled}"


def test_config_with_tokens_is_server_only():
    manifest = (RES / "fxmanifest.lua").read_text()
    server_block = re.search(r"server_scripts\s*\{(.*?)\}", manifest, re.S).group(1)
    assert "'config.lua'" in server_block
    assert "client_scripts" in manifest
    client_block = re.search(r"client_scripts\s*\{(.*?)\}", manifest, re.S).group(1)
    assert "config.lua" not in client_block and "shared_script" not in manifest


def test_manifest_lists_only_existing_files():
    manifest = (RES / "fxmanifest.lua").read_text()
    for name in re.findall(r"'((?:server|client)/[a-z_]+\.lua|config\.lua)'", manifest):
        assert (RES / name).exists(), name


def test_default_token_is_a_placeholder_the_server_refuses():
    cfg = (RES / "config.lua").read_text()
    assert "CHANGE_ME" in cfg and "Modules" in cfg
    assert re.search(r"fun\s*=\s*false", cfg)


def test_registry_has_no_cheat_style_actions():
    banned = ("aimbot", "silent", "esp", "noclip", "godmode", "bypass", "spoof", "inject", "hwid")
    for a in ACTIONS:
        assert not any(b in a.id for b in banned), a.id


@pytest.mark.skipif(not LUAC, reason="luac not installed")
def test_all_lua_files_pass_syntax_check():
    files = [str(p) for p in RES.rglob("*.lua")]
    assert files
    r = subprocess.run([LUAC, "-p", *files], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


@pytest.mark.skipif(not LUA, reason="lua not installed")
def test_lua_unit_tests_pass():
    r = subprocess.run([LUA, "tests/lua/test_core.lua"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "0 failed" in r.stdout


@pytest.mark.skipif(not LUA, reason="lua not installed")
def test_lua_sha256_matches_hashlib_on_random_data():
    rng = random.Random(7)
    samples = [b"", b"a", b"abc" * 21, bytes(range(256)), b"\x00" * 64, b"x" * 55, b"x" * 56, b"x" * 63, b"x" * 64, b"x" * 65]
    samples += [bytes(rng.randrange(256) for _ in range(rng.randrange(0, 300))) for _ in range(40)]
    r = subprocess.run([LUA, "tests/lua/sha_cli.lua"], cwd=ROOT, input="\n".join(s.hex() for s in samples) + "\n",
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert r.stdout.split() == [hashlib.sha256(s).hexdigest() for s in samples]
