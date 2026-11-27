<a name="control-evidence-and-bounded-test-planning"></a>

# Control evidence and interpretation limits

Developer documentation · English. [Deutsche Nutzerdokumentation](../README.md#dokumentation).

This reference describes received SET traffic and evidence for write adoption.
The integration limits its write feature to [device time alignment](CLOCK_SYNC.md).
Captured SET traffic alone cannot establish ownership of a setting.

## Observed messages

Identities include all three header bytes. Counts below refer to 30 deduplicated
historical capture windows, not independent devices. They exclude the later
controlled calendar and fan-level experiments.

| Identity / DP / payload bytes | Observed interpretation | Evidence | External control status |
| --- | --- | --- | --- |
| 118000 / 032E / 4 | Packed local calendar | BDE edits, controller readback and a successful external correction | Confirmed on one installation: BDE display and 65 seconds of continued telemetry; calendar resets after full power interruption on the reference generation |
| 118000 / 00E1 / 2 | Requested fan level | 954 SETs; levels 1–4 | At the original tap in Auto, a one-shot level-2 request briefly changed the controller status and fan rpm before level 1 returned; no persistent control. Earlier BDE-tap attempt had no observable effect |
| 118000 / 0227 / 4 | Target room temperature, float32 | 942 SETs; observed values 18, 21, 21.5, 24, 26 and 30 °C | Earlier 22→22.5 °C test received an ACK, then 22 °C again after about 1.3 s; BDE remained at 22 °C |
| 118000 / 020A / 2 | Operating mode | 939 SETs; Eco Summer, Comfort and Stove values observed | Persistent external control remains unverified |
| 118000 / 01F8 / 4 | Composite panel flags | 944 SETs; bit 6 is associated with intensive ventilation | Whole-word writing is not justified; other observed bits remain independent/unresolved |
| 118000 / 0226 / 4 | Measured room temperature | 940 SETs; telemetry from the panel | Not a user setting; do not inject simulated measurements |
| 118000 / 0229 / 4 | Unclassified float-shaped value | 942 SETs, constant payload in the reviewed corpus | Excluded: meaning unresolved |
| 118000 / 022A / 4 | Unclassified float-shaped value | 940 SETs, constant payload in the reviewed corpus | Excluded: meaning unresolved |
| 118000 / 022C / 2 | Unclassified state | 944 SETs, values 0 and 1 | Excluded: meaning unresolved |
| 118000 / 03B6 / 4 | Unclassified state | 942 SETs, values 0, 1 and 3 | Excluded: no validated actuator mapping |
| 118007 / 0191 / 2 | Unclassified state on a different identity | 940 SETs, values 0, 1 and 3 | Excluded: do not equate with another node's same-numbered point |

PTC, compressor and valves have no established direct-write mapping. Modbus
register numbers must not be substituted for HESP identifiers. A received
controller response is not by itself a writable command specification.

## Repetition and command ownership

For unchanged values, per-capture median SET intervals for fan level, target
temperature, mode and panel flags lie approximately between 4.9 and 5.3 seconds.
The existing offline SET/ACK audit associates 954/954 fan-level SETs, 942/942
target-temperature SETs and 939/939 mode SETs with an ACK within one second.
These are associations for ordinary captured panel traffic, not successful
external-write counts. An ACK proves neither persistence nor displayed adoption.

Repeated panel traffic is a plausible reason for an external setting to revert.
It does not prove the cause of a particular unsuccessful experiment. Do not use
continuous competing writes to force a desired value. The successful calendar
correction does not establish equivalent ownership for other settings.

The upstream author's [operating-context clarification](https://github.com/markusmauch/proxon-hesp/issues/1#issuecomment-7190339147)
describes a daemon acting as the sole master with the BDE disconnected. It sends
mode, fan level, room temperature and target temperature every five seconds.
The author reports confused responses when both masters transmitted and mutes
the daemon before reconnecting the BDE. This limits the earlier
[repeated-write report](https://github.com/markusmauch/proxon-hesp/blob/0c5151342299084db0f57836f5bbd140822e7e33/docs/dp-referenz.md#L105):
it does not demonstrate coordinated access or persistent setting adoption with
the BDE connected. A reverse path to the BDE was not investigated. Neither
repeated competing writes nor replacement of the BDE is implemented here.

The published [163-entry controller catalog](https://gist.github.com/markusmauch/74b21f6afc79f6bcaea27adcd51bdf61)
uses interpreted access labels such as `W-User` and `W-Inst`. These labels alone
establish neither a usable SET contract nor ownership, displayed adoption or
recovery. The later [original read-query recording](https://gist.github.com/markusmauch/3f1a431a55cc71830be21ca2fd0ba9e0/ba888e35a475906bf6cf9070eed2edf697b66f83)
supplies TX/RX evidence for metadata and controller reads; it contains no SETs
and adds no control-adoption evidence.

The [ESP32 sender at commit `eed1173`](https://github.com/Mannheim68199/proxon-hesp-esp32/blob/eed1173fae88a4bbdd43c1bc7adbcb78f695d3a3/ESP32_Proxon_P1_RS485_Sniffer.ino#L535)
arms transmission after received traffic and sends from a received-message
window. This implementation is not evidence of initialization or bus ownership
on a silent bus without the BDE. Its repeat-time setting bounds the injection
window; it is not a demonstrated protocol for replacing the panel.

## What can be checked without video

Review timestamped transmission evidence separately from received data:

1. Identify the fresh baseline and the exact transmitted message.
2. Distinguish an ACK or an echoed SET from a subsequent controller response.
3. Check how long the controller response holds across normal panel cycles.
4. Compare relevant feedback, such as reported fan level, control value or rpm.
5. Verify the final state, including a separate BDE reference where the choice
   between automatic and manual operation affects interpretation.

HA entities and raw captures decode the same bus. Use the BDE or another
independent source when the claim concerns the displayed setting or a physical
effect. A target-temperature sensor reading from panel SET traffic provides
evidence of the panel's reported value. Controller observations establish
adoption separately.

<a name="proposed-order-and-execution-contract"></a>

## Evidence for external setting adoption

A recorded one-shot level-2 message at the PTC-to-controller tap produced a
validated controller-level-2 response and a brief rpm rise. Level 1 returned
while panel requests and sampled control values stayed at their initial values.
The comparison establishes temporary response on the tested installation.
A BDE-side comparison had no observed effect. The reason for that difference
remains open. Compare the evidence in [data points](DATA_POINTS.md#passive-bde-connection-comparison).

Classify observed effects separately as ACK only, temporary response, sustained
controller adoption or adoption confirmed at the display. Reliable control
requires adoption and recovery evidence across the supported scope. The
published integration exposes the confirmed calendar path only.

## Passive disconnection experiment and manufacturer scope

The reference P-series needs the BDE connected for supported operation. A
passive comparison without the BDE returned no bytes despite an open TCP
connection. Disconnecting the BDE and restarting changed two conditions at
once. The comparison leaves bus initiation and controller behaviour in that
configuration open. [Manufacturer scope and comparison](MANUFACTURER_INFORMATION.md)

Markus Mauch's [P 2H-L read run](https://github.com/markusmauch/proxon-hesp/pull/2#issuecomment-7196275110)
records controller replies to actively sent QUERYs with its BDE disconnected
and daemon stopped. This establishes solicited read responses on that reported
setup. The recording begins with read queries and contains no power-on sequence,
initialization exchange or control write. It does not establish startup without
the BDE, autonomous operation, coordinated access with the BDE or supported
replacement of the panel. Its fixed 250 ms acquisition windows also do not
define a safe transmission schedule. [Original framing and timing](METADATA_EVIDENCE.md#recorded-list-pages-and-negative-replies-26-november-2026).

## Reported panel replacement on a P 2H-L

The author's [follow-up comment](https://github.com/markusmauch/proxon-hesp/issues/1#issuecomment-7196777234)
and [operating description at `0eb5a2a`](https://github.com/markusmauch/proxon-hesp/blob/0eb5a2a33234893a8fafdbfae56ade6f0c510da4/docs/anlage.md#betrieb-ohne-bedienpanel)
report a sole master at X7 replacing the disconnected BDE since July, without
observed faults. This is an author-reported long-term writing setup, separate
from the supplied November read-only recording. It supplies no master
implementation or timestamped write-adoption, sender-loss and recovery trace.

The reported state set contains nine node-2 SETs approximately every five
seconds: `020A`, `00E1`, `0226`, `0227`, `0229`, `022A`, `022C`, `03B6` and
`01F8`. The last five are described as constant values in the replacement
sender: 21.0 for `0229` and `022A`, zero for `022C`, `03B6` and `01F8`.
Their inclusion does not resolve their meaning or establish that every field
is individually required. In particular, `03B6=0` describes the replacement
sender's choice: the supplied July BDE sequence contains both 0 and 1, so it
does not establish an unchanged panel value across modes.

The description calls its sequence the panel's order, but the supplied July
recording gives a counterexample. Starting each cycle at the mode SET:

- Reported replacement order: `020A → 00E1 → 0226 → 0227 → 0229 → 022A → 022C → 03B6 → 01F8`.
- Recorded BDE order: `020A → 022C → 01F8 → 00E1 → 03B6 → 0226 → 0227 → 0229 → 022A`.

All 46 complete mode-SET-to-next-mode-SET cycles in that original recording
have the second order. The nine-point set agrees, but an identical order is
not established. The untimed July log cannot independently confirm the
reported five-second period.

When the replacement sender stops, the author reports continued ventilation
at approximately level 3 and a controller readback `020A=6`; resuming the
sender reportedly restores the sent state. The time to fallback is explicitly
unmeasured. There is no original matched readback for value 6, no confirmed
five-second watchdog, and no new production mode mapping.

The accompanying [remaining questions](https://github.com/markusmauch/proxon-hesp/blob/0eb5a2a33234893a8fafdbfae56ade6f0c510da4/docs/offene-punkte.md#weitere-randbedingungen-der-anlage)
attribute time programs and night setback to the panel. The controller clock
and filter countdown reportedly continue without it; automatic clock setting
is lost, the countdown's relation to that clock is open, and a shutdown after
filter expiry is reported without a timed boundary. PTC permission at node 30
without the BDE remains explicitly open for Stove and Comfort. The nine node-2
SETs do not establish that separate control path.

The author also reports unassignable replies and implausible measurements
when both masters were active, and will not publish a writing master. These
sources describe one installation's observations. Coordinated writes with
an attached BDE, startup, complete panel-function replacement and recovery
across the integration's supported hardware remain unverified. No additional
sender or runtime control is introduced.

<a name="offline-review-of-recorded-operating-sequences-3-october-2026"></a>

## Recorded operating sequences

A comparison of eight distinct receive windows found 67,060 checksum-valid
frames with full byte coverage. It deduplicates identical windows. Overlapping
manual and event windows can include the same traffic.

Comfort captures with requested level 3 show changes in target temperature
`118000/0227/4` among eleven known SET identities. `01F8` bit 11 changes near
target changes. `03B6` and `118007/0191/2` show the states 0, 1 and 3. These are
correlations, not confirmed direct actuator commands. The documented PTC
counterexample still contradicts that interpretation.

The FWT sample adds a steady Comfort/fan-3 comparison, not an operating-mode
transition. Its extra headers must not be merged with similarly numbered P-series
points. The filtered P1 export cannot establish a full transmission cadence.
Persistent external command adoption and the Auto/manual field remain open.
A synchronized BDE selection reference is required to distinguish Auto from
a fixed selection at the same numeric level.

See [candidate decisions](STATUS_EVIDENCE.md) and
[installation-specific fan comparisons](FAN_CURVE_EVIDENCE.md).

## Original P 2H-L BDE mode sequence

The July BDE log supplied in the
[pinned source Gist](https://gist.github.com/markusmauch/3f1a431a55cc71830be21ca2fd0ba9e0/ba888e35a475906bf6cf9070eed2edf697b66f83)
was captured passively at X7 with the BDE as sole master. The author reports
selecting Eco Summer, Eco Winter, Stove, Comfort and Off, and answering Yes
to the heat-element permission prompt in all three heating modes. Its original
checksum-valid `118000/020A/2` SETs follow **1 → 2 → 4 → 3 → 0**, corroborating
the existing mode labels on this installation. Each of the 47 mode SETs is
immediately followed in frame order by a matching empty confirmation. The log
has no timestamps, so it establishes neither ACK latency nor mode duration.
[`panel_modes_recorded.json`](../tests/fixtures/panel_modes_recorded.json) retains
small selected original frames in source order, without invented timestamps.

`118007/0191/2` remains 0 throughout Eco Winter, becomes 1 in Stove, remains
1 initially in Comfort and returns to 0 before the Off SET. `118000/03B6/4`
bit 0 follows the same value sequence. `01F8` and `022C` remain zero, as do
the bit-1 PTC candidates. The earlier
[withdrawn permission interpretation](https://github.com/markusmauch/proxon-hesp/pull/2#issuecomment-7189097549)
therefore remains withdrawn. PTC-Wohnen was not independently read, so these
messages establish neither stored heat-element permission nor physical output.
They also do not support a pure mode encoding of `0191`.

`0229` and `022A` remain constant in this log and supply no new secondary-zone
measurement reference. `0232` is absent, including QUERYs. Its separate November
readback `01` does not resolve its meaning or justify heat-demand telemetry.
No additional runtime mapping or control is introduced.

## Mode-dependent fan selection: reference UI clarification

On the reference BDE, manual fan-level selection is available only in Eco
Summer and Eco Winter. Their Auto selection runs a
user-defined weekday/time/fan-level schedule. Eco modes have no separate
intensive-ventilation option; level 4 can be selected manually. Comfort and Stove
instead let the controller choose the level and offer intensive ventilation as a
timed switch to level 4. Off is the fifth available operating mode; its output
behaviour was not separately checked. A fan-level readback does not distinguish
these UI conditions. This clarification does not establish controller algorithms,
schedule payloads or external control.
[Passive reference guidance](REFERENCE_TESTS.md)

## Targeted offline review: Eco Auto and intensive-ventilation timing

Inventory and production replay validate 13,319 frames with full byte coverage
across six reference windows. Two short Eco Summer windows compare fixed level
1 with Auto at effective level 1. Both contain 98 complete identities. Of these,
93 have the same constant
payload in both windows; the five differences are independently decoded room
temperature, fan rpm, calendar, clock and temperature-block values. Query
arguments remain constant. One complete query round per phase contains the same
39 query identities in the same order. This supplies no identified selection
field or repeatable timing code.

The selection reference is an earlier written video evaluation; the original
video was unavailable for renewed inspection. The fixed-level interval is short
and a different manually selected level lies between it and Auto. Later traffic
has no additional display reference. These limitations prevent treating this
comparison as proof that Auto is never transmitted. A positive assignment requires a synchronized independent reference covering
the same numeric level in both selection modes over full query cycles.

Different selected intensive-ventilation durations and start/end references
likewise supply no identified duration or remaining-time field. A calendar
change near one stop also occurs after intensive ventilation has already ended;
production replay identifies it as device time. Several independently visible
countdown values would be needed to distinguish a timer payload from ordinary
time and temperature changes. Unlabelled steady-state captures do not resolve
these gaps.

The separate [P1 sequence report](https://github.com/Mannheim68199/proxon-hesp-esp32/blob/eed1173fae88a4bbdd43c1bc7adbcb78f695d3a3/DP-Sequenz.md#L55)
describes 48 points repeating in approximately 4.8 seconds after restart, based
on two unfiltered recordings. It provides no complete telegram identities or
raw initialization trace, and establishes neither an Auto selector nor a startup
handshake. This report must not be conflated with the earlier filtered P1 export.
