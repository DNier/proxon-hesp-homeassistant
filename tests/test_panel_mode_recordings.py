"""Original P 2H-L mode frames corroborate labels without assigning PTC states."""

import json
from pathlib import Path

import pytest

from custom_components.proxon_hesp.hesp.checksum import checksum
from custom_components.proxon_hesp.hesp.decoder import Decoder

SOURCE = json.loads(
    (Path(__file__).parent / "fixtures/panel_modes_recorded.json").read_text()
)
FRAMES = {row["label"]: bytes.fromhex(row["hex"]) for row in SOURCE["frames"]}


@pytest.mark.parametrize("frame", FRAMES.values(), ids=FRAMES.keys())
def test_original_frame_checksum_and_length(frame):
    assert checksum(frame[:-2]) == int.from_bytes(frame[-2:], "little")
    assert len(frame) == 10 + frame[7] // 2
    assert frame[5:7] == b"\x00\x00"


@pytest.mark.parametrize(
    ("mode", "wire_value"),
    [("eco_summer", 1), ("eco_winter", 2), ("stove", 4), ("comfort", 3), ("off", 0)],
)
def test_existing_mode_labels_match_original_bde_selection(mode, wire_value):
    request = FRAMES[f"{mode}_mode_set"]
    reply = FRAMES[f"{mode}_mode_ack"]
    assert request[:8] == bytes.fromhex("1180000a02000004")
    assert int.from_bytes(request[8:-2], "little") == wire_value
    assert reply[:8] == bytes.fromhex("2340000a02000000")
    assert Decoder().feed(reply) == []
    readings = Decoder().feed(request + reply)
    assert {reading.key: reading.value for reading in readings} == {
        "operating_mode": mode
    }


def test_recorded_zero_and_one_states_remain_exact_raw_identities():
    for phase, payload in (
        ("eco_winter", "00"),
        ("stove", "01"),
        ("comfort", "00"),
    ):
        suffix = "_cleared" if phase == "comfort" else ""
        for name, header, dp, size, key in (
            ("node30", "118007", "9101", 2, "raw_118007_0191"),
            ("controller", "118000", "b603", 4, "raw_118000_03b6"),
        ):
            frame = FRAMES[f"{phase}_{name}_state{suffix}"]
            assert frame[:5] == bytes.fromhex(header + dp)
            assert frame[7] == size * 2
            readings = Decoder().feed(frame)
            assert {reading.key: reading.value for reading in readings} == {
                key: payload + "00" * (size - 1)
            }


def test_selected_state_clear_frames_precede_off_without_timing_claim():
    labels = list(FRAMES)
    for label in (
        "comfort_controller_state_cleared",
        "comfort_node30_state_cleared",
    ):
        assert labels.index("comfort_mode_set") < labels.index(label)
        assert labels.index(label) < labels.index("off_mode_set")
    assert "elapsed_ms" not in json.dumps(SOURCE)


def test_zero_flags_and_unmapped_022c_add_no_heat_element_semantics():
    flags = FRAMES["panel_flags_zero"]
    assert flags[:8] == bytes.fromhex("118000f801000008")
    assert {reading.key: reading.value for reading in Decoder().feed(flags)} == {
        "intensive_ventilation": False,
        "raw_118000_01f8": "00000000",
    }
    state = FRAMES["unmapped_panel_state_zero"]
    assert state[:8] == bytes.fromhex("1180002c02000004")
    assert Decoder().feed(state) == []
