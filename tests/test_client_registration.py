"""Tests for ThinQ APIv2 client registration and 9006/9012 recovery (CMCore 1982)."""

from __future__ import annotations

import pytest

from custom_components.smartthinq_sensors.wideq import core_exceptions as exc
from custom_components.smartthinq_sensors.wideq.core_async import (
    V2_GATEWAY_URL,
    CoreAsync,
)


class _FakeResp:
    def __init__(self, payload: dict, status: int = 200):
        self._payload = payload
        self.status = status

    async def json(self):
        return self._payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class _FakeSession:
    def __init__(self, handlers):
        self._handlers = list(handlers)
        self.calls: list[tuple[str, str, dict, dict | None]] = []

    def get(self, url, headers=None, **kwargs):
        fn = self._handlers.pop(0)
        self.calls.append(("GET", url, dict(headers or {}), None))
        return fn("GET", url, headers, None)

    def post(self, url, json=None, headers=None, **kwargs):
        fn = self._handlers.pop(0)
        self.calls.append(("POST", url, dict(headers or {}), json))
        return fn("POST", url, headers, json)

    async def close(self):
        return None


async def test_gateway_info_skips_client_registration():
    """Unauthenticated gateway discovery does not call /service/users/client."""
    sess = _FakeSession(
        [
            lambda *a: _FakeResp(
                {"resultCode": "0000", "result": {"empOauthBaseUri": "https://emp.example"}}
            )
        ]
    )
    core = CoreAsync("US", "en-US", session=sess, client_id="initial-cid")
    res = await core.thinq2_get(V2_GATEWAY_URL)
    assert res == {"empOauthBaseUri": "https://emp.example"}
    assert len(sess.calls) == 1
    assert sess.calls[0][0] == "GET"


async def test_thinq2_get_registers_client_once_and_reuses():
    """Authenticated APIv2 GET registers x-client-id once via /service/users/client and reuses it."""
    sess = _FakeSession(
        [
            lambda *a: _FakeResp({"resultCode": "0000", "result": ""}),
            lambda *a: _FakeResp({"resultCode": "0000", "result": {"item": [{"homeId": "h1"}]}}),
            lambda *a: _FakeResp({"resultCode": "0000", "result": {"devices": []}}),
        ]
    )
    callbacks: list[str] = []
    core = CoreAsync(
        "US",
        "en-US",
        session=sess,
        client_id="saved-cid",
        update_clientid_callback=callbacks.append,
    )
    r1 = await core.thinq2_get(
        "https://aic-service.lgthinq.com:46030/v1/service/homes",
        access_token="tok",
        user_number="USR1",
    )
    r2 = await core.thinq2_get(
        "https://aic-service.lgthinq.com:46030/v1/service/homes/h1",
        access_token="tok",
        user_number="USR1",
    )
    assert r1 == {"item": [{"homeId": "h1"}]}
    assert r2 == {"devices": []}
    assert [c[1] for c in sess.calls] == [
        "https://aic-service.lgthinq.com:46030/v1/service/users/client",
        "https://aic-service.lgthinq.com:46030/v1/service/homes",
        "https://aic-service.lgthinq.com:46030/v1/service/homes/h1",
    ]
    assert sess.calls[1][2]["x-client-id"] == "saved-cid"
    assert sess.calls[2][2]["x-client-id"] == "saved-cid"
    assert callbacks == []


async def test_lgedm2_post_control_sync_recovers_from_9006():
    """Control POST retries with a newly registered unique client_id when LG returns 9006."""
    sess = _FakeSession(
        [
            # Initial client registration succeeds
            lambda *a: _FakeResp({"resultCode": "0000", "result": ""}),
            # First control-sync gets 9006 unofficial API rejection
            lambda *a: _FakeResp(
                {
                    "resultCode": "9006",
                    "result": "Please consider using the official API.",
                },
                status=400,
            ),
            # Re-registration with freshly minted client_id succeeds
            lambda *a: _FakeResp({"resultCode": "0000", "result": ""}),
            # Retried control-sync succeeds
            lambda *a: _FakeResp({"resultCode": "0000", "result": {"status": "ok"}}),
        ]
    )
    callbacks: list[str] = []
    core = CoreAsync(
        "US",
        "en-US",
        session=sess,
        client_id="stale-cid",
        update_clientid_callback=callbacks.append,
    )
    out = await core.lgedm2_post(
        "https://aic-service.lgthinq.com:46030/v1/service/devices/dev1/control-sync",
        data={"ctrlKey": "vtCtrl", "command": "Set"},
        access_token="tok",
        user_number="USR1",
        is_api_v2=True,
    )
    assert out == {"status": "ok"}
    assert len(callbacks) == 1
    new_cid = callbacks[0]
    assert new_cid != "stale-cid"
    assert sess.calls[1][2]["x-client-id"] == "stale-cid"
    assert sess.calls[2][2]["x-client-id"] == new_cid
    assert sess.calls[3][2]["x-client-id"] == new_cid


async def test_burnt_persisted_client_id_rotates_on_users_client_9006():
    """If persisted client_id gets 9006 during /service/users/client, a fresh one is minted and registered."""
    sess = _FakeSession(
        [
            lambda *a: _FakeResp(
                {"resultCode": "9006", "result": "Please consider using the official API."},
                status=400,
            ),
            lambda *a: _FakeResp({"resultCode": "0000", "result": ""}),
            lambda *a: _FakeResp({"resultCode": "0000", "result": {"item": []}}),
        ]
    )
    callbacks: list[str] = []
    core = CoreAsync(
        "US",
        "en-US",
        session=sess,
        client_id="burnt-cid",
        update_clientid_callback=callbacks.append,
    )
    res = await core.thinq2_get(
        "https://aic-service.lgthinq.com:46030/v1/service/homes",
        access_token="tok",
        user_number="USR1",
    )
    assert res == {"item": []}
    assert len(callbacks) == 1
    assert sess.calls[2][2]["x-client-id"] == callbacks[0]


async def test_dict_9006_raises_failed_request_without_burning_client_id():
    """A dict payload on 9006 (device/command rejection) raises FailedRequestError without rotating client_id."""
    sess = _FakeSession(
        [
            lambda *a: _FakeResp({"resultCode": "0000", "result": ""}),
            lambda *a: _FakeResp(
                {"resultCode": "9006", "result": {"data": "", "voiceData": None}},
                status=400,
            ),
        ]
    )
    callbacks: list[str] = []
    core = CoreAsync(
        "US",
        "en-US",
        session=sess,
        client_id="valid-cid",
        update_clientid_callback=callbacks.append,
    )
    with pytest.raises(exc.FailedRequestError):
        await core.lgedm2_post(
            "https://aic-service.lgthinq.com:46030/v1/service/devices/dev1/control-sync",
            data={"ctrlKey": "badKey", "command": "Set"},
            access_token="tok",
            user_number="USR1",
            is_api_v2=True,
        )
    assert callbacks == []
    assert len(sess.calls) == 2
