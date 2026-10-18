-- FIVE M CONTROL CENTER: server configuration.
-- This file is SERVER-ONLY. It contains API tokens. Do not add it to client_scripts or shared_scripts.

Config = {}

-- 1) API tokens. Generate a long random string for each operator (at least 24 characters).
--    While every token is still a placeholder, the API refuses all requests (safe default).
Config.Tokens = {
    { token = 'CHANGE_ME_generate_a_long_random_token', role = 'owner', label = 'owner' },
}

-- 2) Roles. Patterns: '*' (everything), 'player.*' (one category), 'player.heal' (one action).
--    A leading '!' removes access. The last matching pattern wins.
Config.Roles = {
    owner     = { '*' },
    admin     = { '*', '!access.audit' },
    moderator = { 'player.info', 'player.heal', 'player.teleport_*', 'players.*', '!players.kick',
                  'world.info', 'world.locations', 'vehicle.catalog', 'diag.status', 'access.whoami' },
    viewer    = { 'players.list', 'players.search', 'world.info', 'world.locations', 'vehicle.catalog',
                  'inventory.catalog', 'diag.status', 'access.whoami' },
}

-- 3) Modules. A disabled module rejects its actions. 'fun' is off by default: enable it on test servers only.
Config.Modules = {
    player = true, combat = true, weapon = true, fun = false, vehicle = true,
    players = true, world = true, inventory = true, diag = true, sec = true, access = true,
}

-- Admin overlay (names, distance, health of nearby players) is shown only to in-game players
-- who hold the ACE permission "fmcc.overlay" (add_ace group.admin fmcc.overlay allow).
Config.AdminOverlay = true

-- 4) API protection.
Config.RateLimit = { requests = 40, windowMs = 10000 }     -- per client address
Config.AuthFailures = { limit = 5, windowMs = 60000 }      -- failed logins per client address
Config.MaxBodyBytes = 16384

-- 5) Catalogs. Requests outside these lists are rejected when the matching Restrict option is true.
Config.RestrictVehicles = true
Config.VehicleCatalog = {
    { model = 'adder', label = 'Truffade Adder' }, { model = 'sultan', label = 'Karin Sultan' },
    { model = 'kuruma', label = 'Karin Kuruma' }, { model = 'bati', label = 'Pegassi Bati 801' },
    { model = 'sanchez', label = 'Maibatsu Sanchez' }, { model = 'police', label = 'Police Cruiser' },
    { model = 'buzzard2', label = 'Nagasaki Buzzard' }, { model = 'dinghy', label = 'Nagasaki Dinghy' },
}
Config.RestrictWeapons = true
Config.WeaponCatalog = {
    { name = 'WEAPON_PISTOL', label = 'Pistol' }, { name = 'WEAPON_COMBATPISTOL', label = 'Combat Pistol' },
    { name = 'WEAPON_SMG', label = 'SMG' }, { name = 'WEAPON_CARBINERIFLE', label = 'Carbine Rifle' },
    { name = 'WEAPON_PUMPSHOTGUN', label = 'Pump Shotgun' }, { name = 'WEAPON_KNIFE', label = 'Knife' },
}
Config.Locations = {
    { name = 'Legion Square', x = 195.17, y = -933.77, z = 30.69, h = 144.5 },
    { name = 'LS Airport', x = -1037.0, y = -2737.0, z = 20.17, h = 330.0 },
    { name = 'Sandy Shores', x = 1850.0, y = 3680.0, z = 34.0, h = 210.0 },
}
-- Used only when no inventory adapter exposes a catalog.
Config.ItemCatalog = { { name = 'water', label = 'Water' }, { name = 'bread', label = 'Bread' } }

-- 6) Inventory adapter: 'auto' | 'ox_inventory' | 'qb' | 'esx' | 'none'
Config.InventoryAdapter = 'auto'

-- 7) Defensive monitoring (alerts only: this resource never bans or kicks automatically).
Config.Security = {
    EntitySpawn = { enabled = true, limit = 25, windowMs = 10000, populationTypes = { 6, 7 } },
    Movement = { enabled = true, maxOnFootSpeed = 45.0, intervalMs = 2000, strikes = 2 },
    EventGuardAlerts = true,
}
Config.MaxAlerts = 200
Config.MaxAudit = 500
