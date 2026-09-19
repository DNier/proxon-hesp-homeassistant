# Diagnostics and offline analysis

The capture enhancements below are available in **version 0.9.0**.
Version 0.8.0 has a fixed 120-second limit and no capture-status entity. Existing
format-version-1 exports remain supported by the offline tools.

## Downloading diagnostics

Home Assistant diagnostics include connection and decoder counters, freshness
information and an optional passive recording. Version 0.9.0 also
includes the integration version, explicitly selected profile and last supported
valid-data receipt timestamp. The integration omits configured
network addresses and identifiers from its diagnostic data. Review the complete
export before sharing it: Home Assistant metadata and recorded bus bytes can
still contain information about your installation.

`application_bytes_sent` remains zero in normal operation. A connected TCP socket
does not guarantee that supported, fresh telemetry is being received.

## Recording

On the device page, select **Start capture**. If investigating a
specific reading, note the corresponding BDE display and the time. Select
**Stop capture**, then download diagnostics. The capture uses the existing
receiver; it does not open another connection or send requests.

Under the integration's **Options**, choose a duration from **30 to 600 seconds**
(default **120**). Changes apply to the next recording without reconnecting or
clearing a running/saved recording. The current recording retains its original
limit. The start button keeps its unique ID; existing custom names are preserved.

Recording stops at its selected time limit, 1 MiB, 4096 chunks, a manual stop or
disconnect. A longer time limit does not guarantee a longer recording: the same
memory and chunk limits still apply.
Starting again replaces the previous recording. **Clear capture**, reload and
restart remove the recording. A stopped capture stays in memory and appears in
subsequent diagnostic downloads until cleared or replaced. Download it before
updating or restarting Home Assistant.

The export includes:

- `started_utc`: recording start time;
- `stopped_utc`: stop time, or null while recording/idle;
- `status`: `idle`, `recording`, `manual`, `duration_limit`, `byte_limit`,
  `chunk_limit` or `disconnected`;
- `actual_duration_seconds`: monotonic time from start until stop (or now while
  recording), including periods without received data;
- `bytes` and `chunk_count`: recorded data size and receive-block count;
- `duration_seconds`: time limit chosen for this recording, not measured duration;
- `configured_duration_seconds`: current option for the next recording;
- `integration_version`, `profile`, `max_bytes`, `max_chunks`: interpretation
  context and memory limits;
- `chunks`: hexadecimal TCP receive blocks and relative `elapsed_ms` timestamps.

Chunks are not telegram boundaries and a recording may start or end mid-frame.
The final chunk time measures the observed receive span, not the exact stop time.
`actual_duration_seconds` measures the recording lifecycle independently of chunk
arrival. After stopping, its value is frozen. Wall-clock start/stop timestamps may
be affected by clock corrections; duration uses a monotonic clock.
A `recording` export is a snapshot of a recording still in progress.

New exports use **format version 2** and retain the existing `chunks` format.
Older format-version-1 exports use `size_limit` for both memory limits and do not
provide an exact stop time or actual duration. Offline tools do not manufacture
these missing values.

Recording includes unknown and rejected bytes. It is kept in memory, not in
entity attributes, Recorder or log files. Keep full recordings, display photos,
network details and personal notes outside the public repository.

## Diagnostic entities

**Capture status** is enabled by default. Its translated state shows whether a
recording is running or why it stopped. Attributes include start/stop timestamps,
actual duration, size, chunk count and limits; raw payloads are never attributes.
Progress is refreshed approximately every five seconds while the entry is loaded.
Start, stop, clear and limit/disconnect changes are delivered immediately, including
when a recording's timer expires without any subsequent bus telegram.

Two optional diagnostic entities are disabled by default:

- **Gateway connection** reports TCP connectivity, not freshness of telemetry.
- **Last valid data received** reports the UTC timestamp of the latest received
  supported decoder reading. Unsupported or invalid bytes do not advance it.
  It is not a statement that every channel is fresh. The timestamp is retained
  on disconnect, refreshed in HA within approximately five seconds during normal
  reception, and reset to unknown on reload until valid data arrives.

Status and connection diagnostics remain readable during a disconnect. Existing
telemetry continues to become unavailable according to its own freshness rules.
Reload/unload cancels recording and freshness timers and removes entity listeners.
Starting again replaces the previous recording; clearing returns status to idle.

### Upgrade from 0.8.0

Keep the existing entry. The original 54 entity identities, user names and
activation preferences remain; three diagnostic entities are added (57 total).
Entries without recording options use 120 seconds automatically. No config-entry
migration or extra gateway connection is required. Download any recording before
updating because reload/restart still clears the in-memory buffer.

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
