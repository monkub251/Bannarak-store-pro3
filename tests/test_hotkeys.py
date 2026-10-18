import pytest

from app.core import hotkeys as hk


@pytest.mark.parametrize("raw,want", [("ctrl+k", "Ctrl+K"), ("Shift+Ctrl+1", "Ctrl+Shift+1"), ("f5", "F5"),
                                      ("alt+shift+f12", "Alt+Shift+F12"), ("Meta+A", "Meta+A")])
def test_normalize(raw, want):
    assert hk.normalize(raw) == want


@pytest.mark.parametrize("raw", ["", "K", "Ctrl+", "Ctrl+Ctrl+K", "Hyper+K", "Ctrl+Enter", "Ctrl+F13", "Ctrl+K, Ctrl+B", None])
def test_rejects(raw):
    with pytest.raises(ValueError):
        hk.normalize(raw)


def test_defaults_are_valid_and_unique():
    assert hk.find_conflicts(hk.DEFAULT_HOTKEYS) == {}
    for seq in hk.DEFAULT_HOTKEYS.values():
        assert hk.normalize(seq) == seq


def test_conflicts_reported():
    assert hk.find_conflicts({"a": "Ctrl+K", "b": "Ctrl+K", "c": "F5"}) == {"Ctrl+K": ["a", "b"]}
