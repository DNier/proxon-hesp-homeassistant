## 0.8.0 — Clean read-only release

The supervised temperature test is complete: no lasting change to the BDE
setpoint was observed. This release removes the experimental sender and returns
the integration to receive-only operation.

- Removed the prepare/send temperature-test actions, confirmation tokens,
  separate test capture and access to the TCP writer outside the receiver.
- Preserved all 54 sensor, binary-sensor and capture-button registrations,
  unique IDs, user settings and existing telemetry decoding.
- Preserved passive capture start/stop/clear and ordinary diagnostics.
- Updated the German/English setup text, README and development plan. Archived
  the completed test and documented its result and the remaining BDE-access work.
- Retained the README logo and blue Open HACS Repository button.

### Upgrade from 0.7.x

Download any capture you still need, update through HACS to **0.8.0**, then
**restart Home Assistant**. Keep the existing PROXON entry; no reconfiguration
or removal/re-addition is needed.

**Removed experimental API:** `proxon_hesp.prepare_target_temperature_test` and
`proxon_hesp.send_target_temperature_test` are no longer available. Remove any
saved calls to them. The `target_temperature_test` diagnostic section is removed;
`application_bytes_sent` remains present and zero. There is no replacement write
or climate/fan control in this release.

The test does not establish whether 22.5 °C was briefly applied internally.
Persistent BDE synchronization remains unverified. See the
[investigation report](https://github.com/DNier/proxon-hesp-homeassistant/blob/v0.8.0/docs/BDE_ZUGRIFF_UNTERSUCHUNG.md).

Validation: **150 tests passed**, Ruff lint and format checks passed. The new HA
lifecycle regression covers capture buttons, disconnect/reconnect, reload and
unload, checks entity identity and a custom name survive, verifies the removed
actions are unavailable, and asserts zero payload writes on every connection.
Tests use simulated streams; no new live command was sent to the installation.
