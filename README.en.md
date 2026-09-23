# PROXON HESP for Home Assistant

[Deutsche Hauptdokumentation](README.md)

A local integration for PROXON P-series systems with a transparent RS485-to-TCP
gateway. No MQTT broker, cloud service or separate application is required.
The supported reference configuration is **LT-ZIM V1.6 / PTC 4× V1.2 / BDE Comfort**;
other revisions are unverified. Model and firmware are not automatically detected.
This independent project is not affiliated with the equipment manufacturer.

## Install

Home Assistant **2026.9 or later** is required for stable **0.11.0** and beta
**0.12.0b5**. Add this repository to HACS as a custom repository, category
**Integration**, install PROXON HESP and restart HA. Then use
**Settings → Devices & services → Add integration → PROXON HESP**.
Enter the gateway host, TCP port (default 4196), name and supported profile.
Configure the gateway separately for transparent TCP, **19200 baud, 8N1**;
do not enable Modbus conversion. Stop competing TCP clients before setup.
There is no universal wiring guide: connector pinouts vary by board revision.

## Features and boundaries

The integration reads temperatures, fan/compressor speeds, requested mode and
fan level, bypass/intensive ventilation, filter time and operating hours.
It supports passive manual and compressor-event recordings. Missing telemetry
is unavailable, never assumed zero or off. Compressor rotation does not identify
heating, cooling, defrost or PTC activity. General climate/fan control is unsupported.

Beta 0.12 adds optional heating-room monitoring using existing switches, power
sensors and optional thermostat/temperature/humidity references. Existing
thermostats retain control. Physical acceptance of room monitoring is pending.
The optional device-time button is the only HESP write action: one explicit
calendar correction, no automatic synchronization or retries. Corrected time can
change which existing time-program period is active. Setup and capture stay passive.

Back up HA before upgrading to 0.12.0b5: its configuration format cannot be loaded
by older versions. Downgrading requires the previous backup. Keep the existing
entry to preserve identities and preferences. Download recordings before restarting;
they exist only in memory. Beta 0.12.0b5 groups technical telemetry under Diagnostics and makes detailed
readings optional on new installations. Existing activation preferences remain unchanged.

## Documentation and contributing

German is the maintained language for user guides and release notes. This page
is a short entry point, not a second complete manual. The HA UI supports German
and English. Development references remain in English:

- [Development, tests and contribution requirements](CONTRIBUTING.md)
- [Data points and limitations](docs/DATA_POINTS.md)
- [Offline capture analysis](docs/OFFLINE_ANALYSIS.md)
- [Control evidence](docs/CONTROL_EVIDENCE.md)
- [Checksum derivation](docs/CHECKSUM_ALGORITHM.md)

For installation, room configuration, diagnostics and upgrades, see the
[German documentation index](README.md#dokumentation) and [release notes](RELEASE_NOTES.md).
Original code is [MIT licensed](LICENSE); protocol attribution and exclusions
are documented in [NOTICE.md](NOTICE.md).

[Experimental status-bit comparison guide (German)](docs/EXPERIMENTAL.md).
