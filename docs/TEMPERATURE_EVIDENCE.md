# Temperature encoding and validation (0.15.1)

Developer documentation · English. [German user guide](GETTING_STARTED.md).

Only checksum-valid `224000 / 03B7 / 22` responses provide the ten existing
temperature channels. Their order is T1, T7, T4, T3, T5, T6, T8, T12, T10 and
T13; the eleventh 16-bit slot remains unpublished. All values are little-endian
deci-degrees. Entity identities, units and normal freshness rules are unchanged.

## Independent evidence and scope

Earlier positive-temperature comparisons establish the channel order. Additional
natural winter-operation recordings contain several different `FFxx` words in
T4 and T6, with continuous sequences across zero. Examples include `FFFE → FFFF
→ 0000 → 0001` for T6, consistent with signed int16 tenths of a degree.

A separate BDE video explicitly shows T6 **−1.5 °C**, including the minus sign.
The subsequent passive reference recording contains T6 `FFF3` and `FFF2`, which
decode as −1.3 and −1.4 °C. This agrees with the negative range and encoding but
is not a synchronized exact-value comparison or precision calibration. T4 is
shown as +0.1 and 0.0 °C in the video; its later recorded `FFF6`–`FFF8` values
are not claimed as simultaneous negative display references. The signed format
is applied consistently to the existing block, not as ten independently verified
negative channel displays. Untested hardware variants remain outside that claim.

Minimal recorded frames and fixed wire checksums protect the new interpretation.
Full diagnostics, images, original filenames and household histories are not
distributed. Tests only replay bytes locally; they do not contact equipment.

## Conservative receive rules

- Decode int16 values and divide by ten. Accept raw −500…1500 (−50…150 °C)
  as a receive plausibility guard, not a manufacturer operating range.
- Keep `FFFF` excluded. Its signed numerical value would be −0.1 °C, but its
  possible use as an error value has not been independently ruled out. A channel
  reporting it is not refreshed and may remain unavailable at this boundary.
- Reject out-of-range words individually, including `7FFF` and `8000`.
  Invalid channels cannot suppress valid neighbouring measurements or become zero.
- Omitted values do not refresh a previous reading. After the existing 30-second
  expiry or a disconnect they are unavailable. No new error entity is inferred.
- Continue requiring the exact identity, reserved fields, length and checksum;
  malformed data never gain meaning merely because a signed number looks plausible.

This is not a complete temperature fault-sentinel specification. It corrects
the observed negative-number gap while preserving an explicit unknown boundary.
Future evidence may distinguish `FFFF` or other fault representations separately.
