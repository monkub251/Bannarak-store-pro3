-- Defensive monitoring. Everything here raises alerts for human review; nothing bans or kicks automatically.
FMCC = FMCC or {}
FMCC.Security = {}
local S, Core = FMCC.Security, FMCC.Core
local alerts, expected = {}, {}

local function snapshot(src)
    if not src or not GetPlayerName(src) then return nil end
    local masked = {}
    for _, id in ipairs(GetPlayerIdentifiers(src)) do masked[#masked + 1] = Core.maskIdentifier(id) end
    local ped = GetPlayerPed(src)
    local coords
    if ped ~= 0 then
        local c = GetEntityCoords(ped)
        coords = { x = c.x, y = c.y, z = c.z }
    end
    return { coords = coords, ping = GetPlayerPing(src), identifiers = masked }
end

function S.alert(kind, src, detail, evidence)
    alerts[#alerts + 1] = {
        t = os.time(), kind = kind, player = src, name = src and GetPlayerName(src) or nil,
        detail = detail, evidence = evidence or snapshot(src),
    }
    while #alerts > Config.MaxAlerts do table.remove(alerts, 1) end
    FMCC.Audit.add('system', 'alert.' .. kind, { player = src }, false, detail)
    FMCC.Log.add('alert', kind .. ' player=' .. tostring(src) .. ' ' .. detail)
end

function S.alerts(limit)
    local out = {}
    for i = #alerts, math.max(1, #alerts - limit + 1), -1 do out[#out + 1] = alerts[i] end
    return out
end

function S.clear() alerts = {} end

-- Call before a legitimate teleport so the movement monitor does not flag it.
function S.expect(src, ms) expected[src] = GetGameTimer() + ms end

---------------------------------------------------------------- guarded net events (rate limited)
function S.guard(name, limit, windowMs, fn)
    local lim = Core.newLimiter(limit, windowMs)
    RegisterNetEvent(name, function(...)
        local src = source
        if type(src) ~= 'number' or src <= 0 then return end
        local ok, count = lim.hit(src, GetGameTimer())
        if not ok then
            if Config.Security.EventGuardAlerts and count == limit + 1 then
                S.alert('event_spam', src, ('event %s exceeded %d calls per %d ms'):format(name, limit, windowMs))
            end
            return
        end
        fn(src, ...)
    end)
end

---------------------------------------------------------------- entity spawn monitor
local spawnCfg = Config.Security.EntitySpawn
if spawnCfg.enabled then
    local limiter = Core.newLimiter(spawnCfg.limit, spawnCfg.windowMs)
    local flaggedAt = {}
    local populations = {}
    for _, p in ipairs(spawnCfg.populationTypes) do populations[p] = true end
    AddEventHandler('entityCreated', function(entity)
        if not DoesEntityExist(entity) then return end
        local owner = NetworkGetEntityOwner(entity)
        if not owner or owner <= 0 then return end
        if not populations[GetEntityPopulationType(entity)] then return end
        local ok = limiter.hit(owner, GetGameTimer())
        if not ok and (not flaggedAt[owner] or GetGameTimer() - flaggedAt[owner] > 60000) then
            flaggedAt[owner] = GetGameTimer()
            S.alert('entity_spawn', owner, ('more than %d script entities in %d ms'):format(spawnCfg.limit, spawnCfg.windowMs))
        end
    end)
end

---------------------------------------------------------------- movement monitor
local mv = Config.Security.Movement
local last, strikes = {}, {}
if mv.enabled then
    CreateThread(function()
        while true do
            Wait(mv.intervalMs)
            local now = GetGameTimer()
            for _, sid in ipairs(GetPlayers()) do
                local src = tonumber(sid)
                local ped = GetPlayerPed(sid)
                if ped ~= 0 then
                    local c = GetEntityCoords(ped)
                    local prev = last[src]
                    last[src] = { x = c.x, y = c.y, z = c.z, t = now }
                    local skip = (expected[src] and now < expected[src])
                        or GetVehiclePedIsIn(ped, false) ~= 0 or GetEntityHealth(ped) <= 0
                    if prev and not skip then
                        local v = Core.speed(prev.x, prev.y, prev.z, c.x, c.y, c.z, now - prev.t)
                        if v > mv.maxOnFootSpeed then
                            strikes[src] = (strikes[src] or 0) + 1
                            if strikes[src] >= mv.strikes then
                                strikes[src] = 0
                                S.alert('movement', src, ('on-foot speed %.1f m/s exceeds %.1f'):format(v, mv.maxOnFootSpeed))
                            end
                        else
                            strikes[src] = 0
                        end
                    end
                end
            end
        end
    end)
end

AddEventHandler('playerDropped', function()
    local src = source
    last[src], strikes[src], expected[src] = nil, nil, nil
end)

---------------------------------------------------------------- resource integrity (literal manifest files only)
local function manifestFiles(resource)
    local files, seen = {}, {}
    local function add(path)
        if path and not seen[path] and not path:find('[%*%?]') then
            seen[path] = true
            files[#files + 1] = path
        end
    end
    add('fxmanifest.lua')
    for _, key in ipairs({ 'client_script', 'server_script', 'shared_script', 'file' }) do
        for i = 0, (GetNumResourceMetadata(resource, key) or 0) - 1 do
            add(GetResourceMetadata(resource, key, i))
        end
    end
    return files
end

local function hashResource(resource)
    if GetResourceState(resource) == 'missing' then return nil, 'resource not found: ' .. resource end
    local hashes, unreadable = {}, {}
    for _, path in ipairs(manifestFiles(resource)) do
        local data = LoadResourceFile(resource, path)
        if data then hashes[path] = Core.sha256(data) else unreadable[#unreadable + 1] = path end
    end
    return hashes, unreadable
end

local function loadStore()
    local ok, t = pcall(json.decode, GetResourceKvpString('fmcc:baseline') or '{}')
    return ok and type(t) == 'table' and t or {}
end

function S.baseline(resource)
    local hashes, unreadable = hashResource(resource)
    if not hashes then return nil, unreadable end
    local store = loadStore()
    store[resource] = { t = os.time(), files = hashes }
    SetResourceKvp('fmcc:baseline', json.encode(store))
    local n = 0
    for _ in pairs(hashes) do n = n + 1 end
    return { resource = resource, filesHashed = n, unreadable = unreadable }
end

function S.check(resource)
    local base = loadStore()[resource]
    if not base then return nil, 'no baseline saved for ' .. resource .. '; run sec.integrity_baseline first' end
    local now, unreadable = hashResource(resource)
    if not now then return nil, unreadable end
    local modified, added, removed = {}, {}, {}
    for path, h in pairs(now) do
        if not base.files[path] then added[#added + 1] = path
        elseif base.files[path] ~= h then modified[#modified + 1] = path end
    end
    for path in pairs(base.files) do
        if not now[path] then removed[#removed + 1] = path end
    end
    table.sort(modified); table.sort(added); table.sort(removed)
    local clean = #modified + #added + #removed == 0
    if not clean then
        S.alert('integrity', nil, ('%s: %d modified, %d added, %d removed since baseline'):format(resource, #modified, #added, #removed), {})
    end
    return { resource = resource, baselineTime = base.t, clean = clean, modified = modified, added = added, removed = removed, unreadable = unreadable }
end

function S.identifiers(src)
    local out, kinds, valid = {}, {}, true
    for _, id in ipairs(GetPlayerIdentifiers(src)) do
        local ok = Core.identifierValid(id)
        out[#out + 1] = { id = Core.maskIdentifier(id), valid = ok }
        kinds[id:match('^(%w+):') or '?'] = true
        valid = valid and ok
    end
    local license = GetPlayerIdentifierByType(src, 'license')
    local duplicates = {}
    if license then
        for _, sid in ipairs(GetPlayers()) do
            local other = tonumber(sid)
            if other ~= src and GetPlayerIdentifierByType(other, 'license') == license then duplicates[#duplicates + 1] = other end
        end
    end
    return { identifiers = out, hasLicense = license ~= nil, allValid = valid, duplicateLicenseWith = duplicates }
end
