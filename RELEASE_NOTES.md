## 0.11.0 — Continuous event recording

- Extend automatic compressor event prehistory to 180 seconds; retain 180 seconds
  after the triggering transition. Windows remain subject to memory limits.
- Automatically retain the four latest event recordings, replacing the oldest
  when a new window starts. Expose recording and replacement counts. Clear all
  saved events with the existing clear button; manual recording stays independent.
- Increase the per-recording receive-block limit to 16384 and the continuous
  prebuffer to 512 KiB / 8192 chunks, accommodating small TCP receive blocks.
- Include earlier recordings in diagnostic exports. Offline inventory, replay
  and comparison support `--event --event-index 0` for the oldest retained window;
  `--event` alone still selects the latest.
- Preserve all 60 entity identities and existing settings. Compressor rotation
  still does not classify heating, cooling, defrost or PTC activity.

### Upgrade and validation

Install 0.11.0 through HACS and restart Home Assistant. Keep the existing entry.
Download existing recordings before restarting; recordings are held in memory only.
The automatic recording option is preserved. If not already enabled, enable it
under Settings → Devices & services → PROXON HESP → Configure. Download diagnostics
after the relevant transitions; clearing between events is no longer necessary.

197 automated tests passed; Ruff lint and formatting passed. Validation covers upgrade from 0.8.0, automatic rollover, continuous prehistory,
full windows with small TCP chunks, independent manual recording and offline
selection. Physical-device acceptance remains pending.

## 0.10.0 — Automatic compressor event recording

- Add a default-enabled compressor-running binary sensor derived from validated
  speed: on above 0 rpm, off at 0 rpm. Missing, expired or disconnected telemetry
  is unavailable, never assumed off. Invalid frames cannot refresh the state.
- Add opt-in passive event recording with up to 60 seconds of prehistory and
  180 seconds after a fresh validated compressor start or stop. Keep the first
  event capture until explicitly cleared; expose status and a clear/rearm button.
- Keep manual recording independent and provide a separate diagnostic export;
  inventory, replay and comparison accept `--event`. Both captures are bounded.
- Keep all 57 existing entity identities and settings; add three entities (60 total).
- Do not classify heating, cooling, defrost or PTC activity from rotation,
  requested mode or temperature differences. Recorded transitions do not yet
  validate a complete thermal-state classifier.

### Upgrade and validation

Install 0.10.0 through HACS and restart Home Assistant. Keep the existing entry.
Export saved recordings before restarting; captures are held in memory only.
Under Settings → Devices & services → PROXON HESP → Configure, enable
Automatic event capture. Download diagnostics when Event capture shows Ready,
then use Clear event capture and rearm for the next event.

185 automated tests passed, including upgrade from 0.8.0, bounded pre/post
recording, invalid/fragmented telegrams, disconnect handling, independent manual
recording and offline event export selection. Ruff lint and formatting passed.
Offline replay of 23 existing captures detected the recorded compressor stop.
Live acceptance of this version on physical hardware is still pending.

## 0.9.1 — Controller fan level in Stove mode

- Recognize the observed status words `8000921A` and `8000931A` as controller
  fan level 3. The optional diagnostic previously rejected these words and
  became unavailable after its freshness timeout.
- Keep validation limited to complete, display-confirmed words. No PTC,
  valve or heating-state interpretation is added.
- Preserve all 57 entity identities, user settings and passive operation.

### Upgrade and validation

Install 0.9.1 through HACS and restart Home Assistant. Keep the existing
integration entry. Export any recording you need before restarting.

174 automated tests passed, including recorded frames at every stream split,
unknown-word rejection, HA entity updates and existing upgrade/lifecycle checks.
Ruff lint and formatting checks passed. Offline replay of the supporting
recordings recognizes both new words; unrelated unknown words remain rejected.

## 0.9.0 — Capture and connection diagnostics

- Add an enabled capture-status sensor with actual duration, start/stop times,
  size and separate reasons for duration, byte and chunk limits or disconnect.
- Add recording options from 30 to 600 seconds (default 120). Changes apply to
  the next recording without reload, connection changes or loss of captured data.
- Add optional TCP connection and last supported valid-data timestamp diagnostics.
- Export format version 2 includes measured duration, stop time, integration
  version and profile. The receive-chunk format is unchanged; offline analysis
  continues to support older exports.
- Preserve the original 54 entity identities and settings; add three diagnostics.
  Recording remains passive and bounded to 1 MiB / 4096 chunks.

### Upgrade and validation

Download recordings you need before updating; they exist only in memory. Install
0.9.0 through HACS, restart Home Assistant and keep the existing integration entry.
The recording limit defaults to 120 seconds for existing entries.

170 automated tests passed, including upgrade from the 0.8.0 entity contract,
timer completion without traffic, options persistence and resource cleanup.
Ruff lint and formatting checks passed. These are simulated checks, not a claim
of compatibility with every hardware configuration.

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
