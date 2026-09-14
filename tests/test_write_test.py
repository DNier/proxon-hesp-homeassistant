"""One-shot limits with fake streams; no real gateway or heat pump writes."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import voluptuous as vol
from homeassistant.auth.const import GROUP_ID_ADMIN
from homeassistant.core import Context
from homeassistant.exceptions import ServiceValidationError, Unauthorized
from homeassistant.helpers.service import async_get_all_descriptions
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proxon_hesp.const import DOMAIN, PROFILE
from custom_components.proxon_hesp.coordinator import ProxonRuntime
from custom_components.proxon_hesp.hesp.decoder import Reading
from custom_components.proxon_hesp.services import PREPARE, SEND
from custom_components.proxon_hesp.write_test import ExperimentRejected, _target_frame


def set_value(runtime, key, value, age=0):
    runtime.values[key] = (Reading(key, value), time.monotonic() - age)


@pytest.fixture
def experiment(hass):
    runtime = ProxonRuntime(hass, "unused.test", 4196)
    writer = MagicMock()
    writer.is_closing.return_value = False
    writer.drain = AsyncMock()
    runtime.temperature_test.connection_changed(writer)
    runtime.connected = True
    set_value(runtime, "target_temperature", 21)
    set_value(runtime, "operating_mode", "comfort")
    yield runtime, writer, runtime.temperature_test
    runtime.capture.clear()
    runtime.temperature_test.close()


def arm(test, delta=0.5):
    plan = test.prepare(21, delta)
    test.prepared_at -= 11
    test.capture.monotonic_start -= 11
    return plan["confirmation_token"]


def test_frame_matches_independent_recording():
    assert _target_frame(21).hex() == "11800027020000080000a84152d0"
    assert _target_frame(19).hex() == "1180002702000008000098418acd"


@pytest.mark.parametrize("temperature", [17.5, 30.5, float("nan"), float("inf")])
def test_invalid_frame_value(temperature):
    with pytest.raises(ExperimentRejected):
        _target_frame(temperature)


@pytest.mark.parametrize(
    "expected,delta", [(20, 0.5), (21, 1), (21, 0), (float("nan"), 0.5)]
)
async def test_invalid_prepare(experiment, expected, delta):
    _, writer, test = experiment
    with pytest.raises(ExperimentRejected):
        test.prepare(expected, delta)
    writer.write.assert_not_called()
    assert test.capture.reason == "idle"


async def test_prepare_is_passive_separate_recording_and_private(experiment):
    runtime, writer, test = experiment
    runtime.capture.start()
    runtime.capture.feed(b"previous_capture")
    plan = test.prepare(21, -0.5)
    assert plan["test_temperature"] == 20.5
    assert plan["original_temperature"] == 21
    assert plan["expires_in_seconds"] == 60
    assert plan["minimum_wait_seconds"] == 10
    assert runtime.capture.size == len(b"previous_capture")
    assert test.capture.size == 0
    assert plan["confirmation_token"] not in str(runtime.diagnostics())
    assert runtime.diagnostics()["application_bytes_sent"] == 0
    writer.write.assert_not_called()


@pytest.mark.parametrize("original,delta", [(18, -0.5), (30, 0.5), (17.5, 0.5)])
async def test_bounds(experiment, original, delta):
    runtime, writer, test = experiment
    set_value(runtime, "target_temperature", original)
    with pytest.raises(ExperimentRejected):
        test.prepare(original, delta)
    writer.write.assert_not_called()


async def test_baseline_token_expiration_and_reprepare(experiment):
    _, writer, test = experiment
    plan = test.prepare(21, 0.5)
    with pytest.raises(ExperimentRejected, match="already prepared"):
        test.prepare(21, 0.5)
    for token in ("wrong", "ä", plan["confirmation_token"]):
        with pytest.raises(ExperimentRejected):
            await test.send(token)
    test.prepared_at -= 61
    assert test.diagnostics()["outcome"] == "expired"
    with pytest.raises(ExperimentRejected, match="expired"):
        await test.send(plan["confirmation_token"])
    new_plan = test.prepare(21, 0.5)
    assert new_plan["confirmation_token"] != plan["confirmation_token"]
    with pytest.raises(ExperimentRejected):
        await test.send(plan["confirmation_token"])
    writer.write.assert_not_called()


@pytest.mark.parametrize(
    "change",
    [
        "mode",
        "target",
        "stale_target",
        "stale_mode",
        "disconnect",
        "reconnect",
        "capture",
        "closing",
    ],
)
async def test_recheck_before_send(experiment, change):
    runtime, writer, test = experiment
    token = arm(test)
    if change == "mode":
        set_value(runtime, "operating_mode", "eco_summer")
    elif change == "target":
        set_value(runtime, "target_temperature", 22)
    elif change.startswith("stale"):
        key = "operating_mode" if change == "stale_mode" else "target_temperature"
        reading, _ = runtime.values[key]
        set_value(runtime, key, reading.value, age=11)
    elif change == "disconnect":
        test.connection_changed(None)
    elif change == "reconnect":
        test.connection_changed(None)
        test.connection_changed(writer)
    elif change == "closing":
        writer.is_closing.return_value = True
    else:
        test.capture.stop()
    with pytest.raises(ExperimentRejected):
        await test.send(token)
    writer.write.assert_not_called()


async def test_panel_changed_and_changed_back_invalidates(experiment):
    runtime, writer, test = experiment
    token = arm(test)
    set_value(runtime, "target_temperature", 22)
    test.observe()
    set_value(runtime, "target_temperature", 21)
    with pytest.raises(ExperimentRejected):
        await test.send(token)
    writer.write.assert_not_called()


async def test_exactly_one_write_and_no_optimistic_state(experiment):
    runtime, writer, test = experiment
    token = arm(test)
    runtime._capture_data(b"before")
    results = await asyncio.gather(
        test.send(token), test.send(token), return_exceptions=True
    )
    assert results[0]["outcome"] == "transport_flushed_unverified"
    assert isinstance(results[1], ExperimentRejected)
    writer.write.assert_called_once_with(_target_frame(21.5))
    writer.drain.assert_awaited_once()
    assert runtime.get("target_temperature").value == 21
    runtime._capture_data(b"after")
    diagnostic = runtime.diagnostics()
    assert diagnostic["application_bytes_sent"] == 14
    detail = diagnostic["target_temperature_test"]
    assert detail["write_attempts"] == 1
    assert detail["transmission_attempt"]["direction"] == "tx_attempt"
    assert detail["transmission_attempt"]["elapsed_ms"] >= 11000
    assert detail["transmission_attempt"]["hex"] == _target_frame(21.5).hex()
    assert [c["hex"] for c in detail["receive_capture"]["chunks"]] == [
        b"before".hex(),
        b"after".hex(),
    ]
    assert token not in str(diagnostic)
    test.connection_changed(None)
    test.connection_changed(writer)
    with pytest.raises(ExperimentRejected, match="consumed"):
        test.prepare(21, 0.5)


@pytest.mark.parametrize("failure", ["write", "drain", "timeout", "cancel"])
async def test_ambiguous_failures_never_retry(experiment, failure):
    _, writer, test = experiment
    token = arm(test)
    if failure == "write":
        writer.write.side_effect = OSError("failed")
    else:
        writer.drain.side_effect = {
            "drain": OSError("failed"),
            "timeout": TimeoutError(),
            "cancel": asyncio.CancelledError(),
        }[failure]
    with pytest.raises((OSError, asyncio.CancelledError)):
        await test.send(token)
    assert test.diagnostics()["outcome"] == "delivery_unknown"
    with pytest.raises(ExperimentRejected):
        await test.send(token)
    with pytest.raises(ExperimentRejected, match="consumed"):
        test.prepare(21, 0.5)
    writer.write.assert_called_once()


async def test_blocked_drain_times_out_without_retry(experiment):
    _, writer, test = experiment
    token = arm(test)
    gate = asyncio.Event()
    writer.drain.side_effect = gate.wait
    with pytest.raises(TimeoutError):
        await test.send(token)
    with pytest.raises(ExperimentRejected):
        await test.send(token)
    assert test.outcome == "delivery_unknown"
    writer.write.assert_called_once()


async def test_clear_disarms_but_never_resets_attempt_allowance(experiment):
    _, writer, test = experiment
    token = arm(test)
    test.stop_capture(clear=True)
    with pytest.raises(ExperimentRejected):
        await test.send(token)
    writer.write.assert_not_called()
    token = arm(test)
    await test.send(token)
    test.stop_capture(clear=True)
    assert test.capture.reason == "idle"
    assert test.tx is None and test.original is None and test.requested is None
    assert test.bytes_offered == 14 and test.attempts == 1
    with pytest.raises(ExperimentRejected, match="consumed"):
        test.prepare(21, 0.5)


async def test_real_runtime_and_admin_services_use_existing_stream(hass, frames):
    reader = asyncio.StreamReader()
    reader.feed_data(frames["0xe1"])
    writer = MagicMock()
    writer.is_closing.return_value = False
    writer.wait_closed = AsyncMock()
    writer.drain = AsyncMock()
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="PROXON",
        unique_id="test-unit",
        data={"host": "private.test", "port": 4196, "profile": PROFILE},
    )
    entry.add_to_hass(hass)
    admin = await hass.auth.async_create_user("Test admin", group_ids=[GROUP_ID_ADMIN])
    user = await hass.auth.async_create_user("Non-admin")
    context = Context(user_id=admin.id)
    data = {"config_entry_id": entry.entry_id, "expected_temperature": 21, "delta": 0.5}

    async def call(name, data, context=context, response=True):
        return await hass.services.async_call(
            DOMAIN, name, data, blocking=True, return_response=response, context=context
        )

    with patch("asyncio.open_connection", return_value=(reader, writer)) as connect:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        runtime = entry.runtime_data
        test = runtime.temperature_test
        assert test.writer is writer
        set_value(runtime, "target_temperature", 21)
        set_value(runtime, "operating_mode", "comfort")
        for name in (PREPARE, SEND):
            assert hass.services.has_service(DOMAIN, name)
        descriptions = (await async_get_all_descriptions(hass))[DOMAIN]
        assert descriptions[PREPARE]["fields"]["config_entry_id"]["selector"] == {
            "config_entry": {"integration": DOMAIN}
        }
        assert "confirmation_token" in descriptions[SEND]["fields"]
        writer.write.assert_not_called()
        with pytest.raises(Unauthorized):
            await call(PREPARE, data, Context(user_id=user.id))
        with pytest.raises(ServiceValidationError, match="administrator"):
            await call(PREPARE, data, Context())
        with pytest.raises(ServiceValidationError, match="response"):
            await call(PREPARE, data, response=False)
        with pytest.raises(ServiceValidationError, match="loaded"):
            await call(PREPARE, {**data, "config_entry_id": "missing"})
        with pytest.raises(vol.Invalid):
            await call(PREPARE, {**data, "hex": "arbitrary"})
        assert test.capture.reason == "idle"
        plan = await call(PREPARE, data)
        writer.write.assert_not_called()
        test.prepared_at -= 11
        send_data = {
            "config_entry_id": entry.entry_id,
            "confirmation_token": plan["confirmation_token"],
        }
        with pytest.raises(Unauthorized):
            await call(SEND, send_data, Context(user_id=user.id))
        writer.write.assert_not_called()
        result = await call(SEND, send_data)
        assert result["outcome"] == "transport_flushed_unverified"
        connect.assert_awaited_once_with("private.test", 4196)
        writer.write.assert_called_once_with(_target_frame(21.5))
        assert runtime.get("target_temperature").value == 21
        with pytest.raises(ServiceValidationError):
            await call(SEND, send_data)
        assert await hass.config_entries.async_unload(entry.entry_id)
        assert test.token is None and test.writer is None
        assert test.capture.timer is None
        writer.close.assert_called_once()
        with pytest.raises(ServiceValidationError, match="loaded"):
            await call(PREPARE, data)
