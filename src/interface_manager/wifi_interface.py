import logging
import time
from enum import Enum

from .adapters.nmcli_adapter import NMCliAdapter
from .network_interface_base import NetworkInterface, InterfaceTypes

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class WiFiInterface(NetworkInterface):
    WAIT_FOR_CONNECTION_UP_S = 5

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
        self._hotspot_connection = f'hotspot-{self._device}'
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
                print(config)
                cfg = config[self._device]
                parameters = ["connection_type", "ip", "mask", "route", "ssid", "passphrase"]
                for parameter in parameters:
                    if parameter not in cfg:
                        raise Exception(f"Configuration missing parameters: {parameter}")
                self._connection_type = self.ConnectionType.from_string(cfg["connection_type"])
                self._ip = cfg["ip"]
                self._mask = cfg["mask"]
                self._route = cfg["route"]
                self._ssid = cfg["ssid"]
                self._passphrase = cfg["passphrase"]
                logger.info(f"Read parameters for {self._device}: {self._connection_type} | IP {self._ip} | Mask {self._mask} | Route {self._route} | SSID {self._ssid}")
                self.reload()
            except Exception as e:
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

    def initialise(self):
        connections = self._adapter.connection()
        hotspot_found = False
        enabled = False
        for connection in connections:
            if connection.name == self._hotspot_connection:
                if hotspot_found:
                    logger.warning(f"More than one connection {connection.name} found, remove")
                    self._adapter.connection_down(name=connection.name, wait=self.WAIT_FOR_CONNECTION_UP_S, ignore_error=True)
                    self._adapter.connection_delete(name=connection.name)
                    continue
                hotspot_found = True
                status = self._adapter.connection_show(name=connection.name)
                logger.info(f"Found connection {connection.name}, status autoconnect {status['connection.autoconnect']}")
                if status['connection.autoconnect'] == 'yes':
                    enabled = True
                    self._connection_type = self.ConnectionType.CONNECTION_TYPE_AP
            elif connection.device == self._device:
                status = self._adapter.connection_show(name=connection.name)
                logger.info(f"Found connection {connection.name}, status autoconnect {status['connection.autoconnect']}")
                if status['connection.autoconnect'] == 'yes':
                    enabled = True
                    self._connection_type = self.ConnectionType.CONNECTION_TYPE_STATION

        if not enabled:
            if hotspot_found:
                self._connection_type = self.ConnectionType.CONNECTION_TYPE_DISABLED
            else:
                self._connection_type = self.ConnectionType.CONNECTION_TYPE_AP

        if not hotspot_found:
            logger.info(f"{self._device} Hotspot connection {self._hotspot_connection} not found, create")
            self._adapter.connection_add(conn_type='wifi', options={'con-name': self._hotspot_connection}, ifname=self._device, autoconnect=False, ssid=self._ssid)
            self.reload()

        self.refresh()

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
        return
        # # self._adapter.stop_dnsmasq()
        # # self._adapter.stop_hostapd()
        # connections = self._adapter.connection()
        # for connection in connections:
        #     if connection.device == self._device:
        #         if leave_active_name and leave_active_name == connection.name:
        #             logger.info(f'Skip deleting connection {self._device} {connection.name}')
        #         else:
        #             logger.warning(f'Delete connection {self._device} {connection.name}')
        #             self._adapter.connection_down(name=connection.name, wait=self.WAIT_FOR_CONNECTION_UP_S, ignore_error=True)
        #             try:
        #                 self._adapter.connection_delete(connection.name)
        #             except Exception as e:
        #                 logger.error(f'Error deleting Wi-Fi {self._device}: {e}')
        # self._scan()

    def reload(self):
        with self._lock:
            logging.info(f"Reload {self._device}...")
            try:
                self._update_pending = True
                if self._connection_type == self.ConnectionType.CONNECTION_TYPE_DISABLED:
                    self._status_message('Disabling...')
                    self._adapter.connection_modify(name=self._hotspot_connection, options={'connection.autoconnect': 'no'})
                    self._adapter.connection_down(name=self._hotspot_connection, wait=self.WAIT_FOR_CONNECTION_UP_S, ignore_error=True)
                    self._reset_wifi()
                    time.sleep(2)
                    self._adapter.ip_link_set_down(self._device)
                    self._update_pending = False
                    self._status_message('Disabled')
                elif self._connection_type == self.ConnectionType.CONNECTION_TYPE_STATION:
                    if self._ssid and self._passphrase:
                        self._adapter.connection_modify(name=self._hotspot_connection, options={'connection.autoconnect': 'no'})
                        self._adapter.connection_down(name=self._hotspot_connection, wait=self.WAIT_FOR_CONNECTION_UP_S, ignore_error=True)
                        self._status_message('Power on...')
                        self._scan()
                        self._adapter.ip_link_set_up(self._device)
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
                                self._update_pending = False
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
                            self._adapter.connection_modify(name=self._hotspot_connection, options={'connection.interface-name': self._device})
                            self._adapter.connection_modify(name=self._hotspot_connection, options={'connection.autoconnect': 'yes'})
                            self._adapter.connection_modify(name=self._hotspot_connection, options={'802-11-wireless.mode': 'ap'})
                            self._adapter.connection_modify(name=self._hotspot_connection, options={'802-11-wireless.ssid': self._ssid})
                            self._adapter.connection_modify(name=self._hotspot_connection, options={'802-11-wireless-security.key-mgmt': 'wpa-psk'})
                            self._adapter.connection_modify(name=self._hotspot_connection, options={'802-11-wireless-security.psk': self._passphrase})
                            self._adapter.connection_modify(name=self._hotspot_connection, options={'802-11-wireless-security.pmf': 'disable'})
                            self._adapter.connection_modify(name=self._hotspot_connection, options={'ipv4.method': 'shared'})
                            self._adapter.connection_up(name=self._hotspot_connection, wait=self.WAIT_FOR_CONNECTION_UP_S)

                            # Alternative:
                            # nmcli con add type wifi ifname wlan0 con-name Hostspot autoconnect yes ssid Hostspot
                            # nmcli con modify Hostspot 802-11-wireless.mode ap 802-11-wireless.band bg ipv4.method shared
                            # nmcli con modify Hostspot wifi-sec.key-mgmt wpa-psk
                            # nmcli con modify Hostspot wifi-sec.psk "veryveryhardpassword1234"
                            # nmcli con up Hostspot

                            self._update_pending = False
                            self._status_message(f'{self.status}')
                            return
                        except Exception as e:
                            self._status_message(f'Hotspot: {e}', error=True)
                else:
                    self._update_pending = False
                    self._status_message('Unknown network type', error=True)
            except Exception as e:
                self._status_message(f"Wi-Fi: {e}", error=True)

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

                if self._connection_type == self.ConnectionType.CONNECTION_TYPE_STATION:
                    self._ssid = self._adapter.iw_dev_link(self._device)

                self._ip = ipv4_addr
                self._mask = ipv4_mask
                self._route = ipv4_bcast

            except Exception as e:
                self._status_message(f'Error checking {self._device}: {e}', error=True)

