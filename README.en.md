# PROXON with Home Assistant – HESP integration without a Modbus module

Independent community project for PROXON systems. Not an official integration of Zimmermann Lüftungs- und Wärmesysteme GmbH & Co. KG.

[Deutsche Hauptdokumentation](README.md)

**PROXON HESP** is a local Home Assistant custom integration for a **PROXON P2**
ventilation and heating system, using its existing HESP bus and a transparent
RS485-to-TCP gateway. No Modbus module, MQTT broker, cloud service or separate
application is required. It can be installed through HACS as a custom repository.
The P2 reference configuration is **LT-ZIM V1.6 / PTC 4× V1.2 / BDE Comfort**.
A **FWT 2-L with LT-ZIM V1.3 and BDE Comfort V03.7.9B00** is also community-tested
with unmodified version 0.12.0 and profile `lt_zim_16_observed`. Display comparisons
cover temperatures, Eco Summer/Comfort modes, fan level and speeds, bypass, counters
and filter time. Active heat-pump operation, valve mappings and clock writes remain
unverified on that configuration. See [compatibility and evidence](docs/COMPATIBILITY.md#community-getestet-fwt-2-l).
Other revisions are not automatically supported. Model and firmware are not automatically detected.

The reference installation uses a **Waveshare RS232/485/422 TO POE ETH (B)**
gateway in transparent TCP mode at **19200 baud, 8N1**. This specific model is
not required; alternative gateways must support the same transparent serial
transport without Modbus conversion.

## Manufacturer information

In correspondence shared with the project on 29 September 2026, Zimmermann
states that the queried P-series generation has no Modbus interface or retrofit
option; the historical module was intended only for FWT 1.0. External HESP
analysis is not supported, and internal protocol details will not be provided.
The T300-to-FWT connection is not evidence of third-party T300 support here.

The manufacturer describes date/time loss after complete power interruption as
normal for this generation: check and correct the clock after an interruption.
The integration's time alignment remains manual. Keep the BDE connected: a
supervised disconnection experiment yielded no received bytes and reported red
blinking; telemetry returned after reconnection. No control command was sent,
so control without the BDE remains untested. See the scoped
[manufacturer information and observation report (German)](docs/MANUFACTURER_INFORMATION.md).

## Install

[![Open repository in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=DNier&repository=proxon-hesp-homeassistant&category=integration)

Home Assistant **2026.9 or later** is required for stable **0.12.1**. Add this repository to HACS as a custom repository, category
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

Version 0.12.0 adds optional heating-room monitoring using existing switches, power
sensors and optional thermostat/temperature/humidity references. Existing
thermostats retain control. Missing or stale power measurements leave heating
activity unknown; availability alone does not prove central heating permission.
The optional device-time button is the only HESP write action: one explicit
calendar correction, no automatic synchronization or retries. Corrected time can
change which existing time-program period is active. Setup and capture stay passive.

Back up HA before upgrading from a version before 0.12.0b3: the migrated
configuration format cannot be loaded by those older versions. Downgrading requires the previous backup. Keep the existing
entry to preserve identities and preferences. Download recordings before restarting;
they exist only in memory. Version 0.12.0 groups technical telemetry under Diagnostics and makes detailed
readings optional on new installations. Existing activation preferences remain unchanged.

Optional diagnostic entities expose experimental status bits and the observed
BDE heating/cooling solenoid-valve indication. The valve can remain on after
compressor stop and does not establish active cooling. Stable release status
does not extend the documented hardware compatibility or confirm unknown bits.

## Community discussion

Join the [Home Assistant forum topic](https://community.home-assistant.io/t/proxon-p-series-via-hesp-local-integration-without-a-modbus-module-testers-and-contributors-welcome/1026553)
for a connection overview, compatibility reports and ways to contribute.
Reports from other owners are most useful with board revisions, BDE software
version and a matching display observation. Review diagnostics for private
information before sharing them.

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
