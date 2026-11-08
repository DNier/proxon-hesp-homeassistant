# Candidate HESP addresses and exchange analysis

Developer documentation · English. Available in the offline tools from 0.16.1.

## Source and confidence

Martin (`mkneppe`) proposed interpreting the three header bytes as a packed
address word in [discussion #2](https://github.com/DNier/proxon-hesp-homeassistant/discussions/2#discussioncomment-19475847)
and [upstream PR #2](https://github.com/markusmauch/proxon-hesp/pull/2).
The reviewed proposal is pinned to
[`f7600bd`](https://github.com/mkneppe/proxon-hesp/blob/f7600bdfffe675e00d5fa86d659fe58fde60393b/docs/protokoll.md).
It was derived from a FWT 2-R recording; no manufacturer specification or
original recording from that report has been supplied to this project yet.

The proposed decomposition is consistent with the retained P2 reference
recordings. It is an offline interpretation of complete validated identities,
not automatic hardware discovery or permission to interpret other devices'
payloads. Numerical endpoint addresses do not identify physical products.

## Header decomposition

For the three bytes in wire order, let `H = int.from_bytes(header, "little")`:

| Field | Expression | Width |
| --- | --- | --- |
| Type | `H & 0x0F` | 4 bits |
| Source | `(H >> 4) & 0x3FF` | 10 bits |
| Destination | `(H >> 14) & 0x3FF` | 10 bits |

Type names are candidate `query` (0), `set` (1), `response` (2) and `confirm`
(3). Other type codes remain unknown and are retained. The ten-bit field bounds
are the proposal's representation, not evidence of observed devices at every
possible address.

| Recorded identity | Type | Source → destination |
| --- | --- | --- |
| `108000` | query | 1 → 2 |
| `118000` | set | 1 → 2 |
| `224000` | response | 2 → 1 |
| `234000` | confirm | 2 → 1 |
| `108007` | query | 1 → 30 |
| `118007` | set | 1 → 30 |
| `e24100` | response | 30 → 1 |
| `e34100` | confirm | 30 → 1 |

The retained P2 corpus contains those routes, including actual responses from
30, without the room addresses 10–15 or unknown address 40 reported on the FWT.
Absence is scoped to that recorded bus segment. It does not contradict another
installation or prove global absence of hardware. Overlapping capture windows
are not independent trials.

The P2 responses to `0x0194` from 30 contain `0500`; its meaning remains unknown.
A constant value is not a device identifier. The existing PTC candidates retain
their distinct identities: `118000/01F8` and `118000/03B6` address 2, whereas
`118007/0191` addresses 30 under this hypothesis. Correlated or forwarded flags
are possible, but neither this routing nor an empty confirmation establishes a
PTC state or physical heating effect.

## Offline exchange candidates

The existing inventory remains the only wire parser. Address analysis consumes
its checksum-validated frame observations, preserving header, DP, payload length,
payload bytes, global frame index and TCP completion timestamp. Unknown addresses
are inspectable without widening the production decoder's allowlists.

A candidate exchange has a query followed by a response, or a set followed by a
confirmation, with reversed endpoint addresses and the same DP. A configurable
maximum response delay bounds the search (default 1,000 ms, inclusive). Request
and reply payload lengths may differ. Unrelated interleaved routes do not merge
identities. Repeated outstanding requests of the same matching key are ambiguous;
the matcher does not simply choose the latest request.

Unparsed bytes, omitted frame indexes and selected-window boundaries break
continuity. Late, orphaned, duplicate and ambiguous responses remain explicit.
Separate recordings never share pending requests. Equal timestamps retain frame
order but only establish the TCP timestamp resolution, not zero electrical delay.
Unanswered requests do not imply an absent or switched-off device.

HESP transaction identifiers have not been established. Even a unique candidate
pair cannot exclude every delayed duplicate, establish write rights, confirm a
payload interpretation, or prove an actuator's effect. No message is transmitted.

## Regression evidence

`tests/fixtures/address_frames.json` retains four minimal original wire frames
with their recorded checksums. They show one `0191` set/confirmation and one
`0194` query/response for address 30. Relative intervals are preserved after
shifting the time origin; no household wall-clock schedule is published.
Synthetic cases exercise other addresses and ambiguous ordering; synthetic
frames are not evidence for additional supported hardware.

See [offline usage](OFFLINE_ANALYSIS.md), [checksum derivation](CHECKSUM_ALGORITHM.md)
and [attribution](../NOTICE.md). No new runtime entity, control action or
compatibility claim is added by these tools.
