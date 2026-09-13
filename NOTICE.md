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

Original project code is licensed under the MIT License; see LICENSE.
The adapted source material identified above remains subject to CC BY 4.0.
The MIT License does not replace those attribution and license obligations.

## Logo

The supplied PROXON logo in `custom_components/proxon_hesp/brand/` is used
to identify the integration. It is not licensed under the project MIT License.
All rights in the logo remain with its respective rights holders. Its use does
not imply manufacturer endorsement of this independent integration.
