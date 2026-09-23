"""Device-scoped capture controls and an explicit calendar correction."""

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
        ("event_capture_clear", "mdi:delete-clock-outline"),
    )
)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        [
            *(CaptureButton(entry, description) for description in DESCRIPTIONS),
            ClockSyncButton(
                entry,
                ButtonEntityDescription(
                    key="clock_sync",
                    translation_key="clock_sync",
                    icon="mdi:clock-check-outline",
                    entity_category=EntityCategory.CONFIG,
                    entity_registry_enabled_default=False,
                ),
            ),
        ]
    )


class CaptureButton(ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, entry, description):
        self.entity_description = description
        self.runtime = entry.runtime_data
        self._attr_unique_id = f"{entry.unique_id}_{description.key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.unique_id)})

    async def async_press(self):
        if self.entity_description.key == "event_capture_clear":
            self.runtime.event_capture.clear()
            return
        action = self.entity_description.key.removeprefix("capture_")
        getattr(self.runtime.capture, action)()


class ClockSyncButton(CaptureButton):
    """Optional manual action; no automatic invocation on setup or reconnect."""

    async def async_added_to_hass(self):
        self.async_on_remove(self.runtime.listen(self.async_write_ha_state))
        self.async_on_remove(self.runtime.listen_diagnostics(self.async_write_ha_state))

    @property
    def available(self):
        return (
            self.runtime.get("uptime") is not None and self.runtime.writer is not None
        )

    @property
    def extra_state_attributes(self):
        return {
            "status": self.runtime.clock_sync_status,
            "target_local_time": self.runtime.clock_sync_target,
        }

    async def async_press(self):
        await self.runtime.sync_clock()
