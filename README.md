# PROXON HESP for Home Assistant

Project foundation for a Home Assistant custom integration for the PROXON
P-series HESP bus via a transparent RS485-to-TCP gateway.

## Status

Initial repository setup. No installable integration is available yet.

The intended implementation reads HESP traffic locally over TCP, without MQTT.
The first version will expose read-only entities. Protocol handling will be
separated from Home Assistant entity and configuration code.

## References

- [Markus Mauch's HESP documentation](https://markusmauch.github.io/proxon-hesp/)
- [Documentation repository](https://github.com/markusmauch/proxon-hesp)

Markus Mauch's documentation is published under CC BY 4.0. Any adapted material
must retain appropriate attribution. This repository currently contains no
copied protocol implementation.

Connector labels and pin assignments can differ between board revisions.
This project does not yet provide verified wiring instructions.

This is an independent project and is not affiliated with the manufacturer.
