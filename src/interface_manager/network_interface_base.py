import logging
import threading
from enum import Enum

from .adapters.nmcli_adapter import NMCliAdapter

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class InterfaceTypes(Enum):
    INTERFACE_TYPE_UNDEFINED = "undefined"
    INTERFACE_TYPE_WIFI = "wifi"
    INTERFACE_TYPE_WIFI_AP = "ap"
    INTERFACE_TYPE_ETHERNET = "ethernet"


class NetworkInterface:
    TYPE = InterfaceTypes.INTERFACE_TYPE_UNDEFINED

    def __init__(self, device, adapter: NMCliAdapter, def_config):
        self._connection_type = ""
        self._ip_read_only = False
        self._lock = threading.RLock()
        self._def_config = def_config
        self._status = None
        self._adapter = adapter
        self._device = device
        self._ip = ""
        self._mask = ""
        self._route = ""
        self._status_message_str = ""
        self._status_error = False

    def _status_message(self, message, error=False):
        logger.info(f"Status Message {self._device}: {message}")
        self._status_message_str = message
        self._status_error = error

    def refresh(self):
        raise NotImplementedError("Refresh on the base class not implemented")

    def initialise(self):
        raise NotImplementedError("Initialise on the base class not implemented")

    def _reload(self):
        raise NotImplementedError("Reload on the base class not implemented")

    def get_status(self):
        with self._lock:
            status = {
                self._device: {
                    "message": self._status_message_str,
                    "error": self._status_error,
                    "status": self.status
                }
            }
            return status

    @classmethod
    def parameters(cls):
        return [x for x in dir(cls)
                if isinstance( getattr(cls, x), property) ]

    @property
    def status(self):
        with self._lock:
            devices = self._adapter.device_status()
            for device in devices:
                if device.device == self._device:
                    return device.state
            return "No device"

    @property
    def device(self):
        with self._lock:
            return self._device

    @property
    def type(self):
        with self._lock:
            return self.TYPE

    @property
    def ip(self):
        with self._lock:
            return self._ip

    @ip.setter
    def ip(self, value):
        with self._lock:
            # if self._ip_read_only:
            #     return
            if self._ip != value:
                self._ip = value

    @property
    def connection_type(self):
        with self._lock:
            return self._connection_type

    @connection_type.setter
    def connection_type(self, value):
        with self._lock:
            if self._connection_type != value:
                self._connection_type = value

    @property
    def mask(self):
        with self._lock:
            return self._mask

    @mask.setter
    def mask(self, value):
        with self._lock:
            if self._mask != value:
                self._mask = value

    @property
    def route(self):
        with self._lock:
            return self._route

    @route.setter
    def route(self, value):
        with self._lock:
            if self._route != value:
                self._route = value

    def __getitem__(self, key):
        with self._lock:
            if hasattr(self, key):
                return getattr(self, key)
            else:
                raise KeyError(f"'{key}' not found")

    def __setitem__(self, key, value):
        with self._lock:
            if hasattr(self.__class__, key) and isinstance(getattr(self.__class__, key), property):
                setattr(self, key, value)
            else:
                raise KeyError(f"'{key}' not found or not writable")
