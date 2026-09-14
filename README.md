<p align="center">
  <img src="https://raw.githubusercontent.com/DNier/proxon-hesp-homeassistant/main/custom_components/proxon_hesp/brand/logo.png" alt="PROXON HESP" width="160" height="160">
</p>

# PROXON HESP for Home Assistant

A local Home Assistant custom integration for the PROXON P-series HESP bus
via a transparent RS485-to-TCP gateway.

## Status: 0.8.0 read-only release

An installable **read-only** custom integration for Home Assistant 2026.9+.
Development tests use Home Assistant 2026.9.2 / Python 3.14. Compatibility is
validated against recordings and observations from the supported installation;
this is not a compatibility claim for every PROXON variant.

Version 0.8.0 removes the completed experimental temperature-write actions.
The integration receives telemetry and provides optional passive captures.
It sends no HESP requests or control commands during setup, operation or reconnect.
See [upgrading from 0.7.x](#upgrading-from-07x) and the
[BDE investigation results](docs/BDE_ZUGRIFF_UNTERSUCHUNG.md).

Supported profile: the observed LT-ZIM V1.6 / PTC 4× V1.2 installation, with
four BDE values plus controller telemetry received from its HESP bus.
The maintenance report identifies the local central unit as **P 2 H-L**;
a separate service form says **P 1.0 (Hermes)**. Cooling was retrofitted on
3 September 2026. Hardware, firmware, report discrepancies and the comparison
with Markus Mauch's P 2H-L are recorded in the
[reference installation profile](docs/ANLAGENPROFIL.md). These are local evidence,
not automatically detected attributes or a compatibility promise for all P units.

Panel entities:

| Entity | Meaning |
|---|---|
| Room temperature | Unrounded temperature transmitted by the BDE |
| Target temperature | BDE temperature setpoint; read-only |
| Requested fan level | BDE requested level; may differ from the BDE display during cooling; not measured fan speed |
| Operating mode | BDE program; Eco Summer locally compared with the display |

These values represent the **panel's transmitted state**, not a new command's
acknowledgement or an independently measured actuator state. Other mode names
come from the reference documentation and still need variant-specific checks.
There are deliberately no climate/fan controls, arbitrary writes or active polls.
No MQTT broker, cloud service or separate process is needed.

The HA-independent protocol modules currently ship inside the component's
`hesp` directory. Extraction into a separately versioned library is planned;
no unpublished external package is required to install this preview.

## Controller telemetry

Filter remaining time uses days and has been compared with the BDE display.
Eight operating-hour counters were matched exactly against the installation's
BDE: fan levels 1–4, heat pump heating/cooling, controller and preheating.
They now use hours and descriptive names, retaining their existing unique IDs.
No long-term statistics class is assigned until reset behavior is understood.
Previously disabled entries remain disabled on upgrade; user settings are preserved.

The integration includes two actual fan speeds (supply/extract, rpm) and ten
controller temperatures (T1, T3–T8, T10, T12, T13, °C) as enabled sensors on
the same device. Temperatures display one decimal place; fan speeds display
whole rpm while retaining the received precision. Both use measurement
statistics. The BDE room-temperature sensor stays separate from these channels.

The 0x03B7 block is decoded only for the verified positive deci-degree encoding
(0–150 °C). Negative encodings and sensor-error codes are not yet documented;
high raw values are rejected rather than interpreted as signed temperatures.
Valid sibling channels continue updating; rejected channels expire after the
normal 30-second freshness interval. Fan readings must be finite and within
0–10000 rpm. These are sanity limits, not manufacturer operating limits.
The unused eleventh temperature slot is not published. DP 0x00D7 is treated
separately as raw fan control values, not target rpm (see optional fan diagnostics).

DP 0x032E remains a neutral diagnostic counter without a unit: its previously
assumed meaning as seconds since startup is not established on this installation.
Its internal key stays `uptime` solely to preserve entity identity.

18 short response payloads remain disabled-by-default hexadecimal diagnostic
sensors. Most meanings remain unknown; 0x051C now also has a numeric sensor.
Do not use the raw payloads as measurements or automation inputs.
Enable individual entries only for a targeted comparison with normal BDE changes;
record before/after, time and the corresponding display. A zero payload does not
prove that a component is off or that no fault exists. No arbitrary bus writes.

See [data-point coverage](docs/DATENPUNKTE.md) for evidence and remaining gaps.

### Operating state and compressor speed

An enabled, read-only **Intensive ventilation active**
binary sensor reads bit 6 (`0x40`) of the BDE's 32-bit little-endian flags
at DP `0x01F8`. Local recordings distinguish timed intensive ventilation in
Comfort from manual fan level 4 in Eco Summer. Other flag bits are ignored.
The sensor becomes unavailable without fresh data after 30 seconds or on
disconnect. Duration, remaining time and the automatic fan-selection mode are
not inferred. See the [local validation record](docs/INTENSIVLUEFTUNG_BEOBACHTUNGEN.md).

**Compressor speed** reads Float32 LE from controller DP `0x051C` in rpm,
with measurement statistics and whole-rpm display precision. Full received
precision is retained. The existing raw `0x051C` entity keeps its identity and
enabled/disabled setting. Non-finite, negative and above-10000 rpm readings
do not update the numeric sensor; 0 rpm is a valid stopped reading. The range
is a receive sanity guard, not a manufacturer operating limit.

**Bypass switching state** reads exactly `0` (off) or `1` (on) from controller
DP `0x0160`. It reports the state displayed by the BDE, not measured flap
position, and is not an open/closed cover or control. Other values are rejected.
The source mappings are recorded in the [heating/cooling observations](docs/KUEHLUNG_BEOBACHTUNGEN.md).

All three entities are enabled by default on the existing device. Missing or
invalid updates do not become zero/off: each last valid value expires after
30 seconds without a valid update, and disconnect makes it unavailable.
The temperature setpoint receive guard now accepts the observed 30 °C setting;
the local BDE supports 18–30 °C. All these changes remain passive.

### Optional fan diagnostics

Three additional sensors are disabled by default and categorized as diagnostics:

- **Controller fan level**: controller DP `0x0208`, restricted to eight recorded
  status words covering levels 1–4. It can remain at 4 during cooling after
  intensive ventilation ends while **Requested fan level** returns to 3.
  It is a reported controller stage, not a measured airflow or speed.
- **Supply fan control (raw)** and **Extract fan control (raw)**: the two
  Float32 LE values at `0x00D7`. They are unitless and have no statistics class.
  Historical SD metadata suggests millivolts, but a simultaneous mapping and
  electrical measurement are missing; these are not measured voltages or rpm.

Unknown status words and non-finite/out-of-range controls (outside 0–10000)
do not refresh their values. The last valid value expires after 30 seconds;
disconnect makes it unavailable. Each control channel is validated independently.
Other status bits, faults, defrost and off states are not inferred.
Existing entity IDs and user settings remain unchanged. No bus writes are added.
See [SD and capture evidence](docs/SD_KARTEN_ABGLEICH.md).

## HACS installation

This public repository can be added to HACS as a custom integration repository.
Version 0.8.0 receives data only; there are no write-test actions.

[![Open this repository in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=DNier&repository=proxon-hesp-homeassistant&category=integration)

Use the button above to open or add this repository in HACS, or follow these steps:

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

## Upgrading from 0.7.x

1. Download any recording you still need before restarting; captures are held
   only in memory and are cleared by reload/restart.
2. Update to **0.8.0** in HACS and **restart Home Assistant**.
3. Keep the existing PROXON integration entry. All 54 entity registrations,
   unique IDs, history, names and enabled/disabled preferences are retained.

The experimental `prepare_target_temperature_test` and
`send_target_temperature_test` actions are removed. Any saved calls to these
retired actions must be removed; there is no replacement write action.
The experimental `target_temperature_test` diagnostics section is also removed.
Ordinary diagnostics, their zero `application_bytes_sent` field, and all three
passive capture buttons remain available. The completed test and its limits are
recorded in the [test archive](docs/SOLLTEMPERATUR_TEST.md).

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
- Values are published only when the reconstructed byte-recurrence checksum
  matches and type/range validation succeeds. The algorithm was checked against
  11,599 recorded candidates, including long responses; see
  [derivation and validation](docs/CHECKSUM_ALGORITHM.md).
- Unsupported frame shapes, other nodes and corrupted candidates produce no
  value. A valid checksum alone does not establish a data point's meaning.
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
