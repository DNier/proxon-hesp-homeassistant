<p align="center">
  <img src="https://raw.githubusercontent.com/DNier/proxon-hesp-homeassistant/main/custom_components/proxon_hesp/brand/logo.png" alt="PROXON HESP" width="160" height="160">
</p>

# PROXON HESP for Home Assistant

A local Home Assistant integration for PROXON P-series systems using
a transparent RS485-to-TCP gateway on the HESP bus. No MQTT broker, cloud service
or separate application is required.

The integration receives existing bus traffic without polling. The optional
**Align device time** button is the only write action: it sends one calendar
update when pressed. Setup, reconnects and recordings never send commands.
The existing controller continues to operate the system.

## Beta 0.12.0b2

Optional manufacturer-independent heating rooms group existing HA entities into
virtual room devices and report electrical heating from valid power measurements.
Area assignment on room creation is corrected in beta 2; saved selections on
unassigned room devices are recovered automatically after updating.
Existing thermostats remain responsible for switching. The beta also adds an
optional device calendar sensor and manual time-alignment button.

See [room setup](docs/ROOMS.md), [time alignment](docs/CLOCK_SYNC.md) and the
[release notes](RELEASE_NOTES.md). Physical acceptance of room monitoring is pending;
**0.11.0 remains the stable release**.

## New in 0.11.0

Optional **Automatic event capture** saves up to 180 seconds before and after
compressor starts or stops. Enable it under **Settings → Devices & services →
PROXON HESP → Configure**. The four latest recordings are kept automatically;
new recordings replace the oldest. Download device diagnostics to retrieve them.
**Clear event captures** clears all saved events; restart also discards them.
Manual captures remain independent. The receive-block limit is now 16384 per
recording to accommodate fragmented TCP traffic. See
[recording instructions](docs/DIAGNOSTICS.md).

The **Compressor running** binary sensor derives on/off from fresh, validated
compressor speed. It becomes unavailable with the speed reading. This indicates
rotation only; current heating, cooling, defrost and PTC activity remain
unclassified. Existing entities and settings are preserved.

## New in 0.9.1

The optional controller fan-level diagnostic now recognizes two additional
status words observed with displayed level 3 in Stove mode. Existing entities
and settings are preserved. Unknown words remain unavailable.

## Capture diagnostics since 0.9.0

Capture status now shows recording progress and the stopping reason. Recording
duration is configurable from 30 to 600 seconds (default 120), with bounded
memory use. Optional diagnostics report TCP connectivity and the last valid
supported data receipt. See [capture diagnostics](docs/DIAGNOSTICS.md).

## Compatibility

Versions **0.11.0** and **0.12.0b2** require **Home Assistant 2026.9 or later**. Development tests
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
| Local device date/time, experimental device clock and raw response payloads | Optional diagnostics |
| Start, stop and clear a passive recording | Diagnostic buttons |
| Align device time with Home Assistant | Optional configuration button |

Values become unavailable after 30 seconds without a valid update, or immediately
on disconnect. Missing data is not interpreted as zero, off or fault-free.
The optional local date/time sensor validates calendar fields and weekday but
does not assume a timezone or synchronize the device clock.
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

### Calendar diagnostics (next version)

The next version adds a local date/time sensor and an explicit time-alignment
button, both disabled by default (62 entities in total). Existing identities, enabled/disabled preferences and numeric raw
calendar values are preserved. The raw calendar sensor receives a clearer name.
The time-alignment button is the only new write action; no general control
service is added. See [time alignment](docs/CLOCK_SYNC.md).

### Upgrading from 0.8.0

Download any recording you need, update to 0.11.0 through HACS and restart Home
Assistant. Keep the existing integration entry: all 54 previous entity identities
and user settings remain. Six entities are added, giving 60 entities in total. Automatic event recording
is disabled by default; enable it through Configure when needed.
The recording limit stays at 120 seconds until changed in the integration options.

### Upgrading from 0.7.x

Download recordings you need before restarting; they exist only in memory.
Update to 0.8.0 and keep the existing integration entry. All 54 entity registrations,
unique IDs and user preferences are retained.

The experimental `proxon_hesp.prepare_target_temperature_test` and
`proxon_hesp.send_target_temperature_test` actions have been removed. Remove any
saved calls to them. There is no replacement target-temperature action. The experimental
`target_temperature_test` diagnostic section is also removed; ordinary diagnostics
and passive capture buttons remain available.

## Troubleshooting and recordings

If setup fails, check gateway mode, serial settings and competing TCP clients.
If individual values become unavailable, the stream may lack supported valid
updates for those data points. TCP connectivity alone does not prove fresh data.

Download diagnostics from the integration to inspect counters and freshness.
For a targeted investigation, use the device's **Start capture** button
(**Start capture (2 minutes)** in 0.8.0),
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

## Optionale Heizräume

Vorhandene Heizschalter, Leistungssensoren und Thermostate lassen sich über die
Integrationsoptionen beliebig vielen Räumen zuordnen. Jeder Raum erhält ein eigenes
virtuelles Gerät mit lesender Überwachung von Erreichbarkeit, Schaltzustand und
elektrischem Heizbetrieb. Die bestehende Temperaturregelung bleibt verantwortlich.
Es sind keine bestimmten Hersteller oder privaten Entitätsnamen vorausgesetzt.

Einrichtung, Messwertgrenzen und Verhalten bei Ausfällen: [Heizräume](docs/ROOMS.md).
