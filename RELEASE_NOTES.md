## Investigation capture (receive-only)

Three device diagnostic buttons start a two-minute capture, stop it, or clear it.
Download through the device's Home Assistant diagnostics action.

- Uses the existing TCP connection; no transmitted commands or second client.
- Raw bytes, including unknown frames, with UTC start and relative timestamps.
- Bounded to 120 seconds, 1 MiB and 4096 chunks; stops on disconnect.
- In-memory only; reload/restart clears data. Explicit start is required.
- Raw recordings can contain measurements/device information; review before sharing.

Update through HACS and restart Home Assistant. Existing sensor IDs are preserved.
