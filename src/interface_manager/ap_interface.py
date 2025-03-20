import logging
import time
from enum import Enum

from .network_interface_base import InterfaceTypes, NetworkInterface
from .adapters.nmcli_adapter import NMCliAdapter

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class APInterface(NetworkInterface):

    class ConnectionType(str, Enum):
        CONNECTION_TYPE_DISABLED = "disabled"
        CONNECTION_TYPE_AP = "ap"

        @classmethod
        def from_string(cls, value: str):
            try:
                return cls(value)
            except ValueError:
                available_types = ", ".join([e.value for e in cls])
                raise ValueError(f"Invalid connection type: {value}, available types are: {available_types}")

    TYPE = InterfaceTypes.INTERFACE_TYPE_WIFI_AP

    def __init__(self, device, adapter: NMCliAdapter, def_config):
        if not device:
            device = def_config.get('AP', 'APInterfaceDevice')
        super().__init__(device, adapter, def_config)
        self._ip_read_only = False
        self._ssid = ""
        self._passphrase = ""
        self._load_defaults()

    def _load_defaults(self):
        self._ssid = self._def_config.get('AP', 'DefaultAPSSID')
        self._passphrase = self._def_config.get('AP', 'DefaultAPPassphrase')
        self._mac = self._def_config.get('AP', 'APMAC')
        self._enable_ip_forward = self._def_config.getint('AP', 'IPForwardEnable')
        self._connection_type = self.ConnectionType.from_string(self._def_config.get('AP', 'DefaultAPConnectionType'))
        self._ip = self._def_config.get('AP', 'DefaultAPIP')
        self._mask = self._def_config.get('AP', 'DefaultAPMask')
        self._route = self._def_config.get('AP', 'DefaultAPRoute')

    def load_config(self, config, initialise=False):
        with self._lock:
            try:
                cfg = config[self._device]
                parameters = ["connection_type", "ip", "mask", "route", "ssid", "passphrase"]
                for parameter in parameters:
                    if parameter not in cfg:
                        raise Exception(f"Configuration missing parameters: {parameter}")
                self._connection_type.from_string(cfg["connection_type"])
                self._ip = cfg["ip"]
                self._mask = cfg["mask"]
                self._route = cfg["route"]
                self._ssid = cfg["ssid"]
                self._passphrase = cfg["passphrase"]
                logger.info(f"Read parameters for {self._device}: {self._connection_type} | IP {self._ip} | Mask {self._mask} | Route {self._route} | SSID {self._ssid}")
            except Exception as e:
                if initialise:
                    logger.warning(f"No configuration for {self._device} found ({e}), use defaults")
                else:
                    logger.warning(f"Failed to apply configuration {config} for {self._device}: ({e})")
                    raise Exception(f"Failed to apply configuration {config} for {self._device}: ({e})")

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

    def refresh(self):
        with self._lock:
            try:
                if self._update_pending:
                    self.reload()
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

                self._ssid = self._adapter.iw_dev_link(self._device)

                if self._connection_type == self.ConnectionType.CONNECTION_TYPE_AP:
                    self._ip = ipv4_addr
                    self._mask = ipv4_mask
                    self._route = ipv4_bcast

            except Exception as e:
                self._status_message(f'Error checking {self._device}: {e}', error=True)

    def initialise(self):
        devices = self._adapter.device()
        found = False
        for device in devices:
            if device.device == self._device:
                found = True
                break
        if not found:
            self._adapter.iw_add_interface('phy0', self._device, '__ap')
            self._adapter.enable_ip_forward(self._enable_ip_forward)
        self._adapter.ip_link_set_dev_address(self._device, self._mac)
        self._adapter.ip_link_set_up(self._device)

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

    def _reset_ap(self):
        # self._adapter.stop_dnsmasq()
        # self._adapter.stop_hostapd()
        connections = self._adapter.connection()
        for connection in connections:
            if connection.device == self._device:
                logger.warning(f'Delete connection {self._device}: {connection.name}')
                try:
                    self._adapter.connection_down(name=connection.name)
                except Exception as e:
                    logger.error(f'Error deactivating AP {self._device}: {e}')
                try:
                    self._adapter.connection_delete(connection.name)
                except Exception as e:
                    logger.error(f'Error deleting AP {self._device}: {e}')

    def reload(self):
        with self._lock:
            self._update_pending = True
            try:
                if self._connection_type == self.ConnectionType.CONNECTION_TYPE_DISABLED:
                    self._status_message('Disabling...')
                    self._reset_ap()
                    self._update_pending = False
                    self._status_message('Disabled')
                elif self._connection_type == self.ConnectionType.CONNECTION_TYPE_AP:
                    for tries in range(2):
                        try:
                            self._status_message('Resetting...')
                            self._reset_ap()
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

                            self._update_pending = False
                            self._status_message(f'{self.status}')
                        except Exception as e:
                            self._status_message(f'Hotspot: {e}', error=True)
                    else:
                        self._status_message('Unknown network type', error=True)
            except Exception as e:
                self._status_message(f"Wi-Fi AP: {e}", error=True)
