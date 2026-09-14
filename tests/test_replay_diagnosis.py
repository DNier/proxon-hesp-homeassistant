"""Production replay results must not depend on TCP chunk boundaries."""

from tests.test_controller import FRAMES
from tools.replay_diagnosis import replay


def test_replay_chunk_invariance():
    data = b"noise" + b"".join(FRAMES.values()) * 2
    expected = replay(data, len(data))
    for chunk_size in (1, 3, 8, 13, 127):
        assert replay(data, chunk_size) == expected
    assert expected["readings"]["filter_days"]["count"] == 2
    assert expected["readings"]["device_clock"]["last"] == "00:02:16"
    assert "fan_rpm" not in expected["readings"]
