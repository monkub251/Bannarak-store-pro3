-- Pure logic with no FiveM natives, so it can be unit-tested with a plain Lua 5.4 interpreter.
local Core = {}

---------------------------------------------------------------- SHA-256 (change detection)
local K = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
}
local M32 = 0xffffffff
local function rrot(x, n) return ((x >> n) | (x << (32 - n))) & M32 end
local FMT16 = ">" .. string.rep("I4", 16)

function Core.sha256(msg)
    local h0, h1, h2, h3 = 0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a
    local h4, h5, h6, h7 = 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
    local len = #msg
    msg = msg .. "\128" .. string.rep("\0", (55 - len) % 64) .. string.pack(">I8", len * 8)
    for chunk = 1, #msg, 64 do
        local w = { string.unpack(FMT16, msg, chunk) }
        for i = 17, 64 do
            local a, b = w[i - 15], w[i - 2]
            local s0 = rrot(a, 7) ~ rrot(a, 18) ~ (a >> 3)
            local s1 = rrot(b, 17) ~ rrot(b, 19) ~ (b >> 10)
            w[i] = (w[i - 16] + s0 + w[i - 7] + s1) & M32
        end
        local a, b, c, d, e, f, g, h = h0, h1, h2, h3, h4, h5, h6, h7
        for i = 1, 64 do
            local S1 = rrot(e, 6) ~ rrot(e, 11) ~ rrot(e, 25)
            local ch = (e & f) ~ ((~e) & g)
            local t1 = (h + S1 + ch + K[i] + w[i]) & M32
            local S0 = rrot(a, 2) ~ rrot(a, 13) ~ rrot(a, 22)
            local maj = (a & b) ~ (a & c) ~ (b & c)
            local t2 = (S0 + maj) & M32
            h, g, f, e, d, c, b, a = g, f, e, (d + t1) & M32, c, b, a, (t1 + t2) & M32
        end
        h0, h1, h2, h3 = (h0 + a) & M32, (h1 + b) & M32, (h2 + c) & M32, (h3 + d) & M32
        h4, h5, h6, h7 = (h4 + e) & M32, (h5 + f) & M32, (h6 + g) & M32, (h7 + h) & M32
    end
    return string.format("%08x%08x%08x%08x%08x%08x%08x%08x", h0, h1, h2, h3, h4, h5, h6, h7)
end

---------------------------------------------------------------- authentication helpers
function Core.safeEqual(a, b)
    if type(a) ~= "string" or type(b) ~= "string" then return false end
    local diff = #a ~ #b
    for i = 1, math.max(#a, #b) do
        diff = diff | ((a:byte(i) or 0) ~ (b:byte(i) or 0))
    end
    return diff == 0
end

function Core.tokenIsStrong(t)
    return type(t) == "string" and #t >= 24 and t:sub(1, 9) ~= "CHANGE_ME"
end

function Core.bearer(header)
    if type(header) ~= "string" then return nil end
    return header:match("^[Bb]earer%s+(%S+)$")
end

---------------------------------------------------------------- permissions
local function matches(pattern, action)
    if pattern == "*" or pattern == action then return true end
    local star = pattern:find("*", 1, true)
    if star and star == #pattern then
        return action:sub(1, star - 1) == pattern:sub(1, star - 1)
    end
    return false
end

function Core.permits(patterns, action)
    local allowed = false
    for _, p in ipairs(patterns or {}) do
        local neg = p:sub(1, 1) == "!"
        if neg then p = p:sub(2) end
        if matches(p, action) then allowed = not neg end
    end
    return allowed
end

---------------------------------------------------------------- rate limiting
function Core.newLimiter(limit, windowMs)
    local buckets = {}
    local self = {}
    function self.hit(key, nowMs)
        local b = buckets[key]
        if not b or nowMs - b.start >= windowMs then
            b = { start = nowMs, count = 0 }
            buckets[key] = b
        end
        b.count = b.count + 1
        return b.count <= limit, b.count
    end
    function self.peek(key, nowMs)
        local b = buckets[key]
        if not b or nowMs - b.start >= windowMs then return 0 end
        return b.count
    end
    function self.reset(key) buckets[key] = nil end
    return self
end

---------------------------------------------------------------- argument validation
function Core.args(params)
    local self = { p = type(params) == "table" and params or {}, errs = {} }
    local function miss(name, default)
        local v = self.p[name]
        if v == nil or v == "" then
            if default == nil then self.errs[#self.errs + 1] = name .. " is required" end
            return true, default
        end
        return false, v
    end
    function self.fail(msg) self.errs[#self.errs + 1] = msg end
    function self.int(name, min, max, default)
        local m, v = miss(name, default)
        if m then return v end
        v = tonumber(v)
        if not v or v ~= math.floor(v) or v < min or v > max then
            self.errs[#self.errs + 1] = name .. " must be a whole number from " .. min .. " to " .. max
            return nil
        end
        return math.tointeger(v)
    end
    function self.num(name, min, max, default)
        local m, v = miss(name, default)
        if m then return v end
        v = tonumber(v)
        if not v or v ~= v or v < min or v > max then
            self.errs[#self.errs + 1] = name .. " must be a number from " .. min .. " to " .. max
            return nil
        end
        return v + 0.0
    end
    function self.str(name, maxLen, pattern, default)
        local m, v = miss(name, default)
        if m then return v end
        if type(v) ~= "string" or #v > maxLen or (pattern and not v:match(pattern)) then
            self.errs[#self.errs + 1] = name .. " is invalid (max " .. maxLen .. " characters" ..
                (pattern and ", letters, digits and _ only" or "") .. ")"
            return nil
        end
        return v
    end
    function self.bool(name, default)
        local v = self.p[name]
        if v == nil then
            if default == nil then self.errs[#self.errs + 1] = name .. " is required" end
            return default
        end
        if v == true or v == "true" or v == 1 then return true end
        if v == false or v == "false" or v == 0 then return false end
        self.errs[#self.errs + 1] = name .. " must be true or false"
    end
    function self.choice(name, list, default)
        local m, v = miss(name, default)
        if m then return v end
        for _, c in ipairs(list) do if c == v then return v end end
        self.errs[#self.errs + 1] = name .. " must be one of: " .. table.concat(list, ", ")
    end
    function self.err() return #self.errs > 0 and table.concat(self.errs, "; ") or nil end
    function self.check()
        local e = self.err()
        if e then error({ fmcc = e }, 0) end
    end
    return self
end

---------------------------------------------------------------- small utilities
function Core.maskIdentifier(id)
    local kind, value = tostring(id):match("^(%w+):(.+)$")
    if not kind then return "invalid" end
    if kind == "ip" then return "ip:hidden" end
    return kind .. ":" .. value:sub(1, 4) .. "..." .. value:sub(-2)
end

function Core.identifierValid(id)
    local kind, value = tostring(id):match("^(%w+):(.+)$")
    if not kind then return false end
    if kind == "license" or kind == "license2" then return #value == 40 and value:match("^%x+$") ~= nil end
    if kind == "steam" then return #value >= 8 and #value <= 17 and value:match("^%x+$") ~= nil end
    if kind == "discord" then return #value >= 15 and #value <= 20 and value:match("^%d+$") ~= nil end
    if kind == "fivem" or kind == "xbl" or kind == "live" then return value:match("^%d+$") ~= nil end
    return true
end

function Core.speed(x1, y1, z1, x2, y2, z2, dtMs)
    if dtMs <= 0 then return 0.0 end
    local dx, dy, dz = x2 - x1, y2 - y1, z2 - z1
    return math.sqrt(dx * dx + dy * dy + dz * dz) / (dtMs / 1000.0)
end

FMCC = FMCC or {}
FMCC.Core = Core
return Core
