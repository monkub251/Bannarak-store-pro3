FMCC = FMCC or {}
FMCC.Audit = {}
FMCC.Log = {}

local RES = GetCurrentResourceName()
local entries, logs, dirty = {}, {}, false

local raw = LoadResourceFile(RES, 'data/audit.json')
if raw then
    local ok, t = pcall(json.decode, raw)
    if ok and type(t) == 'table' then entries = t end
end

local function redact(params)
    local out = {}
    if type(params) ~= 'table' then return out end
    for k, v in pairs(params) do
        local key = tostring(k):lower()
        if key ~= 'token' and key ~= 'password' then
            out[k] = type(v) == 'string' and v:sub(1, 100) or v
        end
    end
    return out
end

function FMCC.Audit.add(who, action, params, ok, message)
    entries[#entries + 1] = { t = os.time(), who = who, action = action, params = redact(params), ok = ok, msg = message }
    while #entries > Config.MaxAudit do table.remove(entries, 1) end
    dirty = true
end

function FMCC.Audit.list(limit)
    local out = {}
    for i = #entries, math.max(1, #entries - limit + 1), -1 do out[#out + 1] = entries[i] end
    return out
end

function FMCC.Log.add(level, message)
    logs[#logs + 1] = { t = os.time(), level = level, message = tostring(message):sub(1, 1500) }
    while #logs > 100 do table.remove(logs, 1) end
    print(('[fmcc:%s] %s'):format(level, tostring(message):sub(1, 300)))
end

function FMCC.Log.list(limit)
    local out = {}
    for i = #logs, math.max(1, #logs - limit + 1), -1 do out[#out + 1] = logs[i] end
    return out
end

CreateThread(function()
    while true do
        Wait(5000)
        if dirty then
            dirty = false
            SaveResourceFile(RES, 'data/audit.json', json.encode(entries), -1)
        end
    end
end)
