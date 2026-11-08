"""Compare inventory SET-type candidates without parsing or transmitting bytes.

The low command nibble classifies candidates, not their sender or meaning.
Raw reports and manually supplied reference observations belong in private storage.
"""

from bisect import bisect_left, bisect_right

from custom_components.proxon_hesp.capture import (
    MAX_LABEL_LENGTH,
    MAX_OBSERVATION_LENGTH,
    MAX_OBSERVATIONS,
    validate_observation_text,
)
from tools.frame_observations import frames as _frames
from tools.frame_observations import integer as _integer


def changed_bits(before: str, after: str) -> list[dict] | None:
    """Byte offsets and LSB-first bit indexes; no inferred semantic labels."""
    left, right = bytes.fromhex(before), bytes.fromhex(after)
    if len(left) != len(right):
        return None
    return [
        {"byte": offset, "bit": bit, "before": (a >> bit) & 1, "after": (b >> bit) & 1}
        for offset, (a, b) in enumerate(zip(left, right, strict=True))
        for bit in range(8)
        if (a ^ b) & (1 << bit)
    ]


def normalize_data_points(data_points):
    """Validate a bounded iterable once, including one-shot generators."""
    if data_points is None:
        return None
    try:
        iterator = iter(data_points)
    except TypeError as err:
        raise ValueError("data_points must be an iterable of integers") from err
    result = set()
    for index, point in enumerate(iterator):
        if index >= 65536:
            raise ValueError("too many data_points")
        result.add(_integer(point, "data point", maximum=65535))
    return result


def _reference_points(observations):
    if (
        not isinstance(observations, list | tuple)
        or len(observations) > MAX_OBSERVATIONS
    ):
        raise ValueError("observations must be a bounded list or tuple")
    result = []
    for row in observations:
        if not isinstance(row, dict) or set(row) - {
            "elapsed_ms",
            "label",
            "observation",
            "evidence_id",
            "trigger_elapsed_ms",
        }:
            raise ValueError("invalid point observation")
        item = {
            "elapsed_ms": _integer(row.get("elapsed_ms"), "observation elapsed_ms"),
            "label": validate_observation_text(row.get("label"), MAX_LABEL_LENGTH),
            "observation": validate_observation_text(
                row.get("observation"), MAX_OBSERVATION_LENGTH
            ),
        }
        if "evidence_id" in row:
            item["evidence_id"] = validate_observation_text(row["evidence_id"], 128)
        if "trigger_elapsed_ms" in row:
            item["trigger_elapsed_ms"] = _integer(
                row["trigger_elapsed_ms"], "trigger_elapsed_ms"
            )
        result.append(item)
    return result


def _nearby_samples(point, samples, times, window_ms):
    result = []
    for identity, rows in samples.items():
        start = bisect_left(times[identity], point)
        end = bisect_right(times[identity], point)
        if start < end:
            selected = [rows[start]]
            if end - start > 1:
                selected.append(rows[end - 1])
        else:
            selected = [rows[start - 1]] if start else []
            if start < len(rows):
                selected.append(rows[start])
        for row in selected:
            delta = row["elapsed_ms"] - point
            if abs(delta) <= window_ms:
                result.append(
                    {
                        "identity": identity,
                        "elapsed_ms": row["elapsed_ms"],
                        "frame_index": row["frame_index"],
                        "payload_hex": row["payload_hex"],
                        "delta_ms": delta,
                        "relation": "before"
                        if delta < 0
                        else "after"
                        if delta > 0
                        else "at",
                        "same_timestamp_order_ambiguous": delta == 0,
                    }
                )
    return sorted(result, key=lambda row: (row["identity"], row["frame_index"]))


def analyze_sets(
    inventory_report: dict,
    *,
    max_gap_ms: int = 30000,
    observations=(),
    observation_window_ms: int = 5000,
    data_points=None,
) -> dict:
    """Summarize observed SET-type sequences, with explicit continuity boundaries.

    Windows, framing and checksums are supplied by inventory, never reimplemented.
    A reference point does not assert any interval before or after its timestamp.
    """
    _integer(max_gap_ms, "max_gap_ms", minimum=1)
    _integer(observation_window_ms, "observation_window_ms")
    if not isinstance(inventory_report, dict):
        raise ValueError("inventory_report must be a dictionary")
    window = inventory_report.get("window")
    if not isinstance(window, dict):
        raise ValueError("inventory window is required")
    start = _integer(window.get("start_ms"), "window start_ms")
    end = window.get("end_ms")
    if end is not None:
        _integer(end, "window end_ms", minimum=start + 1)
    capture_end = _integer(inventory_report.get("last_chunk_ms"), "last_chunk_ms")
    points = normalize_data_points(data_points)
    references = _reference_points(observations)
    groups, previous, transitions, samples = {}, {}, [], {}
    for row in _frames(inventory_report):
        if row["elapsed_ms"] < start or (end is not None and row["elapsed_ms"] >= end):
            raise ValueError("frame observation outside selected window")
        if row["elapsed_ms"] > capture_end:
            raise ValueError("frame observation outside capture")
        if int(row["header"][:2], 16) & 0x0F != 1 or (
            points is not None and row["dp"] not in points
        ):
            continue
        key = row["identity"]
        samples.setdefault(key, []).append(row)
        stream = (row["header"], row["dp"])
        old = previous.get(stream)
        group = groups.setdefault(
            key,
            {
                "header": row["header"],
                "dp": f"0x{row['dp']:04X}",
                "payload_bytes": row["payload_bytes"],
                "total": 0,
                "repeats": 0,
                "transitions": 0,
                "baselines": 0,
                "runs": [],
            },
        )
        reasons = []
        if old is None:
            reasons.append("first_observation")
        else:
            if row["payload_bytes"] != old["payload_bytes"]:
                reasons.append("payload_length_change")
            if row["elapsed_ms"] - old["elapsed_ms"] >= max_gap_ms:
                reasons.append("gap")
            if row["unparsed_bytes_before"] != old["unparsed_bytes_before"]:
                reasons.append("unparsed_bytes")
        group["total"] += 1
        if not reasons and old["payload_hex"] == row["payload_hex"]:
            group["repeats"] += 1
            run = group["runs"][-1]
            run["samples"] += 1
            run["last_seen_ms"] = row["elapsed_ms"]
            run["last_frame_index"] = row["frame_index"]
        else:
            baseline = bool(reasons)
            group["baselines" if baseline else "transitions"] += 1
            bracket = (
                None
                if baseline
                else {
                    "last_old_ms": old["elapsed_ms"],
                    "first_new_ms": row["elapsed_ms"],
                    "last_old_frame_index": old["frame_index"],
                    "first_new_frame_index": row["frame_index"],
                }
            )
            run = {
                "kind": "baseline" if baseline else "transition",
                "reasons": reasons or ["payload_change"],
                "first_seen_ms": row["elapsed_ms"],
                "last_seen_ms": row["elapsed_ms"],
                "first_frame_index": row["frame_index"],
                "last_frame_index": row["frame_index"],
                "samples": 1,
                "payload_hex": row["payload_hex"],
                "previous_payload_hex": None if baseline else old["payload_hex"],
                "changed_bits": None
                if baseline
                else changed_bits(old["payload_hex"], row["payload_hex"]),
                "transition_bracket": bracket,
            }
            group["runs"].append(run)
            if not baseline:
                transitions.append(
                    {
                        "identity": key,
                        "elapsed_ms": row["elapsed_ms"],
                        "frame_index": row["frame_index"],
                        "transition_bracket": bracket,
                        "previous_payload_hex": old["payload_hex"],
                        "payload_hex": row["payload_hex"],
                        "changed_bits": run["changed_bits"],
                    }
                )
        previous[stream] = row

    sample_times = {
        key: [row["elapsed_ms"] for row in rows] for key, rows in samples.items()
    }
    for point in references:
        time = point["elapsed_ms"]
        point["status"] = (
            "outside_capture"
            if time > capture_end
            else "outside_window"
            if time < start or (end is not None and time >= end)
            else "context_only"
        )
        matches = []
        if point["status"] == "context_only":
            matches = [
                {**change, "delta_ms": change["elapsed_ms"] - time}
                for change in transitions
                if abs(change["elapsed_ms"] - time) <= observation_window_ms
            ]
            matches.sort(key=lambda row: (abs(row["delta_ms"]), row["frame_index"]))
        point["nearby_changes"] = matches
        point["nearby_samples"] = (
            _nearby_samples(time, samples, sample_times, observation_window_ms)
            if point["status"] == "context_only"
            else []
        )

    return {
        "classification": "SET-type candidate: first header byte low nibble is 1",
        "time_basis": (
            "TCP chunk completing frame, not electrical bus or exact switch time"
        ),
        "window": {"start_ms": start, "end_ms": end},
        "max_gap_ms": max_gap_ms,
        "observation_window_ms": observation_window_ms,
        "data_points": None
        if points is None
        else [f"0x{dp:04X}" for dp in sorted(points)],
        "groups": dict(sorted(groups.items())),
        "observations": references,
        "caution": (
            "Classification does not identify BDE origin, acceptance or payload "
            "meaning. First observations and observations after gaps, skipped "
            "bytes or length changes are baselines. A transition bracket bounds "
            "consecutive observations, not a measured physical switch time. "
            "Equal timestamps preserve frame order, not wire latency. Missing "
            "samples do not establish state. Reference observations are points "
            "only; photo/reference time and trigger time remain distinct. Nearby "
            "samples and changes are correlation only. Same-time frame order "
            "relative to a photo is unknown. Gap limits are analysis parameters, "
            "not measured protocol timing. No state is extended outside the "
            "observed samples."
        ),
    }
