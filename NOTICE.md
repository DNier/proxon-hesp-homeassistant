# Attribution

The limited checksum contribution table in
`custom_components/proxon_hesp/hesp/checksum.py` and the protocol/data-point
interpretation are adapted from Markus Mauch's PROXON HESP documentation:

- https://github.com/markusmauch/proxon-hesp
- https://markusmauch.github.io/proxon-hesp/protokoll/
- https://markusmauch.github.io/proxon-hesp/dp-referenz/

Source material: © 2026 Markus Mauch, CC BY 4.0:
https://creativecommons.org/licenses/by/4.0/

Changes: table converted to Python, restricted receive-only stream extraction
and validation for four observed panel SET data points. This implementation is
independent and is not endorsed by Markus Mauch or the equipment manufacturer.
Unknown checksum contributions remain unknown; no general encoder is provided.

No project-wide license for original code has been selected yet. This attribution
does not relicense the rest of the project. Select a code license before a public release.
