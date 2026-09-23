"""Read-only reported panel and controller switching states."""

import time
from datetime import UTC, datetime, timedelta

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
            *(ProxonExperimentalBit(entry, bit) for bit in (8, 9, 28)),
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


class ProxonExperimentalBit(ProxonBinarySensor):
    """Expose an observed bit without assigning an actuator meaning."""

    def __init__(self, entry, bit):
        super().__init__(
            entry,
            BinarySensorEntityDescription(
                key=f"experimental_0208_bit_{bit}",
                translation_key=f"experimental_0208_bit_{bit}",
                entity_category=EntityCategory.DIAGNOSTIC,
                entity_registry_enabled_default=False,
                icon="mdi:flask-outline",
            ),
        )
        self.bit = bit
        self._sample_stamp = None
        self._received_at = None

    async def async_added_to_hass(self):
        self.async_on_remove(self.runtime.listen(self._update_sample))
        self._update_sample()

    def _update_sample(self):
        sample = self.runtime.values.get("experimental_status_0208")
        if sample is not None and sample[1] != self._sample_stamp:
            self._sample_stamp = sample[1]
            self._received_at = (
                datetime.now(UTC)
                - timedelta(seconds=max(0, time.monotonic() - sample[1]))
            ).isoformat()
        self.async_write_ha_state()

    @property
    def available(self):
        return self.runtime.get("experimental_status_0208") is not None

    @property
    def is_on(self):
        reading = self.runtime.get("experimental_status_0208")
        if reading is None:
            return None
        return bool(
            int.from_bytes(bytes.fromhex(reading.value), "little") & (1 << self.bit)
        )

    @property
    def extra_state_attributes(self):
        reading = self.runtime.get("experimental_status_0208")
        return {
            "data_point": "0x0208",
            "telegram_identity": "224000",
            "bit": self.bit,
            "bit_numbering": "LSB 0, little-endian uint32",
            "payload_hex": reading.value if reading else None,
            "status_word_hex": (
                f"{int.from_bytes(bytes.fromhex(reading.value), 'little'):08X}"
                if reading
                else None
            ),
            "last_valid_update": self._received_at,
            "interpretation": "unconfirmed",
        }
