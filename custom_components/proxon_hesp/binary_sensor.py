"""Read-only reported panel and controller switching states."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ProxonConfigEntry
from .const import DOMAIN
from .rooms import async_setup_rooms

DESCRIPTIONS = (
    BinarySensorEntityDescription(
        key="intensive_ventilation",
        translation_key="intensive_ventilation",
        icon="mdi:fan-plus",
    ),
    BinarySensorEntityDescription(
        key="bypass_status",
        translation_key="bypass_status",
        icon="mdi:swap-horizontal",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ProxonConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    await async_setup_rooms(hass, entry, async_add_entities, "binary_sensor")
    async_add_entities(
        [
            *(ProxonBinarySensor(entry, desc) for desc in DESCRIPTIONS),
            ProxonCompressorSensor(
                entry,
                BinarySensorEntityDescription(
                    key="compressor_running",
                    translation_key="compressor_running",
                    icon="mdi:engine",
                ),
            ),
            ProxonConnectionSensor(
                entry,
                BinarySensorEntityDescription(
                    key="connection",
                    translation_key="connection",
                    device_class=BinarySensorDeviceClass.CONNECTIVITY,
                    entity_category=EntityCategory.DIAGNOSTIC,
                    entity_registry_enabled_default=False,
                ),
            ),
        ]
    )


class ProxonBinarySensor(BinarySensorEntity):
    """Report observed states with independent freshness for each data point."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self, entry: ProxonConfigEntry, description: BinarySensorEntityDescription
    ) -> None:
        self.entity_description = description
        self.runtime = entry.runtime_data
        self._attr_unique_id = f"{entry.unique_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name=entry.title,
            manufacturer="Zimmermann",
            model="PROXON P-Serie (HESP)",
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.runtime.listen(self.async_write_ha_state))

    @property
    def available(self) -> bool:
        return self.runtime.get(self.entity_description.key) is not None

    @property
    def is_on(self) -> bool | None:
        reading = self.runtime.get(self.entity_description.key)
        return reading.value if reading is not None else None


class ProxonCompressorSensor(ProxonBinarySensor):
    """Derive rotation from fresh validated RPM, not thermal operating mode."""

    @property
    def available(self) -> bool:
        return self.runtime.get("compressor_rpm") is not None

    @property
    def is_on(self) -> bool | None:
        reading = self.runtime.get("compressor_rpm")
        return reading.value > 0 if reading is not None else None


class ProxonConnectionSensor(ProxonBinarySensor):
    """TCP connection only; this does not assert fresh or supported telemetry."""

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.runtime.listen_diagnostics(self.async_write_ha_state))

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return self.runtime.connected
