-- Client effects. The server decides who may trigger them; every handler here only affects the local player.
local function me() return PlayerPedId() end

local function notify(msg)
    BeginTextCommandThefeedPost('STRING')
    AddTextComponentSubstringPlayerName(msg)
    EndTextCommandThefeedPostTicker(false, false)
end

local function loadModel(hash, timeoutMs)
    if not IsModelInCdimage(hash) then return false end
    RequestModel(hash)
    local limit = GetGameTimer() + (timeoutMs or 5000)
    while not HasModelLoaded(hash) do
        Wait(0)
        if GetGameTimer() > limit then return false end
    end
    return true
end

local function loadDict(dict, timeoutMs)
    if not DoesAnimDictExist(dict) then return false end
    RequestAnimDict(dict)
    local limit = GetGameTimer() + (timeoutMs or 3000)
    while not HasAnimDictLoaded(dict) do
        Wait(0)
        if GetGameTimer() > limit then return false end
    end
    return true
end

local function currentVehicle()
    local veh = GetVehiclePedIsIn(me(), false)
    return veh ~= 0 and veh or nil
end

local function drawText(text, x, y, scale)
    SetTextFont(4); SetTextScale(scale, scale); SetTextColour(255, 255, 255, 235)
    SetTextOutline(); SetTextCentre(true)
    BeginTextCommandDisplayText('STRING'); AddTextComponentSubstringPlayerName(text)
    EndTextCommandDisplayText(x, y)
end

---------------------------------------------------------------- player / movement
RegisterNetEvent('fmcc:cl:heal', function()
    local ped = me()
    SetEntityHealth(ped, GetEntityMaxHealth(ped))
    ClearPedBloodDamage(ped)
end)

RegisterNetEvent('fmcc:cl:armor', function(amount) SetPedArmour(me(), amount) end)

local function teleport(x, y, z, h)
    local ped = me()
    RequestCollisionAtCoord(x, y, z)
    SetPedCoordsKeepVehicle(ped, x, y, z)
    if h then SetEntityHeading(ped, h) end
    local limit = GetGameTimer() + 2000
    while not HasCollisionLoadedAroundEntity(ped) and GetGameTimer() < limit do Wait(0) end
end

RegisterNetEvent('fmcc:cl:teleport', function(x, y, z, h) teleport(x + 0.0, y + 0.0, z + 0.0, h) end)

RegisterNetEvent('fmcc:cl:teleportWaypoint', function()
    local blip = GetFirstBlipInfoId(8)
    if not DoesBlipExist(blip) then return notify('Set a map waypoint first.') end
    local c = GetBlipInfoIdCoord(blip)
    for z = 1000.0, 0.0, -25.0 do
        RequestCollisionAtCoord(c.x, c.y, z)
        SetPedCoordsKeepVehicle(me(), c.x, c.y, z)
        Wait(50)
        local found, groundZ = GetGroundZFor_3dCoord(c.x, c.y, z, false)
        if found then
            SetPedCoordsKeepVehicle(me(), c.x, c.y, groundZ + 1.0)
            return
        end
    end
    notify('Could not find ground at the waypoint.')
end)

RegisterNetEvent('fmcc:cl:freeze', function(state)
    FreezeEntityPosition(currentVehicle() or me(), state)
end)

RegisterNetEvent('fmcc:cl:model', function(name)
    local hash = joaat(name)
    if not loadModel(hash) then return notify('Model "' .. name .. '" could not be loaded.') end
    SetPlayerModel(PlayerId(), hash)
    SetModelAsNoLongerNeeded(hash)
    SetPedDefaultComponentVariation(me())
end)

---------------------------------------------------------------- combat training
local trainingActive = false
local crosshair = { style = 'off', size = 8, r = 255, g = 255, b = 255 }
local hitmarker, hitUntil = false, 0
local overlay = false
local stats = { shots = 0, hits = 0, kills = 0 }

RegisterNetEvent('fmcc:cl:crosshair', function(style, size, color)
    crosshair.style, crosshair.size = style, size
    crosshair.r = tonumber(color:sub(1, 2), 16)
    crosshair.g = tonumber(color:sub(3, 4), 16)
    crosshair.b = tonumber(color:sub(5, 6), 16)
    trainingActive = true
end)

RegisterNetEvent('fmcc:cl:hitmarker', function(enabled) hitmarker = enabled; trainingActive = true end)
RegisterNetEvent('fmcc:cl:overlay', function(enabled) overlay = enabled end)

RegisterNetEvent('fmcc:cl:dummy', function()
    trainingActive = true
    local hash = joaat('a_m_m_business_01')
    if not loadModel(hash) then return notify('Training dummy model could not be loaded.') end
    local pos = GetOffsetFromEntityInWorldCoords(me(), 0.0, 10.0, 0.0)
    local ped = CreatePed(4, hash, pos.x, pos.y, pos.z, GetEntityHeading(me()) + 180.0, false, false)
    SetEntityAsMissionEntity(ped, true, true)
    FreezeEntityPosition(ped, true)
    SetBlockingOfNonTemporaryEvents(ped, true)
    SetModelAsNoLongerNeeded(hash)
    SetTimeout(300000, function()
        if DoesEntityExist(ped) then DeletePed(ped) end
    end)
end)

AddEventHandler('gameEventTriggered', function(name, args)
    if name ~= 'CEventNetworkEntityDamage' or not trainingActive then return end
    local victim, attacker = args[1], args[2]
    if attacker == me() and victim ~= me() and IsEntityAPed(victim) then
        stats.hits = stats.hits + 1
        if args[6] == 1 then stats.kills = stats.kills + 1 end
        hitUntil = GetGameTimer() + 150
    end
end)

local function drawCrosshair()
    local w, h = GetActualScreenResolution()
    local px, py = 1.0 / w, 1.0 / h
    local s, r, g, b = crosshair.size, crosshair.r, crosshair.g, crosshair.b
    HideHudComponentThisFrame(14)
    if crosshair.style == 'dot' then
        DrawRect(0.5, 0.5, (s / 3) * px, (s / 3) * py, r, g, b, 235)
    elseif crosshair.style == 'cross' then
        local gap, t = 4, 2
        DrawRect(0.5 - (gap + s / 2) * px, 0.5, s * px, t * py, r, g, b, 235)
        DrawRect(0.5 + (gap + s / 2) * px, 0.5, s * px, t * py, r, g, b, 235)
        DrawRect(0.5, 0.5 - (gap + s / 2) * py, t * px, s * py, r, g, b, 235)
        DrawRect(0.5, 0.5 + (gap + s / 2) * py, t * px, s * py, r, g, b, 235)
    elseif crosshair.style == 'circle' then
        for i = 0, 23 do
            local ang = math.rad(i * 15)
            DrawRect(0.5 + math.cos(ang) * s * px, 0.5 + math.sin(ang) * s * py, 2 * px, 2 * py, r, g, b, 235)
        end
    end
end

local function drawOverlay()
    local myCoords = GetEntityCoords(me())
    for _, pid in ipairs(GetActivePlayers()) do
        local ped = GetPlayerPed(pid)
        if ped ~= me() then
            local c = GetEntityCoords(ped)
            local dist = #(c - myCoords)
            if dist <= 150.0 then
                local onScreen, sx, sy = World3dToScreen2d(c.x, c.y, c.z + 1.0)
                if onScreen then
                    drawText(('%s [%d]  %dm  HP %d'):format(GetPlayerName(pid), GetPlayerServerId(pid), math.floor(dist), GetEntityHealth(ped)), sx, sy, 0.3)
                end
            end
        end
    end
end

CreateThread(function()
    while true do
        if trainingActive or overlay then
            if crosshair.style ~= 'off' then drawCrosshair() end
            if hitmarker and GetGameTimer() < hitUntil then drawText('x', 0.5, 0.47, 0.6) end
            if IsPedShooting(me()) then stats.shots = stats.shots + 1 end
            if overlay then drawOverlay() end
            Wait(0)
        else
            Wait(500)
        end
    end
end)

CreateThread(function()
    local sent = { shots = -1, hits = -1, kills = -1 }
    while true do
        Wait(5000)
        if trainingActive and (stats.shots ~= sent.shots or stats.hits ~= sent.hits or stats.kills ~= sent.kills) then
            sent = { shots = stats.shots, hits = stats.hits, kills = stats.kills }
            TriggerServerEvent('fmcc:sv:stats', stats.shots, stats.hits, stats.kills)
        end
    end
end)

---------------------------------------------------------------- weapons
RegisterNetEvent('fmcc:cl:giveWeapon', function(weapon, ammo) GiveWeaponToPed(me(), joaat(weapon), ammo, false, true) end)
RegisterNetEvent('fmcc:cl:weaponComponent', function(weapon, component)
    GiveWeaponComponentToPed(me(), joaat(weapon), joaat(component))
end)
RegisterNetEvent('fmcc:cl:setAmmo', function(weapon, ammo) SetPedAmmo(me(), joaat(weapon), ammo) end)
RegisterNetEvent('fmcc:cl:removeWeapons', function() RemoveAllPedWeapons(me(), true) end)

---------------------------------------------------------------- fun / testing
RegisterNetEvent('fmcc:cl:emote', function(dict, name)
    if not loadDict(dict) then return notify('Animation dictionary "' .. dict .. '" was not found.') end
    TaskPlayAnim(me(), dict, name, 8.0, -8.0, -1, 49, 0.0, false, false, false)
end)

RegisterNetEvent('fmcc:cl:scenario', function(name) TaskStartScenarioInPlace(me(), name, 0, true) end)
RegisterNetEvent('fmcc:cl:ragdoll', function(ms) SetPedToRagdoll(me(), ms, ms, 0, false, false, false) end)

RegisterNetEvent('fmcc:cl:clone', function()
    local clone = ClonePed(me(), false, false, true)
    SetTimeout(60000, function()
        if DoesEntityExist(clone) then DeletePed(clone) end
    end)
end)

---------------------------------------------------------------- vehicles
RegisterNetEvent('fmcc:cl:spawnVehicle', function(model)
    local hash = joaat(model)
    if not loadModel(hash, 8000) then return notify('Vehicle model "' .. model .. '" could not be loaded.') end
    local ped = me()
    local pos = GetOffsetFromEntityInWorldCoords(ped, 0.0, 4.0, 0.5)
    local veh = CreateVehicle(hash, pos.x, pos.y, pos.z, GetEntityHeading(ped), true, false)
    SetVehicleOnGroundProperly(veh)
    SetPedIntoVehicle(ped, veh, -1)
    SetModelAsNoLongerNeeded(hash)
end)

RegisterNetEvent('fmcc:cl:repairVehicle', function()
    local veh = currentVehicle()
    if not veh then return notify('Get into a vehicle first.') end
    SetVehicleFixed(veh); SetVehicleDeformationFixed(veh); SetVehicleDirtLevel(veh, 0.0); SetVehicleEngineHealth(veh, 1000.0)
end)

RegisterNetEvent('fmcc:cl:deleteVehicle', function()
    local veh = currentVehicle()
    if not veh then return notify('Get into a vehicle first.') end
    SetEntityAsMissionEntity(veh, true, true)
    DeleteVehicle(veh)
end)

RegisterNetEvent('fmcc:cl:colorVehicle', function(primary, secondary)
    local veh = currentVehicle()
    if not veh then return notify('Get into a vehicle first.') end
    SetVehicleColours(veh, primary, secondary)
end)

RegisterNetEvent('fmcc:cl:upgradeVehicle', function()
    local veh = currentVehicle()
    if not veh then return notify('Get into a vehicle first.') end
    SetVehicleModKit(veh, 0)
    for mod = 0, 49 do
        if mod ~= 23 and mod ~= 24 then
            local count = GetNumVehicleMods(veh, mod)
            if count > 0 then SetVehicleMod(veh, mod, count - 1, false) end
        end
    end
    ToggleVehicleMod(veh, 18, true)
end)

---------------------------------------------------------------- spectate
local spectating, returnCoords = false, nil

RegisterNetEvent('fmcc:cl:spectate', function(serverId, x, y, z)
    local ped = me()
    if not spectating then returnCoords = GetEntityCoords(ped) end
    spectating = true
    SetEntityVisible(ped, false, false)
    SetEntityCollision(ped, false, false)
    FreezeEntityPosition(ped, true)
    SetEntityCoords(ped, x + 0.0, y + 0.0, z + 10.0, false, false, false, false)
    local limit = GetGameTimer() + 5000
    local targetPlayer = GetPlayerFromServerId(serverId)
    while (targetPlayer == -1 or not NetworkIsPlayerActive(targetPlayer)) and GetGameTimer() < limit do
        Wait(100)
        targetPlayer = GetPlayerFromServerId(serverId)
    end
    if targetPlayer == -1 then return notify('Target is out of range and could not be streamed in.') end
    NetworkSetInSpectatorMode(true, GetPlayerPed(targetPlayer))
end)

RegisterNetEvent('fmcc:cl:spectateStop', function()
    if not spectating then return end
    local ped = me()
    NetworkSetInSpectatorMode(false, ped)
    if returnCoords then SetEntityCoords(ped, returnCoords.x, returnCoords.y, returnCoords.z, false, false, false, false) end
    SetEntityVisible(ped, true, false)
    SetEntityCollision(ped, true, true)
    FreezeEntityPosition(ped, false)
    spectating, returnCoords = false, nil
end)

---------------------------------------------------------------- world (only active after the first world.* action)
local world, worldSince = nil, 0

RegisterNetEvent('fmcc:cl:world', function(state)
    world, worldSince = state, GetGameTimer()
    if world and world.override and world.weather then
        ClearOverrideWeather(); ClearWeatherTypePersist()
        SetWeatherTypeNowPersist(world.weather)
        SetOverrideWeather(world.weather)
    end
end)

CreateThread(function()
    TriggerServerEvent('fmcc:sv:requestWorld')
    while true do
        if world and world.override then
            local minutes = world.hour * 60 + world.minute
            if not world.freeze then minutes = minutes + (GetGameTimer() - worldSince) // 2000 end -- default game speed: 2 s per minute
            NetworkOverrideClockTime((minutes // 60) % 24, minutes % 60, 0)
            Wait(world.freeze and 0 or 1000)
        else
            Wait(1000)
        end
    end
end)
