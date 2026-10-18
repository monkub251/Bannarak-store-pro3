-- One handler per API action. A handler returns a table on success, or nil plus a message on failure.
-- Arguments are validated through Core.args; a.check() raises a bad-request error for the dispatcher.
FMCC = FMCC or {}
FMCC.Actions = {}
FMCC.World = { override = false, hour = 12, minute = 0, freeze = false, weather = 'CLEAR' }
FMCC.CombatStats = {}

local Core, S = FMCC.Core, FMCC.Security
local function A(id, fn) FMCC.Actions[id] = fn end
local function cl(target, name, ...) TriggerClientEvent('fmcc:cl:' .. name, target, ...) end
local SENT = { dispatched = true, note = "sent to the player's client; delivery is not confirmed" }

local function online(a, key)
    local t = a.int(key or 'target', 1, 65535)
    if t and not GetPlayerName(t) then a.fail('player ' .. t .. ' is not online'); return nil end
    return t
end

local function xyz(c) return { x = c.x, y = c.y, z = c.z } end

local function catalogHas(list, field, value)
    for _, e in ipairs(list) do if e[field] == value then return true end end
    return false
end

local function weaponLabel(hash)
    for _, w in ipairs(Config.WeaponCatalog) do
        if (GetHashKey(w.name) & 0xffffffff) == (hash & 0xffffffff) then return w.label, w.name end
    end
end

---------------------------------------------------------------- 1. player / movement
A('player.info', function(a)
    local t = online(a); a.check()
    local ped = GetPlayerPed(t)
    if ped == 0 then return nil, 'player has no ped yet (still loading)' end
    return {
        id = t, name = GetPlayerName(t), ping = GetPlayerPing(t), health = GetEntityHealth(ped),
        armor = GetPedArmour(ped), heading = GetEntityHeading(ped), coords = xyz(GetEntityCoords(ped)),
        inVehicle = GetVehiclePedIsIn(ped, false) ~= 0, routingBucket = GetPlayerRoutingBucket(t),
    }
end)

A('player.heal', function(a) local t = online(a); a.check(); cl(t, 'heal'); return SENT end)

A('player.armor', function(a)
    local t = online(a); local amount = a.int('amount', 0, 100, 100); a.check()
    cl(t, 'armor', amount); return SENT
end)

A('player.teleport_coords', function(a)
    local t = online(a)
    local x, y, z = a.num('x', -10000, 10000), a.num('y', -10000, 10000), a.num('z', -500, 2500)
    a.check(); S.expect(t, 8000); cl(t, 'teleport', x, y, z); return SENT
end)

A('player.teleport_player', function(a)
    local t, d = online(a), online(a, 'dest'); a.check()
    local ped = GetPlayerPed(d)
    if ped == 0 then return nil, 'destination player has no ped yet' end
    local c = GetEntityCoords(ped)
    S.expect(t, 8000); cl(t, 'teleport', c.x, c.y, c.z); return SENT
end)

A('player.teleport_waypoint', function(a)
    local t = online(a); a.check(); S.expect(t, 12000); cl(t, 'teleportWaypoint'); return SENT
end)

A('player.freeze', function(a)
    local t = online(a); local state = a.bool('state'); a.check(); cl(t, 'freeze', state); return SENT
end)

A('player.set_model', function(a)
    local t = online(a); local model = a.str('model', 40, '^[%w_]+$'); a.check(); cl(t, 'model', model); return SENT
end)

---------------------------------------------------------------- 2. combat / training
A('combat.crosshair', function(a)
    local t = online(a)
    local style = a.choice('style', { 'dot', 'cross', 'circle', 'off' })
    local size = a.int('size', 2, 40, 8)
    local color = a.str('color', 6, '^%x%x%x%x%x%x$', 'ffffff')
    a.check(); cl(t, 'crosshair', style, size, color); return SENT
end)

A('combat.hitmarker', function(a)
    local t = online(a); local enabled = a.bool('enabled'); a.check(); cl(t, 'hitmarker', enabled); return SENT
end)

A('combat.stats', function(a)
    local t = online(a); a.check()
    local s = FMCC.CombatStats[t] or { shots = 0, hits = 0, kills = 0 }
    local acc = s.shots > 0 and math.floor(s.hits / s.shots * 1000) / 10 or 0
    return { shots = s.shots, hits = s.hits, kills = s.kills, accuracyPercent = acc,
        note = 'self-reported by the training client; for practice statistics only, not evidence for moderation' }
end)

A('combat.spawn_dummy', function(a) local t = online(a); a.check(); cl(t, 'dummy'); return SENT end)

A('combat.overlay', function(a)
    local t = online(a); local enabled = a.bool('enabled'); a.check()
    if enabled and not Config.AdminOverlay then return nil, 'Config.AdminOverlay is false' end
    if enabled and not IsPlayerAceAllowed(t, 'fmcc.overlay') then
        return nil, 'that player lacks the ACE permission fmcc.overlay (add_ace group.admin fmcc.overlay allow)'
    end
    cl(t, 'overlay', enabled); return SENT
end)

---------------------------------------------------------------- 3. weapons
A('weapon.info', function(a)
    local t = online(a); a.check()
    local ped = GetPlayerPed(t)
    if ped == 0 then return nil, 'player has no ped yet' end
    local hash = GetSelectedPedWeapon(ped)
    local label, name = weaponLabel(hash)
    return { weaponHash = hash & 0xffffffff, label = label or 'unknown (not in Config.WeaponCatalog)', name = name }
end)

local function weaponArg(a)
    local w = a.str('weapon', 40, '^WEAPON_[%w_]+$')
    if w and Config.RestrictWeapons and not catalogHas(Config.WeaponCatalog, 'name', w) then
        a.fail('weapon is not in Config.WeaponCatalog')
    end
    return w
end

A('weapon.give', function(a)
    local t = online(a); local w = weaponArg(a); local ammo = a.int('ammo', 0, 9999, 100); a.check()
    cl(t, 'giveWeapon', w, ammo); return SENT
end)

A('weapon.component', function(a)
    local t = online(a); local w = weaponArg(a); local c = a.str('component', 60, '^COMPONENT_[%w_]+$'); a.check()
    cl(t, 'weaponComponent', w, c); return SENT
end)

A('weapon.set_ammo', function(a)
    local t = online(a); local w = weaponArg(a); local ammo = a.int('ammo', 0, 9999); a.check()
    cl(t, 'setAmmo', w, ammo); return SENT
end)

A('weapon.remove_all', function(a) local t = online(a); a.check(); cl(t, 'removeWeapons'); return SENT end)

---------------------------------------------------------------- 4. fun / testing (module off by default)
A('fun.emote', function(a)
    local t = online(a)
    local dict, name = a.str('dict', 60, '^[%w_@%-%.]+$'), a.str('name', 60, '^[%w_@%-%.]+$')
    a.check(); cl(t, 'emote', dict, name); return SENT
end)

A('fun.scenario', function(a)
    local t = online(a); local s = a.str('scenario', 60, '^[%w_]+$'); a.check(); cl(t, 'scenario', s); return SENT
end)

A('fun.ragdoll', function(a)
    local t = online(a); local ms = a.int('duration_ms', 500, 10000, 2000); a.check(); cl(t, 'ragdoll', ms); return SENT
end)

A('fun.clone', function(a) local t = online(a); a.check(); cl(t, 'clone'); return SENT end)

---------------------------------------------------------------- 5. vehicles
A('vehicle.catalog', function() return { vehicles = Config.VehicleCatalog } end)

A('vehicle.spawn', function(a)
    local t = online(a); local model = a.str('model', 32, '^[%w_]+$')
    if model and Config.RestrictVehicles and not catalogHas(Config.VehicleCatalog, 'model', model) then
        a.fail('model is not in Config.VehicleCatalog')
    end
    a.check(); cl(t, 'spawnVehicle', model); return SENT
end)

A('vehicle.info', function(a)
    local t = online(a); a.check()
    local ped = GetPlayerPed(t)
    local veh = ped ~= 0 and GetVehiclePedIsIn(ped, false) or 0
    if veh == 0 then return { inVehicle = false } end
    local hash = GetEntityModel(veh)
    local label
    for _, v in ipairs(Config.VehicleCatalog) do
        if (GetHashKey(v.model) & 0xffffffff) == (hash & 0xffffffff) then label = v.label end
    end
    return { inVehicle = true, modelHash = hash & 0xffffffff, label = label, plate = GetVehicleNumberPlateText(veh),
        bodyHealth = GetEntityHealth(veh), engineHealth = GetVehicleEngineHealth(veh), coords = xyz(GetEntityCoords(veh)) }
end)

A('vehicle.repair', function(a) local t = online(a); a.check(); cl(t, 'repairVehicle'); return SENT end)
A('vehicle.delete', function(a) local t = online(a); a.check(); cl(t, 'deleteVehicle'); return SENT end)
A('vehicle.upgrade', function(a) local t = online(a); a.check(); cl(t, 'upgradeVehicle'); return SENT end)

A('vehicle.color', function(a)
    local t = online(a)
    local p, s = a.int('primary', 0, 160, 0), a.int('secondary', 0, 160, 0)
    a.check(); cl(t, 'colorVehicle', p, s); return SENT
end)

---------------------------------------------------------------- 6. player list / management
local function listPlayers()
    local out = {}
    for _, sid in ipairs(GetPlayers()) do
        local id = tonumber(sid)
        local ped = GetPlayerPed(sid)
        local row = { id = id, name = GetPlayerName(sid), ping = GetPlayerPing(sid) }
        if ped ~= 0 then
            local c = GetEntityCoords(ped)
            row.coords = { x = math.floor(c.x), y = math.floor(c.y), z = math.floor(c.z) }
            row.health = GetEntityHealth(ped)
        end
        out[#out + 1] = row
    end
    return out
end

A('players.list', function() local p = listPlayers(); return { count = #p, players = p } end)

A('players.search', function(a)
    local q = a.str('query', 32); a.check()
    local needle, out = q:lower(), {}
    for _, p in ipairs(listPlayers()) do
        if tostring(p.id) == q or (p.name or ''):lower():find(needle, 1, true) then out[#out + 1] = p end
    end
    return { count = #out, players = out }
end)

local function noteKey(t)
    local license = GetPlayerIdentifierByType(t, 'license')
    return license and ('fmcc:note:' .. license) or nil
end

A('players.note_add', function(a)
    local t = online(a); local text = a.str('note', 300); a.check()
    local key = noteKey(t)
    if not key then return nil, 'player has no license identifier, so a note cannot be attached' end
    local ok, notes = pcall(json.decode, GetResourceKvpString(key) or '[]')
    notes = ok and type(notes) == 'table' and notes or {}
    notes[#notes + 1] = { t = os.time(), text = text }
    while #notes > 50 do table.remove(notes, 1) end
    SetResourceKvp(key, json.encode(notes))
    return { saved = true, totalNotes = #notes }
end)

A('players.note_list', function(a)
    local t = online(a); a.check()
    local key = noteKey(t)
    if not key then return nil, 'player has no license identifier' end
    local ok, notes = pcall(json.decode, GetResourceKvpString(key) or '[]')
    return { notes = ok and notes or {} }
end)

A('players.spectate', function(a)
    local admin, target = online(a, 'admin'), online(a, 'target'); a.check()
    if admin == target then return nil, 'admin and target must be different players' end
    local ped = GetPlayerPed(target)
    if ped == 0 then return nil, 'target has no ped yet' end
    local c = GetEntityCoords(ped)
    S.expect(admin, 15000); cl(admin, 'spectate', target, c.x, c.y, c.z); return SENT
end)

A('players.spectate_stop', function(a)
    local admin = online(a, 'admin'); a.check(); cl(admin, 'spectateStop'); return SENT
end)

A('players.kick', function(a)
    local t = online(a); local reason = a.str('reason', 100, nil, 'No reason given'); a.check()
    DropPlayer(t, 'Removed by an administrator: ' .. reason)
    return { kicked = true }
end)

---------------------------------------------------------------- 7. world / environment
local WEATHER = { 'CLEAR', 'EXTRASUNNY', 'CLOUDS', 'OVERCAST', 'RAIN', 'THUNDER', 'FOGGY', 'SMOG', 'SNOW', 'BLIZZARD', 'XMAS', 'NEUTRAL' }
local function pushWorld() TriggerClientEvent('fmcc:cl:world', -1, FMCC.World) end

A('world.info', function()
    local w = FMCC.World
    return { override = w.override, hour = w.hour, minute = w.minute, timeFrozen = w.freeze, weather = w.weather,
        note = w.override and 'time and weather are controlled by this resource' or 'no override set; the game or another resource controls time and weather' }
end)

A('world.set_time', function(a)
    local h, m = a.int('hour', 0, 23), a.int('minute', 0, 59, 0); a.check()
    local w = FMCC.World; w.override, w.hour, w.minute = true, h, m; pushWorld(); return { hour = h, minute = m }
end)

A('world.set_weather', function(a)
    local weather = a.choice('weather', WEATHER); a.check()
    local w = FMCC.World; w.override, w.weather = true, weather; pushWorld(); return { weather = weather }
end)

A('world.freeze_time', function(a)
    local state = a.bool('state'); a.check()
    local w = FMCC.World; w.override, w.freeze = true, state; pushWorld(); return { timeFrozen = state }
end)

A('world.locations', function() return { locations = Config.Locations } end)

A('world.teleport_preset', function(a)
    local t = online(a); local name = a.str('preset', 40); a.check()
    for _, l in ipairs(Config.Locations) do
        if l.name:lower() == name:lower() then
            S.expect(t, 8000); cl(t, 'teleport', l.x, l.y, l.z, l.h); return SENT
        end
    end
    return nil, 'no location preset named "' .. name .. '" in Config.Locations'
end)

A('world.entities', function()
    return { vehicles = #GetAllVehicles(), peds = #GetAllPeds(), objects = #GetAllObjects() }
end)

---------------------------------------------------------------- 8. inventory
A('inventory.catalog', function()
    local items, source = FMCC.Inventory.catalog()
    return { source = source, count = #items, items = items }
end)

A('inventory.search', function(a)
    local q = a.str('query', 40); a.check()
    local items, source = FMCC.Inventory.catalog()
    local needle, out = q:lower(), {}
    for _, it in ipairs(items) do
        if it.name:lower():find(needle, 1, true) or (it.label or ''):lower():find(needle, 1, true) then out[#out + 1] = it end
    end
    return { source = source, count = #out, items = out }
end)

A('inventory.view', function(a)
    local t = online(a); a.check()
    local items, source = FMCC.Inventory.view(t)
    if not items then return nil, source end
    return { adapter = source, count = #items, items = items }
end)

A('inventory.give', function(a)
    local t = online(a); local item = a.str('item', 50, '^[%w_%-]+$'); local count = a.int('count', 1, 1000, 1); a.check()
    return FMCC.Inventory.give(t, item, count)
end)

---------------------------------------------------------------- 10. diagnostics
local function framework()
    for _, f in ipairs({ { 'qbx_core', 'qbox' }, { 'qb-core', 'qbcore' }, { 'es_extended', 'esx' } }) do
        if GetResourceState(f[1]) == 'started' then return f[2] end
    end
    return 'standalone'
end

A('diag.status', function()
    return {
        resource = GetCurrentResourceName(), version = GetResourceMetadata(GetCurrentResourceName(), 'version', 0),
        uptimeSeconds = (GetGameTimer() - FMCC.Stats.started) // 1000, onesync = GetConvar('onesync', 'off'),
        players = #GetPlayers(), maxClients = GetConvarInt('sv_maxclients', 0), framework = framework(),
        inventoryAdapter = FMCC.Inventory.adapter() or 'none', serverBuild = GetConvar('version', 'unknown'),
    }
end)

A('diag.resources', function()
    local out = {}
    for i = 0, GetNumResources() - 1 do
        local name = GetResourceByFindIndex(i)
        if name and #out < 500 then out[#out + 1] = { name = name, state = GetResourceState(name) } end
    end
    return { count = #out, resources = out }
end)

A('diag.validate', function()
    local checks = {}
    local function add(name, ok, detail, warn) checks[#checks + 1] = { check = name, status = ok and 'ok' or (warn and 'warn' or 'fail'), detail = detail } end
    local strong = 0
    for _, t in ipairs(Config.Tokens) do if Core.tokenIsStrong(t.token) and Config.Roles[t.role] then strong = strong + 1 end end
    add('api tokens', strong > 0, strong .. ' usable token(s); tokens need 24+ characters and a defined role')
    add('onesync', GetConvar('onesync', 'off') ~= 'off', 'onesync=' .. GetConvar('onesync', 'off') .. ' (server-side reads and entity monitoring need it)')
    add('vehicle catalog', #Config.VehicleCatalog > 0, #Config.VehicleCatalog .. ' entries', true)
    add('weapon catalog', #Config.WeaponCatalog > 0, #Config.WeaponCatalog .. ' entries', true)
    add('fun module', not Config.Modules.fun, Config.Modules.fun and 'enabled: use only on a test server' or 'disabled', true)
    add('rate limit', Config.RateLimit.requests >= 5, Config.RateLimit.requests .. ' requests per ' .. Config.RateLimit.windowMs .. ' ms', true)
    add('inventory adapter', FMCC.Inventory.adapter() ~= nil, FMCC.Inventory.adapter() or 'none detected; inventory.* uses the config catalog only', true)
    return { checks = checks }
end)

A('diag.errors', function(a)
    local limit = a.int('limit', 1, 100, 25); a.check(); return { entries = FMCC.Log.list(limit) }
end)

A('diag.perf', function()
    local s = FMCC.Stats
    return { requests = s.requests, denied = s.denied, errors = s.errors,
        avgHandlerMs = s.requests > 0 and math.floor(s.totalMs / s.requests * 100) / 100 or 0, maxHandlerMs = s.maxMs,
        vehicles = #GetAllVehicles(), peds = #GetAllPeds(), objects = #GetAllObjects(), players = #GetPlayers() }
end)

---------------------------------------------------------------- 11. security
A('sec.integrity_baseline', function(a)
    local r = a.str('resource', 64, '^[%w_%-%.]+$', GetCurrentResourceName()); a.check(); return S.baseline(r)
end)

A('sec.integrity_check', function(a)
    local r = a.str('resource', 64, '^[%w_%-%.]+$', GetCurrentResourceName()); a.check(); return S.check(r)
end)

A('sec.alerts', function(a) local n = a.int('limit', 1, 200, 50); a.check(); return { alerts = S.alerts(n) } end)
A('sec.identifiers', function(a) local t = online(a); a.check(); return S.identifiers(t) end)
A('sec.clear_alerts', function() S.clear(); return { cleared = true } end)

---------------------------------------------------------------- 12. access
A('access.whoami', function(_, principal)
    return { label = principal.label, role = principal.role, patterns = Config.Roles[principal.role] }
end)

A('access.roles', function()
    local out = {}
    for name, patterns in pairs(Config.Roles) do out[#out + 1] = { role = name, patterns = patterns } end
    table.sort(out, function(x, y) return x.role < y.role end)
    return { roles = out }
end)

A('access.audit', function(a) local n = a.int('limit', 1, 500, 50); a.check(); return { entries = FMCC.Audit.list(n) } end)
