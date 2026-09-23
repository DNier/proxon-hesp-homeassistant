# Align device time

After power loss, some validated controllers return to an initial calendar date.
This can affect time-program selection. The optional **Align device time**
button corrects the device calendar using Home Assistant's configured timezone.
It does not change the requested operating mode or send a fan-level command,
but the corrected time can cause the existing time program to select a different
fan level.

## Use

1. Check that Home Assistant's date, time and timezone are correct.
2. On the PROXON device page, enable **Align device time** in its entity settings.
   The button is disabled by default and requires fresh calendar telemetry.
3. Press the button once and check the BDE date/time display.

The button sends exactly one calendar telegram on the existing connection and
waits up to 20 seconds for a matching controller calendar response. A plain ACK
is insufficient. Its `status` attribute changes to `confirmed` when a matching
calendar response arrives, or `already_current` if no correction was needed.
An update can cross a minute boundary, so the following calendar minute is also
accepted as confirmation. Confirmation is not a guarantee of long-term retention.

A failed or interrupted attempt is `unconfirmed`, with an action error where
applicable. Check the BDE before trying again: a failed response does not prove
that the command was not applied. There are no automatic retries or queued
presses. A 30-second cooldown applies after an attempted write. Disconnection
aborts confirmation; reconnecting never resends the command.

## Scope

The calendar includes year, month, day, weekday, hour and minute. Seconds are
not set, so this is a calendar/minute correction, not exact clock synchronization.
The protocol carries no timezone information. The button uses Home Assistant's
configured local timezone, including its current daylight-saving offset.
Existing numeric calendar data and entity identities remain unchanged.

The command was observed to work on the validated LT-ZIM V1.6 / PTC 4× V1.2 /
BDE Comfort installation through the original PTC-to-controller connection.
Other revisions are unverified. A short successful observation does not prove
persistence across power loss. No startup synchronization, periodic writing,
operating-mode control or arbitrary payload service is included.

Telemetry, discovery/probing, recordings and connection recovery remain passive.
Do not run a second TCP recorder against a single-client gateway while the
integration is connected. Diagnostic RX captures contain received traffic only;
the application byte counter and last time-alignment target describe writes
separately.
