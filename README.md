<p align="center">
  <img src="custom_components/proxon_hesp/brand/logo.png" alt="PROXON HESP" width="160" height="160">
</p>

# PROXON HESP for Home Assistant

Project foundation for a Home Assistant custom integration for the PROXON
P-series HESP bus via a transparent RS485-to-TCP gateway.

## Status: 0.3.1 development preview

An installable **receive-only** custom integration for Home Assistant 2026.9+.
Development tests use Home Assistant 2026.9.2 / Python 3.14. It is not a
production release and has not been installed on the user's live HA instance.

Supported profile: the observed LT-ZIM V1.6 / PTC 4× V1.2 installation, with
four BDE values plus controller telemetry received from its HESP bus:

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

## Controller telemetry (0.3.1)

Filter remaining time uses days (reference mapping, local display check pending).
Eight operating-hour counters were matched exactly against the installation's
BDE: fan levels 1–4, heat pump heating/cooling, controller and preheating.
They now use hours and descriptive names, retaining their existing unique IDs.
No long-term statistics class is assigned until reset behavior is understood.
Previously disabled entries remain disabled on upgrade; user settings are preserved.

DP 0x032E remains a neutral diagnostic counter without a unit: its previously
assumed meaning as seconds since startup is not established on this installation.
Its internal key stays `uptime` solely to preserve entity identity.

18 unknown short response payloads remain disabled-by-default hexadecimal
diagnostic sensors. Do not use them as measurements or automation inputs.
Enable individual entries only for a targeted comparison with normal BDE changes;
record before/after, time and the corresponding display. A zero payload does not
prove that a component is off or that no fault exists. No arbitrary bus writes.

See [data-point coverage](docs/DATENPUNKTE.md) for evidence and remaining gaps.

## HACS installation

This public repository can be added to HACS as a custom integration repository.
Version 0.3.1 is a receive-only development preview.

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

- Only catalogued panel SET and controller response shapes are extracted. Other frames are
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
  IP addresses or identifiers. An explicitly started capture includes raw bus
  bytes, which may contain measurements and device information. Counter names describe
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

The project uses the supplied PROXON logo for its integration icon and README.
The logo is excluded from the project code license; see NOTICE.md. Repository topics and issues are enabled. GitHub Actions
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

## Publishing updates

Maintainers bump the manifest and project version, update `uv.lock` and
`RELEASE_NOTES.md`, then push the changes. Run the **Publish release** workflow
on main to test and publish a matching GitHub tag/release. A plain development
push does not publish a release. Existing releases must not be overwritten.

HACS checks for updates periodically; GitHub does not push an immediate install
into Home Assistant. For an installation previously tracking main, select a
published version once in HACS. Updates still require installation and restart.

## Investigation capture

On the PROXON device page use **Start capture (2 minutes)**. Open the desired
BDE measurement page during the recording and note the time or take a photo.
Then press **Stop capture** and **Download diagnostics** on the same device.
The JSON contains `capture.started_utc`, a status/reason, byte count, and
`capture.chunks` with relative milliseconds and hexadecimal TCP receive blocks.
These blocks are not telegram boundaries. The capture may start mid-frame.

Only the existing TCP receiver is used; no requests are sent. Unknown and
checksum-rejected bytes are included for investigation. Recording ends after
120 seconds, 1 MiB, 4096 chunks or disconnect. Starting again replaces the old
capture. **Clear capture**, integration reload or HA restart removes it.
Download before updating/reloading. A stopped capture stays in memory until
cleared or replaced, and is included in subsequent diagnostic downloads.
Raw captures may contain device information and measurements: review before
sharing publicly. Ordinary diagnostics have an empty capture until activated.
No raw data is written into entity attributes, the recorder or log files.
