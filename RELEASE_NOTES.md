## 0.8.0 — Read-only telemetry and passive diagnostics

This release removes the experimental temperature-write actions. The integration
receives existing bus traffic without sending HESP requests or control commands.

- Retains all 54 sensor, binary-sensor and capture-button registrations, unique
  IDs, user preferences and existing telemetry decoding.
- Retains passive capture start, stop and clear, plus ordinary diagnostics.
- Removes the experimental sender, preparation/confirmation state and dedicated
  write-test diagnostic data.

### Upgrade from 0.7.x

Download recordings you need before updating; they exist only in memory.
Update through HACS to **0.8.0**, restart Home Assistant and keep the existing
PROXON entry. No removal or reconfiguration is required.

The actions `proxon_hesp.prepare_target_temperature_test` and
`proxon_hesp.send_target_temperature_test` are no longer available. Remove saved
calls to them. The `target_temperature_test` diagnostics section has also been
removed. `application_bytes_sent` remains present and zero. There is no replacement
write action or climate/fan control.

### Validation

At release: 150 tests passed; Ruff lint and formatting checks also passed. Lifecycle
coverage verifies capture buttons, reconnect, reload, unload, retained identity
and custom names, removal of the experimental actions and zero payload writes.
These checks use simulated streams and do not establish compatibility with every
hardware variant. Current development checks are described in
[CONTRIBUTING.md](CONTRIBUTING.md).
