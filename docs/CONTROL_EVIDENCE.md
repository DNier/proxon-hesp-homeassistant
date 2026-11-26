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
recovery. Its payload-only snapshot cannot replace timed original TX/RX frames.

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
