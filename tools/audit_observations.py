"""Align user observations with passive payloads; correlation is not semantics.

Reports contain raw payloads and user text. Keep them outside version control.
No equipment connection is opened and no new wire parser is used.
"""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from custom_components.proxon_hesp.capture import (
    MAX_LABEL_LENGTH,
    MAX_OBSERVATION_LENGTH,
    MAX_OBSERVATIONS,
    validate_observation_text,
)
from tools.inventory_capture import inventory, load_capture


def _observations(capture: dict, end_ms: int) -> list[dict]:
    items = capture.get("observations", [])
    if not isinstance(items, list) or len(items) > MAX_OBSERVATIONS:
        raise ValueError("observations must be a bounded list")
    result = []
    for index, item in enumerate(items):
        timestamp = item["elapsed_ms"]
        if type(timestamp) is not int or not 0 <= timestamp <= end_ms:
            raise ValueError("observation time outside recorded interval")
        if result and timestamp < result[-1]["elapsed_ms"]:
            raise ValueError("observation timestamps must be monotonic")
        result.append(
            {
                "index": index,
                "elapsed_ms": timestamp,
                "label": validate_observation_text(item["label"], MAX_LABEL_LENGTH),
                "observation": validate_observation_text(
                    item["observation"], MAX_OBSERVATION_LENGTH
                ),
            }
        )
    return result


def _features(group: dict) -> dict:
    """Only values constant throughout an interval can support a candidate."""
    payloads = [bytes.fromhex(value) for value in group["values"]]
    result = {"payload": group["values"][0]} if len(payloads) == 1 else {}
    for offset in range(group["payload_bytes"]):
        for bit in range(8):
            values = {(payload[offset] >> bit) & 1 for payload in payloads}
            if len(values) == 1:
                result[f"byte[{offset}].bit[{bit}]"] = values.pop()
    return result


def audit(capture: dict, *, settle_ms: int = 10000, max_gap_ms: int = 30000) -> dict:
    """Compare stable intervals following repeated user-reported states.

    Each label has its own timeline, bounded by the next mark of that label.
    A mark states a reference condition from then on; it is not a measured edge.
    Missing references never imply an unchanged or absent equipment state.
    """
    if type(settle_ms) is not int or settle_ms < 0:
        raise ValueError("settle_ms must be a nonnegative integer")
    if type(max_gap_ms) is not int or max_gap_ms < 2:
        raise ValueError("max_gap_ms must be an integer of at least 2")
    overview = inventory(capture["chunks"])
    duration = capture.get("actual_duration_seconds")
    if duration is not None and (
        isinstance(duration, bool)
        or not isinstance(duration, int | float)
        or not 0 <= duration <= 86400
    ):
        raise ValueError("actual duration must be a finite nonnegative number")
    end_ms = max(
        overview["last_chunk_ms"] + 1 if capture["chunks"] else 0,
        round(duration * 1000) if duration is not None else 0,
    )
    marks = _observations(capture, end_ms)
    by_label = defaultdict(list)
    for mark in marks:
        by_label[mark["label"]].append(mark)

    cached = {}

    def window(start, end):
        key = (start, end)
        if key not in cached:
            cached[key] = inventory(capture["chunks"], start_ms=start, end_ms=end)
        return cached[key]

    labels = {}
    for label, items in by_label.items():
        state_counts = Counter(item["observation"] for item in items)
        comparable = len(state_counts) >= 2 and min(state_counts.values()) >= 2
        intervals = []
        for index, item in enumerate(items):
            start = item["elapsed_ms"] + settle_ms
            end = items[index + 1]["elapsed_ms"] if index + 1 < len(items) else end_ms
            interval = {
                **item,
                "window": {"start_ms": start, "end_ms": end},
                "groups": {},
            }
            intervals.append(interval)
            if start >= end:
                interval["status"] = "empty_after_settling"
                continue
            interval["status"] = "observed"
            groups = window(start, end)["groups"]
            # Half-gap bins conservatively bound gaps between repeated frames.
            # An empty bin is insufficient coverage, not proof of lost traffic.
            bins = (
                [
                    window(point, min(point + max_gap_ms // 2, end))["groups"]
                    for point in range(start, end, max_gap_ms // 2)
                ]
                if comparable
                else []
            )
            for identity, group in groups.items():
                status = (
                    "single_sample"
                    if group["count"] < 2
                    else "coverage_not_checked"
                    if not comparable
                    else "insufficient_coverage"
                    if any(identity not in bucket for bucket in bins)
                    else "repeated"
                )
                interval["groups"][identity] = {
                    "status": status,
                    "count": group["count"],
                    "first_seen_ms": group["first_seen_ms"],
                    "last_seen_ms": group["last_seen_ms"],
                    "values": group["values"],
                    "constant_features": _features(group),
                }

        candidates, rejected = [], Counter()
        identities = sorted(
            {identity for interval in intervals for identity in interval["groups"]}
        )
        for identity in identities:
            features = sorted(
                {
                    feature
                    for interval in intervals
                    for feature in interval["groups"]
                    .get(identity, {})
                    .get("constant_features", {})
                }
            )
            for feature in features:
                values, uncertain = defaultdict(list), []
                for interval in intervals:
                    group = interval["groups"].get(identity)
                    if (
                        group is None
                        or group["status"] != "repeated"
                        or feature not in group["constant_features"]
                    ):
                        uncertain.append(interval["index"])
                        continue
                    values[interval["observation"]].append(
                        group["constant_features"][feature]
                    )
                if any(len(set(samples)) > 1 for samples in values.values()):
                    rejected["conflicting_same_observation"] += 1
                    continue
                if not comparable or any(
                    len(values[state]) < 2 for state in state_counts
                ):
                    rejected["insufficient_state_repetitions"] += 1
                    continue
                mapping = {state: values[state][0] for state in state_counts}
                if len(set(mapping.values())) < len(mapping):
                    rejected["does_not_distinguish_all_states"] += 1
                    continue
                # Even one valid contradictory sample is a counterexample.
                # Missing or sparse coverage cannot erase observed disagreement.
                if any(
                    group is not None
                    and group["constant_features"].get(feature)
                    != mapping[interval["observation"]]
                    for interval in intervals
                    for group in [interval["groups"].get(identity)]
                ):
                    rejected["contradictory_observed_values"] += 1
                    continue
                candidates.append(
                    {
                        "identity": identity,
                        "feature": feature,
                        "status": "partial" if uncertain else "repeatable",
                        "values_by_observation": mapping,
                        "supporting_interval_count": sum(map(len, values.values())),
                        "uncertain_interval_indexes": uncertain,
                    }
                )
        candidates.sort(
            key=lambda item: (
                bool(item["uncertain_interval_indexes"]),
                -item["supporting_interval_count"],
                item["identity"],
                item["feature"],
            )
        )
        labels[label] = {
            "status": "comparable" if comparable else "insufficient_references",
            "state_interval_counts": dict(state_counts),
            "intervals": intervals,
            "candidates": candidates,
            "rejected_feature_counts": dict(rejected),
        }
    return {
        "time_basis": "TCP chunk completing frame; relative to capture start",
        "reference_basis": "Unverified user statements, exact label and text matching",
        "caution": "Candidates are correlation only, with no sensor inference. "
        "The first sample is a baseline, never a confirmed transition. "
        "Missing, unstable or insufficiently covered intervals remain uncertain. "
        "An observation is assumed to persist until the next mark of the same label; "
        "mark every relevant change. Complete capture coverage does not prove "
        "complete bus coverage.",
        "settle_ms": settle_ms,
        "max_gap_ms": max_gap_ms,
        "coverage_rule": "At least two frames; at least one in every half-gap bin",
        "end_ms": end_ms,
        "overview": {
            key: overview[key]
            for key in ("frames", "unparsed_bytes", "max_chunk_gap_ms", "last_chunk_ms")
        },
        "observations": marks,
        "labels": labels,
    }


def render(report: dict) -> str:
    lines = ["# Observation alignment", "", report["caution"], "", report["time_basis"]]
    for label, result in report["labels"].items():
        lines += ["", f"## {label}: {result['status']}"]
        for interval in result["intervals"]:
            lines.append(
                f"Reference {interval['index']}: "
                + json.dumps(
                    {key: interval[key] for key in ("observation", "window", "status")},
                    ensure_ascii=False,
                )
            )
        lines.append(f"Candidates: {len(result['candidates'])}")
        lines.extend(
            json.dumps(item, ensure_ascii=False) for item in result["candidates"]
        )
        lines.append(
            "Rejected features: " + json.dumps(result["rejected_feature_counts"])
        )
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--settle-ms", type=int, default=10000)
    parser.add_argument("--max-gap-ms", type=int, default=30000)
    parser.add_argument("--event", action="store_true")
    parser.add_argument("--event-index", type=int, default=-1)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.event_index != -1 and not args.event:
        parser.error("--event-index requires --event")
    paths = [path.resolve() for path in (args.capture, args.output, args.report)]
    if len(set(paths)) != len(paths):
        parser.error("input and output paths must differ")
    try:
        result = audit(
            load_capture(args.capture, event=args.event, event_index=args.event_index),
            settle_ms=args.settle_ms,
            max_gap_ms=args.max_gap_ms,
        )
    except (ValueError, KeyError, TypeError) as err:
        parser.error(str(err))
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    args.report.write_text(render(result))


if __name__ == "__main__":
    main()
