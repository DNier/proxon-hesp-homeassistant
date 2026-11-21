# Bounded BDE operating-display indication

The optional diagnostic enum sensor **BDE operating display** reports `heating`
(German: **Heizbetrieb**) for three exact source combinations as of 0.16.9 and,
from 0.16.5, `blank` (German: **Betriebsfeld leer**) for a separate exact
source combination. The same entity reports `cooling` (German:
**Kühlbetrieb**) for one confirmed Comfort combination. The entity is
disabled by default. Each state describes the display label on the reference
installation. Physical heat output, PTC activity and defrost require
independent evidence.

## Admitted source combinations

All identities, lengths and original checksums are validated by the existing
receiver. The combination is intentionally finite; no individual status bit is
promoted to a heating flag.

| State | `118000/020A/2` | Complete `224000/0208/4` | Complete `224000/006C/4` | `224000/051C/4` |
| --- | --- | --- | --- | --- |
| `heating` | `2` / Eco Winter | `0x82001312` (`12130082`), `0x8200131A` (`1a130082`), or `0x82009312` (`12930082`, since 0.16.9) | `0x27` (`27000000`) | Finite, validated speed above zero |
| `blank` | `2` / Eco Winter | `0x8000100A` (`0a100080`) | `0x25` (`25000000`) | Finite, validated speed exactly zero |
| `cooling` | `3` / Comfort | `0x80001522` (`22150080`) | `0x0227` (`27020000`) | Finite, validated speed above zero |

Each source must be fresh within six seconds and receipts must form a coherent
context. The combination must persist for at least 15 seconds of actual received
source observations. Reading an unchanged cached property cannot create new
proof. Changes outside the admitted mode/status/valve context, source gaps,
invalid numeric/mode values, disconnects and restarts invalidate the derived display; a later valid combination must qualify
again. Any transition between admitted complete contexts, including heating
to blank and the reverse, starts a new 15-second proof window. The existing general telemetry freshness remains unchanged.

Other combinations are unavailable, including other complete level-3 status
words, uncorroborated startup/stop contexts and the longer bit-28 phases. Unavailable never means that the BDE display is
blank, that the heat pump is off or that heating has stopped. There is no fallback
to the last label, operating mode alone, a valve bit or warm supply air.

## Evidence and time alignment

A display reference is aligned using the full visible device-minute bracket.
Received device-calendar messages bound that interval without assuming that
Home Assistant and the BDE share a synchronized clock. A qualified reference
requires the exact mode, status and valve words and positive speed across the
bracket for a heating or cooling label. The tracker starts labelling after
15 seconds of coherent receipt.

| Status and valve word | Independent evidence and limit |
| --- | --- |
| `0x82001312 / 0x27` | Four BDE heating readings match qualified intervals. |
| `0x8200131A / 0x27` | Two BDE heating readings match qualified intervals at level 3. A separate interval in the same recording overlaps `0x8200111A`, so it supplies no additional label. |
| `0x9200131A / 0x27` or `/ 0xA7` | The reviewed intervals leave an unresolved word transition or have insufficient independent references. Both combinations remain unassigned. |

Count independent display episodes rather than matching raw windows. Raw
matches without an independent display label carry no label evidence.
`tests/fixtures/bde_display_frames.json` contains a minimal recorded reference.
`tests/fixtures/bde_display_fan3_frames.json` combines recorded wire frames
with synthetic receipt timing to test the qualification rule.

### Additional level 2 heating context (0.16.9)

One original BDE photo shows Eco Winter, level 2 and Heizbetrieb. Received
device-calendar responses bound the displayed minute. The complete status word
`0x82009312`, valve word `0x27` and mode remain stable across that bracket,
with positive compressor speed and source gaps below six seconds.

The start of the photo bracket precedes the tracker's 15-second qualification.
In the original replay, qualification starts only after 15 seconds of coherent
reception with positive speed. The public regression tests use one minimal
recorded status frame and synthetic combinations with the existing vectors.
The difference from `0x82001312` establishes this complete word only. The
neighboring words remain subject to their own display evidence.

## Blank-field evidence

Two independent BDE readings at Eco Winter and level 1 show an empty operating
field across the full qualified interval. A third compatible reference has a
short gap at the earliest possible observation time. A preceding compressor-stop
phase has a different complete status word and requires its own display
reference. Zero speed or Eco Winter on its own leaves the display field unknown.

Public regression tests use previously published wire frames with synthetic
timing to exercise qualification, transitions and Home Assistant availability.
The original display references establish the scope of the comparison.

## Cooling label in Comfort

Two independently captured P2 Comfort episodes show **Kühlbetrieb**. In both
episodes the complete status and valve words remained stable across the
qualifying device-minute bracket. Positive compressor speed and all four fresh
sources were present throughout. The second episode establishes at least 15
seconds of qualifying reception before the earliest possible image time.

Enable **P2 reference BDE display** in the integration options for the
[documented P2 configuration](COMPATIBILITY.md). The option is off by
default. This applies the P2-specific rule on the existing
`lt_zim_16_observed` connection. Qualification starts again after a
display profile, mode or connection change.
Other Comfort combinations may illuminate the upper green LED or report
positive compressor speed while the operating field is blank. The
adjacent status word `0x80001122` remains unassigned.
[Hardware compatibility](COMPATIBILITY.md).

## PTC counterexamples remain separate

Independent display references show PTC-Wohnen On while all three candidate
bits are clear. Alignment uses visible device-clock minutes or camera offsets
cross-checked against neighbouring numerical fan and temperature displays.
One reference uses timestamped extracted frames from an original video. The
operating-display rule classifies only the labelled contexts above, with PTC
interpretation evaluated separately. [PTC evidence and limits](STATUS_EVIDENCE.md)

## Integration and upgrade behaviour

The existing entity keeps its stable unique ID, no unit and no statistics class.
Version 0.16.5 adds only the `blank` enum option. Existing entity identities,
enabled settings, recording formats and configuration entries are preserved.
The display uses the data received on the existing passive connection. On other hardware or firmware the exact context may remain
unavailable; this does not extend the documented compatibility claims.

See [data points](DATA_POINTS.md), [switching-state boundaries](STATUS_EVIDENCE.md)
and [contributing requirements](../CONTRIBUTING.md).
