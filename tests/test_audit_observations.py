"""Observation correlation must retain repetitions, counterexamples and gaps."""

import json

import pytest

from custom_components.proxon_hesp.hesp.checksum import checksum
from tools.audit_observations import audit, main, render

IDENTITY = "998009/0xFFFF/1"


def frame(value, *, header="998009"):
    body = bytes.fromhex(header + "ffff000002") + bytes([value])
    return body + checksum(body).to_bytes(2, "little")


def capture(states=("Auto", "Manual", "Auto", "Manual"), *, varying=False):
    chunks = []
    for index, state in enumerate(states):
        for second in range(6):
            value = (64 if state == "Manual" else 0) | (second % 2 if varying else 0)
            chunks.append(
                {"elapsed_ms": index * 6000 + second * 1000, "hex": frame(value).hex()}
            )
    return {
        "actual_duration_seconds": len(states) * 6,
        "chunks": chunks,
        "observations": [
            {"elapsed_ms": index * 6000, "label": "BDE selection", "observation": state}
            for index, state in enumerate(states)
        ],
    }


def candidates(source):
    return audit(source, settle_ms=0, max_gap_ms=4000)["labels"]["BDE selection"][
        "candidates"
    ]


def test_repeated_complete_unknown_identity_payload_and_bit_candidates():
    report = audit(capture(), settle_ms=0, max_gap_ms=4000)
    result = report["labels"]["BDE selection"]
    assert result["state_interval_counts"] == {"Auto": 2, "Manual": 2}
    assert {item["identity"] for item in result["candidates"]} == {IDENTITY}
    assert {item["feature"] for item in result["candidates"]} == {
        "payload",
        "byte[0].bit[6]",
    }
    assert all(item["status"] == "repeatable" for item in result["candidates"])
    assert all(item["supporting_interval_count"] == 4 for item in result["candidates"])
    payload = next(
        item for item in result["candidates"] if item["feature"] == "payload"
    )
    assert payload["values_by_observation"] == {"Auto": "00", "Manual": "40"}
    assert "baseline" in render(report)
    assert "transition_count" not in result["intervals"][0]["groups"][IDENTITY]


def test_changing_payload_can_have_constant_candidate_bit():
    result = candidates(capture(varying=True))
    assert [item["feature"] for item in result] == ["byte[0].bit[6]"]
    assert result[0]["values_by_observation"] == {"Auto": 0, "Manual": 1}


def test_every_state_needs_two_repeated_reference_intervals():
    source = capture(("Auto", "Manual", "Auto"))
    report = audit(source, settle_ms=0, max_gap_ms=4000)
    result = report["labels"]["BDE selection"]
    assert result["status"] == "insufficient_references"
    assert not result["candidates"]
    assert (
        result["intervals"][0]["groups"][IDENTITY]["status"] == "coverage_not_checked"
    )
    # No annotations means no fabricated baseline or unchanged equipment state.
    del source["observations"]
    assert audit(source)["labels"] == {}


def test_missing_interval_remains_partial_with_enough_other_repetitions():
    source = capture(("Auto", "Manual") * 3)
    for chunk in source["chunks"]:
        if 6000 <= chunk["elapsed_ms"] < 12000:
            chunk["hex"] = frame(17, header="998008").hex()
    result = candidates(source)
    assert result
    assert all(item["status"] == "partial" for item in result)
    assert all(item["uncertain_interval_indexes"] == [1] for item in result)
    assert all(item["supporting_interval_count"] == 5 for item in result)


def test_single_valid_counterexample_is_not_hidden_by_sparse_coverage():
    source = capture(("Auto", "Manual") * 3)
    for chunk in source["chunks"]:
        if 6000 <= chunk["elapsed_ms"] < 12000:
            chunk["hex"] = frame(
                0 if chunk["elapsed_ms"] == 6000 else 17,
                header="998009" if chunk["elapsed_ms"] == 6000 else "998008",
            ).hex()
    assert not candidates(source)
    report = audit(source, settle_ms=0, max_gap_ms=4000)
    assert (
        report["labels"]["BDE selection"]["rejected_feature_counts"][
            "contradictory_observed_values"
        ]
        == 2
    )


def test_opposite_value_for_repeated_same_reference_rejects_mapping():
    source = capture()
    for chunk in source["chunks"]:
        if 12000 <= chunk["elapsed_ms"] < 18000:
            chunk["hex"] = frame(64).hex()
    report = audit(source, settle_ms=0, max_gap_ms=4000)
    result = report["labels"]["BDE selection"]
    assert not result["candidates"]
    assert result["rejected_feature_counts"]["conflicting_same_observation"] == 2


def test_identity_coverage_gap_is_visible_even_with_dense_other_traffic():
    source = capture()
    for chunk in source["chunks"]:
        if 2000 <= chunk["elapsed_ms"] < 4000:
            chunk["hex"] = frame(17, header="998008").hex()
    report = audit(source, settle_ms=0, max_gap_ms=4000)
    result = report["labels"]["BDE selection"]
    assert report["overview"]["max_chunk_gap_ms"] == 1000
    assert (
        result["intervals"][0]["groups"][IDENTITY]["status"] == "insufficient_coverage"
    )
    assert not result["candidates"]  # only one fully covered Auto interval remains


def test_settling_excludes_change_lag_but_fragment_uses_completion_timestamp():
    source = capture()
    # Delayed state update must be outside the accepted stable interval.
    for chunk in source["chunks"]:
        if chunk["elapsed_ms"] in (6000, 18000):
            chunk["hex"] = frame(0).hex()
    assert not candidates(source)
    report = audit(source, settle_ms=1000, max_gap_ms=4000)
    assert len(report["labels"]["BDE selection"]["candidates"]) == 2
    # The parser accepts a frame split at a marker and dates its completion.
    source = capture()
    item = source["chunks"][6]
    raw = bytes.fromhex(item["hex"])
    source["chunks"][5]["hex"] += raw[:5].hex()
    item["hex"] = raw[5:].hex()
    report = audit(source, settle_ms=0, max_gap_ms=4000)
    assert (
        report["labels"]["BDE selection"]["intervals"][1]["groups"][IDENTITY][
            "first_seen_ms"
        ]
        == 6000
    )


def test_interleaved_labels_have_independent_intervals_and_exact_state_text():
    source = capture()
    source["observations"].insert(
        1, {"elapsed_ms": 2000, "label": "Other", "observation": "Auto"}
    )
    report = audit(source, settle_ms=0, max_gap_ms=4000)
    assert report["labels"]["BDE selection"]["intervals"][0]["window"]["end_ms"] == 6000
    assert report["labels"]["Other"]["status"] == "insufficient_references"
    source["observations"][-1]["observation"] = "manual"
    assert not candidates(source)  # free text is not guessed into normalized states


@pytest.mark.parametrize(
    "marker",
    [
        {"elapsed_ms": -1, "label": "A", "observation": "B"},
        {"elapsed_ms": True, "label": "A", "observation": "B"},
        {"elapsed_ms": 30000, "label": "A", "observation": "B"},
        {"elapsed_ms": 0, "label": "A\n", "observation": "B"},
        {"elapsed_ms": 0, "label": "A", "observation": " "},
    ],
)
def test_invalid_reference_rejected(marker):
    source = capture()
    source["observations"] = [marker]
    with pytest.raises(ValueError):
        audit(source)


@pytest.mark.parametrize(
    "options", [{"settle_ms": -1}, {"max_gap_ms": 1}, {"max_gap_ms": True}]
)
def test_invalid_alignment_options(options):
    with pytest.raises(ValueError):
        audit(capture(), **options)


@pytest.mark.parametrize("duration", [0, 4])
def test_marker_at_recording_end_without_traffic_is_retained(duration):
    source = {
        "actual_duration_seconds": duration,
        "chunks": [],
        "observations": [
            {"elapsed_ms": duration * 1000, "label": "BDE", "observation": "Auto"}
        ],
    }
    report = audit(source, settle_ms=0)
    result = report["labels"]["BDE"]
    assert report["observations"][0]["elapsed_ms"] == duration * 1000
    assert result["intervals"][0]["status"] == "empty_after_settling"
    assert not result["candidates"]


def test_cli_wrapped_export_keeps_input_and_writes_private_reports(
    tmp_path, monkeypatch
):
    source, output, readable = (
        tmp_path / name for name in ("source.json", "out.json", "out.md")
    )
    data = {"data": {"capture": capture()}}
    source.write_text(json.dumps(data))
    args = [
        "audit",
        str(source),
        "--settle-ms",
        "0",
        "--max-gap-ms",
        "4000",
        "--output",
        str(output),
        "--report",
        str(readable),
    ]
    monkeypatch.setattr("sys.argv", args)
    main()
    assert json.loads(output.read_text())["labels"]["BDE selection"]["candidates"]
    assert "Unverified" in json.loads(output.read_text())["reference_basis"]
    assert "correlation" in readable.read_text()
    args[args.index(str(output))] = str(source)
    with pytest.raises(SystemExit):
        main()
    assert json.loads(source.read_text()) == data
