"""Preparation cannot produce SETs or arbitrary parameter requests."""

import pytest

from tools.prepare_read_queries import TEMPERATURES, plan, query_candidate


def test_plan_is_offline_and_metadata_is_not_guessed():
    result = plan()
    assert result["transmission_enabled"] is False
    assert len(result["temperature_candidates"]) == 10
    assert all("frame" not in item for item in result["metadata"])


@pytest.mark.parametrize("dp", [0x0227, 0x0038, -1, 0xFFFF])
def test_non_allowlisted_requests_rejected(dp):
    with pytest.raises(ValueError):
        query_candidate(dp)


def test_query_identity_and_fixed_count():
    for dp in TEMPERATURES:
        frame = query_candidate(dp)
        assert frame[:3] == bytes.fromhex("108000")
        assert frame[3:5] == dp.to_bytes(2, "little")
        assert frame[5:10] == bytes.fromhex("0000040100")
        assert len(frame) == 12
