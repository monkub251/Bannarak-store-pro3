-- Run from the repository root: lua5.4 tests/lua/test_core.lua
local Core = dofile("fivem_resource/fmcc_control/server/core.lua")
local passed, failed = 0, 0
local function eq(name, got, want)
    if got == want then passed = passed + 1 else
        failed = failed + 1
        print(("FAIL %s: got %s, want %s"):format(name, tostring(got), tostring(want)))
    end
end

eq("sha256 empty", Core.sha256(""), "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
eq("sha256 abc", Core.sha256("abc"), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
eq("sha256 two blocks", Core.sha256("abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq"),
    "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1")
eq("sha256 million a", Core.sha256(string.rep("a", 1000000)),
    "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0")

eq("safeEqual same", Core.safeEqual("secret-token", "secret-token"), true)
eq("safeEqual differs", Core.safeEqual("secret-token", "secret-tokeN"), false)
eq("safeEqual length", Core.safeEqual("abc", "abcd"), false)
eq("safeEqual nil", Core.safeEqual(nil, "abc"), false)
eq("token placeholder", Core.tokenIsStrong("CHANGE_ME_generate_a_long_random_token"), false)
eq("token short", Core.tokenIsStrong("short"), false)
eq("token strong", Core.tokenIsStrong("k3j2h4g5f6d7s8a9q0w1e2r3t4y5"), true)
eq("bearer ok", Core.bearer("Bearer abc123"), "abc123")
eq("bearer bad", Core.bearer("Basic abc123"), nil)

eq("permits star", Core.permits({ "*" }, "player.heal"), true)
eq("permits category", Core.permits({ "player.*" }, "player.heal"), true)
eq("permits other category", Core.permits({ "player.*" }, "players.list"), false)
eq("permits prefix wildcard", Core.permits({ "player.teleport_*" }, "player.teleport_coords"), true)
eq("permits deny wins last", Core.permits({ "*", "!players.kick" }, "players.kick"), false)
eq("permits deny keeps rest", Core.permits({ "*", "!players.kick" }, "players.list"), true)
eq("permits empty", Core.permits({}, "player.heal"), false)

local lim = Core.newLimiter(3, 1000)
eq("limiter 1", (lim.hit("a", 0)), true)
eq("limiter 2", (lim.hit("a", 10)), true)
eq("limiter 3", (lim.hit("a", 20)), true)
eq("limiter 4 blocked", (lim.hit("a", 30)), false)
eq("limiter other key", (lim.hit("b", 30)), true)
eq("limiter window reset", (lim.hit("a", 1100)), true)
eq("limiter peek", lim.peek("a", 1200), 1)
eq("limiter peek expired", lim.peek("a", 5000), 0)

local a = Core.args({ target = "7", name = "WEAPON_PISTOL", ammo = 50, ok = "true", mode = "dot", x = "1.5" })
eq("args int", a.int("target", 1, 65535), 7)
eq("args str", a.str("name", 40, "^[%w_]+$"), "WEAPON_PISTOL")
eq("args bool", a.bool("ok"), true)
eq("args choice", a.choice("mode", { "dot", "cross" }), "dot")
eq("args num", a.num("x", -10, 10), 1.5)
eq("args default", a.int("missing", 0, 10, 4), 4)
eq("args no error", a.err(), nil)
local b = Core.args({ target = 99999, name = "bad name!" })
b.int("target", 1, 65535)
b.str("name", 40, "^[%w_]+$")
b.int("absent", 1, 5)
eq("args error count", select(2, b.err():gsub(";", ";")), 2)
eq("args check raises", pcall(b.check), false)

eq("mask id", Core.maskIdentifier("license:0123456789abcdef0123456789abcdef01234567"), "license:0123...67")
eq("mask ip", Core.maskIdentifier("ip:10.0.0.1"), "ip:hidden")
eq("id license valid", Core.identifierValid("license:0123456789abcdef0123456789abcdef01234567"), true)
eq("id license short", Core.identifierValid("license:abc"), false)
eq("id discord valid", Core.identifierValid("discord:123456789012345678"), true)
eq("id discord bad", Core.identifierValid("discord:12ab"), false)
eq("speed", math.floor(Core.speed(0, 0, 0, 30, 40, 0, 1000)), 50)

print(("lua core tests: %d passed, %d failed"):format(passed, failed))
os.exit(failed == 0 and 0 or 1)
