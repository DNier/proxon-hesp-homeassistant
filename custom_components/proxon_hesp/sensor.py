"""Read-only panel and controller sensors."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ProxonConfigEntry
from .const import DOMAIN
from .hesp.decoder import MODES, RAW_POINTS, TEMPERATURE_KEYS

DESCRIPTIONS = (
    *(
        SensorEntityDescription(
            key=key,
            translation_key=key,
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=1,
        )
        for key in TEMPERATURE_KEYS
    ),
    *(
        SensorEntityDescription(
            key=key,
            translation_key=key,
            native_unit_of_measurement="rpm",
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=0,
            icon="mdi:engine" if key == "compressor_rpm" else "mdi:fan",
        )
        for key in ("fan_supply_rpm", "fan_extract_rpm", "compressor_rpm")
    ),
    SensorEntityDescription(
        key="device_clock",
        translation_key="device_clock",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:clock-outline",
    ),
    *(
        SensorEntityDescription(
            key=f"raw_{dp:04x}",
            translation_key=f"raw_{dp:04x}",
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            icon="mdi:code-braces",
        )
        for dp in RAW_POINTS
    ),
    SensorEntityDescription(
        key="room_temperature",
        translation_key="room_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="target_temperature",
        translation_key="target_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="fan_level",
        translation_key="fan_level",
        icon="mdi:fan",
    ),
    SensorEntityDescription(
        key="operating_mode",
        translation_key="operating_mode",
        device_class=SensorDeviceClass.ENUM,
        options=list(MODES.values()),
    ),
    SensorEntityDescription(
        key="filter_days",
        translation_key="filter_days",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.DAYS,
        suggested_display_precision=0,
        icon="mdi:air-filter",
    ),
    SensorEntityDescription(
        key="uptime",
        translation_key="uptime",
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
    ),
    *(
        SensorEntityDescription(
            key=f"counter_{dp:04x}",
            translation_key=f"counter_{dp:04x}",
            entity_category=EntityCategory.DIAGNOSTIC,
            device_class=SensorDeviceClass.DURATION,
            native_unit_of_measurement=UnitOfTime.HOURS,
            suggested_display_precision=0,
            icon="mdi:counter",
        )
        for dp in (0x02D0, 0x02D1, 0x02D2, 0x02D3, 0x02D4, 0x02D5, 0x02D7, 0x02D9)
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ProxonConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(ProxonSensor(entry, description) for description in DESCRIPTIONS)


class ProxonSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry: ProxonConfigEntry, description: SensorEntityDescription):
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
    def native_value(self):
        reading = self.runtime.get(self.entity_description.key)
        return reading.value if reading else None
