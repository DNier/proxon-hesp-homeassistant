"""Independent installation's wire samples protect existing decoding boundaries.

Numeric agreement is not independent confirmation of units or BDE semantics.
Provenance: docs/COMMUNITY_EXPORT_ANALYSIS.md.
"""

import json
from pathlib import Path

import pytest

from custom_components.proxon_hesp.hesp.checksum import checksum
from custom_components.proxon_hesp.hesp.decoder import Decoder
from tools.inventory_capture import inventory

FRAMES = json.loads(
    (Path(__file__).parent / "fixtures/community_frames.json").read_text()
)


@pytest.mark.parametrize("raw", FRAMES.values())
def test_independent_wire_samples_have_original_valid_checksums(raw):
    frame = bytes.fromhex(raw)
    assert checksum(frame[:-2]) == int.from_bytes(frame[-2:], "little")


def test_other_installation_fan_values_do_not_define_a_global_level_mapping():
    decoder = Decoder()
    values = {
        r.key: r.value for r in decoder.feed(bytes.fromhex(FRAMES["fan_controls"]))
    }
    assert values == {"fan_supply_control": 7000.0, "fan_extract_control": 7000.0}
    assert {
        r.key: r.value for r in decoder.feed(bytes.fromhex(FRAMES["fan_level"]))
    } == {"fan_level": 3}


def test_metadata_type_does_not_enable_unknown_two_byte_value():
    # 022C and 0227 share metadata type 0204, but observed widths differ.
    frame = bytes.fromhex(FRAMES["metadata_type_counterexample"])
    result = inventory([{"elapsed_ms": 0, "hex": frame.hex()}])
    assert result["groups"]["118000/0x022C/2"]["values"] == ["0100"]
    assert Decoder().feed(frame) == []


@pytest.mark.parametrize("key,size", [("counter_block", 112), ("counter_tail", 40)])
def test_complete_counter_blocks_remain_offline_evidence(key, size):
    result = inventory([{"elapsed_ms": 0, "hex": FRAMES[key]}])
    assert result["frames"] == 1
    assert result["unparsed_bytes"] == 0
    assert next(iter(result["groups"].values()))["payload_bytes"] == size
    assert Decoder().feed(bytes.fromhex(FRAMES[key])) == []
