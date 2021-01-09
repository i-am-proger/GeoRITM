import logging

from homeassistant.components.binary_sensor import DOMAIN, BinarySensorEntity
# from homeassistant.components.georitm import (DOMAIN as GEORITM_DOMAIN, GeoRITMDevice)
from custom_components.georitm import (DOMAIN as GEORITM_DOMAIN, GeoRITMDevice)


_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Add the GeoRITM Switch entities"""
    entities = []
    for device in hass.data[GEORITM_DOMAIN].get_devices():
        entities.append(GeoRITMGuardSensor(hass, device))
        if 'areas' in device:
            for area in device['areas']:
                entities.append(GeoRITMAreaSensor(hass, device, area))
                for zone in area['zones']:
                    entities.append(GeoRITMZoneSensor(hass, device, area, zone))
    add_entities(entities, update_before_add=False)


class GeoRITMGuardSensor(GeoRITMDevice, BinarySensorEntity):
    """Representation of a GeoRITM guard binary sensor."""

    def __init__(self, hass, device):
        GeoRITMDevice.__init__(self, hass, device)
        self._name = "{}: Охрана".format(device['name'])

    def get_state(self):
        if self._device:
            self._attributes.update({
                'objType'      : self._device.get('objType', ''),
                'region'       : self._device.get('region', ''),
                'city'         : self._device.get('city', ''),
                'addressShort' : self._device.get('addressShort', ''),
                'lat'          : self._device.get('lat', ''),
                'lon'          : self._device.get('lon', '')
            })
            return int(self._device['objectState']['isGuarded']) == 0
        return False

    @property
    def unique_id(self):
        return "{}.{}_{}_guard".format(DOMAIN, GEORITM_DOMAIN, self._deviceid)

    @property
    def device_class(self):
        return 'safety'

    @property
    def is_on(self):
        self._state = self.get_state()
        return self._state

    @property
    def icon(self):
        return 'mdi:lock-open-outline' if self._state else 'mdi:lock'

    @property
    def force_update(self):
        return True

    @property
    def state_attributes(self):
        return {}

    @property
    def supported_features(self):
        return 0


class GeoRITMAreaSensor(GeoRITMDevice, BinarySensorEntity):
    """Representation of a GeoRITM area binary sensor."""

    def __init__(self, hass, device, area):
        GeoRITMDevice.__init__(self, hass, device)
        self._name = "{}: {}".format(device['name'], area['name'] if area['name'] else "Зона {}".format(area['num']))
        self._areaid = area['id']

    def get_state(self):
        if self._device:
            for area in self._device.get('areas', []):
                if area['id'] == self._areaid:
                    self._attributes.update({
                        'areaId'   : area['id'],
                        'areaName' : area['name']
                    })
                    return int(area['hasAlarm']) == 1
        return True

    @property
    def unique_id(self):
        return "{}.{}_{}_{}".format(DOMAIN, GEORITM_DOMAIN, self._deviceid, self._areaid)

    @property
    def device_class(self):
        return 'problem'

    @property
    def is_on(self):
        self._state = self.get_state()
        return self._state

    @property
    def icon(self):
        return 'mdi:bell-ring' if self._state else 'mdi:bell'

    @property
    def force_update(self):
        return True

    @property
    def state_attributes(self):
        return {}

    @property
    def supported_features(self):
        return 0


class GeoRITMZoneSensor(GeoRITMDevice, BinarySensorEntity):
    """Representation of a GeoRITM zone binary sensor."""

    def __init__(self, hass, device, area, zone):
        GeoRITMDevice.__init__(self, hass, device)
        self._name = "{}: {} - {}".format(device['name'], area['name'] if area['name'] else "Зона {}".format(area['num']), zone['name'] if zone['name'] else "Раздел {}".format(zone['num']))
        self._areaid = area['id']
        self._zoneid = zone['id']

    def get_state(self):
        if self._device:
            for area in self._device.get('areas', []):
                if area['id'] == self._areaid:
                    for zone in area.get('zones', []):
                        if zone['id'] == self._zoneid:
                            self._attributes.update({
                                'areaId'   : area['id'],
                                'areaName' : area['name'],
                                'zoneId'   : zone['id'],
                                'zoneName' : zone['name']
                            })
                            return int(zone['hasAlarm']) == 1
        return True

    @property
    def unique_id(self):
        return "{}.{}_{}_{}".format(DOMAIN, GEORITM_DOMAIN, self._deviceid, self._zoneid)

    @property
    def device_class(self):
        return 'problem'

    @property
    def is_on(self):
        self._state = self.get_state()
        return self._state

    @property
    def icon(self):
        return 'mdi:bell-ring' if self._state else 'mdi:bell'

    @property
    def force_update(self):
        return True

    @property
    def state_attributes(self):
        return {}

    @property
    def supported_features(self):
        return 0
