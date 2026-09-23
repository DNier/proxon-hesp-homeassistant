# HESP checksum: reconstructed byte recurrence

Developer documentation · English. [Deutsche Nutzerdokumentation](../README.md#dokumentation).

Implemented checksum derivation for the supported HESP message shapes.

## Algorithm

Start with the 16-bit state `0xFFFF`. For every message byte, in wire order:

1. XOR the byte into the low eight state bits.
2. Apply the fixed linear transformation T to the entire 16-bit state.

The final state is transmitted as two little-endian bytes. Those bytes are not
part of the input. T is stored as 16 columns (`BYTE_TRANSFORM`); applying T means
XORing column i for each set state bit i. This is a constant-size algorithm for
all supported message lengths, not a table of observed payloads or checksums.
It does not assert an equivalent named standard CRC polynomial.

## Independent derivation

Source: [Markus Mauch's protocol reference](https://markusmauch.github.io/proxon-hesp/protokoll/#modell-in-tabellenform),
CC BY 4.0. The public contributions V[16] through V[43] suffice.

Assume a shared linear byte step. Then T(V[e]) = V[e+8]. The 20 equations
for e=16..35 have input rank 16, are consistent, and determine T uniquely.
The inverse also has rank 16. Reversing T over the published query
`10800060010000040100` with checksum `0xE149` yields the initial state `0xFFFF`.
No checksum from the private captures is needed for either result.

Reproduce with `uv run python -m tools.derive_checksum`.
The helper checks rank, conflicts, invertibility, the derived columns and seed.
This is a uniquely solved transform *under the byte recurrence assumption*;
the independent captures provide evidence that the assumption describes HESP.

The old short-frame contribution table had correlated/free contributions
absorbed into its particular solution. Extending that solution by setting missing
entries to zero would be invalid. The byte recurrence removes that limitation
and restores an explicit initial state. This explains why fitting each long
frame independently previously remained underdetermined.

## Validation against recordings

Six complete JSON captures were scanned for observed node/type headers
108000, 118000, 224000, 234000, zero reserved bytes and even nibble lengths.
All 11,599 complete candidates have matching checksums; zero mismatches.
Observed payload sizes: 0, 1, 2, 4, 8, 12, 16, 22, 40 and 112 bytes.
This count is a header-candidate scan, not a claim of parsing every bus byte.
The repeated frames are not 11,599 independent payloads; unique counts per
capture are included in CHECKSUM_VALIDATION.json.

The newest recording, previously held out from the empirical affine models,
contributes 2,173 matches, including 24 actual-speed responses (0x00C9)
and 24 temperature blocks (0x03B7). Neither this recording nor the older
private captures was used to fit the final recurrence. The public table and
one public short-frame example alone determine it.

Run `uv run python -m tools.validate_checksum_captures CAPTURE... --output REPORT`.
Reports omit raw frames, private paths, network identifiers and video metadata.
Original captures and video remain local and outside the repository.

Ten fixed wire examples from the first and newest recordings test filter,
clock/date raw values, fan responses and temperature blocks. Expected checksums
are copied from the wire. Every individual bit of each example, including the
checksum bytes, is flipped and must fail verification. Existing decoder tests
continue to cover stream splitting, corruption recovery, value bounds and nodes.
The test suite includes these checks; see [contributing](../CONTRIBUTING.md)
for the current verification commands.

## Production boundary

The checksum function accepts message sizes 8..120 bytes, spanning the observed
headers and maximum payload. Outside that bound it returns None. Intermediate
lengths use the same recurrence but were not all observed individually.

The decoder's existing data-point, node, length and semantic allowlists remain
in force. Correct checksum validation does not alone authorize a new sensor or
an active query. In particular, 0x032E can now pass checksum validation while its
meaning still remains a neutral raw diagnostic, not seconds or a decoded date.
Version 0.4.0 also adds explicitly mapped actual fan speeds (0x00C9) and
temperatures (0x03B7) with their own node, length and value checks.
No bus sender, automatic read query or control operation is added.
