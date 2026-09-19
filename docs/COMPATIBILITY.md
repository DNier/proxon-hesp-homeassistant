# Hardware compatibility

## Validated profile

The `lt_zim_16_observed` profile is based on passive recordings and BDE display
comparisons with the following hardware:

| Component | Observed configuration |
|---|---|
| Mainboard | Hermes LT-ZIM V1.6 |
| PTC board | PTC module 4× V1.2 |
| User interface | BDE Comfort, displayed version V03.6.07A0 |
| Connection | Transparent RS485-to-TCP gateway |
| Serial mode | 19200 baud, 8N1 |

These are compatibility reference details, not automatically detected device
attributes. A matching product name alone does not establish compatibility.
Telemetry availability also depends on installed options and existing bus traffic.

## Bus boundary

In the validated configuration, the BDE connects to PTC-X1. The passive HESP tap
is on the connection from **PTC-X2 to mainboard-X5**. This is distinct from the
direct BDE-to-PTC segment. Results from one segment do not establish the protocol
or electrical characteristics of the other.

Connector labels differ across revisions. Do not infer pinouts from labels,
wire colours or photographs of another system. This documentation is not a
wiring guide. The gateway must forward raw serial data rather than convert it
to Modbus.

## Scope and limitations

- The integration monitors the P-series ventilation/heating controller. It does
  not provide T300 hot-water telemetry or support for FWT/Modbus devices.
- Cooling observations do not establish cooling capability on every installation.
- Controller, BDE and other appliance firmware versions are separate properties.
- Choosing a profile is an explicit user choice. Model, serial number and
  firmware are not inferred from the gateway address.
- Validated values and unresolved interpretations are listed in
  [data-point coverage](DATA_POINTS.md).

## Reporting another configuration

Include the board revisions, BDE version, installed options, software version
and the specific entities compared with the display. Describe which bus segment
was observed. Do not include serial numbers, service documents, addresses or
network credentials. Start with a concise description and sanitized diagnostics;
full recordings are not required for an initial compatibility report.
