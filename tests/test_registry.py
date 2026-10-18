import pytest

from app.core.registry import ACTIONS, ACTION_BY_ID, CATEGORIES, actions_for, coerce_params


def test_ids_unique_and_categorized():
    ids = [a.id for a in ACTIONS]
    assert len(ids) == len(set(ids))
    keys = {c.key for c in CATEGORIES}
    assert {a.category for a in ACTIONS} <= keys


def test_twelve_categories_present():
    assert len(CATEGORIES) == 12
    assert all(actions_for(c.key) for c in CATEGORIES if not c.local)


def test_coerce_defaults_and_types():
    assert coerce_params("player.armor", {"target": "5"}) == {"target": 5, "amount": 100}
    assert coerce_params("player.teleport_coords", {"target": 1, "x": "1.5", "y": "-2", "z": "30"}) == {"target": 1, "x": 1.5, "y": -2.0, "z": 30.0}
    assert coerce_params("player.freeze", {"target": 1, "state": True})["state"] is True
    assert coerce_params("world.set_weather", {"weather": "RAIN"}) == {"weather": "RAIN"}
    assert coerce_params("sec.integrity_check", {"resource": "  "}) == {}


@pytest.mark.parametrize("action,raw,fragment", [
    ("player.heal", {}, "Player ID is required"),
    ("player.heal", {"target": "abc"}, "whole number"),
    ("player.heal", {"target": "0"}, "between 1 and 65535"),
    ("player.heal", {"target": "1.5"}, "whole number"),
    ("player.armor", {"target": 1, "amount": "101"}, "between 0 and 100"),
    ("world.set_weather", {"weather": "LAVA"}, "must be one of"),
    ("player.freeze", {"target": 1, "state": "maybe"}, "yes or no"),
    ("players.note_add", {"target": 1, "note": "x" * 301}, "at most 300"),
    ("nope.nope", {}, "Unknown action"),
])
def test_coerce_errors(action, raw, fragment):
    with pytest.raises(ValueError, match=fragment):
        coerce_params(action, raw)


def test_dangerous_actions_flagged():
    assert {a.id for a in ACTIONS if a.danger} == {"weapon.remove_all", "vehicle.delete", "players.kick", "sec.clear_alerts"}
    assert ACTION_BY_ID["players.kick"].danger
