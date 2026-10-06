# Attribution

The checksum byte transform in
`custom_components/proxon_hesp/hesp/checksum.py`, the reference contributions in
`tools/derive_checksum.py`, and the protocol/data-point
interpretation are adapted from Markus Mauch's PROXON HESP documentation:

- https://github.com/markusmauch/proxon-hesp
- https://markusmauch.github.io/proxon-hesp/protokoll/
- https://markusmauch.github.io/proxon-hesp/dp-referenz/

Source material: © 2026 Markus Mauch, CC BY 4.0:
https://creativecommons.org/licenses/by/4.0/

Changes: a fixed invertible byte transform and initial state were reconstructed
from the published bit contributions and example query; independent recorded
frames validate short and long messages. See docs/CHECKSUM_ALGORITHM.md.
Stream extraction remains restricted and receive-only. This implementation is
independent and is not endorsed by Markus Mauch or the equipment manufacturer.
No active bus sender or general frame encoder is provided.

Original project code is licensed under the MIT License; see LICENSE.
The adapted source material identified above remains subject to CC BY 4.0.
The MIT License does not replace those attribution and license obligations.

Service-setting meanings are corroborated with Mannheim68199's public
PROXON HESP ESP32 data-point table and service-app photograph at commit
`2ef75eb99d663f1aabb6bdd121e46cb2b5ee94a5`:
https://github.com/Mannheim68199/proxon-hesp-esp32/tree/2ef75eb99d663f1aabb6bdd121e46cb2b5ee94a5
The photograph is referenced, not redistributed. No license or manufacturer
endorsement of that source is inferred. See docs/SERVICE_SETTINGS_EVIDENCE.md.

## Logo

The supplied PROXON logo in `custom_components/proxon_hesp/brand/` is used
to identify the integration. It is not licensed under the project MIT License.
All rights in the logo remain with its respective rights holders. Its use does
not imply manufacturer endorsement of this independent integration.

In private correspondence shared with the project on 29 September 2026,
Zimmermann did not grant permission for use of the logo in GitHub, Home Assistant,
HACS or comparable public projects. The absence of an explicit removal request
is not represented as consent. This notice does not assert that the specific
use is legally permitted or prohibited. See docs/MANUFACTURER_INFORMATION.md
for the scope of the manufacturer's response.
