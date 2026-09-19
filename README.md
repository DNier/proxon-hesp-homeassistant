<p align="center">
  <img src="https://raw.githubusercontent.com/DNier/proxon-hesp-homeassistant/main/custom_components/proxon_hesp/brand/logo.png" alt="PROXON HESP" width="160" height="160">
</p>

# PROXON HESP for Home Assistant

A local, read-only Home Assistant integration for PROXON P-series systems using
a transparent RS485-to-TCP gateway on the HESP bus. No MQTT broker, cloud service
or separate application is required.

The integration receives existing bus traffic. It does not send HESP requests,
change settings or control the equipment. The existing controller continues to
operate the system.

## Compatibility

Version **0.8.0** requires **Home Assistant 2026.9 or later**. Development tests
use Home Assistant 2026.9.2 and Python 3.14.

The validated hardware profile is **LT-ZIM V1.6 with PTC 4× V1.2 and BDE Comfort**.
Support is based on recordings and display comparisons from this configuration;
other PROXON revisions are not automatically supported. The profile is selected
during setup, not detected from the gateway.

See [hardware compatibility](docs/COMPATIBILITY.md) before installing.
This independent project is not affiliated with the equipment manufacturer.

## Features

| Feature | Availability |
|---|---|
| Room and target temperatures, requested fan level, operating mode | Enabled by default |
| Ten controller temperatures and supply/extract fan speeds | Enabled by default |
| Compressor speed, bypass switching state, intensive ventilation state | Enabled by default |
| Filter remaining days and eight operating-hour counters | Enabled by default |
| Controller fan level and two raw fan control values | Optional diagnostics |
| Experimental device clock and raw response payloads | Optional diagnostics |
| Start, stop and clear a passive recording | Diagnostic buttons |

Values become unavailable after 30 seconds without a valid update, or immediately
on disconnect. Missing data is not interpreted as zero, off or fault-free.
Requested fan level can differ from the controller's reported level. Switching
states are not measurements of physical actuator position.

There are no climate/fan controls, fault-text sensor, intensive-ventilation
countdown or hot-water integration. See [data points and limitations](docs/DATA_POINTS.md)
for units, validation rules and experimental features.

## Installation with HACS

[![Open this repository in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=DNier&repository=proxon-hesp-homeassistant&category=integration)

1. Add `https://github.com/DNier/proxon-hesp-homeassistant` to HACS as a custom
   repository with category **Integration**, or use the button above.
2. Download **PROXON HESP** and restart Home Assistant.
3. Open **Settings → Devices & services → Add integration → PROXON HESP**.
4. Enter the gateway host, TCP server port (default `4196`), name and profile.

For manual installation, copy `custom_components/proxon_hesp` into your Home
Assistant configuration's `custom_components` directory, restart, then add the
integration as above.

Configure the gateway separately for transparent TCP server operation at
**19200 baud, 8N1** on the supported HESP segment. Do not enable Modbus conversion.
The integration does not configure the gateway. Connector labels and pinouts
vary by board revision; this project does not provide universal wiring instructions.

Setup listens for up to 20 seconds for supported, checksum-verified data.
A reachable TCP port alone is insufficient. Stop other capture clients first:
the gateway may accept only one connection. Each integration entry uses one
receiving connection, including during passive recording.

## Updates and reconfiguration

Install updates through HACS and restart Home Assistant. Use **Reconfigure** to
change the host, port or name while preserving entity identity and history.
Deleting and recreating the entry creates a new identity. Different host aliases
for the same gateway cannot currently be detected as duplicates.

### Upgrading from 0.7.x

Download recordings you need before restarting; they exist only in memory.
Update to 0.8.0 and keep the existing integration entry. All 54 entity registrations,
unique IDs and user preferences are retained.

The experimental `proxon_hesp.prepare_target_temperature_test` and
`proxon_hesp.send_target_temperature_test` actions have been removed. Remove any
saved calls to them. There is no replacement write action. The experimental
`target_temperature_test` diagnostic section is also removed; ordinary diagnostics
and passive capture buttons remain available.

## Troubleshooting and recordings

If setup fails, check gateway mode, serial settings and competing TCP clients.
If individual values become unavailable, the stream may lack supported valid
updates for those data points. TCP connectivity alone does not prove fresh data.

Download diagnostics from the integration to inspect counters and freshness.
For a targeted investigation, use the device's **Start capture (2 minutes)** button,
then **Stop capture** and download diagnostics. Recordings contain raw measurements
and potentially device information; review them before sharing.

See [diagnostics and offline analysis](docs/DIAGNOSTICS.md) for recording limits,
privacy guidance and comparisons between captures or time windows.

## Development

See [contributing](CONTRIBUTING.md) for setup, checks, evidence requirements and
release preparation. Tests use fixtures and simulated gateways; they do not
connect to equipment. The protocol modules ship with the integration, so no
unpublished external package is needed.

- [Hardware compatibility](docs/COMPATIBILITY.md)
- [Data points and limitations](docs/DATA_POINTS.md)
- [Diagnostics and offline analysis](docs/DIAGNOSTICS.md)
- [Checksum derivation](docs/CHECKSUM_ALGORITHM.md)
- [Release notes](RELEASE_NOTES.md)

## License and acknowledgements

Original code is licensed under [MIT](LICENSE). Protocol interpretation and the
checksum derivation build on [Markus Mauch's HESP documentation](https://markusmauch.github.io/proxon-hesp/),
licensed under CC BY 4.0. Adapted material retains that attribution and license;
see [NOTICE.md](NOTICE.md). The PROXON logo is excluded from the MIT license and
remains the property of its rights holders.
