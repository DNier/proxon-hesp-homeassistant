"""Synthetic framing fixtures do not assert real metadata semantics."""

import pytest

from custom_components.proxon_hesp.hesp.checksum import checksum
from tools.audit_metadata import audit_metadata


def frame(dp, values):
    payload = b"".join(v.to_bytes(2, "little") for v in values)
    body = b"\x22\x40\x00" + int(dp, 16).to_bytes(2, "little")
    body += b"\x00\x00" + bytes([len(payload) * 2]) + payload
    return (body + checksum(body).to_bytes(2, "little")).hex()


def replies():
    return {
        dp: frame(dp, values)
        for dp, values in {
            "0033": [0x226, 0x227],
            "0034": [0x204, 0x204],
            "0038": [0xFF, 0xFF],
        }.items()
    }


def test_aligns_only_verified_frames_without_claiming_permissions():
    result = audit_metadata(replies())
    assert result["rows"][1] == {
        "dp": "0x0227",
        "type_code": "0x0204",
        "mask_code": "0x00FF",
    }
    assert result["semantics"] == "unconfirmed_type_and_mask_codes"


@pytest.mark.parametrize(
    "mutation",
    ["truncated", "corrupt", "wrong_dp", "unequal", "missing", "zero_length"],
)
def test_rejects_unsafe_alignment(mutation):
    data = replies()
    if mutation == "truncated":
        data["0033"] = frame("0033", list(range(28)))[:128]
    elif mutation == "corrupt":
        data["0033"] = data["0033"][:-2] + "ff"
    elif mutation == "wrong_dp":
        data["0033"] = frame("0034", [1, 2])
    elif mutation == "unequal":
        data["0034"] = frame("0034", [1])
    elif mutation == "missing":
        del data["0038"]
    else:
        data["0033"] = frame("0033", [])
    with pytest.raises(ValueError):
        audit_metadata(data)
