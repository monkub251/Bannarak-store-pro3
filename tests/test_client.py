import pytest

from app.core.client import ApiClient, ApiError
from tests.mock_server import MockServer, TOKEN


def client(srv, token=TOKEN, **kw):
    return ApiClient(srv.url, "fmcc_control", token, **kw)


def test_success_sends_bearer_and_json():
    with MockServer() as srv:
        data = client(srv).call("player.heal", {"target": 3})
        req = srv.requests[0]
        assert data == {"action": "player.heal", "echo": {"target": 3}}
        assert req["path"] == "/fmcc_control/api"
        assert req["auth"] == f"Bearer {TOKEN}"
        assert req["body"] == {"action": "player.heal", "params": {"target": 3}}


def test_missing_token_never_hits_network():
    with MockServer() as srv:
        with pytest.raises(ApiError) as e:
            client(srv, token="").call("diag.status")
        assert e.value.code == "no_token" and srv.requests == []
        assert "Interface" in e.value.hint


def test_unauthorized_has_actionable_hint():
    with MockServer() as srv:
        with pytest.raises(ApiError) as e:
            client(srv, token="wrong").call("diag.status")
        assert e.value.code == "unauthorized" and e.value.status == 401
        assert "config.lua" in str(e.value) and not e.value.is_network


def test_forbidden_and_action_failed_codes():
    with MockServer() as srv:
        with pytest.raises(ApiError) as e:
            client(srv).call("players.kick", {"target": 1})
        assert e.value.code == "forbidden" and "Config.Roles" in e.value.hint
        with pytest.raises(ApiError) as e2:
            client(srv).call("vehicle.spawn", {"target": 9})
        assert e2.value.code == "action_failed" and "not online" in e2.value.message


def test_html_404_means_resource_not_started():
    with MockServer() as srv:
        srv.mode = "html404"
        with pytest.raises(ApiError) as e:
            client(srv).call("diag.status")
        assert e.value.code == "not_found" and e.value.is_network


def test_non_json_reply():
    with MockServer() as srv:
        srv.mode = "garbage"
        with pytest.raises(ApiError) as e:
            client(srv).call("diag.status")
        assert e.value.code == "bad_response"


def test_connection_refused():
    srv = MockServer()
    url = srv.url
    srv.server_close()
    with pytest.raises(ApiError) as e:
        ApiClient(url, "fmcc_control", TOKEN, timeout=2).call("diag.status")
    # Linux refuses instantly ("unreachable"); Windows retries until the timeout ("timeout"). Both are network errors with hints.
    assert e.value.code in ("unreachable", "timeout") and e.value.is_network and e.value.hint


def test_timeout():
    with MockServer() as srv:
        srv.mode = "slow"
        with pytest.raises(ApiError) as e:
            client(srv, timeout=0.3).call("diag.status")
        assert e.value.code == "timeout"


def test_repr_hides_token():
    assert TOKEN not in repr(ApiClient("http://x", "r", TOKEN))
