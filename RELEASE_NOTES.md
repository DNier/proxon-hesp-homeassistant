Read-only development version of PROXON HESP for Home Assistant 2026.9+.

- Eight BDE-verified operating-hour sensors, with descriptive names and hours.
- Four panel sensors and filter remaining time.
- Unknown counter 0x032E is neutral and has no assumed unit.
- Unknown hexadecimal diagnostics remain disabled by default.
- Existing entity IDs are preserved; no control commands are sent.

After installation or update, restart Home Assistant. When migrating from a
manually downloaded main branch, select this tagged version in HACS once.
Future published releases can then be offered through HACS update checks.
