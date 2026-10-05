# Offline capture analysis

Developer documentation · English. User instructions: [Diagnose und Aufnahmen](DIAGNOSTICS.md).


Use `--event` with inventory, replay or comparison to select the latest
automatic recording from a full diagnostic export; the default remains the manual
capture. Add `--event-index 0` for the oldest retained event (`1` for the next,
and `-1` for the latest). Older single-event exports remain supported:

```sh
uv run python -m tools.inventory_capture diagnostics.json --event --output tmp/event.json
uv run python -m tools.replay_diagnosis diagnostics.json --event --output tmp/event-replay.json
uv run python -m tools.compare_captures diagnostics.json --event \
  --before-end-ms 60000 --after-start-ms 60000 \
  --output tmp/event-comparison.json --report tmp/event-comparison.md
```

For comparisons, replace the example 60000 ms with the actual first event's
`elapsed_ms`; a short prebuffer means the event occurs earlier in the export.

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

### Aligning recorded user observations

Manual captures can contain an `observations` list. Each entry has `elapsed_ms`,
`label` and `observation`, for example a label `BDE air selection` with text
`Auto` or `Manual level 3` in a suitable Eco mode. On the reference installation,
Comfort/Stove do not offer that choice; Eco Auto follows a weekly schedule.
These are unverified user statements, not decoded
equipment values. Use the same label and exact state text for every repetition;
the tool does not guess that differently spelled texts mean the same state.

```sh
uv run python -m tools.audit_observations diagnostics.json \
  --settle-ms 10000 --max-gap-ms 30000 \
  --output tmp/observations.json --report tmp/observations.md
```

The tool reuses the inventory parser and includes all supported complete
identities, not just production sensor data points. It opens no connection and
sends no queries. Outputs contain raw values and user text and belong in a
private location. Older captures without annotations produce no inferred
reference states.

Each label has an independent timeline. A state is assumed to hold from its
mark until the next mark with that label, or the end of the recording. Mark
every relevant change; an unmarked BDE change invalidates that reference
assumption. The initial `--settle-ms` (default 10 seconds) is excluded from each
interval to allow for observation and equipment update delays. This is a
configurable analysis parameter, not a measured reaction time. A first frame is
always a baseline, never a confirmed edge at the mark's timestamp.

Candidate comparison needs at least two different states, each recorded in
at least two reference intervals. Supporting intervals need at least two
valid frames of the identity and one frame in every bin of half the configured
`--max-gap-ms`. This conservatively bounds gaps between samples. The default
30 seconds is a configurable analysis limit, not a guaranteed protocol cadence.
Empty bins mean insufficient coverage; they do not distinguish silence from
missing traffic. The final, possibly shorter bin also needs a sample; this is
deliberately conservative and can mark an interval uncertain close to its end.
Unrelated traffic cannot make a missing identity fresh. A mark at the exact
recording end is retained with an empty remaining interval, without inventing
later frames.

The report ranks complete payloads and individual LSB-first bits that remain
constant within each supporting interval, repeat for the same reported state
and differ between all reported states. Bits can qualify when other parts of
their payload vary. A single valid contradictory sample rejects a proposed
mapping, including a sample in an otherwise sparsely covered interval. Missing
or insufficiently covered intervals remain listed as uncertain: a candidate
with enough other repetitions is marked `partial`, not fully repeatable.
Labels with insufficient repeated references produce no candidates.

`repeatable` means only a repeated correlation in this recording. It confirms
neither meaning nor causation and cannot identify Auto, heating, a valve or a
new sensor on its own. Review counterexamples in other captures and independent
BDE references before assigning semantics. Timestamps still refer to the TCP
chunk completing the frame. The tool cannot recover electrical bus timing or
compensate for delayed marking.


## Recorded QUERY and reply shapes

Use the existing QUERY audit to compare checksum-valid queries with reply forms
in one selected recording:

```sh
uv run python -m tools.audit_recorded_queries diagnostics.json \
  --output tmp/query-shapes.json
uv run python -m tools.audit_recorded_queries diagnostics.json --capture event \
  --event-index 0 --output tmp/event-query-shapes.json
```

`--capture manual` is the default; `--capture event` selects the latest retained
event unless an index is supplied. `--event-index` requires event selection.
The output must differ from the input. Full HA exports, capture wrappers and
bare manual captures use the same loader and framing/checksum rules as the
inventory tool. The command opens no connection and has no sender.

The report includes exported-byte coverage, query arguments and counts, exact
expected reply identities, observed counts/first/last times, and other groups
with the same DP but different headers or lengths. Its lookup table describes
38 previously recorded query/reply forms, not a universal protocol specification.
Unsupported query forms remain listed without inventing a reply length.
`not_observed` means the expected form was absent from this selected capture;
it is not proof that the device rejected an individual request.

| Recorded QUERY DP | Argument | Recorded controller reply payload bytes |
| --- | --- | --- |
| `0160` | 1 | 1 |
| `051C` | 1 | 4 |
| `0330` | 0 | 4 |
| `0178` | 6 | 12 |
| `02D6` | 20 | 40 |
| `02DF` | 28 | 112 |

These examples demonstrate why an argument cannot simply be converted to a byte
count. An exact reply shape occurring in the same recording is **co-occurrence**,
not a paired transaction, control readback or proof of the request's sender.
Replies can precede requests or occur several times. The tool does not assign
meaning, units, freshness, access rights or permission to transmit. In particular,
the counter blocks have [recorded counterexamples to alias mappings](DATA_POINTS.md#unmapped-reply-blocks).
Keep these raw reports private.

For a non-JSON binary file, the CLI retains its earlier candidate-list output
without inventing timestamps; event selection is unavailable for that input.
The Python `inventory(bytes)` helper also retains that candidate-scan API,
including checksum status. Unlike the new capture audit, this byte scan does
not establish frame boundaries for embedded patterns.

## Metadatenantworten prüfen

`python -m tools.audit_metadata input.json --output result.json` prüft vollständige
Antworttelegramme auf `0033`, `0034` und `0038`. Die Eingabe ist ein JSON-Objekt
mit diesen drei Schlüsseln und je einem vollständigen Hex-Telegramm als Wert.
Das Werkzeug verwendet die vorhandene Inventarisierung und Prüfsumme; es öffnet
keine Verbindung zur Anlage. Abgeschnittene Antworten, abweichende Identitäten,
leere Nutzdaten und unterschiedlich lange Listen werden zurückgewiesen.

Die Ausgabe enthält positionsweise Datenpunkt, Typcode und Maskencode. Sie
bestätigt weder deren Bedeutung noch Schreibrechte oder einen vollständigen
Gerätekatalog. Für Antworten mit Identität `224000` und Datenpunkt `0033`, `0034` oder `0038`
wird das belegte Längenfeld `00` als 128 Byte Nutzdaten erkannt: insgesamt
138 Byte einschließlich Header und Prüfsumme. Diese Ausnahme gilt ausschließlich
für diese drei Antworten. Insbesondere bleiben leere Bestätigungen leer.
Die Herkunft und Grenzen der Belege beschreibt [METADATA_EVIDENCE.md](METADATA_EVIDENCE.md).
Die Prüfung vollständiger Frames bestätigt nicht, dass alle Katalogseiten oder
alle Datenpunkte eines Geräts enthalten sind.

Der getrennte `ReadProbe` ist weiterhin nur für die bereits beobachtete
Filterabfrage `0x00ED` vorbereitet. Er besitzt keinen Netzwerkzugriff und verlangt
einen koordinierten Sender. Ein erfolgreicher Offline-Test belegt keine sichere
Busarbitrierung über TCP. Empfangene passende Antworten können außerdem vom
regulären Master ausgelöst worden sein; sie beweisen allein keine Reaktion auf
eine eigene Abfrage. Die passive Integration startet keine solchen Tests.

Die [Gegenprüfung eines Community-Exports](COMMUNITY_EXPORT_ANALYSIS.md) beschreibt
belegte Gemeinsamkeiten, anlagenspezifische Lüfterwerte und die Grenzen gefilterter
SQL-Aufzeichnungen. Die Originaldaten wurden nicht als kontinuierlicher Busstrom
zusammengesetzt.

## Lüfterkennlinien vergleichen

`python -m tools.audit_fan_curves input.json --output result.json` vergleicht
vollständige Antworten auf `00D2`/`00D3` mit einer Liste von `00D7`-Antworten.
Die Ausgabe enthält ausschließlich numerische Kandidatenpositionen; sie ist
keine Erkennung der tatsächlichen Luftstufe. Eingabeformat, Belege und Grenzen
stehen in [FAN_CURVE_EVIDENCE.md](FAN_CURVE_EVIDENCE.md).
