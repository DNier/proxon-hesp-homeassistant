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
