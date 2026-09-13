# PROXON HESP for Home Assistant

Project foundation for a Home Assistant custom integration for the PROXON
P-series HESP bus via a transparent RS485-to-TCP gateway.

## Status: 0.1.0 development preview

An installable **receive-only** custom integration for Home Assistant 2026.9+.
Development tests use Home Assistant 2026.9.2 / Python 3.14. It is not a
production release and has not been installed on the user's live HA instance.

Supported profile: the observed LT-ZIM V1.6 / PTC 4× V1.2 installation, with
four BDE values received from its HESP bus:

| Entity | Meaning |
|---|---|
| Room temperature | Unrounded temperature transmitted by the BDE |
| Target temperature | BDE temperature setpoint; read-only |
| Fan level | BDE requested level, not measured fan speed |
| Operating mode | BDE program; Eco Summer locally compared with the display |

These values represent the **panel's transmitted state**, not a new command's
acknowledgement or an independently measured actuator state. Other mode names
come from the reference documentation and still need variant-specific checks.
There are deliberately no climate/fan controls, arbitrary writes or active polls.
No MQTT broker, cloud service or separate process is needed.

The HA-independent protocol modules currently ship inside the component's
`hesp` directory. Extraction into a separately versioned library is planned;
no unpublished external package is required to install this preview.

## HACS installation

This public repository can be added to HACS as a custom integration repository.
Version 0.1.0 is a receive-only development preview.

1. Open **HACS → ⋮ → Custom repositories**.
2. Add `https://github.com/DNier/proxon-hesp-homeassistant`, category **Integration**.
3. Find **PROXON HESP** in HACS and download it.
4. Restart Home Assistant.
5. Add **PROXON HESP** under **Settings → Devices & services** and enter the gateway
   host and port. HACS installs the files; HA performs the device setup.

Updates are downloaded through HACS and require an HA restart. GitHub releases
are recommended for versioned updates; without releases HACS uses the default
branch. Inclusion in the HACS default catalog is not required.

The repository includes HACS metadata, local integration icons and a HACS
validation workflow. Check the GitHub Actions results before installing a new development version.

See [HACS requirements](https://www.hacs.xyz/docs/publish/integration/) and
[public repository requirement](https://www.hacs.xyz/docs/publish/start/).

## Manual installation

1. Copy `custom_components/proxon_hesp` into the HA configuration directory's
   `custom_components` folder. Do not copy this repository's virtual environment.
2. Restart Home Assistant.
3. Open **Settings → Devices & services → Add integration → PROXON HESP**.
4. Enter the gateway host and TCP server port (default 4196), name and profile.

The probe listens for up to 20 seconds for supported checksum-verified data.
TCP reachability alone is not accepted as a successful probe. Stop other TCP
capture tools first: the gateway may accept only one client. Setup of the
integration itself also waits for supported data and is retried by HA on failure.

Configure the gateway separately for transparent TCP server operation, 19200
baud, 8N1 on the verified HESP side. **Do not enable Modbus conversion.** Network
configuration is not automatically modified. This README is not a wiring guide.

The selected profile is an explicit compatibility choice, not hardware
autodetection. Other revisions are not declared supported. The exact product
model/serial/firmware are not inferred from the gateway address.

Use the entry's **Reconfigure** action to change host/port/name while preserving
entity identity. The installation receives a persisted random ID; changing IP
or replacing the gateway keeps it. Deleting and recreating the entry creates a
new identity because a stable physical unit identifier is not yet available.
Different aliases for the same host cannot currently be identified as duplicates.

## Data quality and limitations

- Only four exact panel SET frame shapes are extracted. Unknown frames are
  skipped; this is not yet a general HESP frame parser.
- Values are published only when their short-frame checksum is covered by the
  reference model and matches, and type/range validation succeeds.
- Unsupported checksum bits, other nodes and corrupted candidates produce no
  value. The reference model is incomplete; it is not a general CRC algorithm.
- Cached values become unavailable after 30 seconds without a valid update;
  disconnects invalidate all values immediately. Stale values are not restored
  as current measurements after restart.
- An open but silent/unsupported stream triggers reconnection. Reconnect uses
  bounded backoff, and unloading closes the connection and cancels tasks/timers.
- Downloadable HA diagnostics contain counters and freshness information, not
  IP addresses, identifiers, temperatures or raw traffic. Counter names describe
  candidate extraction, not validation of every bus telegram.

## Development and verification

```sh
uv sync --group dev
uv run pytest -q
uv run ruff check custom_components tests
uv run ruff format --check custom_components tests
```

Tests use captured frame fixtures and a simulated gateway; the test suite never
connects to real equipment. HA config-flow, registry, sensor and lifecycle tests
run against the actual Home Assistant test harness.

The integration icon is an original, generic airflow symbol, not the
manufacturer's logo. Repository topics and issues are enabled. GitHub Actions
validate HACS compatibility on pushes and pull requests.

See [development plan](docs/ENTWICKLUNGSPLAN.md) and [attribution](NOTICE.md).
Original code is licensed under [MIT](LICENSE). Adapted reference material
remains under CC BY 4.0 as described in [NOTICE.md](NOTICE.md).

## References

- [Markus Mauch's HESP documentation](https://markusmauch.github.io/proxon-hesp/)
- [Documentation repository](https://github.com/markusmauch/proxon-hesp)

Markus Mauch's documentation is published under CC BY 4.0. Any adapted material
must retain appropriate attribution. This repository currently contains no
copied protocol implementation.

Connector labels and pin assignments can differ between board revisions.
This project does not yet provide verified wiring instructions.

This is an independent project and is not affiliated with the manufacturer.
