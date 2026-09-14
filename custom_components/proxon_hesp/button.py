"""Device-scoped capture controls; never send anything to the bus."""

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.helpers.entity import DeviceInfo, EntityCategory

from .const import DOMAIN

DESCRIPTIONS = tuple(
    ButtonEntityDescription(
        key=key,
        translation_key=key,
        icon=icon,
        entity_category=EntityCategory.DIAGNOSTIC,
    )
    for key, icon in (
        ("capture_start", "mdi:record-rec"),
        ("capture_stop", "mdi:stop"),
        ("capture_clear", "mdi:delete-outline"),
    )
)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        CaptureButton(entry, description) for description in DESCRIPTIONS
    )


class CaptureButton(ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, entry, description):
        self.entity_description = description
        self.runtime = entry.runtime_data
        self._attr_unique_id = f"{entry.unique_id}_{description.key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.unique_id)})

    async def async_press(self):
        action = self.entity_description.key.removeprefix("capture_")
        getattr(self.runtime.capture, action)()
