FMCC = FMCC or {}
local Core = FMCC.Core
local RES = GetCurrentResourceName()
FMCC.Stats = { requests = 0, denied = 0, errors = 0, totalMs = 0, maxMs = 0, started = GetGameTimer() }

local apiLimiter = Core.newLimiter(Config.RateLimit.requests, Config.RateLimit.windowMs)
local failLimiter = Core.newLimiter(Config.AuthFailures.limit, Config.AuthFailures.windowMs)

local tokens = {}
for _, t in ipairs(Config.Tokens) do
    if Core.tokenIsStrong(t.token) and Config.Roles[t.role] then tokens[#tokens + 1] = t end
end

local function send(res, status, body)
    res.writeHead(status, { ['Content-Type'] = 'application/json', ['Cache-Control'] = 'no-store' })
    res.send(json.encode(body))
end
local function failure(code, message) return { ok = false, error = { code = code, message = message } } end

local function header(headers, name)
    for k, v in pairs(headers or {}) do
        if tostring(k):lower() == name then return v end
    end
end

local function authenticate(headers)
    local presented = Core.bearer(header(headers, 'authorization'))
    if not presented then return nil end
    local found
    for _, t in ipairs(tokens) do
        if Core.safeEqual(presented, t.token) then found = t end -- no early exit: constant work per request
    end
    return found
end

local function onError(e)
    if type(e) == 'table' then return e end
    return debug.traceback(tostring(e), 2)
end

SetHttpHandler(function(req, res)
    local addr = req.address or 'unknown'
    local now = GetGameTimer()
    if req.path ~= '/api' or req.method ~= 'POST' then
        return send(res, 404, failure('not_found', 'POST /api is the only endpoint'))
    end
    if #tokens == 0 then
        return send(res, 503, failure('not_configured', 'no usable token in config.lua (24+ characters, not a placeholder)'))
    end
    if failLimiter.peek(addr, now) >= Config.AuthFailures.limit then
        return send(res, 429, failure('locked', 'too many failed logins from this address; wait a minute'))
    end
    if not apiLimiter.hit(addr, now) then
        return send(res, 429, failure('rate_limited', 'too many requests; slow down'))
    end

    req.setDataHandler(function(body)
        local principal = authenticate(req.headers)
        if not principal then
            failLimiter.hit(addr, GetGameTimer())
            FMCC.Stats.denied = FMCC.Stats.denied + 1
            FMCC.Audit.add('unknown', 'auth', { address = addr }, false, 'invalid or missing token')
            return send(res, 401, failure('unauthorized', 'missing or invalid bearer token'))
        end
        if type(body) ~= 'string' or #body > Config.MaxBodyBytes then
            return send(res, 413, failure('too_large', 'request body is missing or too large'))
        end
        local okJson, payload = pcall(json.decode, body)
        if not okJson or type(payload) ~= 'table' or type(payload.action) ~= 'string' then
            return send(res, 400, failure('bad_request', 'body must be JSON like {"action":"player.heal","params":{}}'))
        end

        local action = payload.action
        local handler = FMCC.Actions[action]
        if not handler then return send(res, 404, failure('unknown_action', 'unknown action: ' .. action:sub(1, 60))) end
        local category = action:match('^(%w+)%.')
        if not Config.Modules[category] then
            return send(res, 403, failure('module_disabled', 'module "' .. tostring(category) .. '" is disabled in Config.Modules'))
        end
        if not Core.permits(Config.Roles[principal.role], action) then
            FMCC.Stats.denied = FMCC.Stats.denied + 1
            FMCC.Audit.add(principal.label, action, payload.params, false, 'forbidden for role ' .. principal.role)
            return send(res, 403, failure('forbidden', 'role "' .. principal.role .. '" may not run ' .. action))
        end

        local t0 = GetGameTimer()
        local ok, data, message = xpcall(handler, onError, Core.args(payload.params), principal)
        local ms = GetGameTimer() - t0
        local s = FMCC.Stats
        s.requests, s.totalMs, s.maxMs = s.requests + 1, s.totalMs + ms, math.max(s.maxMs, ms)

        if not ok then
            if type(data) == 'table' and data.fmcc then
                FMCC.Audit.add(principal.label, action, payload.params, false, data.fmcc)
                return send(res, 400, failure('bad_request', data.fmcc))
            end
            s.errors = s.errors + 1
            FMCC.Log.add('error', action .. ': ' .. tostring(data))
            FMCC.Audit.add(principal.label, action, payload.params, false, 'internal error')
            return send(res, 500, failure('internal_error', 'handler failed; see diag.errors on the server'))
        end
        if data == nil then
            FMCC.Audit.add(principal.label, action, payload.params, false, message)
            return send(res, 422, failure('action_failed', message or 'the action could not be completed'))
        end
        FMCC.Audit.add(principal.label, action, payload.params, true)
        send(res, 200, { ok = true, data = data })
    end)
end)

-- client -> server events (rate limited, validated)
FMCC.Security.guard('fmcc:sv:requestWorld', 3, 30000, function(src)
    TriggerClientEvent('fmcc:cl:world', src, FMCC.World)
end)

FMCC.Security.guard('fmcc:sv:stats', 6, 30000, function(src, shots, hits, kills)
    local function n(v) v = tonumber(v); if not v or v < 0 or v > 10000000 then return nil end return math.floor(v) end
    shots, hits, kills = n(shots), n(hits), n(kills)
    if shots and hits and kills then FMCC.CombatStats[src] = { shots = shots, hits = hits, kills = kills } end
end)

AddEventHandler('playerDropped', function() FMCC.CombatStats[source] = nil end)

CreateThread(function()
    Wait(500)
    if #tokens == 0 then
        FMCC.Log.add('warn', 'no usable API token in config.lua; the API will refuse every request until one is set')
    else
        FMCC.Log.add('info', ('API ready at http://<server-ip>:<port>/%s/api with %d token(s)'):format(RES, #tokens))
    end
    if GetConvar('onesync', 'off') == 'off' then
        FMCC.Log.add('warn', 'onesync is off; server-side player reads and entity monitoring will not work')
    end
end)
