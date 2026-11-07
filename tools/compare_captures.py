"""Compare passive captures using the existing inventory, without equipment access.

Reports contain raw payloads: keep them private. Times are TCP chunk completion
 times, never electrical bus times. Missing observations do not imply state.
"""

import argparse
import json
from pathlib import Path

from tools.inventory_capture import inventory, load_capture
from tools.set_comparison import analyze_sets, changed_bits, normalize_data_points

METADATA = (
    "format_version",
    "started_utc",
    "status",
    "duration_seconds",
    "max_bytes",
    "max_chunks",
    "integration_version",
    "profile",
    "configured_duration_seconds",
)


def describe(
    capture: dict,
    window: tuple,
    event: dict | None,
    *,
    set_data_points=None,
    set_max_gap_ms=30000,
    set_observation_window_ms=5000,
    observations=None,
) -> dict:
    result = inventory(
        capture["chunks"],
        start_ms=window[0],
        end_ms=window[1],
        include_frame_observations=True,
    )
    marks = capture.get("observations", []) if observations is None else observations
    result["set_analysis"] = analyze_sets(
        result,
        max_gap_ms=set_max_gap_ms,
        data_points=set_data_points,
        observations=marks,
        observation_window_ms=set_observation_window_ms,
    )
    del result["frame_observations"]
    result["metadata"] = {key: capture.get(key) for key in METADATA}
    if event is not None:
        if type(event["elapsed_ms"]) is not int or event["elapsed_ms"] < 0:
            raise ValueError("event time must be a nonnegative integer")
    result["event"] = event
    for group in result["groups"].values():
        changes = group["changes"]
        group["transition_count"] = len(changes) - 1
        for index, change in enumerate(changes):
            change["previous_payload_hex"] = (
                changes[index - 1]["payload_hex"] if index else None
            )
            change["changed_bits"] = (
                changed_bits(change["previous_payload_hex"], change["payload_hex"])
                if index
                else None
            )
            if event is not None:
                change["event_delta_ms"] = change["elapsed_ms"] - event["elapsed_ms"]
    return result


def compare(
    before: dict,
    after: dict,
    *,
    before_window=(0, None),
    after_window=(0, None),
    before_event=None,
    after_event=None,
    set_data_points=None,
    set_max_gap_ms=30000,
    set_observation_window_ms=5000,
    before_observations=None,
    after_observations=None,
) -> dict:
    """Compare observed sequences; each window is half-open [start, end)."""
    set_data_points = normalize_data_points(set_data_points)
    options = {
        "set_data_points": set_data_points,
        "set_max_gap_ms": set_max_gap_ms,
        "set_observation_window_ms": set_observation_window_ms,
    }
    left = describe(
        before, before_window, before_event, observations=before_observations, **options
    )
    right = describe(
        after, after_window, after_event, observations=after_observations, **options
    )
    groups = {}
    for key in sorted(left["groups"].keys() | right["groups"].keys()):
        a, b = left["groups"].get(key), right["groups"].get(key)
        item = {"presence": "both" if a and b else "only_before" if a else "only_after"}
        if a and b:
            old, new = a["changes"][-1]["payload_hex"], b["changes"][-1]["payload_hex"]
            item.update(
                last_before=old,
                last_after=new,
                changed_bits=changed_bits(old, new),
                new_payloads=sorted(set(b["values"]) - set(a["values"])),
                missing_payloads=sorted(set(a["values"]) - set(b["values"])),
                same_observed_sequence=(
                    a["values"] == b["values"]
                    and [x["payload_hex"] for x in a["changes"]]
                    == [x["payload_hex"] for x in b["changes"]]
                ),
            )
        groups[key] = item
    return {
        "time_basis": "TCP chunk completing frame; relative to each capture start",
        "caution": "Absence is not unchanged or off. Gaps may be silence or loss. "
        "Unparsed bytes include noise, invalid or incomplete frames. "
        "Event proximity is correlation, not causation. "
        "Byte coverage and maximum chunk gap cover the whole capture.",
        "metadata_differences": [
            k for k in METADATA if left["metadata"][k] != right["metadata"][k]
        ],
        "before": left,
        "after": right,
        "groups": groups,
    }


def render(report: dict, *, sets_only: bool = False) -> str:
    lines = [
        "# Capture comparison",
        "",
        report["time_basis"],
        report["caution"],
        "",
        "Metadata differences: " + ", ".join(report["metadata_differences"]),
    ]
    for side in ("before", "after"):
        data = report[side]
        lines += [
            f"\n## {side}",
            json.dumps(data["metadata"], ensure_ascii=False),
            f"Window: {data['window']}; frames: {data['frames']}; "
            f"whole-capture unparsed bytes: {data['unparsed_bytes']}; "
            f"maximum chunk gap: {data['max_chunk_gap_ms']} ms",
        ]
        if data["event"]:
            lines.append(
                "Manual event (correlation only): " + json.dumps(data["event"])
            )
        sets = data["set_analysis"]
        lines += ["", "### SET-type observations", sets["classification"]]
        for key, group in sets["groups"].items():
            lines.append(
                f"{key}: {group['total']} observations, {group['repeats']} repeats, "
                f"{group['transitions']} changes, {group['baselines']} baselines"
            )
            lines.extend(json.dumps(run) for run in group["runs"])
        if not sets["groups"]:
            lines.append("No matching SET-type observations; state is unknown.")
        for observation in sets["observations"]:
            lines.append("Point-in-time reference: " + json.dumps(observation))
        lines.append(
            "Byte/bit indexes are zero-based. First samples and gaps are "
            "baselines. SET payloads do not prove accepted commands or "
            "actuator state; nearby photos establish correlation only."
        )
    if sets_only:
        return "\n".join(lines) + "\n"
    for key, item in report["groups"].items():
        lines += [f"\n## {key}: {item['presence']}", json.dumps(item)]
        for side in ("before", "after"):
            group = report[side]["groups"].get(key)
            if group is None:
                lines.append(f"{side}: no observations")
                continue
            lines.append(
                f"{side}: {group['count']} frames, "
                f"{group['transition_count']} transitions; "
                f"payload frequencies: {group['payload_counts']}"
            )
            lines.extend(json.dumps(change) for change in group["changes"])
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument(
        "after",
        type=Path,
        nargs="?",
        help="Omit to compare two windows of the first capture",
    )
    for side in ("before", "after"):
        parser.add_argument(f"--{side}-start-ms", type=int, default=0)
        parser.add_argument(f"--{side}-end-ms", type=int)
        parser.add_argument(f"--{side}-event-ms", type=int)
        parser.add_argument(f"--{side}-event-description", default="Manual event")
        parser.add_argument(
            f"--{side}-observations",
            type=Path,
            help="Private JSON list of point-in-time references; "
            "replaces embedded observation marks for this side",
        )
    parser.add_argument(
        "--set-dp",
        action="append",
        type=lambda value: int(value, 0),
        help="Limit SET view to a DP, e.g. 0x01F8; repeatable",
    )
    parser.add_argument("--set-max-gap-ms", type=int, default=30000)
    parser.add_argument("--set-observation-window-ms", type=int, default=5000)
    parser.add_argument(
        "--sets-only",
        action="store_true",
        help="Show only SET observations in Markdown; JSON keeps inventory",
    )
    parser.add_argument(
        "--event", action="store_true", help="Use automatic event capture"
    )
    parser.add_argument("--output", type=Path, required=True, help="JSON report")
    parser.add_argument("--report", type=Path, required=True, help="Readable Markdown")
    parser.add_argument(
        "--event-index",
        type=int,
        default=-1,
        help="Event index: 0 oldest, -1 latest (default); requires --event",
    )
    args = parser.parse_args()
    if args.event_index != -1 and not args.event:
        parser.error("--event-index requires --event")
    sources = [args.before, args.after or args.before]
    sources.extend(
        path
        for path in (args.before_observations, args.after_observations)
        if path is not None
    )
    if args.output.resolve() == args.report.resolve() or any(
        out.resolve() == source.resolve()
        for out in (args.output, args.report)
        for source in sources
    ):
        parser.error("output paths must be distinct from each other and inputs")
    options = {}
    options.update(
        set_data_points=args.set_dp,
        set_max_gap_ms=args.set_max_gap_ms,
        set_observation_window_ms=args.set_observation_window_ms,
    )
    for side in ("before", "after"):
        options[f"{side}_window"] = (
            getattr(args, f"{side}_start_ms"),
            getattr(args, f"{side}_end_ms"),
        )
        time = getattr(args, f"{side}_event_ms")
        options[f"{side}_event"] = (
            None
            if time is None
            else {
                "elapsed_ms": time,
                "description": getattr(args, f"{side}_event_description"),
            }
        )
    try:
        for side in ("before", "after"):
            path = getattr(args, f"{side}_observations")
            if path is not None:
                options[f"{side}_observations"] = json.loads(path.read_text())
        report = compare(
            load_capture(args.before, event=args.event, event_index=args.event_index),
            load_capture(
                args.after or args.before,
                event=args.event,
                event_index=args.event_index,
            ),
            **options,
        )
    except (ValueError, KeyError, TypeError) as err:
        parser.error(str(err))
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    args.report.write_text(render(report, sets_only=args.sets_only))


if __name__ == "__main__":
    main()
