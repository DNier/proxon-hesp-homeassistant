"""Offline numerical matches must not turn exceptions into actual fan levels."""

import json
import struct
from pathlib import Path

import pytest

from custom_components.proxon_hesp.hesp.checksum import checksum
from tools.audit_fan_curves import audit_fan_curves


def recorded():
    return json.loads(
        (Path(__file__).parent / "fixtures/fan_curve_replies.json").read_text()
    )


def frame(dp, values):
    payload = struct.pack(f"<{len(values)}f", *values)
    body = bytes.fromhex("224000") + dp.to_bytes(2, "little")
    body += b"\x00\x00" + bytes([2 * len(payload)]) + payload
    return (body + checksum(body).to_bytes(2, "little")).hex()


def test_recorded_pairs_match_only_joint_curve_positions():
    result = audit_fan_curves(recorded())
    assert [r["common_candidate_positions"] for r in result["observations"]] == [
        [3],
        [2],
        [],
        [1],
        [],
        [4],
    ]
    assert result["observations"][4]["channel_candidate_positions"] == [[4], [3]]
    assert result["semantics"] == "numerical_candidates_not_actual_fan_levels"


def test_duplicate_curve_entries_are_ambiguous_not_first_match():
    data = recorded()
    for dp in (0xD2, 0xD3):
        data[f"{dp:04x}"] = frame(dp, [25, 50, 50, 100])
    data["observations"] = [frame(0xD7, [5000, 5000])]
    value = audit_fan_curves(data)["observations"][0]
    assert value["common_candidate_positions"] == [2, 3]
    assert value["result"] == "ambiguous_match"


def test_no_nearest_level_rounding():
    data = recorded()
    data["observations"] = [frame(0xD7, [6900, 7000])]
    assert audit_fan_curves(data)["observations"][0]["result"] == "no_common_match"


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1, 101])
def test_invalid_curve_values_rejected(bad):
    data = recorded()
    data["00d2"] = frame(0xD2, [25, 50, bad, 100])
    with pytest.raises(ValueError):
        audit_fan_curves(data)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1, 10001])
def test_invalid_control_values_rejected(bad):
    data = recorded()
    data["observations"] = [frame(0xD7, [bad, 5000])]
    with pytest.raises(ValueError):
        audit_fan_curves(data)


@pytest.mark.parametrize(
    "mutation", ["missing", "truncated", "wrong_dp", "crc", "empty", "extra", "size"]
)
def test_malformed_or_unsupported_input_rejected(mutation):
    data = recorded()
    if mutation == "missing":
        del data["00d2"]
    elif mutation == "truncated":
        data["00d2"] = data["00d2"][:-2]
    elif mutation == "wrong_dp":
        data["00d2"] = data["00d3"]
    elif mutation == "crc":
        data["00d2"] = data["00d2"][:-2] + "ff"
    elif mutation == "empty":
        data["observations"] = []
    elif mutation == "extra":
        data["00d2"] += data["00d3"]
    else:
        data["00d2"] = frame(0xD2, [25, 50])
    with pytest.raises(ValueError):
        audit_fan_curves(data)
