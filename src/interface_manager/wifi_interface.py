import logging
import time
from enum import Enum

from .adapters.nmcli_adapter import NMCliAdapter
from .network_interface_base import NetworkInterface, InterfaceTypes

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class WiFiInterface(NetworkInterface):
    class ConnectionType(str, Enum):
        CONNECTION_TYPE_DISABLED = "disabled"
        CONNECTION_TYPE_STATION = "station"
        CONNECTION_TYPE_AP = "ap"

        @classmethod
        def from_string(cls, value: str):
            try:
                return cls(value)
            except ValueError:
                available_types = ", ".join([e.value for e in cls])
                raise ValueError(f"Invalid connection type: {value}, available types are: {available_types}")

    TYPE = InterfaceTypes.INTERFACE_TYPE_WIFI

    def __init__(self, device, adapter: NMCliAdapter, def_config):
        super().__init__(device, adapter, def_config)
        self._connection_type = self.ConnectionType.CONNECTION_TYPE_DISABLED
        self._ssid = ""
        self._passphrase = ""
        self._ip_read_only = True
        self._load_defaults()

    def _load_defaults(self):
        self._connection_type = self.ConnectionType.from_string(self._def_config.get('WiFi', 'DefaultWiFiConnectionType'))
        self._ip = self._def_config.get('WiFi', 'DefaultWiFiIP')
        self._mask = self._def_config.get('WiFi', 'DefaultWiFiMask')
        self._route = self._def_config.get('WiFi', 'DefaultWiFiRoute')
        self._ssid = self._def_config.get('WiFi', 'DefaultWiFiSSID')
        self._passphrase = self._def_config.get('WiFi', 'DefaultWiFiPassphrase')

    def load_config(self, config):
        with self._lock:
            try:
                cfg = config[self._device]
                if not all(name in cfg for name in ["connection_type", "ip", "mask", "route", "ssid", "passphrase"]):
                    raise Exception("Not all parameters saved in the configuration, revert to defaults")
                self._connection_type.from_string(cfg["connection_type"])
                self._ip = cfg["ip"]
                self._mask = cfg["mask"]
                self._route = cfg["route"]
                self._ssid = cfg["ssid"]
                self._passphrase = cfg["passphrase"]
                logger.info(f"Read parameters for {self._device}: {self._connection_type} | IP {self._ip} | Mask {self._mask} | Route {self._route} | SSID {self._ssid}")
            except Exception as e:
                logger.warning(f"No configuration for {self._device} found ({e}), use defaults")

    def get_config(self):
        with self._lock:
            conf = {
                self._device: {
                    "type": self.type.value,
                    "connection_type": self._connection_type.value,
                    "ip": self._ip,
                    "mask": self._mask,
                    "route": self._route,
                    "ssid": self._ssid,
                    "passphrase": self._passphrase
                }
            }
            return conf

    def initialise(self):
        pass

    @property
    def connection_type(self):
        with self._lock:
            return self._connection_type.value

    @connection_type.setter
    def connection_type(self, value):
        with self._lock:
            if self._connection_type != value:
                self._connection_type = self.ConnectionType.from_string(value)

    @property
    def ssid(self):
        with self._lock:
            return self._ssid

    @ssid.setter
    def ssid(self, value):
        with self._lock:
            if self._ssid != value:
                self._ssid = value

    @property
    def passphrase(self):
        with self._lock:
            return self._passphrase

    @passphrase.setter
    def passphrase(self, value):
        with self._lock:
            if self._passphrase != value:
                self._passphrase = value

    @property
    def scan(self):
        with self._lock:
            return self._scan()

    def _scan(self):
        wifi_list = set()
        logger.info(f'Start scan on {self._device}')
        results = self._adapter.device_wifi(ifname=self._device)
        for result in results:
            if result.ssid:
                wifi_list.add(result.ssid)
        logger.info(f'Scan results {self._device}: {wifi_list}')
        return list(wifi_list)

    def _reset_wifi(self, leave_active_name=''):
        # self._adapter.stop_dnsmasq()
        # self._adapter.stop_hostapd()
        connections = self._adapter.connection()
        for connection in connections:
            if connection.device == self._device:
                if leave_active_name and leave_active_name == connection.name:
                    logger.info(f'Skip deleting connection {self._device} {connection.name}')
                else:
                    logger.warning(f'Delete connection {self._device} {connection.name}')
                    try:
                        self._adapter.connection_down(name=connection.name)
                    except Exception as e:
                        logger.error(f'Error deactivating Wi-Fi {self._device}: {e}')
                    try:
                        self._adapter.connection_delete(connection.name)
                    except Exception as e:
                        logger.error(f'Error deleting Wi-Fi {self._device}: {e}')
        self._scan()

    def reload(self):
        try:
            if self._connection_type == self.ConnectionType.CONNECTION_TYPE_DISABLED:
                self._status_message('Disabling...')
                self._reset_wifi()
                time.sleep(2)
                self._adapter.radio_wifi_off()
                self._status_message('Disabled')
            elif self._connection_type == self.ConnectionType.CONNECTION_TYPE_STATION:
                if self._ssid and self._passphrase:
                    self._status_message('Power on...')
                    self._adapter.radio_wifi_on()
                    time.sleep(2)
                    for tries in range(2):
                        try:
                            self._status_message('Resetting...')
                            self._reset_wifi()
                            time.sleep(2)
                            if tries:
                                self._status_message(f'Connecting to {self._ssid} try {tries}...')
                            else:
                                self._status_message(f'Connecting to {self._ssid}...')
                            # TODO: Check timeout
                            logger.info(f'Connecting to {bytes(self._ssid, "utf-8")}')
                            self._adapter.device_wifi_connect(ssid=f'{self._ssid}',
                                                              password=f'{self._passphrase}')
                            self._adapter.connection_modify(name=self._ssid, options={'connection.autoconnect': 'yes'})
                            self._status_message(f'{self.status}')
                            break
                        except Exception as e:
                            self._status_message(f'Station: {e}', error=True)
                            time.sleep(2)
                else:
                    self._status_message(f'Enter the credentials', error=True)
            elif self._connection_type == self.ConnectionType.CONNECTION_TYPE_AP:
                for tries in range(2):
                    try:
                        self._status_message('Resetting...')
                        self._reset_wifi()
                        time.sleep(2)
                        if tries:
                            self._status_message(f'Creating access point try {tries}...')
                        else:
                            self._status_message('Creating access point...')
                        self._adapter.device_wifi_hotspot(con_name="hotspot", ifname=self._device, ssid=f'{self._ssid}', password=f'{self._passphrase}')
                        self._adapter.connection_modify(name='hotspot', options={'ipv4.method': 'shared'})
                        self._adapter.connection_modify(name='hotspot', options={'connection.autoconnect': 'yes'})
                        self._adapter.connection_modify(name='hotspot', options={'802-11-wireless.mode': 'wpa-psk'})

                        # Alternative:
                        # nmcli con add type wifi ifname wlan0 con-name Hostspot autoconnect yes ssid Hostspot
                        # nmcli con modify Hostspot 802-11-wireless.mode ap 802-11-wireless.band bg ipv4.method shared
                        # nmcli con modify Hostspot wifi-sec.key-mgmt wpa-psk
                        # nmcli con modify Hostspot wifi-sec.psk "veryveryhardpassword1234"
                        # nmcli con up Hostspot

                        self._status_message(f'{self.status}')
                    except Exception as e:
                        self._status_message(f'Hotspot: {e}', error=True)
                else:
                    self._status_message('Unknown network type', error=True)
            else:
                self._status_message('Unknown network type', error=True)
        except Exception as e:
            self._status_message(f"Wi-Fi: {e}", error=True)

    def refresh(self):
        with self._lock:
            try:
                self._status_message(self.status)
                iface = self._adapter.ifconfig(self._device)

                ipv4_addr = iface.ipv4_addr
                if iface.ipv4_addr is None:
                    ipv4_addr = '0.0.0.0'

                ipv4_mask = iface.ipv4_mask
                if iface.ipv4_mask is None:
                    ipv4_mask = '0.0.0.0'

                ipv4_bcast = iface.ipv4_bcast
                if iface.ipv4_bcast is None:
                    ipv4_bcast = '0.0.0.0'

                if self._connection_type == self.ConnectionType.CONNECTION_TYPE_STATION:
                    self._ip = ipv4_addr
                    self._mask = ipv4_mask
                    self._route = ipv4_bcast

            except Exception as e:
                self._status_message(f'Error checking {self._device}: {e}', error=True)

