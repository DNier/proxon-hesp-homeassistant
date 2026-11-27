# Bounded BDE operating-display indication

The optional diagnostic enum sensor **BDE operating display** reports `heating`
(German: **Heizbetrieb**) for three original source combinations and, from
0.16.21, two additional P2-only combinations. Version 0.16.23 adds a third
P2-only combination. From 0.16.5, it reports `blank`
(German: **Betriebsfeld leer**) for a separate exact
source combination. The same entity reports `cooling` (German:
**Kühlbetrieb**) for one confirmed Comfort combination. The entity is
disabled by default. Each state describes the display label on the reference
installation. Physical heat output, PTC activity and defrost require
independent evidence.

## Admitted source combinations

All identities, lengths and original checksums are validated by the existing
receiver. The combination is intentionally finite; no individual status bit is
promoted to a heating flag.

| State | `118000/020A/2` | Complete `224000/0208/4` | Complete `224000/006C/4` | `224000/051C/4` | P2 reference option required |
| --- | --- | --- | --- | --- | --- |
| `heating` | `2` / Eco Winter | `0x82001312` (`12130082`), `0x8200131A` (`1a130082`), or `0x82009312` (`12930082`, since 0.16.9) | `0x27` (`27000000`) | Finite, validated speed above zero | No |
| `heating` (from 0.16.21) | `2` / Eco Winter | `0x8200931A` (`1a930082`) | `0x27` (`27000000`) | Finite, validated speed above zero | Yes |
| `heating` (from 0.16.21) | `2` / Eco Winter | `0x92009312` (`12930092`) | `0xA7` (`a7000000`) | Finite, validated speed above zero | Yes |
| `heating` (from 0.16.23) | `2` / Eco Winter | `0x92009312` (`12930092`) | `0x27` (`27000000`) | Finite, validated speed above zero | Yes |
| `blank` | `2` / Eco Winter | `0x8000100A` (`0a100080`) | `0x25` (`25000000`) | Finite, validated speed exactly zero | No |
| `cooling` | `3` / Comfort | `0x80001522` (`22150080`) | `0x0227` (`27020000`) | Finite, validated speed above zero | Yes |

For the Eco Winter operating display, each source must be fresh within seven
seconds and receipts must form a coherent context. The Comfort cooling display
keeps its six-second source limit. Initial qualification still requires at least
15 seconds of actual received source observations. Reading an unchanged cached
property cannot create new proof.

An already qualified heating label remains available when the status changes
between the heating combinations admitted for the active display profile while
every required source stays fresh and valid. This does not extend the admitted
words or allow a different valve word. A transition
to blank or cooling, an unassigned context, an expired or invalid source,
disconnect or restart invalidates the indication and starts a new qualification
window. There is no grace period beyond the source deadline. The green LED,
the mode-dependent fan-level indication and general telemetry retain their
separate freshness limits.

Other combinations are unavailable, including unassigned complete level-3 status
words, uncorroborated startup/stop contexts and unassigned bit-28 combinations.
Unavailable never means that the BDE display is
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
| `0x8200931A / 0x27` | A separately timed main-page photograph shows Heizbetrieb, level 3 and the lit LED; the received context remains unchanged throughout the device minute. The label is P2-only. |
| `0x92009312 / 0xA7` | A phone photo-information minute, user timing confirmation and independently received device clock agree. The whole minute has the same words and positive speed; the main page shows Heizbetrieb, level 2 and the lit LED. The label is P2-only. |
| `0x92009312 / 0x27` | Two separate P2 episodes show Heizbetrieb, level 2 and the lit LED. An approximate-minute reference and later offset-bearing camera originals align with native status/valve receipts and positive reported speed. Original mode/RPM receipt timing is not retained, so historical 15-second qualification is not asserted. |
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

### Additional P2 heating contexts (0.16.21)

Two separate main-page photographs support the additional complete contexts in
the table. Device-clock observations independently agree with each visible
minute; the accepted mode, status and valve words stay unchanged throughout
those minutes with positive compressor speed. The transmitted JPEGs contain
no camera exposure seconds; the original 0.16.21 comparison therefore used
minute-bounded references. Later inspection of the camera originals refined
the level-2 episode's nominal exposure times. The comparison still uses native
decoded Recorder receipts rather than an original wire-frame replay, and
exposure precision does not establish calibrated transition timing.

The level-2 reference's associated switching-state image has no visible clock.
Later inspection of the camera originals resolved the nominal exposure order:
the switching-state image was taken after the main-page image, with the received
valve indication changing from On to Off between them. MV-Abtau Off on that
later page therefore does not contradict the earlier main-page context.
Camera-to-receiver synchronization and display-update delay remain unmeasured;
the images do not establish a synchronized PTC or valve reference.

Both new heating contexts use the existing seven-second Eco Winter source
limit and 15-second initial qualification. The LED's separate eight-second
limit remains unchanged. Level 2 is additionally available only for the
complete P2 Eco Winter / `12930092` / `a7000000` / positive-RPM context, with
all four sources fresh within seven seconds. It does not become a generic
word-only fan rule. Existing word-only P2 fan rules retain their six-second
limit. No received interval is presented as permanently fresh telemetry.

### Additional P2 heating and level-2 context (0.16.23)

Two independent episodes on the reference P2 show Eco Winter, **Heizbetrieb**,
level 2 and a lit upper LED with the complete status/valve combination
`12930092 / 27000000`. One uses a confirmed approximate device-minute bracket;
the later episode uses offset-bearing camera-original exposure times. Native
status and valve receipts bracket the later photographs with the same complete
words, and Recorder retains positive compressor-speed changes. Requested fan
level remains a separate quantity and is not the level-2 reference.

This exact context admits the literal heating label and displayed level 2 only
with **P2 reference BDE display** enabled. All four actually received sources
must be fresh and coherent within seven seconds. Initial heating qualification
still requires 15 seconds of valid reception. Already qualified heating can
continue through changes between `12930092 / a7000000` and
`12930092 / 27000000` while all required sources stay valid and fresh.

The retained history does not expose original mode/RPM receipt times at the
photographs. Positive published RPM and status/valve receipt brackets do not
constitute a complete wire replay or retroactive qualification. The runtime
guards remain necessary. The `12930080 / 27000000`, `12930082 / 67000000` and
`12930082 / 47000000` LED additions establish neither a heating label nor a
new fan or PTC state.

## Further green LED contexts (0.16.24)

A direct user observation establishes that the upper green LED remained lit
through the reported availability gaps. A complete passive receiver capture
from the running 0.16.23 integration reproduces two of those gaps with the
gateway connected. Both contain Eco Winter status `1a930092`; the exact valve
words are `27000000` and `a7000000`, with valid positive compressor speed.
All four required sources continue to arrive within eight seconds. The
largest source interval in the retained capture is 7.607 seconds. These gaps
are therefore missing LED assignments rather than expired source data.

Version 0.16.24 admits these two complete contexts only for the selected P2
display, using `state_basis: display_reference`. The `27000000` combination
recurs in two distinct gaps; the `a7000000` combination is retained within
one of them. This difference in the number of occurrences remains part of the
evidence. No heating text, controller fan level, PTC state or general status-bit
meaning is assigned from the LED observation.

A separate gap coincides with loss of the gateway connection and other HA
telemetry. The reported physical LED can remain on during that gap, but the
integration cannot determine its current state without incoming data. It
continues to report unavailable on disconnect, expired or invalid sources,
other modes, unsupported words and display-profile changes. Historical states
are not rewritten. Public receiver regressions use synthetic combinations and
receipt timing; the complete original capture remains private.

### Extended observation and Comfort comparison

The reference user directly observed the LED continuously green throughout
a 46-hour observation in November 2026, including every HA availability gap.
This is a reported physical observation,
not an inferred continuity state. A complete, paginated Recorder read covers
the entire 46-hour window and retains 247 LED rows, 263 status-entity
rows, 195 valve-entity rows and 15,445 RPM rows. Each of the status and valve
series includes five unavailable rows. No LED Off state is
recorded. The 125 unavailable rows form 122 continuous unavailable periods;
attribute updates can divide one period into several rows.

The retained complete words add the following finite LED references in 0.16.24,
with fresh positive RPM and the selected P2 display required throughout:

| Mode | Complete `224000/0208/4` payload | Admitted complete `224000/006C/4` payloads |
| --- | --- | --- |
| Eco Winter | `12930090` | `27000000`, `a7000000`, `c7000000`, `e7000000` |
| Eco Winter | `12930092` | `c7000000`, `e7000000` |
| Eco Winter | `1a930082` | `67000000` |
| Eco Winter | `1a930092` | `27000000`, `47000000`, `67000000`, `a7000000`, `e7000000` |
| Comfort | `1a930080` | `27000000`, `47000000`, `67000000` |
| Comfort | `1a930090` | `27000000`, `a7000000`, `c7000000`, `e7000000` |

After the switch to Comfort, the old integration's LED remains
unavailable through the end of the window. The words `1a930082` / `1a930080`
and `1a930092` / `1a930090` differ by `0x02000000` (bit 25), and the retained
contexts share several valve words and positive RPM. Eco Winter itself also
contains `12930080` and `12930090`; the difference does not establish a general
mode or LED bit. Only the listed mode/status/valve tuples are admitted.

Immediately after the mode change, Recorder briefly retains the prior
Eco Winter word `1a930082`. That cached combination is excluded from Comfort:
the first newly received Comfort status is `1a930080`. A mode change continues
to require a new status receipt before the LED becomes available.

Complete original receiver windows inside the observation interval and a
separate current passive snapshot reproduce unknown Comfort contexts while
all required sources are fresh. They include `1a930080 / 27000000` and
`1a930090 / a7000000` or `/ 27000000`. Recorder preserves state changes rather
than every unchanged source receipt, so it does not prove uninterrupted source
freshness for the whole 46 hours. No unrecorded wire interval is reconstructed.
Original recordings, exact household timestamps and the complete interval
matrix remain private.

All new references use `state_basis: display_reference` without
`assumed_state`. The existing eight-second deadlines, invalid-value rejection,
connection reset and display-profile checks remain in force. The physical LED
observation does not make missing telemetry current. These additions establish
neither a heating label nor new fan/PTC semantics. Existing independently
confirmed fan-level rules remain unchanged.

## Additional Stove LED reference (0.16.25)

Two separately recorded reference-P2 BDE episodes show the upper LED green
in Stove mode with full status `1a930080` (`0x8000931A`), valve word
`27000000` (`0x27`) and finite positive compressor RPM. The displayed
PTC-Wohnen state is On in one recording and Off in the other. The retained
mode/status/valve/RPM receipts remain within six seconds across both optical
brackets; their complete original streams have valid checksums and no unparsed
bytes. This is an optical Stove reference, rather than an inference from the
matching Comfort status word.

Version 0.16.25 admits only this complete Stove tuple, with the selected
P2 display and the existing individual eight-second source limits. A mode
change requires a new status receipt even when Comfort and Stove share the
same payload. The reference adds no heating text, fan-level or PTC meaning.
Other Stove status/valve combinations remain unassigned.

Bit 8 is set in the observed green Stove word and the admitted Eco Winter and
Comfort words. A separately observed dark Stove episode instead has
`1a920080`, valve `a7000000` and zero RPM. Its camera alignment is weaker and
the valve/RPM context also differs; it is not a new Off mapping or a controlled
single-bit contrast. An independent visible LED transition with sufficiently
precise complete receiver timing is still needed for a general bit rule.
Positive RPM is an admission condition for this finite reference, not a
necessary condition for the physical LED: other retained optical references
show green at zero RPM.

## Observed availability gaps (November 2026)

Reference observations reviewed on 26 and 27 November show coverage gaps in
the pre-0.16.23 contexts. An unavailable LED entity
can coincide with a visibly green LED, both with a dark screen and with a lit
main page. The later photo sequence shows **Heizbetrieb** during the interval
bracketed by two HA screenshots of the same unavailable LED state. A missing
operating label is therefore not a necessary companion of the LED availability
gap. Subsequent native history confirms that the LED, operating-display and
controller-fan entities were all unavailable during the later photographs;
the complete status/valve words were `12930092 / 27000000`.

A separately exposed switching-state page in the sequence shows the LED green
with Bypass, PTC-Wohnen, MV-Abtau, MV-Vorwärme and MV-Heizen/Kühlen all Off.
The main and switching pages were photographed at different times; they do not
establish a simultaneous discrepancy or equate the heating label with an
actuator state.

The original camera timestamps include an offset, whereas the screenshots do
not. Their nominal timing and visible date/minute context agree, but clock
synchronization was not measured. Each short photo sequence is one episode,
and still images do not establish continuous illumination between exposures.
The reviewed evidence does not establish original mode/RPM receipt timing at
the later exposures. Version 0.16.23 admits the exact context under the existing
runtime freshness requirements, without asserting a historical qualification
replay or a general status-bit interpretation.

The earlier retained interval brackets green-LED photos with status payload
`12930080` (`0x80009312`) and valve payload `27000000` (`0x27`). That status
word is now admitted only for the LED with this exact valve word, Eco Winter
and fresh positive RPM. The retained status and valve receipts do not establish
original mode/RPM freshness at the exposures. Its payloads are not assumed for
the later photo sequence and add no operating-display or fan interpretation.
See [LED availability and source limits](DATA_POINTS.md#upper-green-bde-led).

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
