# Service-setting telemetry evidence

Version 0.14.0 adds eleven optional, disabled-by-default diagnostic sensors.
These are configured settings, not measured power, airflow or current fan speed.
No queries, writes or extra connections are introduced. Existing `raw_0110`
and `raw_0116` entities and their IDs remain unchanged.

## Sources and scope

The [community data-point table](https://github.com/Mannheim68199/proxon-hesp-esp32/blob/2ef75eb99d663f1aabb6bdd121e46cb2b5ee94a5/DP-Sequenz.md)
and service-app photograph in the same repository snapshot label the following
settings. The photograph's readback labels, not its adjacent editable selections,
match the asymmetric community reply vectors already stored in
`tests/fixtures/fan_curve_replies.json`.

| Controller reply | Encoding | Meaning | Community readback | Local recorded value |
| --- | --- | --- | --- | --- |
| `224000/00D2/16` | four float32 LE | Supply stages 1–4, % | 31 / 50 / 70 / 100 | 25 / 40 / 52 / 100 |
| `224000/00D3/16` | four float32 LE | Extract stages 1–4, % | 25 / 50 / 70 / 100 | 25 / 40 / 52 / 100 |
| `224000/0110/4` | float32 LE | Cooling threshold, °C | 3.0 | 3.0 |
| `224000/0116/4` | two uint16 LE | Maximum heating / cooling output, % | 100 / 90 | 100 / 90 |

An offline checksum/framing inventory of 39 original diagnostic exports found
these replies in 50 stored capture windows, including nested previous/event
windows. Windows may overlap; this is repeated observation, not 50 independent
devices or experiments. Each point had one unique payload across this corpus.
The local symmetric fan curves alone cannot establish supply/extract order;
that interpretation relies on the asymmetric community example and app labels.
The photograph and captures are not a synchronized setting-change experiment.
This is a corroborated P-series interpretation, not universal device certification.
No full private exports or copies of the photograph are published here.

## Receive behaviour

Exact node, reserved bytes, payload size and checksum are mandatory. Percentages
must be finite and within 0–100. The cooling threshold must be finite within
0–100 °C; this is only a receive sanity guard, not a manufacturer setting range.
Invalid channels are skipped independently. Raw observations remain available
even when derived threshold/output values are rejected. Values share the existing
30-second freshness rule and become unavailable without fresh reception or on
disconnect; no persisted setting or missing-data default is inferred.
No statistics class is assigned. The threshold has no absolute-temperature
device class because its delta/reference semantics are not further established.

## Not implemented

`0178` remains unmapped: the public table lists seven slots, whereas validated
local replies contain six (`80, 15, 29, 45, 65, 0`). Some app values agree, but
slot alignment and units are unresolved. `022A` remains unknown. The clarified
`03B7` temperature order is already implemented and adds no new temperatures.
