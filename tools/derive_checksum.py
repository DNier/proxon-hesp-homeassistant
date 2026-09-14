"""Reproduce the byte transform without any private training captures.

Reference V[16:44] and query example: Markus Mauch, CC BY 4.0, see NOTICE.md.
Only structural assumptions are a shared linear byte step and a fixed seed.
"""

from custom_components.proxon_hesp.hesp.checksum import BYTE_TRANSFORM
from tools.analyze_temperature_checksum import reduce

REFERENCE = (
    0xCD56,
    0x9A3D,
    0x34EB,
    0x69D6,
    0xD3AC,
    0xA7C9,
    0x4F03,
    0x9E06,
    0x0534,
    0x0A68,
    0x14D0,
    0x29A0,
    0x5340,
    0xA680,
    0x4D91,
    0x9B22,
    0xB823,
    0x70D7,
    0xE1AE,
    0xC3CD,
    0x870B,
    0x0E87,
    0x1D0E,
    0x3A1C,
    0x78A8,
    0xF150,
    0xE231,
    0xC4F3,
)


def derive():
    basis, inverse = {}, {}
    for before, after in zip(REFERENCE[:20], REFERENCE[8:], strict=True):
        for rows, x, y in ((basis, before, after), (inverse, after, before)):
            row, value = reduce(x, y, rows)
            if row:
                rows[row.bit_length() - 1] = row, value
            elif value:
                raise ValueError("Inconsistent reference")
    if len(basis) != 16 or len(inverse) != 16:
        raise ValueError("Byte transform is not uniquely invertible")

    def transform(value, rows):
        remainder, result = reduce(value, 0, rows)
        if remainder:
            raise ValueError("Undetermined state")
        return result

    # Invert the published complete query/checksum to obtain the initial state.
    state = 0xE149
    for byte in reversed(bytes.fromhex("10800060010000040100")):
        state = transform(state, inverse) ^ byte
    return tuple(transform(1 << i, basis) for i in range(16)), state


if __name__ == "__main__":
    columns, seed = derive()
    assert columns == BYTE_TRANSFORM and seed == 0xFFFF
    print("Unique rank-16 byte transform; initial state:", hex(seed))
    print("Columns:", ", ".join(f"0x{x:04X}" for x in columns))
