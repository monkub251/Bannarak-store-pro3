"""Single list of every server action the app can call, with validated parameters.

tests/test_consistency.py checks that every id here has a handler in the Lua resource and vice versa.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Param:
    name: str
    kind: str                       # int | float | str | bool | choice
    label: str = ""
    required: bool = True
    default: Any = None
    choices: tuple = ()
    min: float | None = None
    max: float | None = None
    max_len: int = 100

    @property
    def title(self) -> str:
        return self.label or self.name.replace("_", " ").capitalize()


@dataclass(frozen=True)
class Action:
    id: str
    title: str
    description: str
    params: tuple = ()
    danger: bool = False

    @property
    def category(self) -> str:
        return self.id.split(".", 1)[0]


@dataclass(frozen=True)
class Category:
    key: str
    title: str
    blurb: str
    local: bool = False


CATEGORIES = (
    Category("player", "Player and movement", "Health, position and movement of a connected player."),
    Category("combat", "Combat training", "Crosshair, hit markers, practice statistics and a target dummy for aim practice."),
    Category("weapon", "Weapons", "Inspect and manage a player's weapons from the server catalog."),
    Category("fun", "Fun and testing", "Emotes, ragdoll and clones. Disabled on the server unless Config.Modules.fun is true."),
    Category("vehicle", "Vehicles", "Spawn, repair, recolor and remove vehicles."),
    Category("players", "Players", "Who is online, notes and permitted spectating."),
    Category("world", "World", "Time, weather, locations and entity counts."),
    Category("inventory", "Inventory", "Item catalog and inventory access through an optional framework adapter."),
    Category("ui", "Interface", "Profiles, hotkeys, appearance and backups.", local=True),
    Category("diag", "Diagnostics", "Server status, resources, configuration checks and performance."),
    Category("sec", "Security", "Integrity checks, alerts and identifier validation for authorized testing."),
    Category("access", "Access", "Your role on the server and the audit trail."),
)

CATEGORY_BY_KEY = {c.key: c for c in CATEGORIES}

TARGET = Param("target", "int", "Player ID", min=1, max=65535)


def _p(name, kind, label="", **kw) -> Param:
    return Param(name, kind, label, **kw)


ACTIONS: tuple[Action, ...] = (
    # player
    Action("player.info", "Show player details", "Health, armor, position, heading and vehicle state.", (TARGET,)),
    Action("player.heal", "Restore health", "Fills the player's health to its maximum.", (TARGET,)),
    Action("player.armor", "Set armor", "Sets body armor from 0 to 100.", (TARGET, _p("amount", "int", "Amount", required=False, default=100, min=0, max=100))),
    Action("player.teleport_coords", "Teleport to coordinates", "Moves the player to exact map coordinates.",
           (TARGET, _p("x", "float", "X", min=-10000, max=10000), _p("y", "float", "Y", min=-10000, max=10000), _p("z", "float", "Z", min=-500, max=2500))),
    Action("player.teleport_player", "Teleport to another player", "Moves the player to where another player stands.", (TARGET, _p("dest", "int", "Destination ID", min=1, max=65535))),
    Action("player.teleport_waypoint", "Teleport to map waypoint", "Moves the player to the waypoint set on their own map.", (TARGET,)),
    Action("player.freeze", "Freeze or release", "Holds the player (or their vehicle) in place.", (TARGET, _p("state", "bool", "Frozen"))),
    Action("player.set_model", "Change ped model", "Switches the player's model, for example mp_m_freemode_01.", (TARGET, _p("model", "str", "Model name", max_len=40))),
    # combat
    Action("combat.crosshair", "Custom crosshair", "Draws a configurable crosshair on the player's screen.",
           (TARGET, _p("style", "choice", "Style", choices=("dot", "cross", "circle", "off")), _p("size", "int", "Size", required=False, default=8, min=2, max=40), _p("color", "str", "Color (hex)", required=False, default="ffffff", max_len=6))),
    Action("combat.hitmarker", "Hit markers", "Shows a marker when the player hits another ped.", (TARGET, _p("enabled", "bool", "Enabled"))),
    Action("combat.stats", "Practice statistics", "Shots, hits, kills and accuracy reported by the training client.", (TARGET,)),
    Action("combat.spawn_dummy", "Spawn target dummy", "Places a frozen practice dummy ten meters ahead of the player.", (TARGET,)),
    Action("combat.overlay", "Admin overlay", "Names, distance and health of nearby players. Needs the ACE permission fmcc.overlay.", (TARGET, _p("enabled", "bool", "Enabled"))),
    # weapon
    Action("weapon.info", "Current weapon", "Shows which weapon the player is holding.", (TARGET,)),
    Action("weapon.give", "Give weapon", "Gives a weapon from the server catalog.", (TARGET, _p("weapon", "str", "Weapon", max_len=40), _p("ammo", "int", "Ammo", required=False, default=100, min=0, max=9999))),
    Action("weapon.component", "Add component", "Attaches a component such as COMPONENT_AT_PI_FLSH.", (TARGET, _p("weapon", "str", "Weapon", max_len=40), _p("component", "str", "Component", max_len=60))),
    Action("weapon.set_ammo", "Set ammo", "Sets the ammo count for one weapon.", (TARGET, _p("weapon", "str", "Weapon", max_len=40), _p("ammo", "int", "Ammo", min=0, max=9999))),
    Action("weapon.remove_all", "Remove all weapons", "Takes every weapon from the player.", (TARGET,), danger=True),
    # fun
    Action("fun.emote", "Play animation", "Plays an animation by dictionary and name.", (TARGET, _p("dict", "str", "Dictionary", max_len=60), _p("name", "str", "Animation", max_len=60))),
    Action("fun.scenario", "Start scenario", "Starts a world scenario such as WORLD_HUMAN_SMOKING.", (TARGET, _p("scenario", "str", "Scenario", max_len=60))),
    Action("fun.ragdoll", "Ragdoll", "Knocks the player down for a short time.", (TARGET, _p("duration_ms", "int", "Duration (ms)", required=False, default=2000, min=500, max=10000))),
    Action("fun.clone", "Clone player", "Creates a local clone that disappears after a minute.", (TARGET,)),
    # vehicle
    Action("vehicle.catalog", "Vehicle catalog", "Models the server allows you to spawn."),
    Action("vehicle.spawn", "Spawn vehicle", "Creates the vehicle in front of the player and seats them.", (TARGET, _p("model", "str", "Model", max_len=32))),
    Action("vehicle.info", "Vehicle details", "Model, plate, health and position of the player's vehicle.", (TARGET,)),
    Action("vehicle.repair", "Repair vehicle", "Fixes damage and cleans the vehicle the player sits in.", (TARGET,)),
    Action("vehicle.delete", "Delete vehicle", "Removes the vehicle the player sits in.", (TARGET,), danger=True),
    Action("vehicle.color", "Set colors", "Primary and secondary color index, 0 to 160.", (TARGET, _p("primary", "int", "Primary", required=False, default=0, min=0, max=160), _p("secondary", "int", "Secondary", required=False, default=0, min=0, max=160))),
    Action("vehicle.upgrade", "Max performance mods", "Applies the highest available upgrade of each type.", (TARGET,)),
    # players
    Action("players.list", "Online players", "Everyone connected, with ping, position and health."),
    Action("players.search", "Find player", "Search by name or exact ID.", (_p("query", "str", "Name or ID", max_len=32),)),
    Action("players.note_add", "Add note", "Attaches a staff note to the player's license.", (TARGET, _p("note", "str", "Note", max_len=300))),
    Action("players.note_list", "Show notes", "Staff notes saved for the player.", (TARGET,)),
    Action("players.spectate", "Spectate", "Puts an in-game staff member into spectator mode on a target.", (_p("admin", "int", "Your player ID", min=1, max=65535), TARGET)),
    Action("players.spectate_stop", "Stop spectating", "Returns the staff member to where they were.", (_p("admin", "int", "Your player ID", min=1, max=65535),)),
    Action("players.kick", "Remove from server", "Disconnects the player with a reason.", (TARGET, _p("reason", "str", "Reason", required=False, default="No reason given", max_len=100)), danger=True),
    # world
    Action("world.info", "World state", "Time and weather as controlled by this resource."),
    Action("world.set_time", "Set time", "Sets the in-game clock for everyone.", (_p("hour", "int", "Hour", min=0, max=23), _p("minute", "int", "Minute", required=False, default=0, min=0, max=59))),
    Action("world.set_weather", "Set weather", "Changes the weather for everyone.", (_p("weather", "choice", "Weather", choices=("CLEAR", "EXTRASUNNY", "CLOUDS", "OVERCAST", "RAIN", "THUNDER", "FOGGY", "SMOG", "SNOW", "BLIZZARD", "XMAS", "NEUTRAL")),)),
    Action("world.freeze_time", "Freeze or resume time", "Holds the clock at the current setting.", (_p("state", "bool", "Frozen"),)),
    Action("world.locations", "Location presets", "Named places defined in the server config."),
    Action("world.teleport_preset", "Teleport to preset", "Moves the player to a named location.", (TARGET, _p("preset", "str", "Location name", max_len=40))),
    Action("world.entities", "Entity counts", "Vehicles, peds and objects currently spawned."),
    # inventory
    Action("inventory.catalog", "Item catalog", "Items known to the inventory adapter or the config."),
    Action("inventory.search", "Find item", "Search the catalog by name or label.", (_p("query", "str", "Item", max_len=40),)),
    Action("inventory.view", "View inventory", "Items a player carries. Needs ox_inventory, qb-core or es_extended.", (TARGET,)),
    Action("inventory.give", "Give item", "Adds an item through the inventory adapter.", (TARGET, _p("item", "str", "Item name", max_len=50), _p("count", "int", "Count", required=False, default=1, min=1, max=1000))),
    # diag
    Action("diag.status", "Server status", "Resource version, uptime, onesync, players and detected framework."),
    Action("diag.resources", "Resource list", "Every resource and whether it is started."),
    Action("diag.validate", "Check server configuration", "Tokens, onesync, catalogs, module flags and rate limits."),
    Action("diag.errors", "Recent errors", "Handler errors and alerts kept in server memory.", (_p("limit", "int", "Entries", required=False, default=25, min=1, max=100),)),
    Action("diag.perf", "Performance counters", "Request counts, handler timings and entity totals."),
    # sec
    Action("sec.integrity_baseline", "Save integrity baseline", "Hashes the manifest files of a resource as the known-good state.", (_p("resource", "str", "Resource (blank = this one)", required=False, max_len=64),)),
    Action("sec.integrity_check", "Check integrity", "Compares a resource against its saved baseline.", (_p("resource", "str", "Resource (blank = this one)", required=False, max_len=64),)),
    Action("sec.alerts", "Security alerts", "Spawn bursts, movement anomalies, event spam and integrity changes.", (_p("limit", "int", "Entries", required=False, default=50, min=1, max=200),)),
    Action("sec.identifiers", "Validate identifiers", "Checks identifier formats and duplicate licenses. Values are masked.", (TARGET,)),
    Action("sec.clear_alerts", "Clear alerts", "Empties the alert list after review.", (), danger=True),
    # access
    Action("access.whoami", "My role", "The role and permissions of the token this profile uses."),
    Action("access.roles", "All roles", "Roles and their permission patterns."),
    Action("access.audit", "Server audit log", "Recent actions and denials recorded by the server.", (_p("limit", "int", "Entries", required=False, default=50, min=1, max=500),)),
)

ACTION_BY_ID = {a.id: a for a in ACTIONS}


def actions_for(category: str) -> list[Action]:
    return [a for a in ACTIONS if a.category == category]


def _parse(p: Param, raw: Any) -> Any:
    if p.kind == "bool":
        if isinstance(raw, bool):
            return raw
        text = str(raw).strip().lower()
        if text not in ("true", "false", "yes", "no", "1", "0"):
            raise ValueError(f"{p.title} must be yes or no")
        return text in ("true", "yes", "1")
    if p.kind == "choice":
        if raw not in p.choices:
            raise ValueError(f"{p.title} must be one of: {', '.join(p.choices)}")
        return raw
    if p.kind in ("int", "float"):
        try:
            number = float(str(raw).strip()) if not isinstance(raw, (int, float)) or isinstance(raw, bool) else float(raw)
        except ValueError:
            number = None
        if number is None or number != number or number in (float("inf"), float("-inf")):
            raise ValueError(f"{p.title} must be a {'whole number' if p.kind == 'int' else 'number'}")
        if p.kind == "int" and number != int(number):
            raise ValueError(f"{p.title} must be a whole number")
        value = int(number) if p.kind == "int" else number
        if (p.min is not None and value < p.min) or (p.max is not None and value > p.max):
            raise ValueError(f"{p.title} must be between {p.min:g} and {p.max:g}")
        return value
    value = str(raw).strip()
    if len(value) > p.max_len:
        raise ValueError(f"{p.title} can be at most {p.max_len} characters")
    return value


def coerce_params(action_id: str, raw: dict[str, Any]) -> dict[str, Any]:
    """Validate user input for an action and return the JSON-ready parameter dict. Raises ValueError."""
    action = ACTION_BY_ID.get(action_id)
    if action is None:
        raise ValueError(f"Unknown action: {action_id}")
    out: dict[str, Any] = {}
    for p in action.params:
        value = raw.get(p.name)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            if p.required and p.default is None:
                raise ValueError(f"{p.title} is required")
            if p.default is not None:
                out[p.name] = p.default
            continue
        out[p.name] = _parse(p, value)
    return out
