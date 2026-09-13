"""Limited checksum model adapted from Markus Mauch (CC BY 4.0).

https://markusmauch.github.io/proxon-hesp/protokoll/#modell-in-tabellenform
Only explicitly known bit contributions are usable. Unknown is never zero.
This is not a general HESP checksum implementation. See NOTICE.md.
"""

VECTORS = {
    0: 0x8BB4,
    1: 0xA379,
    2: 0xB9E0,
    3: 0x0222,
    4: 0,
    5: 0,
    6: 0x6474,
    7: 0x92A8,
    8: 0x80FC,
    9: 0x0169,
    10: 0x02D2,
    11: 0x05A4,
    12: 0x0B48,
    13: 0x1690,
    14: 0x2D20,
    15: 0,
    16: 0xCD56,
    17: 0x9A3D,
    18: 0x34EB,
    19: 0x69D6,
    20: 0xD3AC,
    21: 0xA7C9,
    22: 0x4F03,
    23: 0x9E06,
    24: 0x0534,
    25: 0x0A68,
    26: 0x14D0,
    27: 0x29A0,
    28: 0x5340,
    29: 0xA680,
    30: 0x4D91,
    31: 0x9B22,
    32: 0xB823,
    33: 0x70D7,
    34: 0xE1AE,
    35: 0xC3CD,
    36: 0x870B,
    37: 0x0E87,
    38: 0x1D0E,
    39: 0x3A1C,
    40: 0x78A8,
    41: 0xF150,
    42: 0xE231,
    43: 0xC4F3,
    45: 0xC2BE,
    46: 0,
    48: 0x8E67,
    49: 0x1C5F,
    50: 0x38BE,
    51: 0x717C,
    52: 0xE2F8,
    53: 0xC561,
    54: 0x8A53,
    55: 0x1437,
    56: 0x0C91,
    57: 0x1922,
    58: 0x3244,
    59: 0xECB4,
    61: 0x136C,
    62: 0x6E15,
    63: 0,
    64: 0xCC6B,
    65: 0x9847,
    66: 0x301F,
    67: 0x603E,
    68: 0xC07C,
    69: 0x8069,
    70: 0x0043,
    71: 0x0086,
    72: 0xA403,
    73: 0xE47B,
    76: 0x6242,
    77: 0,
    78: 0x3B0B,
    79: 0,
    81: 0,
    85: 0,
    86: 0x0DAF,
    87: 0x1213,
    88: 0,
    89: 0,
    92: 0,
    93: 0,
}


def checksum(message: bytes) -> int | None:
    """Return the partial model result, or None when outside its scope."""
    if not 8 <= len(message) <= 12:
        return None
    result = 0
    for index, byte in enumerate(message):
        for bit in range(8):
            if byte & (1 << bit):
                position = (len(message) - 1 - index) * 8 + bit
                if position not in VECTORS:
                    return None
                result ^= VECTORS[position]
    return result
