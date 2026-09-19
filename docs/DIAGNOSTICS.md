# Diagnostics and offline analysis

## Downloading diagnostics

Home Assistant diagnostics include connection and decoder counters, freshness
information and an optional passive recording. The integration omits configured
network addresses and identifiers from its diagnostic data. Review the complete
export before sharing it: Home Assistant metadata and recorded bus bytes can
still contain information about your installation.

`application_bytes_sent` remains zero in normal operation. A connected TCP socket
does not guarantee that supported, fresh telemetry is being received.

## Recording

On the device page, select **Start capture (2 minutes)**. If investigating a
specific reading, note the corresponding BDE display and the time. Select
**Stop capture**, then download diagnostics. The capture uses the existing
receiver; it does not open another connection or send requests.

Recording stops at 120 seconds, 1 MiB, 4096 chunks, a manual stop or disconnect.
Starting again replaces the previous recording. **Clear capture**, reload and
restart remove the recording. A stopped capture stays in memory and appears in
subsequent diagnostic downloads until cleared or replaced. Download it before
updating or restarting Home Assistant.

The export includes:

- `started_utc`: recording start time;
- `status`: current state or stopping reason;
- `duration_seconds`: configured time limit, not measured duration;
- `chunks`: hexadecimal TCP receive blocks and relative `elapsed_ms` timestamps.

Chunks are not telegram boundaries and a recording may start or end mid-frame.
The final chunk time measures the observed receive span, not the exact stop time.
A `recording` export is a snapshot of a recording still in progress. The shared
`size_limit` reason can indicate either the byte or chunk limit.

Recording includes unknown and rejected bytes. It is kept in memory, not in
entity attributes, Recorder or log files. Keep full recordings, display photos,
network details and personal notes outside the public repository.

## Offline tools

Run from a development checkout after following [setup instructions](../CONTRIBUTING.md).
These commands do not connect to equipment. Store reports in the ignored `tmp/`
directory or another private location.

```sh
mkdir -p tmp
uv run python -m tools.inventory_capture capture.json --output tmp/inventory.json
uv run python -m tools.replay_diagnosis capture.json --output tmp/replay.json
uv run python -m tools.compare_captures before.json after.json \
  --output tmp/comparison.json --report tmp/comparison.md
```

Inventory retains unknown identities within supported frame shapes. Replay uses
the production decoder and therefore reports only implemented readings. A frame
present in inventory but absent from replay is not necessarily corrupt.

### Comparing time windows

Omit the second filename to compare two windows within one recording:

```sh
uv run python -m tools.compare_captures capture.json \
  --before-end-ms 30000 --after-start-ms 30000 \
  --after-event-ms 31000 --after-event-description 'Display observation' \
  --output tmp/windows.json --report tmp/windows.md
```

Times in this example are illustrative. Each optional event is relative to its
own recording start. Event deltas express temporal correlation, not causation
or a confirmed interpretation of a bit.

Windows are half-open `[start_ms, end_ms)`. The full stream is parsed first so
fragmented frames crossing a window boundary are retained. A frame is assigned
the timestamp of the TCP chunk that completes it, not an electrical bus timestamp.
The first observation in a window is a baseline, not a confirmed transition.

Reports include:

- complete three-byte identity, data point and payload length per group;
- new, missing and shared groups, distinct payloads and their frequencies;
- each actual payload transition, timestamp, previous value and changed bits;
- final observed values on each side, without assuming simultaneous sampling;
- available recording metadata, differences in capture conditions and byte coverage.

Bit positions are LSB-first, with zero-based byte offsets. Different payload
lengths remain separate groups and are not compared bitwise. Repetitions increase
frequency but not the transition count. Missing observations mean neither
unchanged nor off.

Unparsed bytes include noise, unsupported shapes, invalid candidates and incomplete
frames; the tool does not infer which cause applies. Reserved bytes 5/6 must be
zero under the existing inventory rules. Byte coverage and maximum chunk gap
refer to the **whole recording**, even when comparing windows. Gaps can reflect
silence or missing traffic, so complete exported-byte coverage does not prove
continuous capture of the electrical bus.

The inventory and comparison tools accept HA exports (`data.capture`), `capture`
wrappers and bare capture objects. Timestamps must be nonnegative monotonic
integers. Missing metadata remains `null`. Comparison output paths must differ
from the inputs and from each other.

## Sharing a useful report

Include the integration and Home Assistant versions, selected hardware profile,
affected entity and a short description of expected versus observed behaviour.
For a decoding issue, a reviewed minimal telegram and expected interpretation
are more useful than an unfiltered dump. Remove addresses, device identifiers,
serial numbers, personal file paths and unrelated measurements. Do not cause an
equipment fault to obtain a sample.
