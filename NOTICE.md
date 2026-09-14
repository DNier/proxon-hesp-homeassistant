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

## Logo

The supplied PROXON logo in `custom_components/proxon_hesp/brand/` is used
to identify the integration. It is not licensed under the project MIT License.
All rights in the logo remain with its respective rights holders. Its use does
not imply manufacturer endorsement of this independent integration.
