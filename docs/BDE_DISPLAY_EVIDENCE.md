# Bounded BDE operating-display indication

The optional diagnostic enum sensor **BDE operating display** reports only
`heating` for the two exact source combinations below. The German state is
**Heizbetrieb**. It is disabled by default. This mirrors a corroborated display
label on the reference installation; it does not identify physical heat output,
PTC activity, cooling or defrost activity.

## Admitted source combinations

All identities, lengths and original checksums are validated by the existing
receiver. The combination is intentionally finite; no individual status bit is
promoted to a heating flag.

| Source | Required value |
| --- | --- |
| `118000/020A/2` | Operating mode `2` / Eco Winter |
| `224000/0208/4` | Complete little-endian word `0x82001312`, payload `12130082`; or, from 0.16.2, `0x8200131A`, payload `1a130082` |
| `224000/006C/4` | Complete little-endian word `0x27`, payload `27000000` |
| `224000/051C/4` | Finite, validated compressor speed above zero |

Each source must be fresh within six seconds and receipts must form a coherent
context. The combination must persist for at least 15 seconds of actual received
source observations. Reading an unchanged cached property cannot create new
proof. Changes outside the admitted mode/status/valve context, source gaps,
invalid numeric/mode values, disconnects and restarts invalidate the derived display; a later valid combination must qualify
again. A transition between the two admitted complete contexts also starts a
new 15-second proof window. The existing general telemetry freshness remains unchanged.

Other combinations are unavailable, including other complete level-3 status words, startup, stop
and the longer bit-28 phases. Unavailable never means that the BDE display is
blank, that the heat pump is off or that heating has stopped. There is no fallback
to the last label, operating mode alone, a valve bit or warm supply air. No
`off`, `cooling` or `defrost` enum option is inferred.

## Evidence and time alignment

Four independent photo/readout references show the BDE label Heizbetrieb with
the original `0x82001312 / 0x27` combination. In each case, the full displayed device-minute interval lies
inside the same validated status/valve/mode context with positive speed. This is
stronger than assigning a later Telegram receipt time to an earlier trigger.
The references also satisfy the causal 15-second condition at their approximate
readout times.

Version 0.16.2 additionally admits only `0x8200131A / 0x27`, supported by two
independently recorded episodes showing Eco Winter, level 3 and Heizbetrieb.
For each, all four source values and their freshness remain valid across the
entire conservative received device-minute bracket, already after the 15-second
proof window. Device-calendar observations were matched to the visible minute;
the device clock was not assumed synchronized to the camera or HA clock.
A later point from the same recording is not an additional time-safe reference:
its displayed-minute bracket also contains `0x8200111A`. That word remains
unadmitted even though a separate fan-level mapping exists for it.

The unchanged production decoder and display tracker were replayed across 533
terminal archived windows and 60 deduplicated historical diagnostic windows.
The extension preserves all four earlier qualifying current photo references and
adds one current photo plus two nominal historical points. Only one of those
historical points supplies the additional time-safe episode described above.
No opposing qualified label was found among the known retained labelled points. Three additional historical raw matches
of the original combination lack a contemporaneous visible BDE label and
remain unlabelled, rather than being counted as confirmations. Additional
raw-only matches of the new combination likewise supply no independent display labels. These are recording windows, not a count of
independent operating cycles or a continuous observation of the entire period.

Both initially considered `0x9200131A` extensions are excluded. The `0x27`
photo points occur close to a complete-word transition, and the displayed clock
minute does not resolve which word was present when the picture was taken.
The `0xA7` variant has insufficient independent references whose whole displayed
minute is unambiguous under this stricter review. Neither is admitted by masking
bits or extrapolating the confirmed normal-winter combination.

Original household photos, full recordings, device times and Home Assistant
history remain private. The original minimal reference sequence in
`tests/fixtures/bde_display_frames.json` remains unchanged. The additional
`tests/fixtures/bde_display_fan3_frames.json` combines only wire frames already
published before this extension, with explicitly synthetic timing for regression
tests. Those synthetic sequences are not additional recorded display references.
The two independent recorded episodes were replayed separately against the
production decoder and tracker; their original wire bytes and received intervals
were retained in private evidence rather than added to the public fixture.

## PTC counterexamples remain separate

The reviewed PTC-Wohnen-on examples with all three candidate bits clear were
rechecked against independent timing evidence. One uses original camera offsets
and neighbouring numerical fan/temperature displays; another uses device-clock
minutes and retained video presentation timestamps. A preserved HA history also
agrees with the corresponding raw host timeline. PTC/LED/valve transitions were
not used as the synchronization reference.

These checks support retaining the counterexamples to a universal PTC mirror.
The original video container for one historical case is no longer available in
the reviewed local set; retained extracted frames and their original timestamp
logs provide its provenance. This limitation is not hidden or converted into a
new positive mapping. The bounded BDE display adds no PTC state or permission.

## Integration and upgrade behaviour

The new entity has a separate stable unique ID, no unit and no statistics class.
Existing entity identities, enabled settings, recording formats and configuration
entries are preserved. The receiver still owns one passive TCP connection;
observing the display creates no query, control command, clock write or additional
connection. On other hardware or firmware the exact context may remain
unavailable; this does not extend the documented compatibility claims.

See [data points](DATA_POINTS.md), [switching-state boundaries](STATUS_EVIDENCE.md)
and [contributing requirements](../CONTRIBUTING.md).
