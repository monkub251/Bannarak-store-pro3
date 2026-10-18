import logging

from app.core import logging_setup
from app.core.audit import AuditLog, redact


def test_redact_hides_secrets_recursively():
    out = redact({"token": "abc", "nested": {"Password": "p", "ok": 1}, "list": [{"secret": "s"}], "long": "x" * 500})
    assert out["token"] == "[hidden]" and out["nested"]["Password"] == "[hidden]"
    assert out["list"][0]["secret"] == "[hidden]" and out["nested"]["ok"] == 1
    assert len(out["long"]) < 300


def test_audit_roundtrip_newest_first(tmp_path):
    log = AuditLog(tmp_path / "a.jsonl")
    log.add("p", "player.heal", {"target": 1, "token": "zzz"}, True)
    log.add("p", "vehicle.spawn", {"target": 2}, False, "player 2 is not online")
    entries = log.tail(10)
    assert [e["action"] for e in entries] == ["vehicle.spawn", "player.heal"]
    assert entries[1]["params"]["token"] == "[hidden]"
    assert "zzz" not in (tmp_path / "a.jsonl").read_text()


def test_audit_skips_corrupt_lines(tmp_path):
    p = tmp_path / "a.jsonl"
    p.write_text('{"time":"t","profile":"p","action":"a","params":{},"ok":true,"message":""}\nGARBAGE\n')
    assert len(AuditLog(p).tail()) == 1


def test_log_redacts_tokens_in_file_and_ring(tmp_path):
    ring = logging_setup.setup(tmp_path / "logs")
    logging.getLogger("fmcc.test").warning("sending Authorization: Bearer SUPERSECRETTOKEN123 now")
    logging.getLogger("fmcc.test").warning('config token="ANOTHERSECRET" saved')
    for h in logging.getLogger("fmcc").handlers:
        h.flush()
    text = (tmp_path / "logs" / "app.log").read_text()
    assert "SUPERSECRETTOKEN123" not in text and "ANOTHERSECRET" not in text
    assert all("SUPERSECRET" not in m and "ANOTHERSECRET" not in m for _, _, m in ring.records)
    assert "[hidden]" in text
