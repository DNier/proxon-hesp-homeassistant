# PROXON HESP for Home Assistant

PROXON HESP connects a ventilation and heating system to Home Assistant over its
existing HESP bus. It receives local telemetry through a transparent RS485-to-TCP
gateway. The existing system controller and thermostats continue to regulate
the system.

This is an independent community project. [Deutsche Hauptdokumentation](README.md)

## Manufacturer information

The integration uses HESP directly and requires no Modbus module, MQTT broker or
cloud service. Zimmermann does not support external HESP analysis. The
[manufacturer information](docs/MANUFACTURER_INFORMATION.md) describes the scope
for the reference P-series generation and the evidence for keeping the BDE
control panel connected.

## Install

[![Open repository in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=DNier&repository=proxon-hesp-homeassistant&category=integration)

Use **Home Assistant 2026.9 or later**. The reference installation is a
**PROXON P2** with LT-ZIM V1.6, PTC 4× V1.2 and BDE Comfort. The community-tested
**FWT 2-L** has verified read-only coverage for a subset of values. Compare your
boards, panel and bus segment with the [compatibility guide](docs/COMPATIBILITY.md).

1. Configure the gateway for transparent TCP at **19200 baud, 8N1**. Keep the
   BDE connected and close other clients that use the gateway's TCP port.
2. Add this repository to HACS as a custom **Integration**, download the
   [latest stable release](https://github.com/DNier/proxon-hesp-homeassistant/releases/latest)
   and restart Home Assistant.
3. Open **Settings → Devices & services → Add integration → PROXON HESP**.
   Enter the gateway host, TCP port (default `4196`), name and documented profile.

Before an update, export recordings you want to keep and consult the
[upgrade instructions](docs/GETTING_STARTED.md#updates-und-bestehende-installationen).
Keep the existing integration entry.

<a name="bounded-bde-operating-display-0160"></a>

## Features and boundaries

- Read temperatures, fan levels, rotational speeds, filter life and operating
  hours. **Compressor running** describes rotation. The optional
  [BDE operating display](docs/BDE_DISPLAY_EVIDENCE.md) reports **Heating** or
  **Blank operating field** for specific verified Eco Winter conditions. The
  **P2 reference BDE display** integration option enables the upper green LED
  interpretation, additional heating and controller fan-level contexts, and
  one cooling context on the reference P2.
- Capture [diagnostic recordings](docs/DIAGNOSTICS.md) over the existing
  connection or monitor [heating rooms](docs/ROOMS.md) with existing HA entities.
- Align the [device clock](docs/CLOCK_SYNC.md) using the optional button or the
  daylight saving switch, which defaults to off. Turning the switch on can
  correct the clock immediately when fresh device time shows a difference.
  An enabled switch checks again on daylight saving transitions.

## Community discussion

Use [GitHub Discussions](https://github.com/DNier/proxon-hesp-homeassistant/discussions)
or the [Home Assistant forum topic](https://community.home-assistant.io/t/proxon-p-series-via-hesp-local-integration-without-a-modbus-module-testers-and-contributors-welcome/1026553)
for questions and ideas. Use the [issue forms](https://github.com/DNier/proxon-hesp-homeassistant/issues/new/choose)
for bugs and compatibility reports. Keep full diagnostic exports, recordings
and photos private. Share a small sanitized excerpt if it helps explain a
report. Report suspected vulnerabilities [privately](SECURITY.md).

## Documentation and contributing

The maintained [user guides](README.md#dokumentation) and [release notes](RELEASE_NOTES.md)
are in German. The Home Assistant UI supports German and English.

- [Development and contribution guide](CONTRIBUTING.md) · [Code of Conduct](CODE_OF_CONDUCT.md)
- [Data points and validation boundaries](docs/DATA_POINTS.md)
- [Offline capture analysis](docs/OFFLINE_ANALYSIS.md)
- [Control evidence](docs/CONTROL_EVIDENCE.md)
- [Checksum derivation](docs/CHECKSUM_ALGORITHM.md)

[MIT license for project code](LICENSE) · [Protocol attribution and rights](NOTICE.md)
