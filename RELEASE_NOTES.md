## 0.6.0 — Separate requested and controller fan levels

The BDE can request level 3 while its display and controller remain at level 4
for cooling after timed intensive ventilation ends. This release makes those
states distinguishable without adding bus commands.

Three new sensors are disabled by default under the existing device's diagnostics:

- **Controller fan level** / **Luftstufe laut Steuerung** reads controller DP
  0x0208, limited to eight recorded status words covering levels 1–4.
- **Supply fan control (raw)** / **Zuluft-Stellwert (roh)** and
  **Extract fan control (raw)** / **Abluft-Stellwert (roh)** expose the two values
  at 0x00D7. These have no unit or statistics class. Historical SD metadata
  suggests millivolts, but they are not verified voltage measurements or rpm.

The existing panel sensor is now named **Requested fan level** /
**Angeforderte Luftstufe**. Existing entity IDs, custom names and enabled/disabled
choices are preserved. The intensive-ventilation binary sensor remains separate.

Unknown controller status words and invalid control values do not refresh the
corresponding sensor. Each last valid value expires after 30 seconds without a
valid update; disconnect makes it unavailable. Control channels are validated
independently as finite values within 0–10000. Other status bits and special
operating states are not inferred. All reception remains passive.

An offline capture-inventory tool and expanded evidence documentation are included.
Private SD files, videos and complete diagnostic captures are not part of the release.

Validation: 148 tests, lint and formatting checks; replay of all 18 recorded
captures using original chunks and multiple stream boundaries produced identical
results with no rejected checksums. The new diagnostic displays still need a
live comparison after installation.

### Update

Update to 0.6.0 through HACS and restart Home Assistant. Open the PROXON device
and enable the three new diagnostic sensors individually if you want to compare
them with the BDE. No wiring change or USB cable is required.
