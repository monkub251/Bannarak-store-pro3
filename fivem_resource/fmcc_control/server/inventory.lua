-- Optional inventory adapters. All adapters are UNTESTED against live servers: verify on your own framework.
FMCC = FMCC or {}
FMCC.Inventory = {}
local I = FMCC.Inventory

local function started(name) return GetResourceState(name) == 'started' end

function I.adapter()
    local want = Config.InventoryAdapter
    if want == 'none' then return nil end
    if (want == 'auto' or want == 'ox_inventory') and started('ox_inventory') then return 'ox_inventory' end
    if (want == 'auto' or want == 'qb') and (started('qb-core') or started('qbx_core')) then return 'qb' end
    if (want == 'auto' or want == 'esx') and started('es_extended') then return 'esx' end
    return nil
end

local function qbCore()
    local ok, core = pcall(function() return exports['qb-core']:GetCoreObject() end)
    return ok and core or nil
end

local function esx()
    local ok, core = pcall(function() return exports['es_extended']:getSharedObject() end)
    return ok and core or nil
end

function I.catalog()
    local ad = I.adapter()
    local out = {}
    if ad == 'ox_inventory' then
        local ok, items = pcall(function() return exports.ox_inventory:Items() end)
        if ok and type(items) == 'table' then
            for name, d in pairs(items) do out[#out + 1] = { name = name, label = d.label or name } end
            table.sort(out, function(a, b) return a.name < b.name end)
            return out, 'ox_inventory'
        end
    elseif ad == 'qb' then
        local core = qbCore()
        if core and core.Shared and core.Shared.Items then
            for name, d in pairs(core.Shared.Items) do out[#out + 1] = { name = name, label = d.label or name } end
            table.sort(out, function(a, b) return a.name < b.name end)
            return out, 'qb'
        end
    end
    return Config.ItemCatalog, ad and (ad .. ' (catalog taken from Config.ItemCatalog)') or 'config'
end

function I.view(src)
    local ad = I.adapter()
    if not ad then
        return nil, 'no inventory adapter detected: start ox_inventory, qb-core or es_extended, or set Config.InventoryAdapter'
    end
    local out = {}
    if ad == 'ox_inventory' then
        local ok, items = pcall(function() return exports.ox_inventory:GetInventoryItems(src) end)
        if not ok or type(items) ~= 'table' then return nil, 'ox_inventory did not return an inventory for this player' end
        for _, it in pairs(items) do out[#out + 1] = { name = it.name, label = it.label, count = it.count } end
    elseif ad == 'qb' then
        local core = qbCore()
        local player = core and core.Functions.GetPlayer(src)
        if not player then return nil, 'qb-core has no player loaded for this id' end
        for _, it in pairs(player.PlayerData.items or {}) do out[#out + 1] = { name = it.name, label = it.label, count = it.amount } end
    else
        local core = esx()
        local player = core and core.GetPlayerFromId(src)
        if not player then return nil, 'es_extended has no player loaded for this id' end
        for _, it in pairs(player.getInventory()) do
            if (it.count or 0) > 0 then out[#out + 1] = { name = it.name, label = it.label, count = it.count } end
        end
    end
    return out, ad
end

function I.give(src, item, count)
    local ad = I.adapter()
    if not ad then return nil, 'no inventory adapter detected; nothing was given' end
    local ok, res
    if ad == 'ox_inventory' then
        ok, res = pcall(function() return exports.ox_inventory:AddItem(src, item, count) end)
    elseif ad == 'qb' then
        local core = qbCore()
        local player = core and core.Functions.GetPlayer(src)
        if not player then return nil, 'qb-core has no player loaded for this id' end
        ok, res = pcall(function() return player.Functions.AddItem(item, count) end)
    else
        local core = esx()
        local player = core and core.GetPlayerFromId(src)
        if not player then return nil, 'es_extended has no player loaded for this id' end
        ok, res = pcall(function() player.addInventoryItem(item, count); return true end)
    end
    if not ok or not res then return nil, ad .. ' refused the item (unknown item, full inventory or invalid count)' end
    return { given = true, adapter = ad }
end
