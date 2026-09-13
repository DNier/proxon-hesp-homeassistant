"""Exercise real HA flow registration, validation and entry creation."""

from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proxon_hesp.const import DOMAIN, PROFILE
from custom_components.proxon_hesp.hesp.transport import NoSupportedData

INPUT = {"host": "gateway.test", "port": 4196, "name": "PROXON", "profile": PROFILE}


async def test_form_and_create(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    with (
        patch("custom_components.proxon_hesp.config_flow.probe") as probe,
        patch("custom_components.proxon_hesp.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], INPUT
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["host"] == "gateway.test"
    assert len(result["result"].unique_id) == 32
    probe.assert_awaited_once()


@pytest.mark.parametrize(
    "error,expected",
    [(OSError(), "cannot_connect"), (NoSupportedData(), "no_supported_data")],
)
async def test_errors(hass, error, expected):
    with patch("custom_components.proxon_hesp.config_flow.probe", side_effect=error):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=INPUT
        )
    assert result["errors"] == {"base": expected}


async def test_duplicate_never_opens_second_connection(hass):
    MockConfigEntry(domain=DOMAIN, data=INPUT, unique_id="one").add_to_hass(hass)
    with patch("custom_components.proxon_hesp.config_flow.probe") as probe:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=INPUT
        )
    assert result["reason"] == "already_configured"
    probe.assert_not_called()


async def test_reconfigure_preserves_identity_and_skips_same_endpoint_probe(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=INPUT, title="Old", unique_id="stable")
    entry.add_to_hass(hass)
    with (
        patch("custom_components.proxon_hesp.config_flow.probe") as probe,
        patch.object(hass.config_entries, "async_reload", return_value=True),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
            data={**INPUT, "name": "New"},
        )
    assert result["reason"] == "reconfigure_successful"
    assert entry.unique_id == "stable"
    assert entry.title == "New"
    probe.assert_not_called()
