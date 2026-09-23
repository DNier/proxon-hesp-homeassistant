# Data points and validation boundaries

Developer documentation · English. [Deutsche Nutzerdokumentation](../README.md#dokumentation).

This table describes the data-point mappings retained from version 0.8.0.
Version 0.9.0 adds capture status plus optional last-valid-data and connection
diagnostics: 51 sensors, three binary sensors and three capture buttons,
for 57 entities in total. Version 0.10.0's compressor-running binary sensor adds
one entity, derived from the existing speed reading. Automatic event recording
adds a diagnostic status and a clear/rearm button (60 entities total).
Beta 0.12.0b1 adds an optional local calendar sensor
and an optional calendar-alignment button (62 entities total). Existing
data-point mappings remain unchanged.
See [capture diagnostics](DIAGNOSTICS.md). Hardware scope is documented in
[compatibility](COMPATIBILITY.md).

`P` means the three-byte identity `11 80 00`; `C` means `22 40 00`.
The production decoder also requires reserved bytes `00 00`, the expected
payload length and a valid checksum. Integer and floating-point payloads use
little-endian order unless stated otherwise.

| Feature | DP / identity / payload bytes | Type and unit | Evidence and limitation |
|---|---|---|---|
| Requested fan level | 00E1 / P / 2 | Integer 0–4 | Display comparisons; request may differ from the displayed controller level during cooling |
| Operating mode | 020A / P / 2 | Enum | Eco Summer and Stove compared with display; other labels follow the protocol reference and need variant-specific validation |
| Room temperature | 0226 / P / 4 | float32 / °C | Compatible with rounded BDE display; not a precision calibration |
| Target temperature | 0227 / P / 4 | float32 / °C | Display comparisons; receive guard 15–30 °C is not a writable range |
| Ten temperatures | 03B7 / C / 22 | uint16 × 0.1 / °C | Positive encoding and channel mapping compared with display; negative encoding and fault sentinels unresolved |
| Supply/extract fan speeds | 00C9 / C / 8 | Two float32 / rpm | Display comparisons; finite values from 0 to 10000 |
| Compressor speed | 051C / C / 4 | float32 / rpm | Compared during heating, cooling and standstill; raw entity retained |
| Compressor running | Derived from validated compressor speed | Boolean | On above 0 rpm, off at 0; same freshness as speed. Does not identify heating, cooling, defrost or PTC activity |
| Bypass switching state | 0160 / C / 1 | Boolean, 00 or 01 | Reported switching state; not measured flap position |
| Intensive ventilation active | 01F8 / P / 4 | Bit 6 of uint32 | Activation, automatic end and manual-level-4 counterexample checked; other bits ignored |
| Controller fan level | 0208 / C / 4 | Allowlisted uint32 words | Ten observed words; other bits and words are not interpreted; disabled by default |
| Raw fan control values | 00D7 / C / 8 | Two float32 / no unit | No validated voltage or target-rpm interpretation; disabled by default |
| Filter remaining time | 00ED / C / 4 | uint32 / days | Display comparison and decrement observed; reset behaviour unresolved |
| Operating-hour counters | 02D0–02D5, 02D7, 02D9 / C / 4 | uint32 / h | Display mappings confirmed; reset behaviour unresolved, no statistics class |
| Device calendar (raw) | 032E / C / 4 | uint32 / no unit | Packed calendar value; internal key `uptime`, numeric state and existing preferences retained |
| Device date and time (local) | 032E / C / 4 | Local ISO text, minute resolution | Display-matched calendar edits; validated date and weekday; disabled by default |
| Device clock | 0330 / C / 4 | Packed HH:MM:SS | Experimental; no date or timezone; agrees with the calendar minute in reviewed captures; disabled by default |
| Raw diagnostics | Listed below / C | Hexadecimal bytes | Structural and checksum evidence only; disabled by default |

The temperature block supplies T1, T7, T4, T3, T5, T6, T8, T12, T10 and T13
in that order. Its eleventh slot is not published. Raw channel values above 1500
are rejected individually; valid neighbouring channels remain available.

Counter mappings are: `02D0–02D3` fan levels 1–4, `02D4` heat pump heating,
`02D5` heat pump cooling, `02D7` controller, `02D9` preheating.
The value `FFFFFFFF` is rejected for counters and filter days.

## Local device calendar

`032E` is a packed calendar value, not elapsed operating time. Observed BDE
changes to hour, minute, year, month and day match the received payloads.
For the little-endian uint32, bits 0–5 hold minutes, 6–10 hours, 11–13 the
weekday (Sunday = 0), 14–20 the year offset from 2000, 21–24 the month,
and 25–29 the day. Bits 30–31 have no established meaning and must be zero.

The optional `device_datetime` sensor returns local text such as
`2026-09-23T12:50`. It has no timestamp device class, timezone, unit or statistics
class: the protocol does not establish a UTC offset or daylight-saving rule.
It does not combine separately received date and second fields. The existing
`device_clock` sensor remains separate and the numeric `uptime` entity retains
its identity and value format, now labeled as the raw device calendar.

Invalid field ranges, impossible calendar dates and inconsistent weekdays do
not refresh the interpreted sensor. An observed initial state reported Sunday
for 1 January 2011, which was a Saturday; this is rejected. A correctly encoded
2011 date is not rejected merely because of its year. Validation does not prove
that the device clock matches real time. The optional [time-alignment button](CLOCK_SYNC.md) can explicitly correct
these fields; no automatic synchronization takes place. Normal 30-second freshness and disconnect rules apply;
raw diagnostics remain independently available.

## Optional diagnostics

Controller fan level accepts only these complete status words:

| Level | Status words |
|---|---|
| 1 | `8000100A` |
| 2 | `80001012` |
| 3 | `8000101A`, `8000131A`, `8000921A`, `8000931A` |
| 4 | `80001022`, `80001122`, `80001422`, `80001522` |

The two additional words `8000921A` and `8000931A` were compared with displayed
level 3 in Stove mode. Their other bits do not establish PTC, valve or heating
states. These additions extend the version 0.9.0 allowlist without changing
entity identities or enabled/disabled settings.

This allowlist does not establish a general status-bit mapping. The two fan
control values must each be finite and between 0 and 10000. They have no unit
or statistics class because their physical meaning has not been validated.

The 18 hexadecimal diagnostic sensors retain payload byte order and leading zeros:

| Payload bytes | Data points |
|---|---|
| 1 | 0168 |
| 2 | 0120, 0206, 0519, 0123, 020F |
| 4 | 051E, 006C, 00EE, 01F5, 0110, 0105, 0115, 011C, 0116, 051C, 0330, 051D |

The raw `051C` and `0330` entities coexist with their interpreted sensors.
Hexadecimal values are not physical measurements or confirmed actuator states.

### Fan control values and update timing

On the reviewed installation, common supply/extract pairs are 2500/2500 for
level 1, 4000/4000 for level 2, 5200/5200 for level 3 and 10000/10000 for level 4.
Level 2 has limited evidence. Level 4 also occurs with 10000/7000 while both
the requested and reported levels remain 4. These are installation-specific
observations, not a universal conversion or a validated physical unit.

During transitions, the request and control values can change before the next
controller-status poll, approximately five seconds later in reviewed captures.
Keep requested level, reported level, raw control values and measured rpm
separate. Do not infer heating or cooling from a fan-level change.

## Missing and invalid values

Each interpreted value has its own validation and freshness check. Invalid
updates do not refresh a value; after 30 seconds without a valid update it
becomes unavailable. Disconnect invalidates values immediately. Valid zero
speeds and off states remain valid readings. Raw diagnostics can remain available
when the corresponding numeric interpretation is invalid.

Temperatures and measured speeds use measurement statistics where configured.
Counters do not claim a reset model or total-increasing statistics. Existing
unique IDs and user-selected enabled/disabled settings are preserved on upgrade.

## Unimplemented interpretations

- **Fault text 0130:** not observed in the reviewed passive recording corpus.
  Encoding, response shape and display correspondence remain unverified.
  Missing text must not be presented as a fault-free state.
- **Current heating/cooling activity:** requested operating mode is insufficient.
  Reviewed recordings contain both hot and cold supply air in Comfort mode,
  and hot supply air with a running compressor after selecting Eco Summer.
  Cold supply air can persist after the compressor stops. Temperature
  differences and candidate valve bits do not yet distinguish all transitions
  and defrost operation. Operating-hour counters did not change within the
  short recordings; they do not provide instantaneous activity. No inferred
  heating/cooling state is published.
- **PTC state:** reviewed display comparisons show different PTC states with
  identical 006C and 0208 payloads. The 0168 value `02` also occurs with both
  displayed states. These values do not establish a direct PTC-state mapping.
- **Valve states:** candidate bits in 006C/0208 correlate with defrost and
  heating/cooling display states in a small sample, but compressor, bypass and
  operating conditions also change. Preheating has no positive display example
  in that sample. No valve mapping is validated. Further evidence needs
  timestamped display observations during a captured transition that separates
  the candidate state from those other changes; matching bits alone are
  insufficient.
- **Intensive duration or remaining time:** no validated data point. The
  integration does not substitute an estimated countdown.
- **Negative temperatures and error sentinels:** require independent evidence
  before changing the current receive guards.

## Compressor transition evidence

Passive event windows show recurring complete 0208 status-word sequences
(little-endian uint32). These observations describe received telemetry, not
verified electrical switching times or a heating/cooling classifier:

| Context | Observed sequence | Relationship to reported speed |
|---|---|---|
| Starts in Comfort | `8000101A → 8000121A → 8000131A` | Intermediate word lasts about 93 s; final word precedes positive RPM by about 47–52 s |
| Stops while Comfort remains selected | `8000131A → 8000111A → 8000101A` | Intermediate word begins about 91 s before zero RPM |
| Stop following a confirmed manual BDE mode change | `9000131A → 9000111A → 8000111A → 8000101A` | Mode changes to Eco Summer before zero RPM; the extra high bit remains unexplained |

These intervals come from a small set of windows and are not firmware timing
contracts. Status words also occur with zero RPM in other recordings. Bits 8,
9 and 28 must not be named as compressor, demand or valve states on this basis.
The operating-mode observation does not imply that the integration can set it.

The unsupported words above remain unavailable as controller fan levels after
freshness expiry. Requested fan level cannot validate their meaning: `8000111A`
also occurs with requested level 1 while both fan control values remain 5200.
Repeated values of 5200 do not independently prove the displayed controller level.
Unknown status words must not refresh a previous level or suppress valid sibling
readings. The existing complete-word allowlist is unchanged.

Supply air remains warm after reported RPM reaches zero. Raw points 03B6 and
0191 can clear roughly a minute after zero RPM in one context, but before zero
RPM following a manual mode change. Neither is a validated immediate compressor
or heating-active flag. Cooling and defrost still require separate reference
observations before a thermal-state classifier can be accepted.

## Reproducible evidence

Minimal recorded vectors are in `tests/fixtures/`; decoder tests cover exact
identities, lengths, checksum rejection, fragmentation and invalid values.
Feature-specific tests include `test_operating_telemetry.py`,
`test_intensive_ventilation.py`, `test_fan_diagnostics.py` and `test_controller.py`.
Display comparisons establish the scope described above; the automated tests
protect that interpretation but do not independently prove physical meaning.
Full recordings and personal display photographs are not distributed.

See [checksum derivation](CHECKSUM_ALGORITHM.md) and
[contribution requirements](../CONTRIBUTING.md) before proposing another mapping.

## Passive BDE-connection comparison

A tested BDE-side connection produced valid HESP at 19200/8N1 and the same 100
header/data-point/length identities already observed on the PTC-to-controller
connection. Opening measurement and switching-state pages exposed no additional
identities in that recording. This does not establish electrical equivalence,
a universal BDE baud rate or compatibility with other board revisions.
A single externally injected fan-level request produced no observable change
in the BDE display or subsequent telemetry; reliable control is not established.
A separate one-shot calendar SET at the original tap was reflected in controller
responses and confirmed on the BDE, without reversion during 65 seconds of
observation. Only this calendar action is exposed as an optional button.
This does not establish general control support or persistence across power loss.

For known SET messages, external-write evidence and limits of automated testing,
see [control evidence](CONTROL_EVIDENCE.md).

## Experimental status-bit observations (0.12.0b5)

Three disabled-by-default diagnostic binary sensors expose bits 8, 9 and 28 of
validated 224000/0208/4 responses. No actuator semantics are assigned. Raw bytes,
full little-endian status word and reception time accompany each observation.
Unknown words are accepted as raw observations but do not refresh the allowlisted
fan-level reading. Structural/checksum failures remain rejected; normal 30-second
freshness and immediate disconnect unavailability apply. This adds three entities
(65 on the main device). See the [German comparison guide](EXPERIMENTAL.md).
