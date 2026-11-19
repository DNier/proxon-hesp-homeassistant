"""Configure optional daylight saving time correction for one PROXON device."""

import logging
from datetime import date, datetime, timedelta

from homeassistant.components.switch import SwitchEntity
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from .const import CONF_AUTO_CLOCK_SYNC, DOMAIN

_LOGGER = logging.getLogger(__name__)
_CHECK_HOUR = 4
_CHECK_MINUTE = 15
_CLOCK_TOLERANCE = timedelta(minutes=2)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([AutomaticClockSyncSwitch(entry)])


class AutomaticClockSyncSwitch(SwitchEntity):
    """Store the device's opt-in independently of its connection state."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "auto_clock_sync"
    _attr_icon = "mdi:clock-check-outline"

    def __init__(self, entry):
        self._entry = entry
        self._runtime = entry.runtime_data
        self._attr_unique_id = f"{entry.unique_id}_auto_clock_sync"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.unique_id)})
        self._enabled_after: datetime | None = None
        self._last_attempt: date | None = None

    async def async_added_to_hass(self):
        self._enabled_after = dt_util.utcnow()
        self.async_on_remove(
            async_track_time_change(
                self.hass,
                self._async_check,
                hour=_CHECK_HOUR,
                minute=_CHECK_MINUTE,
                second=0,
            )
        )

    async def async_will_remove_from_hass(self):
        self._enabled_after = None

    @property
    def is_on(self) -> bool:
        return self._entry.options.get(CONF_AUTO_CLOCK_SYNC) is True

    async def async_turn_on(self, **kwargs):
        if self.is_on:
            return
        enabled_at = dt_util.utcnow()
        self._enabled_after = enabled_at
        self._set_enabled(True)
        if self._fresh_calendar() is None:
            _LOGGER.warning(
                "Initial clock correction skipped: no fresh device calendar"
            )
            return
        await self._async_align(dt_util.as_local(enabled_at).date())

    async def async_turn_off(self, **kwargs):
        if self.is_on:
            self._set_enabled(False)

    def _set_enabled(self, enabled: bool) -> None:
        self.hass.config_entries.async_update_entry(
            self._entry, options={**self._entry.options, CONF_AUTO_CLOCK_SYNC: enabled}
        )
        self.async_write_ha_state()

    def _fresh_calendar(self) -> datetime | None:
        # A newer invalid calendar telegram cannot authorize a write with old data.
        reading = self._runtime.get("device_datetime")
        if (
            not self._runtime.decoder.last_calendar_valid
            or reading is None
            or not isinstance(reading.value, str)
        ):
            return None
        return datetime.fromisoformat(reading.value)

    async def _async_check(self, local: datetime) -> None:
        if (
            not self.is_on
            or self._enabled_after is None
            or self._last_attempt == local.date()
            or (local.hour, local.minute) != (_CHECK_HOUR, _CHECK_MINUTE)
        ):
            return
        scheduled = local.replace(second=0, microsecond=0)
        if self._enabled_after >= dt_util.as_utc(scheduled):
            return

        previous = local - timedelta(days=1)
        current_offset = local.utcoffset()
        previous_offset = previous.utcoffset()
        if (
            current_offset is None
            or previous_offset is None
            or current_offset == previous_offset
            or local.dst() == previous.dst()
            or local.replace(fold=0).utcoffset() != local.replace(fold=1).utcoffset()
        ):
            return
        shift = current_offset - previous_offset

        calendar = self._fresh_calendar()
        if calendar is None:
            return
        lag = local.replace(tzinfo=None) - calendar
        if abs(lag - shift) > _CLOCK_TOLERANCE:
            return

        await self._async_align(local.date())

    async def _async_align(self, day: date) -> None:
        self._last_attempt = day
        try:
            await self._runtime.sync_clock()
        except HomeAssistantError as err:
            _LOGGER.warning("Automatic device time correction failed: %s", err)
