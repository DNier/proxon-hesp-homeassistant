"""HESP byte recurrence reconstructed from Markus Mauch's CC BY 4.0 table.

The state starts at 0xFFFF. Each byte is XORed into its low bits, followed
by the same invertible 16-bit linear transformation. This extends the
published end-aligned contributions without learning captured checksums.
See NOTICE.md and docs/CHECKSUM_ALGORITHM.md for derivation and validation.
"""

# Column i is the transformed state 1 << i; not a frame-specific lookup.
BYTE_TRANSFORM = (
    0xD1F4,
    0xA379,
    0x4663,
    0x8CC6,
    0x191D,
    0x323A,
    0x6474,
    0xC8E8,
    0x9141,
    0x2213,
    0x4426,
    0x884C,
    0x1009,
    0x2012,
    0x4024,
    0x8048,
)


def checksum(message: bytes) -> int | None:
    """Checksum excluding its two LE wire bytes; bounded to observed sizes.

    Header identity, payload length and value semantics are checked separately
    by the decoder. A matching checksum does not establish those properties.
    """
    if not 8 <= len(message) <= 120:
        return None
    state = 0xFFFF
    for byte in message:
        mixed = state ^ byte
        state = 0
        while mixed:
            bit = mixed & -mixed
            state ^= BYTE_TRANSFORM[bit.bit_length() - 1]
            mixed ^= bit
    return state
