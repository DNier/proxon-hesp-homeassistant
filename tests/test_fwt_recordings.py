"""Minimal original FWT 2-L samples; no private capture metadata.

Source: community diagnostic export linked in docs/COMPATIBILITY.md.
"""

import json
from pathlib import Path

import pytest

from custom_components.proxon_hesp.hesp.checksum import checksum
from custom_components.proxon_hesp.hesp.decoder import Decoder
from tools.audit_fan_curves import audit_fan_curves
from tools.inventory_capture import inventory

FRAMES = json.loads((Path(__file__).parent / "fixtures/fwt_frames.json").read_text())


@pytest.mark.parametrize("raw", FRAMES.values())
def test_fwt_original_checksums_and_fragmentation(raw):
    frame = bytes.fromhex(raw)
    assert checksum(frame[:-2]) == int.from_bytes(frame[-2:], "little")
    expected = {r.key: r.value for r in Decoder().feed(frame)}
    for split in range(len(frame) + 1):
        decoder = Decoder()
        actual = decoder.feed(frame[:split]) + decoder.feed(frame[split:])
        assert {r.key: r.value for r in actual} == expected
    damaged = frame[:-1] + bytes([frame[-1] ^ 1])
    assert Decoder().feed(damaged) == []


def test_fwt_known_values_and_asymmetric_curves():
    readings = Decoder().feed(bytes.fromhex("".join(FRAMES.values())))
    assert {r.key: r.value for r in readings} == {
        "operating_mode": "comfort",
        "fan_level": 3,
        "fan_supply_control": 7000.0,
        "fan_extract_control": 6700.0,
    }
    result = audit_fan_curves(
        {
            "00d2": FRAMES["curve_a"],
            "00d3": FRAMES["curve_b"],
            "observations": [FRAMES["controls"]],
        }
    )
    assert result["observations"][0]["common_candidate_positions"] == [3]
    assert result["semantics"] == "numerical_candidates_not_actual_fan_levels"


def test_fwt_same_dp_other_header_is_not_a_panel_flag():
    raw = FRAMES["other_header"]
    result = inventory([{"elapsed_ms": 0, "hex": raw}])
    assert result["groups"]["118002/0x01F8/4"]["values"] == ["80ccccbf"]
    assert Decoder().feed(bytes.fromhex(raw)) == []
