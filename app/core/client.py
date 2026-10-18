"""HTTP client for the fmcc_control resource. Uses only the standard library."""
from __future__ import annotations

import json
import socket
import ssl
import urllib.error
import urllib.request
from typing import Any

MAX_RESPONSE = 2 * 1024 * 1024

HINTS = {
    "no_token": "Open Interface, pick your profile and paste the token from the server's config.lua.",
    "unauthorized": "The server rejected the token. Copy it again from config.lua; it must match exactly.",
    "locked": "Too many failed logins from this PC. Wait a minute, then fix the token before retrying.",
    "forbidden": "Your role may not run this action. Ask the server owner to adjust Config.Roles.",
    "module_disabled": "Enable the module in Config.Modules on the server and restart the resource.",
    "not_configured": "Set a token of 24+ characters in the server's config.lua and restart the resource.",
    "rate_limited": "Slow down; the server limits requests per address.",
    "unreachable": "Check the address and port, that the server is running, and that the port is reachable from this PC.",
    "timeout": "The server did not answer in time. Check the address or raise the timeout in Interface.",
    "tls": "The certificate could not be verified. Fix the certificate or turn off 'Verify TLS' for a test server.",
    "bad_response": "The address answered, but not like fmcc_control. Check the resource name and that it is started.",
    "not_found": "The resource is not started or the resource name in this profile is wrong.",
}


class ApiError(Exception):
    def __init__(self, code: str, message: str, status: int | None = None):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status

    @property
    def hint(self) -> str:
        return HINTS.get(self.code, "")

    @property
    def is_network(self) -> bool:
        return self.code in ("unreachable", "timeout", "tls", "bad_response", "not_found")

    def __str__(self) -> str:
        return f"{self.message} {self.hint}".strip()


class ApiClient:
    def __init__(self, server_url: str, resource: str, token: str, timeout: float = 6.0, verify_tls: bool = True):
        self.server_url, self.resource, self.token = server_url.rstrip("/"), resource, token
        self.timeout, self.verify_tls = timeout, verify_tls

    def __repr__(self) -> str:  # never leak the token into logs
        return f"ApiClient({self.endpoint!r}, token={'set' if self.token else 'missing'})"

    @property
    def endpoint(self) -> str:
        return f"{self.server_url}/{self.resource}/api"

    def _context(self):
        if not self.endpoint.startswith("https"):
            return None
        ctx = ssl.create_default_context()
        if not self.verify_tls:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        return ctx

    def call(self, action: str, params: dict | None = None) -> Any:
        if not self.token:
            raise ApiError("no_token", "No token is set for this profile.")
        body = json.dumps({"action": action, "params": params or {}}).encode()
        request = urllib.request.Request(
            self.endpoint, data=body, method="POST",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.token}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout, context=self._context()) as resp:
                raw, status = resp.read(MAX_RESPONSE), resp.status
        except urllib.error.HTTPError as exc:
            raw, status = exc.read(MAX_RESPONSE), exc.code
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, ssl.SSLError):
                raise ApiError("tls", f"TLS error: {reason}.") from None
            if isinstance(reason, (socket.timeout, TimeoutError)):
                raise ApiError("timeout", "The server timed out.") from None
            if isinstance(reason, ConnectionRefusedError):
                raise ApiError("unreachable", "Connection refused.") from None
            raise ApiError("unreachable", f"Could not reach the server ({reason}).") from None
        except (socket.timeout, TimeoutError):
            raise ApiError("timeout", "The server timed out.") from None
        except (OSError, ValueError) as exc:
            raise ApiError("unreachable", f"Could not reach the server ({exc}).") from None

        try:
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError
        except ValueError:
            code = "not_found" if status == 404 else "bad_response"
            raise ApiError(code, f"Unexpected reply (HTTP {status}).", status) from None
        if payload.get("ok") is True:
            return payload.get("data")
        err = payload.get("error") if isinstance(payload.get("error"), dict) else {}
        raise ApiError(str(err.get("code", "error")), str(err.get("message", "The server reported an error.")), status)
