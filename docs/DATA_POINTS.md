# Data points and validation boundaries

Developer documentation · English. [Deutsche Nutzerdokumentation](../README.md#dokumentation).

This table describes the integration's data-point mappings.
See [entity migration](#readable-telemetry-and-entity-migration-0150) for
legacy sensor replacements.
The following counts describe earlier releases at the time of their additions,
not the current entity total.

Version 0.9.0 adds capture status plus optional last-valid-data and connection
diagnostics: 51 sensors, three binary sensors and three capture buttons,
for 57 entities in total. Version 0.10.0's compressor-running binary sensor adds
one entity, derived from the existing speed reading. Automatic event recording
adds a diagnostic status and a clear/rearm button (60 entities total).
Beta 0.12.0b1 adds an optional local calendar sensor
and an optional calendar-alignment button (62 entities total). Existing
data-point mappings remain in use.
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
| Ten temperatures | 03B7 / C / 22 | int16 × 0.1 / °C | Positive channel mapping and negative T6 display reference; receive guard −50…150 °C; ambiguous FFFF remains unavailable; [evidence](TEMPERATURE_EVIDENCE.md) |
| Supply/extract fan speeds | 00C9 / C / 8 | Two float32 / rpm | Display comparisons; finite values from 0 to 10000 |
| Compressor control output | 0120 / C / 2 | uint16 / % | Controller output corroborated on the P2 reference. 30 % can occur at 0 rpm. Disabled by default. [Evidence and migration](#compressor-control-output-0168) |
| Compressor speed | 051C / C / 4 | float32 / rpm | Compared during heating, cooling and standstill; raw decoding retained internally |
| Compressor running | Derived from validated compressor speed | Boolean | On above 0 rpm, off at 0; same freshness as speed. Does not identify heating, cooling, defrost or PTC activity |
| Bypass switching state | 0160 / C / 1 | Boolean, 00 or 01 | Reported switching state; not measured flap position |
| Intensive ventilation active | 01F8 / P / 4 | Bit 6 of uint32 | Activation, automatic end and manual-level-4 counterexample checked; other bits ignored |
| Controller fan level | 0208 / C / 4 | Allowlisted uint32 words | Fifteen exact words plus two P2-only fresh Eco Winter contexts; disabled by default |
| Current supply/extract fan control | 00D7 / C / 8 plus fresh same-direction 00D2/00D3 stages | Matched configured stage / % | Raw control divided by 100 must match a fresh stage; each channel independent; no voltage, airflow or fan-level inference; disabled by default |
| Configured fan stages | 00D2, 00D3 / C / 16 each | Four float32 / % each | Supply/extract stage 1–4; community app corroboration, finite 0–100; disabled by default |
| Cooling threshold | 0110 / C / 4 | float32 / °C | Service-app and recorded-value corroboration; receive guard 0–100, not a manufacturer setting range; raw decoding retained internally |
| Heat pump start threshold (configured) | 0115 / C / 4 | float32 / K | ServiceApp `WpEinschaltschwelle`; temperature difference; optional. [Evidence and scope](SERVICE_SETTINGS_EVIDENCE.md#configured-heat-pump-thresholds) |
| Heat pump continuous-run threshold (configured) | 011C / C / 4 | float32 / °C | ServiceApp `WpDauerOnTemp`; controller setting; optional. [Evidence and scope](SERVICE_SETTINGS_EVIDENCE.md#configured-heat-pump-thresholds) |
| Maximum heating/cooling output | 0116 / C / 4 | Two uint16 / % | Configured limits, not measured power; each 0–100; raw decoding retained internally |
| Filter remaining time | 00ED / C / 4 | uint32 / days | Display comparison and decrement observed; reset behaviour unresolved |
| Operating-hour counters | 02D0–02D5, 02D7, 02D9 / C / 4 | uint32 / h | Display mappings confirmed; reset behaviour unresolved, no statistics class |
| Device date and time (local) | 032E / C / 4 | Local ISO text, minute resolution | Display-matched calendar edits; validated date and weekday; disabled by default |
| Device date | 032E / C / 4 | HA date | Date portion of the validated device calendar; shares its freshness; disabled by default |
| Device clock | 0330 / C / 4 | Local HH:MM:SS text | Observed local device time; no date or timezone; agrees with the calendar minute in reviewed captures; disabled by default |
| Raw diagnostics | Listed below / exact identity | Hexadecimal bytes | Partly or fully uninterpreted payloads; disabled by default |

The temperature block supplies T1, T7, T4, T3, T5, T6, T8, T12, T10 and T13
in that order. Its eleventh slot is not published. Values use signed little-endian
deci-degrees with a receive plausibility guard of −500…1500 raw (−50…150 °C),
not manufacturer operating limits. `FFFF` remains excluded: an isolated −0.1 °C
interpretation cannot yet be distinguished from a possible error value. Invalid
channels do not refresh previous readings; valid neighbouring channels continue
to update. Normal freshness and disconnect rules remain in force. See
[temperature evidence and limits](TEMPERATURE_EVIDENCE.md).

Counter mappings are: `02D0–02D3` fan levels 1–4, `02D4` heat pump heating,
`02D5` heat pump cooling, `02D7` controller, `02D9` preheating.
The value `FFFFFFFF` is rejected for counters and filter days.

## Compressor control output (0.16.8)

`compressor_command_percent` reports the controller's current compressor control
output for the manually selected `lt_zim_16_observed` profile. The verified
hardware is the P2 reference. Its captures contain `0`, values from `30` through
`90`, and `100`. The ServiceApp shows `WpAktLeistung` as a percentage and describes
it as the current compressor control output. [ServiceApp field](https://github.com/Mannheim68199/proxon-hesp-esp32/blob/2b4294cfb15cede4b145421037703990fd9958a8/Screenshots/ServiceApp_W%C3%A4rmepumpe.jpg)

The decoder accepts checksum-valid `22 40 00` responses with data point `0120`
and exactly two payload bytes. It reads a little-endian unsigned integer
as a whole percentage. The receive range is 0–100. Out-of-range values do not
refresh the typed reading. Availability expires after 30 seconds without a
valid value or when disconnected. Recorded 30 % samples include standstill at
0 rpm. Use `compressor_rpm` for actual rotation. Electrical or thermal power
requires a separate measurement.

The read-only diagnostic is disabled by default. Setup replaces the legacy
`raw_0120` entity with `compressor_command_percent`, preserving existing opt-in
through the entity migration rules below. Update old dashboard and automation
references to the new entity and its numeric state. The new percent sensor has
its own history. Diagnostic captures retain the original telegrams.

## Readable telemetry and entity migration (0.15.0)

The integration replaces these legacy sensor keys when the updated integration
entry is set up. The first seven replacements were introduced in 0.15.0.

| Retired key | Readable replacement keys |
| --- | --- |
| `raw_0110` | `cooling_threshold` |
| `raw_0116` | `max_heating_output`, `max_cooling_output` |
| `raw_051c` | `compressor_rpm` |
| `raw_0330` | `device_clock` |
| `uptime` | `device_date`, `device_clock` |
| `fan_supply_control` | `fan_supply_control_percent` |
| `fan_extract_control` | `fan_extract_control_percent` |
| `raw_0120` | `compressor_command_percent` |
| `raw_0115` | `heat_pump_start_threshold` |
| `raw_011c` | `heat_pump_continuous_run_threshold` |

An enabled legacy sensor enables a replacement only when that replacement was
disabled by the integration. Explicit user-disabled replacements remain disabled.
Other entity IDs and enabled/disabled preferences are unchanged. The existing
combined `device_datetime` entity also remains available.

Dashboards and automations referring to retired entity IDs must be updated to
the replacement entities. The fan percentages use new identities; historical
control values such as 5200 are not converted to 52 % or mixed into the new
percentage histories. Raw decoding and diagnostic exports are retained
internally, including invalid or unmatched control payloads. This removes
redundant sensor entities without discarding protocol evidence.

`fan_supply_control_percent` and `fan_extract_control_percent` are optional
diagnostics named **Zuluft-Ansteuerung** and **Abluft-Ansteuerung**. They return
the fresh received configured stage percentage that matches the current control
value. Their precise validation and freshness rules are described
[below](#fan-control-values-and-update-timing).

## Unmapped reply blocks

See [service-setting evidence](SERVICE_SETTINGS_EVIDENCE.md) for version 0.14.0
settings, source limits, freshness and invalid-data behaviour.

Recorded controller replies include `224000/02DF/112` (28 little-endian uint32
slots), `224000/02D6/40` (20 uint16 slots) and `224000/0178/12` (six uint16
slots). These describe numerical forms, not confirmed units or BDE meanings.
The production decoder does not publish them as additional counters.

The [Community SQL export](COMMUNITY_EXPORT_ANALYSIS.md#sammelantwort-02df-gleichheit-im-untersuchten-export)
contains equal bulk and individual values. Comparison with original diagnosis
captures rules out a universal alias mapping:

| Recorded comparison | Individual `02D4` versus fifth `02DF` slot | `02D6` versus last 20 `02DF` slots |
| --- | --- | --- |
| P-series, earlier capture | Nonzero individual value, zero bulk value | Different values |
| P-series, later transition | Both increment by one, with a constant nonzero difference | Different values |
| Separate FWT2L capture | Different values and a different offset from the P-series examples | Different values |

All three compared captures have checksum-valid frames and no unparsed stored
bytes. In the P-series transition, both values rise by one but retain the same
nonzero difference. Shared increments do not establish a shared zero point,
reset behaviour, or a counter since restart. The FWT2L values also rule out
reusing the P-series difference for other installations. Neither block may
refresh or overwrite the confirmed individual operating-hour sensors.

The six `0178` values are 80, 15, 29, 45, 65 and 0 in these captures. Their
meaning remains open; apparent relationships to fan settings need an independent
BDE comparison. QUERY arguments and reply lengths are observed separately;
an argument alone is not a general byte-count or register-type rule.

## Local device calendar

`032E` is a packed calendar value, not elapsed operating time. Observed BDE
changes to hour, minute, year, month and day match the received payloads.
For the little-endian uint32, bits 0–5 hold minutes, 6–10 hours, 11–13 the
weekday (Sunday = 0), 14–20 the year offset from 2000, 21–24 the month,
and 25–29 the day. Bits 30–31 have no established meaning and must be zero.

The optional `device_datetime` sensor returns local text, for example the
synthetic value
`2026-01-15T12:00`. It has no timestamp device class, timezone, unit or statistics
class: the protocol does not establish a UTC offset or daylight-saving rule.
It does not combine separately received date and second fields. The
`device_date` and `device_clock` sensors provide separate readable values.
The numeric `uptime` entity is retired in 0.15.0; its internal reading remains
available for calendar validation, time alignment and diagnostic exports.

Invalid field ranges, impossible calendar dates and inconsistent weekdays do
not refresh the interpreted sensor. An observed initial state reported Sunday
for 1 January 2011, which was a Saturday. A correctly encoded 2011 date remains
valid. The checks establish calendar consistency. The [device-time
feature](CLOCK_SYNC.md) can correct a mismatch with Home Assistant when
explicitly requested or enabled. Normal 30-second freshness and disconnect
rules apply. Raw calendar evidence remains available internally.

## Optional diagnostics

Controller fan level accepts only these complete status words:

| Level | Status words |
|---|---|
| 1 | `8000100A` |
| 2 | `80001012`, `80001312`, `82001312`, `82009312` |
| 3 | `8000101A`, `8000131A`, `8000921A`, `8000931A`, `8200131A`, `8200111A` |
| 4 | `80001022`, `80001122`, `80001422`, `80001522` |

The two additional words `8000921A` and `8000931A` were compared with displayed
level 3 in Stove mode. Their other bits do not establish PTC, valve or heating
states. These additions extend the version 0.9.0 allowlist without changing
entity identities or enabled/disabled settings.

Version 0.15.1 adds only `8200131A`: the BDE showed level 3 during natural winter
heating while the recorded complete word remained stable. Requested level 1
and fan control percentages are separate observations, not its validation source.
Bit 25 is not assigned a meaning and is not masked off for other words. The
transition word `82001212` and the complete word `92001312` still need
their own level references.

The complete word `8200111A` (payload `1a110082`, identity
`224000/0208/4`) is supported for level 3 by a BDE reading within a stable
Recorder interval of about 91 seconds. The interval comes from checksum-validated
sensor values. Tests reproduce the observed payload with synthetic framing and
checksum. Words including `8200101A` and `8200121A` remain unassigned.

Two independent Eco Winter display readings place level 2 within stable raw
intervals of the complete word `82001312` (payload `12130082`). Each
displayed device minute is fully contained in its matching interval. Both
captures contain frame `2240000802000008121300820001` with its recorded checksum.
Tests replay that frame at every TCP split. The mapping applies to that complete
word. `82001212` and `92001312` remain unassigned. A level 2 display
reference overlaps a transition between complete words.

Version 0.16.6 adds only `80001312` (payload `12130080`, identity
`224000/0208/4`) as level 2. A BDE main-page reference shows Eco Winter and
level 2. Received device-calendar observations independently bound the visible
clock minute; validated Recorder reception attributes retain this exact word
across the entire bracket with gaps below six seconds. The device clock is not
assumed synchronized to the host clock, and the later photo does not label the
earlier compressor-start edge.

A separately retained earlier capture contains the complete frame
`22400008020000081213008079a2`, including its original checksum. That capture
ends before the photo: the display comparison uses Recorder reception values,
not retained TCP bytes at photo time. Tests replay only this minimal recorded
frame, including its checksum, at every TCP split. This single-episode reference
adds no heating, blank-field, PTC or valve interpretation; the other complete
words remain subject to their own display comparisons.

Version 0.16.9 adds `82009312` (payload `12930082`, identity `224000/0208/4`)
as level 2. A BDE main-page photo shows level 2 in Eco Winter. The exact
word remains fresh throughout the displayed-minute bracket in the original
capture. The same episode supports the separate [bounded heating context](BDE_DISPLAY_EVIDENCE.md#additional-level-2-heating-context-0169).

Two independent P2 observations in Eco Winter support displayed level 3 for
`0x9200131A` (payload `1a130092`, identity `224000/0208/4`). One whole
device minute contains the exact word. For the second observation the
observed room-temperature display and integer device-clock seconds both
place the image within that exact word's interval. The temperature
comparison allows one additional polling interval. Two other level 2
photographs have mixed words within their displayed minutes. With **P2
reference BDE display** enabled, the word produces level 3 when a preceding
Eco Winter mode and this status are both fresh within six seconds. A profile
or mode change, stale mode, or reconnect requires a new matching status.
The operating-display and LED rules use their own contexts.

Version 0.16.20 adds displayed level 3 for the complete word `0x8200931A`
(payload `1a930082`, identity `224000/0208/4`) through the same P2-only path.
The original main-page reference shows Eco Winter and level 3. Preserved passive
frame brackets agree at the approximate send time; Recorder retains the exact
word across the displayed minute and the surrounding interval. This reference
does not derive level 3 from requested level, fan percentages or compressor
speed. Fresh preceding Eco Winter mode and status within six seconds are
required; the general decoder allowlist is unchanged.

Version 0.16.21 adds displayed level 2 for the **complete P2 context** Eco
Winter / `0x92009312` (`12930092`) / valve `0xA7` (`a7000000`) / finite
positive compressor RPM. All four sources must be fresh and coherent within
seven seconds. Enable **P2 reference BDE display** for this additional rule.
Version 0.16.23 additionally admits valve `0x27` (`27000000`) with the same
status, mode, positive-RPM and seven-second source requirements. Two separate
P2 episodes show level 2 in this exact context, including one with
offset-bearing original camera times and matching status/valve receipts.
Requested fan level is not its optical validation source. Original mode/RPM
receipt timing is not retained at the photographs; the runtime must still
receive all four fresh sources. Other valve words, a different mode, expired
sources or a stopped compressor do not admit this level. The general decoder
and existing six-second P2 word-only rules are unchanged.

This allowlist does not establish a general status-bit mapping. Current fan
control percentages have separate validation based on fresh same-direction
configured stages, as described below. Their availability does not depend on
this controller-level allowlist and they have no statistics class.

Optional controller raw sensors retain payload byte order and leading zeros.

| Payload bytes | Data points |
|---|---|
| 1 | 0168 |
| 2 | 0206, 0519, 0123, 020F |
| 4 | 051E, 006C, 00EE, 01F5, 0105, 051D |

Raw decoding and diagnostic captures still include the
[retired raw sensor data points](#readable-telemetry-and-entity-migration-0150).
The retained hexadecimal
states are complete payloads, not physical measurements or complete actuator
interpretations. For example, selected `006C` valve bits are mapped below,
while other bits and unreviewed complete words remain uninterpreted.

Four further optional diagnostics retain complete observed payloads for
event comparisons. Equal data-point numbers on different telegram identities
remain separate; no PTC, demand or actuator meaning is assigned:

| Entity key | Telegram identity | Data point | Payload bytes |
|---|---|---|---|
| `raw_118000_01f8` | `118000` | `01F8` | 4 |
| `raw_118000_03b6` | `118000` | `03B6` | 4 |
| `raw_118007_0191` | `118007` | `0191` | 2 |
| `raw_0208` | `224000` | `0208` | 4 |

These entities are disabled by default and belong to the main device's
diagnostics. Values are lowercase hexadecimal payload bytes without a prefix,
unit, device class or statistics class. All bit patterns, including zero and
uninterpreted status words, remain raw observations. The existing intensive
ventilation and experimental status-bit entities keep their identities and
interpretations. `118007/0191` is accepted only for that exact header, not as a
controller response or a different panel node. Reserved bytes, expected length
and checksum validation remain mandatory; no additional queries are sent.

These four raw sensors and `raw_006c` expose `source_header`,
`dp_id`, `payload_length` and, while fresh, `last_valid_update` attributes.
The last attribute is the received sample's UTC observation time, independent
of device time. Identical valid payloads refresh it; invalid frames do not.
Disconnect and normal per-point expiry remove it and make the value unavailable.
An event observer must distinguish a hexadecimal state change from an
attribute-only freshness update. HA history contains decoded payload samples,
not a complete bus recording; preserve raw captures when frame order, headers
or repeated telegrams matter.

### Fan control values and update timing

The historical recordings include supply/extract control pairs 2500/2500 for
level 1, 4000/4000 for level 2, 5200/5200 for level 3 and 10000/10000 for level 4.
The completed local stage 1–4 comparison supports the factor-100 relationship
to configured stages 25/40/52/100; asymmetric community/FWT comparisons and
service-app percentage labels extend that evidence. Level 4 also occurs with
10000/7000 while both requested and reported levels remain 4. These examples
do not establish a fixed global mapping from a raw value to a fan-level number.
See [fan-curve evidence](FAN_CURVE_EVIDENCE.md) for the recorded comparisons.

In 0.15.0, each finite `00D7` control value in 0–10000 is divided by 100 and
compared only with fresh valid configured stages of its own direction:
`00D2` for supply, `00D3` for extract. Comparison uses absolute tolerance
`0.0001` and relative tolerance `0`. On a match, the sensor returns the received
configured stage percentage. It does not publish an unrestricted conversion of
arbitrary unmatched values. Each direction is evaluated independently, and
duplicate matching stage values do not require a stage-number choice.

Both the control sample and a matching stage must be fresh under the normal
30-second rule. Without fresh valid matching data, that channel is unavailable,
as it is on disconnect. Invalid samples do not refresh the last valid reading.
Zero is accepted only when a fresh matching
stage is configured as 0 %. There is no closest-stage rounding, persisted-curve
fallback or assumed zero. A controller fan-level reading is not required:
an unknown controller status word does not suppress a valid percentage match.

The percentage describes fan control according to the matched received curve
stage, not measured voltage, airflow, fan speed, operating mode or Auto/manual
selection. Configured stages, current control percentages and measured speeds
remain separate readings.

During transitions, the request and control values can change before the next
controller-status poll, approximately five seconds later in reviewed captures.
Keep requested level, reported level, current control percentages and measured rpm
separate. Do not infer heating or cooling from a fan-level change.

### Fan selection depends on operating mode

The reference BDE offers five modes: Off, Eco Summer, Eco Winter, Comfort and Stove.
Comfort and Stove let the controller determine the fan level; manual level
selection is unavailable. Intensive ventilation is a timed switch to level 4
available in those two modes. Eco Summer and Eco Winter offer a fixed level
1–4 or Auto, without a separate intensive-ventilation option. Manually selecting
level 4 in Eco is not intensive ventilation. In those Eco modes, Auto follows a
user-configured weekly time/level schedule; it is not evidence of demand-based
automatic ventilation. Off-mode output behaviour was not separately checked.

The integration's numeric requested/controller fan levels do not identify that
selection or expose the schedule. Level 4 alone also does not identify intensive
ventilation; its existing status flag remains separate. No additional HESP
mapping follows from this UI observation. Other hardware/firmware variants
require their own confirmation.
See [mode-specific reference tests](REFERENCE_TESTS.md).

## Missing and invalid values

Each interpreted value has its own validation and freshness check. Invalid
updates do not refresh a value; after 30 seconds without a valid update it
becomes unavailable. Disconnect invalidates values immediately. Valid zero
speeds and off states remain valid readings. Retained raw entities and internal
diagnostic evidence can remain available when an interpretation is invalid.

Temperatures and measured speeds use measurement statistics where configured.
Counters do not claim a reset model or total-increasing statistics. The seven
retired identities follow the migration described above; all other unique IDs
and user-selected enabled/disabled settings are preserved on upgrade.

## FWT 2-R secondary-zone temperature (0229)

In Martin Kneppe's passive FWT 2-R capture with BDE Comfort V03.6.07A0, the
central panel sends `0x0229` to the main controller (`11 80 00`, SET 1→2, four
payload bytes). As a little-endian float32, it ranges from approximately 20.314
to 20.340 °C. In 27 of the 28 SETs, the four bytes match exactly the latest
`0x01F4` RESPONSE from room module 13 to the panel (`D2 40 00`). The panel SET
is received approximately 3.56–3.59 seconds after that room reply. The first
SET has no preceding room-13 reply in the excerpt. This establishes `0229` as
the forwarded secondary-zone temperature in this configuration. Room address
13 is specific to this recording. [Pinned capture](https://gist.github.com/mkneppe/4484c55c6c50f860e8b49a85bc16c666/8124e56a26b22be6e717a863e380123812fad382)
· [Room-module display comparison](https://github.com/DNier/proxon-hesp-homeassistant/discussions/2#discussioncomment-19689972)

`022A` stays at 20.0 °C, consistent with a secondary-zone target. Two room
modules report that target, so the excerpt cannot resolve its source. The
P2 reference recordings show `0229` and `022A` fixed at 21.0 °C. A live
secondary-zone measurement on P2 still needs corroboration. The FWT 2-R
finding is documented as offline evidence.

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
- **Preheating valve:** MV-Vorwärme has no positive display example, so no
  mapping is published. MV-Abtau now has a directly filmed display transition;
  its optional indication is described below and does not establish active defrost.
- **Intensive duration or remaining time:** no validated data point. The
  integration does not substitute an estimated countdown.
- **Temperature error sentinels:** negative-temperature display evidence now
  supports signed decoding within a receive plausibility bound. The ambiguous
  `FFFF` remains excluded; this is not a complete fault-code mapping. Other
  hardware variants require their own comparison. See [temperature evidence](TEMPERATURE_EVIDENCE.md).

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
readings. The complete-word allowlist only admits independently display-backed words.

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
A one-shot fan-level message at this tap had no observable effect. At the
original PTC-to-controller tap, a one-shot calendar correction was confirmed by
the controller responses and the BDE display. The optional [device-time
feature](CLOCK_SYNC.md) uses this confirmed calendar path. Support for a general
control interface or persistence after power loss has not been established.

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


## BDE heating/cooling solenoid valve indication

The optional diagnostic binary sensor **MV-Heizen/Kühlen** (English:
**Heating/cooling solenoid valve**) mirrors bit 9 (LSB 0, little-endian) of
`224000 / 006C / 4`. It is disabled by default and has no thermal device class.
Enable it in the main device's entity settings. Existing entity IDs and user
settings remain unchanged; the raw 006C sensor remains available separately.

Display comparisons include both states, cooling with bypass off, and a filmed
on-to-off transition after compressor shutdown. The valve indication remains on
for approximately five minutes after reported RPM reaches zero, then the display
and bit change in the same approximately one-second interval. This supports the
BDE indication on the observed installation, not physical valve feedback or a
universal mapping across untested models/firmware. It is **not cooling activity**.
On separate pages of one short natural winter-heating reference clip, BDE
heating operation, positive compressor RPM and warm supply air are visible;
the switching-state page shows this valve off. These are closely successive
observations, not simultaneous readings. Together with the existing comparisons,
they reinforce that this valve alone cannot identify heating or cooling activity.

Only the display-backed payloads `25000000`, `27000000`, `a7000000`,
`25020000`, `27020000`, and `a7020000` are interpreted. Other checksum-valid
words remain raw diagnostics and immediately make this sensor unavailable.
Malformed frames cannot refresh it. It also becomes unavailable after 30 seconds
without fresh accepted source data or on disconnect. Missing data never mean off.
Attributes identify the source, bit, raw payload and observed-installation scope.
The entity only listens; no query, control command or extra polling is sent.

## BDE defrost solenoid valve indication (0.13.1)

The optional diagnostic binary sensor **MV-Abtau** (English: **Defrost solenoid
valve**) mirrors bit 7 of the same validated `224000 / 006C / 4` source. It is
disabled by default, has no thermal device class and belongs to the existing
main device. This is the BDE switching-state indication, not physical valve
feedback or a classifier for active defrost.

Earlier on/off display comparisons are now supplemented by an unobscured filmed
on-to-off transition. PTC-Wohnen stays on while MV-Abtau turns off and the green
LED illuminates; reported positive compressor RPM follows later. The reference
therefore concerns the individual valve indication. It does not confirm a
complete physical defrost cycle or extend the mapping to untested hardware.

Accepted full payloads are `25000000`, `27000000`, `a7000000`, `25020000`,
`27020000`, `a7020000`, `e7000000` and `c7000000`. The last two are display-backed
startup words for this valve only; the existing heating/cooling-valve allowlist
is unchanged. Other structurally valid words immediately make MV-Abtau
unavailable. Invalid frames do not refresh the source, and its existing
30-second freshness and immediate disconnect rules apply. Missing data never
mean off. Attributes identify the bit, complete source identity, raw payload and
observed-installation scope. No additional bus traffic is generated.

This entity is available from 0.13.1 and is not part of 0.13.0.

PTC-Wohnen is deliberately omitted: a reviewed display-on example has zero in
all three candidate panel fields (01F8 bit 11, 03B6 bit 1, 118007/0191 bit 1).
Both on and off transitions now agree during Eco Winter tests, and earlier
Comfort references also agree. The contradictory display-on example occurred
during cooling rundown after a higher setpoint; operating mode alone does not
resolve it. Agreement in other phases does not remove that counterexample.
MV-Vorwärme remains omitted until a positive display example and
corresponding telegram evidence are available.

0208 bit 10 is not a copy of the heating/cooling valve indication: it can clear
while that display still reads on. Bit 28 is absent during a display-confirmed cooling run. Neither
is a generic cooling indicator. Positive RPM can also be reported only after the
LED illuminates and supply air starts cooling, on both the BDE and HESP. The
existing compressor entity reports RPM > 0. The separately documented BDE
operating-display sensor mirrors specific confirmed labels. Physical operating
phases require separate evidence.

## Upper green BDE LED

The optional diagnostic binary sensor `bde_green_led` mirrors the upper green
LED within the documented display-backed contexts for the P2 with LT-ZIM V1.6 and
BDE Comfort. Enable **P2 reference BDE display** in the integration options
on that hardware. A FWT 2-R capture contains the same Comfort frame pair
without a corresponding optical reference. The shared transport profile does
not identify the panel or establish the meaning of the LED.

| Operating mode | Status word (little-endian uint32) | Visible LED |
| --- | --- | --- |
| Eco Winter | `0x8000100A` | Dark |
| Eco Winter | `0x82001312` | Lit |
| Eco Winter | `0x8200131A` (since 0.16.14) | Lit |
| Comfort | `0x8000131A` | Lit |

**From 0.16.19:** Two additional Eco Winter references admit the complete status words
`0x82009312` (`12930082`) and `0x82001112` (`12110082`) only with the complete
valve word `0x27` (`27000000`) and finite positive compressor RPM. Mode,
status, valves and RPM must all be fresh within eight seconds. A different
valve word, stopped compressor or stale source leaves these two contexts
unavailable. They do not establish a general meaning for bit 15 or a rule
based on compressor speed alone.

**From 0.16.20:** The exact Eco Winter / `0x8200931A` (`1a930082`) / valve
`0x27` (`27000000`) context uses the same finite positive RPM and individual
eight-second freshness requirements. Its main-page reference shows the upper
LED lit. Preserved passive frame brackets agree at the nominal send time;
Recorder history retains the complete context throughout the displayed minute
and the surrounding interval. The photo's send time is approximate, rather
than an exact exposure timestamp.
The separate P2-only fan-level rule has its own six-second requirements. This
LED context did not add an operating-display or actuator interpretation in
0.16.20. Version 0.16.21 separately admits its exact heating-label context
under the operating-display qualification rules below.

**From 0.16.21:** The exact Eco Winter / `0x92009312` (`12930092`) / valve
`0xA7` (`a7000000`) / finite positive RPM context also reports the LED lit
as `display_reference`. The P2 option and individual eight-second source
limits apply. Its main-page photograph shows the green LED, Heizbetrieb and
level 2; the received context remains unchanged throughout the device minute. This is a
direct optical reference for this complete context, not a generalized Bit-28
rule or a reference for a neighboring status or valve word.

**From 0.16.23:** Four further exact Eco Winter status/valve combinations report
the LED lit with `state_basis=display_reference` on the selected P2 reference:

| Complete `224000/0208/4` payload | Complete `224000/006C/4` payload | Evidence scope |
| --- | --- | --- |
| `12930080` | `27000000` | Offset-bearing green-LED photographs within an unavailable history interval, with matching status/valve receipt brackets. |
| `12930082` | `67000000` | Passive valve-pulse interval and contemporaneous observer report that the LED remained green. Later photos do not retrospectively photograph the pulse. |
| `12930082` | `47000000` | The same observed pulse, not an additional independent photo episode. |
| `12930092` | `27000000` | Two independent P2 episodes with a green LED, literal Heizbetrieb and displayed level 2. |

Mode, complete status and valve words, and finite positive compressor RPM must
all have actually arrived within eight seconds. Stale sources, different words
or zero speed do not admit these new contexts. A mode change still requires a
new status receipt. These finite additions do not define individual bits or
extend the existing inferred-continuity word set. Only the last combination
also adds the independently documented heating-label and level-2 rules; the
other three add no operating-display, fan or PTC interpretation.

**From 0.16.24:** The directly reported continuously green LED across the
extended November observation also admits the finite Eco Winter and Comfort
status/valve combinations listed in
[the complete comparison](BDE_DISPLAY_EVIDENCE.md#extended-observation-and-comfort-comparison).
These include Comfort `1a930080 / 27000000` and `1a930090 / a7000000`, as well
as the separately listed short valve-pulse contexts. All four required sources
must actually arrive within eight seconds and RPM must be finite and positive.
The LED reports `display_reference`, without `assumed_state`; the observation
is not treated as an inference. The apparent Comfort `1a930082` snapshot at the
mode change is excluded because it retains the preceding Eco Winter status.
Heating-label, fan-level and PTC interpretations remain separate.

**From 0.16.25:** Two separate reference-P2 recordings additionally show
the upper LED green in Stove with `0208=1a930080`, `006C=27000000` and finite
positive RPM, once with PTC-Wohnen On and once Off. Only this complete tuple
is added under the existing P2/freshness checks; other Stove words and a
general mode-independent bit-8 rule remain unassigned.
[Stove evidence and limits](BDE_DISPLAY_EVIDENCE.md#additional-stove-led-reference-01625).

**From 0.16.18:** Both checksum-validated sources, `118000 / 020A / 2` for
mode and `224000 / 0208 / 4` for status, must have arrived within the last
eight seconds. This LED-only limit covers observed unchanged-source intervals
up to 7.479 seconds. It can expose missing data up to two seconds later than
the previous six-second limit. The operating-display and fan-level limits
are unchanged. A mode change requires a new status receipt. The entity is
disabled by default and uses the existing receive stream.

An explicit **continuity assumption** fills two additional Eco Winter contexts:
`0x9200131A` and `0x92001312`. They may continue an already admitted On state
on the same uninterrupted connection while mode, status and finite positive
compressor RPM (`224000 / 051C / 4`) all remain within eight seconds. These
complete words are not independently photographed LED references. The
assumption is restricted by the exact context and freshness, with no fixed
total duration cap while those conditions continue.

The entity exposes `state_basis=display_reference` for the observed
contexts and `state_basis=inferred_continuity` with Home Assistant's
`assumed_state=true` for the two inferred contexts. Missing, invalid, expired
or unassigned data, an explicit Off context, a mode change or disconnect
breaks continuity. Starting or reconnecting directly in a Bit-28 context
cannot infer On. Fresh positive RPM alone cannot restore a lost anchor.
Unavailable states expose `state_basis=unavailable`, without an assumed On.

Two independent P2 readings confirm the lit LED for Eco Winter and
`0x8200131A`. One uses a device-clock bracket, the other a contemporaneous
reading with fresh matching telegrams before and after it. The neighbouring
words `0x9200131A` and `0x92001312` have no direct optical LED reference;
the continuity rule above is an explicit assumption. The LED was also observed
lit with the operating field blank and reported compressor speed zero. The
general interpretation of individual status bits remains open.

The two 0.16.19 contexts have original main-page references aligned
through received device-calendar messages across each image's whole possible
displayed minute. The images show Eco Winter, level 2, Heizbetrieb and the lit upper
LED, with the exact status/valve words and positive speed throughout the
bracket. A later compatible pre-stop photo album has only an approximate
shared send time; it is not another exact timestamp or a Bit-28 reference.
The LED reference does not add `0x82001112` to the operating-display rules:
the original bracket starts before that sensor's 15-second qualification.

### Observed coverage gaps (November 2026)

Reference observations reviewed on 26 and 27 November document a physically
green upper LED while the pre-0.16.23 HA LED entity is unavailable. In the later sequence,
two screenshots of the same unavailable history entry bracket four original
device photos. The LED is visibly green on the dark screen, the main page
showing **Heizbetrieb**, and the switching-state page with all five displayed
switching states Off. Thus an unavailable LED entity does not imply an unlit physical
LED or a missing operating label. The two pages were exposed separately and
do not establish a simultaneous heating/actuator discrepancy.

Each photo sequence is one episode, not four independent reference contexts.
Camera originals provide nominal offset-bearing exposure times; screenshot
offsets and camera-to-HA synchronization remain unmeasured. Still photographs
do not prove continuous illumination or a blink pattern. Earlier repeated
unavailable history intervals have no corresponding physical LED reference.
The native Recorder comparison confirms `12930092 / 27000000` throughout the
later exposures, positive reported RPM and unavailable LED, operating-display
and controller-fan entities. The fresh status/valve receipt brackets do not
establish original mode/RPM receipt times or historical 15-second qualification.
Version 0.16.23 fills the exact missing context while retaining runtime source
freshness and continuity requirements. It does not retrospectively correct
history or establish a general meaning for individual status bits.
[Operating-display evidence and availability limits](BDE_DISPLAY_EVIDENCE.md#observed-availability-gaps-november-2026).

## Bounded BDE operating-display indication (0.16.0)

The optional diagnostic enum `bde_operating_display` reports `heating` for
Eco Winter with full `224000/0208/4=0x82001312`, `0x8200131A` or, from 0.16.9,
`0x82009312`. Each requires full `224000/006C/4=0x27` and fresh positive
`224000/051C/4` compressor speed.
From 0.16.21, **P2 reference BDE display** additionally admits two exact Eco
Winter heating contexts: `0208=0x8200931A` / `006C=0x27` and
`0208=0x92009312` / `006C=0xA7`, both with finite positive compressor RPM.
Version 0.16.23 additionally admits `0208=0x92009312` / `006C=0x27` under the
same P2-only positive-RPM requirements. Two separate episodes support the
literal label and level 2. The seven-second source bound and 15-second initial
heating qualification remain in force. Qualified heating may continue between
the admitted `0xA7` and `0x27` valve contexts while all four sources remain
fresh and valid; the photographs are not retroactive qualification replays.
From 0.16.5 the same entity additionally reports `blank` only for Eco Winter,
full `0208=0x8000100A`, full `006C=0x25` and finite compressor speed exactly zero.
Two independent device-minute-backed references support this blank-label
context. It describes the absent visible BDE operating label, not absent heat
output, a PTC state or a general idle state.

With **P2 reference BDE display** enabled, the same entity reports `cooling`
for Comfort with full
`224000/0208/4=0x80001522`, full `224000/006C/4=0x0227` and fresh positive
`224000/051C/4` compressor speed. Two independent P2 display comparisons
support this exact combination. All three sources must arrive after the
current Comfort mode's first or changed receipt.

All four Eco Winter sources must meet the seven-second freshness/coherency
bound; Comfort cooling retains its six-second bound. Initial qualification
requires 15 seconds of actual valid receptions. Already qualified heating
continues between admitted heating contexts for the active display profile
while every source remains fresh and valid. Changes to blank or cooling,
unassigned contexts and invalid or expired sources start a new qualification
window. Other combinations are unavailable. The existing entity
identity, opt-in setting and general telemetry freshness are preserved.
[Evidence and regression scope](BDE_DISPLAY_EVIDENCE.md).
