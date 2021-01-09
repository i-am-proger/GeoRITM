# The domain of your component. Should be equal to the name of your component.
import logging, json, requests
import voluptuous as vol

from homeassistant.core import ServiceCall
from homeassistant.helpers.entity import Entity
from homeassistant.helpers import discovery, config_validation as cv
from homeassistant.const import (CONF_EMAIL, CONF_PASSWORD, CONF_USERNAME)


DOMAIN = "georitm"

REQUIREMENTS = []

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Exclusive(CONF_USERNAME, CONF_PASSWORD): cv.string, 
        vol.Exclusive(CONF_EMAIL, CONF_PASSWORD): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }, extra=vol.ALLOW_EXTRA),
}, extra=vol.ALLOW_EXTRA)


def setup(hass, config):
    """Set up the GeoRITM component."""

    _LOGGER.debug("Create the main object")

    # hass.data[DOMAIN] = GeoRITM(hass, email, password)
    hass.data[DOMAIN] = GeoRITM(hass, config)

    for platform in ['binary_sensor']:
        discovery.load_platform(hass, platform, DOMAIN, {}, config)

    def send_command(call: ServiceCall):
        data = dict(call.data)
        entity = str(data.pop('entity_id'))
        command = str(data.pop('command'))
        hass.data[DOMAIN].send_command(entity, hass.states.get(entity), command)

    hass.services.register(DOMAIN, 'send_command', send_command)

    return True


class GeoRITM():
    # def __init__(self, hass, email, password):
    def __init__(self, hass, config):
        self._hass = hass

        # get username & password from configuration.yaml
        email    = config.get(DOMAIN, {}).get(CONF_EMAIL,'')
        username = config.get(DOMAIN, {}).get(CONF_USERNAME,'')
        password = config.get(DOMAIN, {}).get(CONF_PASSWORD,'')

        if email and not username: # backwards compatibility
            self._username = email.strip()
        else: # already validated by voluptous
            self._username      = username.strip()

        self._password      = password

        self._user_apikey   = None
        self._devices       = []

        self.do_login(update_devices=True)

    def do_login(self, update_devices=True):
        login_data = {
            'login'    : self._username,
            'password' : self._password
        }
        self._headers = {
            'User-Agent'   : 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
            'Content-Type' : 'application/json'
        }
        r = requests.post('https://core.geo.ritm.ru/restapi/users/login/', headers=self._headers, json=login_data)
        if r.status_code == 200:
            resp = r.json()

            if 'username' not in resp and 'basic' not in resp:
                _LOGGER.error("Couldn't authenticate using the provided credentials!")
                self.do_login(update_devices=update_devices)
                return

            _LOGGER.info("mobileCount    : %s" % resp['mobileCount'])
            _LOGGER.info("stationaryCount: %s" % resp['stationaryCount'])

            self._user_apikey = resp['basic']
            self._headers.update({'Authorization' : 'Basic %s' % self._user_apikey})

            if update_devices:
                self.update_devices()
        else:
            _LOGGER.error("Couldn't authenticate using the provided credentials!")
            self.do_login(update_devices=update_devices)

    def get_devices(self, force_update=False):
        if force_update:
            self.update_devices()
        return self._devices

    def update_devices(self):
        self._devices = []

        if self._user_apikey:
            objects_data = {
                'sort' : 'name'
            }
            for groupType in [0, 1]:
                objects_data.update({'groupType' : groupType})
                r = requests.post('https://core.geo.ritm.ru/restapi/objects/objects-tree-set/', headers=self._headers, json=objects_data)
                if r.status_code == 200:
                    resp = r.json()
                    if isinstance(resp, list):
                        for item in resp:
                            if isinstance(item, dict) and 'objs' in item:
                                self._devices.extend(item['objs'])

        _LOGGER.info("devicesCount   : %s" % len(self._devices))

        if len(self._devices) == 0:
            _LOGGER.info("Re-login component")
            self.do_login(update_devices=False)
        else:
            for device in self._devices:
                if int(device['objType']) == 1:
                    device['areas'] = self.get_areas(device['id'])

        return self._devices

    def get_device(self, deviceid):
        device = {}
        device_data = {
            'objectId' : [deviceid]
        }
        r = requests.post('https://core.geo.ritm.ru/restapi/objects/obj/', headers=self._headers, json=device_data)
        if r.status_code == 200:
            resp = r.json()
            if isinstance(resp, list):
                for item in resp:
                    if isinstance(item, dict):
                        device.update(item)
        if device.get('id') == deviceid:
            if int(device['objType']) == 1:
                device['areas'] = self.get_areas(deviceid)
            return device
        return None

    def get_areas(self, deviceid):
        areas = []
        device_data = {
            'objectId': deviceid
        }
        r = requests.post('https://core.geo.ritm.ru/restapi/objects/obj-areas/', headers=self._headers, json=device_data)
        if r.status_code == 200:
            resp = r.json()
            if isinstance(resp, list):
                for item in resp:
                    if isinstance(item, dict):
                        areas.append(item)
        return areas

    def get_user_apikey(self):
        return self._user_apikey

    async def async_update(self):
        devices = self.update_devices()

    def send_command(self, entity, state, command):
        if entity:
            device = self.get_device(state.attributes['deviceId'])
            if device:
                if command == 'armed':
                    for item in device['devices']:
                        for area in device.get('areas', []):
                            if area['name']:
                                device_data = {
                                    'imei': str(item['imei']),
                                    'area': int(area['num'])
                                }
                                requests.post('https://core.geo.ritm.ru/restapi/objects/arm/', headers=self._headers, json=device_data)
                    self._hass.states.set(entity, 'off', state.attributes.copy())
                elif command == 'disarmed':
                    for item in device['devices']:
                        for area in device.get('areas', []):
                            if area['name']:
                                device_data = {
                                    'imei': str(item['imei']),
                                    'area': int(area['num'])
                                }
                                requests.post('https://core.geo.ritm.ru/restapi/objects/disarm/', headers=self._headers, json=device_data)
                    self._hass.states.set(entity, 'on', state.attributes.copy())


class GeoRITMDevice(Entity):
    """Representation of a GeoRITM entity"""

    def __init__(self, hass, device):
        """Initialize the device."""
        self._hass          = hass
        self._deviceid      = device['id']
        self._device        = self._hass.data[DOMAIN].get_device(self._deviceid)
        self._name          = None
        self._state         = None
        self._attributes    = {
            'deviceId'      : self._deviceid
        }

    def update(self):
        """Update device state."""
        self._device = self._hass.data[DOMAIN].get_device(self._deviceid)

    def get_available(self):
        return self._device['objectState']['isOnline'] == 1 if self._device else False

    @property
    def should_poll(self):
        """Return the polling state."""
        return True

    @property
    def name(self):
        """Return the name."""
        return self._name

    @property
    def available(self):
        """Return true if device is online."""
        return self.get_available()

    @property
    def device_state_attributes(self):
        """Return device specific state attributes."""
        return self._attributes
