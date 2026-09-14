## Experimental device clock

Adds a disabled-by-default diagnostic sensor displaying the observed device
clock as HH:MM:SS. Enable it in the PROXON device entity list if desired.
The value has no inferred date or timezone and may differ from Home Assistant
time. Existing raw DP 0x0330 and all entity identifiers are preserved.

Clock readings require a matching supported checksum and valid time fields.
The integration remains receive-only. No active queries or controls are added.
Temperature arrays and fan RPM remain unsupported pending checksum validation.

Validation: recorded clock frames, corrupt-frame rejection, split TCP input,
invalid time fields and Home Assistant entity registration.

Install through HACS and restart Home Assistant to load the new Python code.
