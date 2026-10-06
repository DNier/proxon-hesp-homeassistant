"""Read-only panel and controller sensors."""

import time
from datetime import UTC, date, datetime, timedelta

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ProxonConfigEntry
from .capture import STATUSES
from .const import DOMAIN
from .event_capture import EVENT_STATUSES
from .hesp.decoder import (
    MODES,
    PANEL_RAW_POINTS,
    RAW_OBSERVATION_SOURCES,
    RAW_POINTS,
    TEMPERATURE_KEYS,
)
from .rooms import async_setup_rooms

AIR_TEMPERATURE_KEYS = frozenset(TEMPERATURE_KEYS[:4])

DESCRIPTIONS = (
    SensorEntityDescription(
        key="cooling_threshold",
        translation_key="cooling_threshold",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        icon="mdi:thermometer",
    ),
    *(
        SensorEntityDescription(
            key=key,
            translation_key=key,
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            native_unit_of_measurement=PERCENTAGE,
            suggested_display_precision=0,
            icon="mdi:tune",
        )
        for key in (
            "max_heating_output",
            "max_cooling_output",
            *(
                f"fan_{direction}_stage_{stage}"
                for direction in ("supply", "extract")
                for stage in range(1, 5)
            ),
        )
    ),
    *(
        SensorEntityDescription(
            key=key,
            translation_key=key,
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            icon="mdi:fan",
        )
        for key in (
            "controller_fan_level",
            "fan_supply_control",
            "fan_extract_control",
        )
    ),
    *(
        SensorEntityDescription(
            key=key,
            translation_key=key,
            entity_category=(
                None if key in AIR_TEMPERATURE_KEYS else EntityCategory.DIAGNOSTIC
            ),
            entity_registry_enabled_default=key in AIR_TEMPERATURE_KEYS,
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
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            native_unit_of_measurement="rpm",
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=0,
            icon="mdi:engine" if key == "compressor_rpm" else "mdi:fan",
        )
        for key in ("fan_supply_rpm", "fan_extract_rpm", "compressor_rpm")
    ),
    SensorEntityDescription(
        key="device_date",
        translation_key="device_date",
        device_class=SensorDeviceClass.DATE,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:calendar",
    ),
    SensorEntityDescription(
        key="device_datetime",
        translation_key="device_datetime",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:calendar-clock",
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
    *(
        SensorEntityDescription(
            key=key,
            translation_key=key,
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            icon="mdi:code-braces",
        )
        for key in (
            "raw_0208",
            *(
                key
                for points in PANEL_RAW_POINTS.values()
                for key, _ in points.values()
            ),
        )
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
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.DAYS,
        suggested_display_precision=0,
        icon="mdi:air-filter",
    ),
    SensorEntityDescription(
        key="uptime",
        translation_key="uptime",
        entity_registry_enabled_default=False,
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
    await async_setup_rooms(hass, entry, async_add_entities, "sensor")
    async_add_entities(
        [
            *(ProxonSensor(entry, description) for description in DESCRIPTIONS),
            ProxonDiagnosticSensor(
                entry,
                SensorEntityDescription(
                    key="event_capture_status",
                    translation_key="event_capture_status",
                    device_class=SensorDeviceClass.ENUM,
                    options=list(EVENT_STATUSES),
                    entity_category=EntityCategory.DIAGNOSTIC,
                    icon="mdi:record-rec",
                ),
            ),
            ProxonDiagnosticSensor(
                entry,
                SensorEntityDescription(
                    key="capture_status",
                    translation_key="capture_status",
                    device_class=SensorDeviceClass.ENUM,
                    options=list(STATUSES),
                    entity_category=EntityCategory.DIAGNOSTIC,
                    icon="mdi:record-rec",
                ),
            ),
            ProxonDiagnosticSensor(
                entry,
                SensorEntityDescription(
                    key="last_valid_received",
                    translation_key="last_valid_received",
                    device_class=SensorDeviceClass.TIMESTAMP,
                    entity_category=EntityCategory.DIAGNOSTIC,
                    entity_registry_enabled_default=False,
                ),
            ),
        ]
    )


class ProxonSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry: ProxonConfigEntry, description: SensorEntityDescription):
        self.entity_description = description
        self.runtime = entry.runtime_data
        self._attr_unique_id = f"{entry.unique_id}_{description.key}"
        self._sample_stamp = None
        self._received_at = None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name=entry.title,
            manufacturer="Zimmermann",
            model="PROXON P-Serie (HESP)",
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.runtime.listen(self._update_sample))
        self._update_sample()

    def _update_sample(self) -> None:
        if self.source_key in RAW_OBSERVATION_SOURCES:
            sample = self.runtime.values.get(self.source_key)
            if sample is not None and sample[1] != self._sample_stamp:
                self._sample_stamp = sample[1]
                self._received_at = (
                    datetime.now(UTC)
                    - timedelta(seconds=max(0, time.monotonic() - sample[1]))
                ).isoformat()
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        return self.runtime.get(self.source_key) is not None

    @property
    def source_key(self) -> str:
        if self.entity_description.key == "device_date":
            return "device_datetime"
        return self.entity_description.key

    @property
    def native_value(self):
        reading = self.runtime.get(self.source_key)
        if reading and self.entity_description.key == "device_date":
            return date.fromisoformat(reading.value.split("T", 1)[0])
        return reading.value if reading else None

    @property
    def extra_state_attributes(self):
        source = RAW_OBSERVATION_SOURCES.get(self.source_key)
        if source is None:
            return None
        identity, dp, size = source
        attributes = {
            "source_header": identity.hex(),
            "dp_id": f"0x{dp:04X}",
            "payload_length": size,
        }
        if self.runtime.get(self.source_key) is not None:
            attributes["last_valid_update"] = self._received_at
        return attributes


class ProxonDiagnosticSensor(ProxonSensor):
    """Local diagnostics remain readable without fresh telemetry."""

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.runtime.listen_diagnostics(self.async_write_ha_state))

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self):
        if self.entity_description.key == "event_capture_status":
            return self.runtime.event_capture.status
        if self.entity_description.key == "capture_status":
            return self.runtime.capture.reason
        return self.runtime.last_valid_received

    @property
    def extra_state_attributes(self):
        if self.entity_description.key == "event_capture_status":
            return self.runtime.event_capture.summary()
        if self.entity_description.key == "capture_status":
            return self.runtime.capture.summary()
        return None
