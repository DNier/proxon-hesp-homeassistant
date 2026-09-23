# Control evidence and bounded test planning

This is an evidence inventory, not an additional transmission API. The only
implemented write action is [device time alignment](CLOCK_SYNC.md). Captured SET
traffic does not establish that an external controller can own the setting.

## Observed messages

Identities include all three header bytes. Counts below refer to 30 deduplicated
historical capture windows, not independent devices. They exclude the later
controlled calendar and fan-level experiments.

| Identity / DP / payload bytes | Observed interpretation | Evidence | External control status |
| --- | --- | --- | --- |
| 118000 / 032E / 4 | Packed local calendar | BDE edits, controller readback and a successful external correction | Confirmed on one installation: BDE display and 65 seconds of continued telemetry; power-loss persistence not established |
| 118000 / 00E1 / 2 | Requested fan level | 954 SETs; levels 1–4 | At the original tap in Auto, a one-shot level-2 request briefly changed the controller status and fan rpm before level 1 returned; no persistent control. Earlier BDE-tap attempt had no observable effect |
| 118000 / 0227 / 4 | Target room temperature, float32 | 942 SETs; observed values 18, 21, 21.5, 24, 26 and 30 °C | Earlier 22→22.5 °C test received an ACK, then 22 °C again after about 1.3 s; BDE remained at 22 °C |
| 118000 / 020A / 2 | Operating mode | 939 SETs; Eco Summer, Comfort and Stove values observed | No demonstrated persistent external control; not a first automated test |
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

## What can be checked without video

Use a timestamped TX record separate from RX and compare:

1. Fresh baseline and the exact one-shot command.
2. Subsequent controller responses, distinguished from SET echoes and ACKs.
3. Persistence across multiple normal panel cycles.
4. Relevant effects, such as controller fan level, control values and rpm.
5. Return to the baseline, including the original automatic/manual selection.

HA entities and raw capture decode the same bus. They are useful views of the
same evidence, not two independent confirmations. Target temperature currently
comes from panel SET traffic, so a matching HA sensor alone cannot establish
controller adoption. Requested fan level likewise must not be confused with the
controller status or physical fan speed.

A video is unnecessary for checking whether raw telemetry changes or reverts.
BDE confirmation is still needed when panel ownership, automatic/manual mode or
an ambiguous physical effect cannot be resolved from telemetry. A short visual
confirmation can suffice; full-length recordings are not always necessary.

## Proposed order and execution contract

**Completed fan-level comparison at the original tap (Auto selected).** A single
level-2 request produced a validated controller-level-2 response about 2.9 seconds
later, followed by level 1 about 7.8 seconds after the request. Panel requests
remained at level 1 throughout. Fan rpm rose briefly and returned near baseline;
control-value polls all showed the original values. No restoration write was
needed. This establishes a transient response, not durable control or a new
BDE setting. Continuous competing writes are not an acceptable remedy.

**Conditions for any further fan-level experiment.** The previous
unsuccessful fan test and successful calendar test used different reported tap
locations; this is a hypothesis to investigate, not proof that location caused
the difference. Reassess the current operating condition first. For a suitable
stable Eco Summer, compressor-off baseline, choose an adjacent observed level.
Allow at least 15 seconds of baseline, then one command and 30–60 seconds of
observation. Do not equate absence of an rpm change with command rejection alone.

Before execution, agree the exact starting level, test level and recovery action.
The raw requested level does not reliably identify automatic/manual selection.
If that selection is unknown, obtain BDE confirmation before testing. Do not
promise complete restoration merely because the old numeric level reappears.

A target-temperature experiment has lower priority: the existing experiment
already failed to demonstrate adoption. Repeat only to test a specific new
hypothesis, with a small predefined change and a verified recovery path. Do not
use the full observed temperature range as a permitted test sweep. Operating mode
and composite flags are deferred; unknown actuator and measurement points are
excluded.

For any agreed test, use the existing connection, one active experiment, bounded
observation and no automatic resend. Do not open a competing connection on a
single-client gateway. Abort on stale data, unexpected operation, a manual change
or communication loss. A normal planned restoration may be sent once when still
appropriate; on uncertainty, stop automation and request manual BDE recovery.
Never replay a stale baseline over a new user choice.

Classify results as no observable effect, ACK only, temporary adoption, sustained
telemetry adoption, or display-confirmed adoption. Record recovery separately.
Only promote a control into the integration after both adoption and recovery are
validated. This document does not authorize or execute those future experiments.
