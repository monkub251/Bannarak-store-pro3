from app.core import compat
from app.core.paths import bundle_dir


def test_profiles_for_required_products_exist_and_are_untested_by_design():
    profiles = {p.id: p for p in compat.load_profiles(bundle_dir() / "compat_profiles")}
    assert {"bt", "ghostx", "global", "other"} <= set(profiles)
    for p in profiles.values():
        assert len(p.checks) >= 5
        assert "untested" in p.summary.lower()
        assert all(c.how for c in p.checks)


def test_profiles_make_no_compatibility_claims():
    text = " ".join(c.how + c.title for p in compat.load_profiles(bundle_dir() / "compat_profiles") for c in p.checks).lower()
    for banned in ("bypass", "evade", "undetect", "spoof", "inject", "guaranteed", "bypasses"):
        assert banned not in text


def test_bad_profile_files_are_skipped(tmp_path):
    (tmp_path / "x.json").write_text("{")
    (tmp_path / "y.json").write_text('{"id": "y"}')
    assert compat.load_profiles(tmp_path) == []
