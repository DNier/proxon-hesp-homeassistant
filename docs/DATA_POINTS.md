# Data points and validation boundaries

This table describes version 0.8.0. There are 49 sensors, two binary sensors and
three passive-capture buttons. Hardware scope is documented in
[compatibility](COMPATIBILITY.md).

`P` means the three-byte identity `11 80 00`; `C` means `22 40 00`.
The production decoder also requires reserved bytes `00 00`, the expected
payload length and a valid checksum. Integer and floating-point payloads use
little-endian order unless stated otherwise.

| Feature | DP / identity / payload bytes | Type and unit | Evidence and limitation |
|---|---|---|---|
| Requested fan level | 00E1 / P / 2 | Integer 0–4 | Display comparisons; request may differ from the displayed controller level during cooling |
| Operating mode | 020A / P / 2 | Enum | Eco Summer compared with display; other labels follow the protocol reference and need variant-specific validation |
| Room temperature | 0226 / P / 4 | float32 / °C | Compatible with rounded BDE display; not a precision calibration |
| Target temperature | 0227 / P / 4 | float32 / °C | Display comparisons; receive guard 15–30 °C is not a writable range |
| Ten temperatures | 03B7 / C / 22 | uint16 × 0.1 / °C | Positive encoding and channel mapping compared with display; negative encoding and fault sentinels unresolved |
| Supply/extract fan speeds | 00C9 / C / 8 | Two float32 / rpm | Display comparisons; finite values from 0 to 10000 |
| Compressor speed | 051C / C / 4 | float32 / rpm | Compared during heating, cooling and standstill; raw entity retained |
| Bypass switching state | 0160 / C / 1 | Boolean, 00 or 01 | Reported switching state; not measured flap position |
| Intensive ventilation active | 01F8 / P / 4 | Bit 6 of uint32 | Activation, automatic end and manual-level-4 counterexample checked; other bits ignored |
| Controller fan level | 0208 / C / 4 | Allowlisted uint32 words | Eight observed words; other bits and words are not interpreted; disabled by default |
| Raw fan control values | 00D7 / C / 8 | Two float32 / no unit | No validated voltage or target-rpm interpretation; disabled by default |
| Filter remaining time | 00ED / C / 4 | uint32 / days | Display comparison and decrement observed; reset behaviour unresolved |
| Operating-hour counters | 02D0–02D5, 02D7, 02D9 / C / 4 | uint32 / h | Display mappings confirmed; reset behaviour unresolved, no statistics class |
| Unclassified counter | 032E / C / 4 | uint32 / no unit | Meaning unresolved; internal key `uptime` retained for entity identity |
| Device clock | 0330 / C / 4 | Packed HH:MM:SS | Experimental; no date or timezone, no synchronized display validation; disabled by default |
| Raw diagnostics | Listed below / C | Hexadecimal bytes | Structural and checksum evidence only; disabled by default |

The temperature block supplies T1, T7, T4, T3, T5, T6, T8, T12, T10 and T13
in that order. Its eleventh slot is not published. Raw channel values above 1500
are rejected individually; valid neighbouring channels remain available.

Counter mappings are: `02D0–02D3` fan levels 1–4, `02D4` heat pump heating,
`02D5` heat pump cooling, `02D7` controller, `02D9` preheating.
The value `FFFFFFFF` is rejected for counters and filter days.

## Optional diagnostics

Controller fan level accepts only these complete status words:

| Level | Status words |
|---|---|
| 1 | `8000100A` |
| 2 | `80001012` |
| 3 | `8000101A`, `8000131A` |
| 4 | `80001022`, `80001122`, `80001422`, `80001522` |

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
- **PTC and valve states:** 006C/0208 remain candidates; simultaneous bit changes
  do not provide unique assignments.
- **Intensive duration or remaining time:** no validated data point. The
  integration does not substitute an estimated countdown.
- **Negative temperatures and error sentinels:** require independent evidence
  before changing the current receive guards.

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
