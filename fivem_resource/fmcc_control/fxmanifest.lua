fx_version 'cerulean'
game 'gta5'
lua54 'yes'

name 'fmcc_control'
description 'FIVE M CONTROL CENTER companion resource (token-authenticated admin API + client effects)'
author 'FMCC'
version '1.0.0'

-- Server-only: config.lua holds API tokens and must never be listed as a shared or client script.
server_scripts {
    'config.lua',
    'server/core.lua',
    'server/audit.lua',
    'server/security.lua',
    'server/inventory.lua',
    'server/actions.lua',
    'server/main.lua',
}

client_scripts {
    'client/main.lua',
}
