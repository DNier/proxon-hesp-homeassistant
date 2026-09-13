"""Use Home Assistant's real test harness, with isolated fake gateways."""

import json
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def frames():
    fixture = Path(__file__).parent / "fixtures/panel_frames.json"
    return {
        key: bytes.fromhex(value)
        for key, value in json.loads(fixture.read_text()).items()
    }
