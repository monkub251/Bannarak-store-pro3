-- Reads hex-encoded strings (one per line) from stdin and prints their SHA-256. Used by the Python tests.
local Core = dofile("fivem_resource/fmcc_control/server/core.lua")
for line in io.lines() do
    local raw = (line:gsub("%x%x", function(h) return string.char(tonumber(h, 16)) end))
    print(Core.sha256(raw))
end
