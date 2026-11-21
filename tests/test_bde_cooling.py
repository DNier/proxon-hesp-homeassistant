"""Synthetic wire sequences for the bounded P2 cooling label."""

import struct
from types import SimpleNamespace

import pytest

from custom_components.proxon_hesp import coordinator
from custom_components.proxon_hesp.bde_display import BdeDisplay
from custom_components.proxon_hesp.const import PROFILE
from custom_components.proxon_hesp.coordinator import ProxonRuntime
from custom_components.proxon_hesp.hesp.checksum import checksum
from custom_components.proxon_hesp.hesp.decoder import Decoder
from custom_components.proxon_hesp.sensor import DESCRIPTIONS


def frame(header, payload):
    body = bytes.fromhex(header) + payload
    return body + checksum(body).to_bytes(2, "little")


MODE = frame("1180000a02000004", bytes.fromhex("0300"))
WINTER = frame("1180000a02000004", bytes.fromhex("0200"))
STATUS = frame("2240000802000008", bytes.fromhex("22150080"))
VALVES = frame("2240006c00000008", bytes.fromhex("27020000"))
RPM = frame("2240001c05000008", struct.pack("<f", 2025))
COOLING = (MODE, STATUS, VALVES, RPM)


def receiver(display):
    clock = SimpleNamespace(now=0.0)
    decoder = Decoder(
        lambda source, readings: display.observe(source, readings, clock.now)
    )

    def feed(at, frames):
        clock.now = at
        decoder.feed(b"".join(frames))

    return feed


def run_cycles(feed, frames, start=0):
    for delta in (0, 5, 10, 15, 20):
        feed(start + delta, frames)


def test_cooling_requires_15s_fresh_receipts_and_expires():
    display = BdeDisplay(p2_reference=True)
    feed = receiver(display)
    for at in (0, 5, 10, 14.999):
        feed(at, COOLING)
        assert display.value(at) is None
    assert display.value(15) is None
    feed(15, COOLING)
    assert display.value(15) == "cooling"
    assert display.value(21) == "cooling"
    assert display.value(21.001) is None
    assert display.expire(21.001)
    feed(21.002, COOLING)
    assert display.value(21.002) is None


@pytest.mark.parametrize(
    ("which", "replacement"),
    [
        (0, WINTER),
        (1, frame("2240000802000008", bytes.fromhex("22110080"))),
        (1, frame("2240000802000008", bytes.fromhex("1a130080"))),
        (1, frame("2240010802000008", bytes.fromhex("22150080"))),
        (1, STATUS[:-1] + bytes([STATUS[-1] ^ 1])),
        (2, frame("2240006c00000008", bytes.fromhex("25020000"))),
        (2, frame("2240006c00000008", bytes.fromhex("27000000"))),
        (3, frame("2240001c05000008", struct.pack("<f", 0))),
        (3, frame("2240001c05000008", struct.pack("<f", float("nan")))),
    ],
)
def test_cooling_rejects_nearby_contexts(which, replacement):
    display = BdeDisplay(p2_reference=True)
    feed = receiver(display)
    frames = list(COOLING)
    frames[which] = replacement
    run_cycles(feed, frames)
    assert display.value(20) is None


def test_mode_epoch_requires_each_new_source_in_wire_order():
    display = BdeDisplay(p2_reference=True)
    feed = receiver(display)
    run_cycles(feed, COOLING)
    assert display.value(20) == "cooling"
    feed(21, (WINTER, STATUS, VALVES, RPM, MODE))
    assert display.value(21) is None
    # Feed the final required receipt in the next clock step. Qualification
    # starts with that receipt, despite the preceding TCP chunk's equal times.
    feed(21.5, (STATUS, VALVES, RPM))
    for at in (26, 31, 36):
        feed(at, COOLING)
    assert display.value(36) is None
    feed(36.5, COOLING)
    assert display.value(36.5) == "cooling"
    display.reset()
    feed(37, COOLING)
    assert display.value(37) is None


@pytest.mark.parametrize(
    ("profile", "p2_reference_display", "expected"),
    [
        (PROFILE, False, None),
        (PROFILE, True, "cooling"),
        ("unspecified_variant", True, None),
    ],
)
def test_runtime_profile_connected_state_and_enum(
    profile, p2_reference_display, expected, hass, monkeypatch
):
    runtime = ProxonRuntime(
        hass,
        "offline.invalid",
        4196,
        profile=profile,
        p2_reference_display=p2_reference_display,
    )
    feed = receiver(runtime.bde_display)
    run_cycles(feed, COOLING)
    assert runtime.get_bde_operating_display() is None
    runtime.connected = True
    monkeypatch.setattr(coordinator, "time", SimpleNamespace(monotonic=lambda: 20))
    assert runtime.get_bde_operating_display() == expected
    options = next(d.options for d in DESCRIPTIONS if d.key == "bde_operating_display")
    assert options == ["heating", "blank", "cooling"]
