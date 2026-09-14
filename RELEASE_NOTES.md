## Twelve new read-only sensors

- Actual supply and extract fan speeds in rpm.
- Ten temperatures: supply T1, fresh air T3, exhaust T4, before evaporator T5,
  evaporator T6, extract air T7, after preheater T8, condenser T10,
  before condenser T12 and compressor T13.
- All twelve are enabled by default on the existing device, with German/English
  names, appropriate units, display precision and measurement statistics.
  Existing entity identities and enabled/disabled settings are preserved.

The reconstructed checksum algorithm matches all 11,599 scanned candidates
from six recordings, including long fan and temperature responses. Its derivation
uses the public reference table and one public example, not fitted private payloads.

Scope: observed LT-ZIM V1.6 installation. Positive temperature encoding is
validated; negative encodings and error codes remain unverified. Such channels
expire rather than displaying guessed negative values; valid siblings continue.
Unknown temperature slot 11, target fan speeds and switching states remain
unpublished. No controls, active polling or additional bus connections are added.

Validation includes fixed recorded checksums, every single-bit corruption of
recorded examples, split TCP frames, channel mappings, invalid values, actual
Home Assistant entity registration, units, statistics and disconnect handling.

Install this update through HACS, then restart Home Assistant to load the new
Python code. The twelve new sensor entities are created automatically.
