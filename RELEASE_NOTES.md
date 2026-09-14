## 0.7.0 — Supervised, one-shot temperature experiment

This development preview adds two admin-only actions for a supervised test:

- `proxon_hesp.prepare_target_temperature_test` confirms the current BDE setpoint,
  starts a separate 120-second recording and returns a short-lived confirmation token.
  Preparation sends nothing.
- `proxon_hesp.send_target_temperature_test` uses that token to attempt exactly
  one temperature SET on the existing gateway connection, without retries.

The experiment is restricted to Comfort mode, fresh received state, a change of
**−0.5 or +0.5 °C**, and the locally observed **18–30 °C** range. Wait at least
10 seconds after preparation and send before 60 seconds have elapsed.
State or connection changes invalidate the preparation. A failed, interrupted
or timed-out send still consumes the single attempt until integration reload.

**Installation, restart, reconnect and normal sensor operation remain passive.**
No climate entity, arbitrary bus writes, periodic override or automatic restoration
is introduced. Restore the original setpoint at the BDE if needed.

### What remains unverified

No live write test has been performed with this function. TCP flush success
does not establish controller acceptance or BDE synchronization. Parallel RS485
transmission can collide with existing traffic, and the BDE/PTC can reassert its
previous value. Observe the physical BDE during the experiment. This is not a
production temperature-control feature.

Diagnostics include the transmitted-frame attempt and separate received traffic;
the confirmation token is omitted from integration diagnostics. Existing capture
Stop/Clear buttons also stop/erase the test recording and disarm a pending test.
Clearing does not grant another write attempt. Entity IDs and user settings remain.

Offline SET/ACK analysis now reports intervals between unchanged repeated commands.
The evidence and test procedure are included; private captures and SD files are not.

### Installation and test

1. In HACS, update or redownload **PROXON HESP 0.7.0** and restart Home Assistant.
2. Open **Developer tools → Actions** as an administrator.
3. Follow the [German step-by-step test guide](https://github.com/DNier/proxon-hesp-homeassistant/blob/v0.7.0/docs/SOLLTEMPERATUR_TEST.md),
   starting with preparation and its response data. Do not create an automation.
4. Observe the BDE, then download diagnostics after the recording finishes.

Validation: **180 tests passed**, including real Home Assistant service setup,
permissions, one-attempt concurrency, stale state, disconnects and ambiguous send
failures using fake streams only. Ruff lint/format and service selectors/translations
were checked. These software checks do not verify behavior on the physical bus.
