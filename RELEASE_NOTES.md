## 0.5.0 — Compressor speed and reported ventilation states

Three new read-only entities are enabled by default on the existing PROXON device:

- **Compressor speed** in rpm, with measurement statistics and whole-rpm display
  precision. Validated against BDE readings in heating, cooling and stopped states.
- **Bypass switching state**, matching the BDE's on/off indication. This is a
  reported switching state, not mechanical position feedback or a control.
- **Intensive ventilation active**, distinguishing timed intensive ventilation
  from manual fan level 4. Duration and automatic fan-selection mode remain unknown.

The target-temperature sensor now accepts the observed 30 °C setpoint.
The reference BDE's user setting range is 18–30 °C; this release adds no controls.

Existing entity IDs and user enable/disable choices are preserved, including
DP 0x051C's raw diagnostic entity. Invalid compressor values and unknown bypass
codes do not update the corresponding typed entity. Last valid values expire
independently after 30 seconds; disconnect makes entities unavailable. A real
zero rpm or off value remains valid.

Validation covers fixed recorded frames, every stream split, single-bit frame
corruption, wrong source/length, invalid numeric/status values, HA registration,
existing raw-entity identity, availability, recovery and unload. The existing
passive transport is unchanged; no polling or bus commands are introduced.

Install this version through HACS and restart Home Assistant. The three new entities will be created automatically. Compare them
with the BDE after installation.
