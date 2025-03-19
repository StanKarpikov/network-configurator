import logging
import queue
import subprocess
import threading
import time
from enum import Enum
from netaddr import IPAddress
from ifconfigparser import IfconfigParser

from src.nmcli_adapter import NMCliAdapter

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class InterfaceTypes(Enum):
    INTERFACE_TYPE_UNDEFINED = 0
    INTERFACE_TYPE_WIFI = 1
    INTERFACE_TYPE_WIFI_AP = 2
    INTERFACE_TYPE_ETHERNET = 3


class NetworkInterface:
    TYPE = InterfaceTypes.INTERFACE_TYPE_UNDEFINED

    def __init__(self, device, adapter: NMCliAdapter, config):
        self._connection_type = ""
        self._ip_read_only = False
        self._lock = threading.RLock()
        self._config = config
        self._status = None
        self._adapter = adapter
        self._device = device
        self._ip = ""
        self._mask = ""
        self._route = ""

    def _status_message(self, message, error=False):
        logger.info(f"Status Message {self._device}: {message}")

    def refresh(self):
        raise NotImplementedError("Refresh on the base class not implemented")

    def initialise(self):
        raise NotImplementedError("Initialise on the base class not implemented")

    def _reload(self):
        raise NotImplementedError("Reload on the base class not implemented")

    @property
    def parameters(self):
        return [name for name, obj in vars(self).items() if isinstance(obj, property)]

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
            self._ip = value
            self._reload()

    @property
    def connection_type(self):
        with self._lock:
            return self._connection_type

    @connection_type.setter
    def connection_type(self, value):
        with self._lock:
            self._connection_type = value
            self._reload()

    @property
    def mask(self):
        with self._lock:
            return self._mask

    @mask.setter
    def mask(self, value):
        with self._lock:
            self._mask = value
            self._reload()

    @property
    def route(self):
        with self._lock:
            return self._route

    @route.setter
    def route(self, value):
        with self._lock:
            self._route = value
            self._reload()

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
                self._reload()
            else:
                raise KeyError(f"'{key}' not found or not writable")


class EthernetInterface(NetworkInterface):
    class ConnectionType(str, Enum):
        CONNECTION_TYPE_DISABLED = "disabled"
        CONNECTION_TYPE_STATIC_IP = "static_ip"
        CONNECTION_TYPE_DYNAMIC_IP = "dynamic_ip"
        CONNECTION_TYPE_DHCP_SERVER = "dhcp_server"

        @classmethod
        def from_string(cls, value: str):
            try:
                return cls(value)
            except ValueError:
                available_types = ", ".join([e.value for e in cls])
                raise ValueError(f"Invalid connection type: {value}, available types are: {available_types}")

    TYPE = InterfaceTypes.INTERFACE_TYPE_ETHERNET

    def __init__(self, device, adapter, config):
        super().__init__(device, adapter, config)
        self.static_ip_connection = f'static-ip-{self._device}'
        self.dynamic_ip_connection = f'dynamic-ip-{self._device}'
        self.dhcp_server_connection = f'dhcp-server-{self._device}'
        self._connection_type = self.ConnectionType.CONNECTION_TYPE_STATIC_IP

    def initialise(self):
        connections = self._adapter.connection()

        static_ip_found = False
        dynamic_ip_found = False
        dhcp_found = False
        for connection in connections:
            if connection.name == self.static_ip_connection:
                static_ip_found = True
            elif connection.name == self.dynamic_ip_connection:
                dynamic_ip_found = True
            elif connection.name == self.dhcp_server_connection:
                dhcp_found = True

        if not static_ip_found:
            self._adapter.connection_add(conn_type='ethernet', options={'con-name': self.static_ip_connection}, ifname=self._device, autoconnect=False)
        if not dynamic_ip_found:
            self._adapter.connection_add(conn_type='ethernet', options={'con-name': self.dynamic_ip_connection}, ifname=self._device, autoconnect=False)
        if not dhcp_found:
            self._adapter.connection_add(conn_type='ethernet', options={'con-name': self.dhcp_server_connection}, ifname=self._device, autoconnect=False)

    def refresh(self):
        with self._lock:
            try:
                self._status_message(self.status)

                ifconfig_output = subprocess.getoutput(f'ifconfig {self._device}')
                logger.debug(f"ifconfig {self._device}: \n" + ifconfig_output)
                interfaces = IfconfigParser(console_output=ifconfig_output)
                iface = interfaces.get_interface(name=self._device)

                ipv4_addr = iface.ipv4_addr
                if iface.ipv4_addr is None:
                    ipv4_addr = '0.0.0.0'

                ipv4_mask = iface.ipv4_mask
                if iface.ipv4_mask is None:
                    ipv4_mask = '0.0.0.0'

                ipv4_bcast = iface.ipv4_bcast
                if iface.ipv4_bcast is None:
                    ipv4_bcast = '0.0.0.0'

                if self._connection_type == self.ConnectionType.CONNECTION_TYPE_DYNAMIC_IP:
                    self._ip = ipv4_addr
                    self._mask = ipv4_mask
                    self._route = ipv4_bcast

            except Exception as e:
                self._status_message(f'Error checking {self._device}: {e}', error=True)

    def _reload(self):
        try:
            mask_bits = IPAddress(self._mask).netmask_bits()
            if self._connection_type == self.ConnectionType.CONNECTION_TYPE_DISABLED:
                self._status_message('Disabling...')
                self._adapter.connection_modify(name=self.dynamic_ip_connection, options={'connection.autoconnect': 'no'})
                self._adapter.connection_down(name=self.dynamic_ip_connection)
                self._adapter.connection_modify(name=self.static_ip_connection, options={'connection.autoconnect': 'no'})
                self._adapter.connection_down(name=self.static_ip_connection)
                self._adapter.connection_modify(name=self.dhcp_server_connection, options={'connection.autoconnect': 'no'})
                self._adapter.connection_down(name=self.dhcp_server_connection)
                self._ip_read_only = True
                self._status_message('Disabled')
            elif self._connection_type == self.ConnectionType.CONNECTION_TYPE_STATIC_IP:
                self._status_message('Setting static IP...')
                self._adapter.connection_modify(name=self.dynamic_ip_connection, options={'connection.autoconnect': 'no'})
                self._adapter.connection_down(name=self.dynamic_ip_connection)
                self._adapter.connection_modify(name=self.dhcp_server_connection, options={'connection.autoconnect': 'no'})
                self._adapter.connection_down(name=self.dhcp_server_connection)
                self._adapter.connection_modify(name=self.static_ip_connection, options={'ipv4.method': 'manual'})
                self._adapter.connection_modify(name=self.static_ip_connection, options={'ipv4.addresses': f'{self._ip}/{mask_bits}'})
                self._adapter.connection_modify(name=self.static_ip_connection, options={'ipv4.gateway': self._route})
                self._adapter.connection_modify(name=self.static_ip_connection, options={'connection.autoconnect': 'yes'})
                self._adapter.connection_modify(name=self.static_ip_connection, options={'ipv4.dns': "8.8.8.8 4.4.4.4"})
                self._adapter.connection_modify(name=self.static_ip_connection, options={'ipv6.method': 'disabled'})
                self._adapter.connection_up(name=self.static_ip_connection)
                self._ip_read_only = False
                self._status_message('Configured')
            elif self._connection_type == self.ConnectionType.CONNECTION_TYPE_DYNAMIC_IP:
                self._status_message('Setting dynamic IP...')
                self._adapter.connection_modify(name=self.static_ip_connection, options={'connection.autoconnect': 'no'})
                self._adapter.connection_down(name=self.static_ip_connection)
                self._adapter.connection_modify(name=self.dhcp_server_connection, options={'connection.autoconnect': 'no'})
                self._adapter.connection_down(name=self.dhcp_server_connection)
                self._adapter.connection_modify(name=self.dynamic_ip_connection, options={'ipv4.method': 'auto'})
                self._adapter.connection_modify(name=self.dynamic_ip_connection, options={'ipv6.method': 'auto'})
                self._adapter.connection_modify(name=self.dynamic_ip_connection, options={'connection.autoconnect': 'yes'})
                self._adapter.connection_up(name=self.dynamic_ip_connection)
                self._ip_read_only = True
                self._status_message('Configured')
            elif self._connection_type == self.ConnectionType.CONNECTION_TYPE_DHCP_SERVER:
                self._status_message('Setting DHCP server...')
                self._adapter.connection_modify(name=self.dynamic_ip_connection, options={'connection.autoconnect': 'no'})
                self._adapter.connection_down(name=self.dynamic_ip_connection)
                self._adapter.connection_modify(name=self.static_ip_connection, options={'connection.autoconnect': 'no'})
                self._adapter.connection_down(name=self.static_ip_connection)
                self._adapter.connection_modify(name=self.dhcp_server_connection, options={'ipv6.method': 'disabled'})
                self._adapter.connection_modify(name=self.dhcp_server_connection, options={'ipv4.method': 'shared'})
                self._adapter.connection_modify(name=self.dhcp_server_connection, options={'ipv4.addresses': f'{self._ip}/{mask_bits}'})
                self._adapter.connection_modify(name=self.dhcp_server_connection, options={'connection.autoconnect': 'yes'})
                self._adapter.connection_up(name=self.dhcp_server_connection)
                self._ip_read_only = False
                self._status_message('Configured')
            else:
                self._status_message('Unknown network type', error=True)
        except Exception as e:
            self._status_message(f"LAN: {e}", error=True)


class WiFiInterface(NetworkInterface):
    class ConnectionType(str, Enum):
        CONNECTION_TYPE_DISABLED = "disabled"
        CONNECTION_TYPE_STATION = "station"

        @classmethod
        def from_string(cls, value: str):
            try:
                return cls(value)
            except ValueError:
                available_types = ", ".join([e.value for e in cls])
                raise ValueError(f"Invalid connection type: {value}, available types are: {available_types}")

    TYPE = InterfaceTypes.INTERFACE_TYPE_WIFI

    def __init__(self, device, adapter: NMCliAdapter, config):
        super().__init__(device, adapter, config)
        self._connection_type = self.ConnectionType.CONNECTION_TYPE_DISABLED
        self._ssid = ""
        self._passphrase = ""
        self._ip_read_only = True

    @property
    def connection_type(self):
        with self._lock:
            return self._connection_type.value

    @connection_type.setter
    def connection_type(self, value):
        with self._lock:
            self._connection_type = self.ConnectionType.from_string(value)

    @property
    def ssid(self):
        with self._lock:
            return self._ssid

    @ssid.setter
    def ssid(self, value):
        with self._lock:
            self._ssid = value

    @property
    def passphrase(self):
        with self._lock:
            return self._passphrase

    @passphrase.setter
    def passphrase(self, value):
        with self._lock:
            self._passphrase = value

    @property
    def scan(self):
        with self._lock:
            return self._scan

    def _scan(self):
        wifi_list = []
        logger.info(f'Start scan on {self._device}')
        results = self._adapter.device_wifi(ifname=self._device)
        for result in results:
            if result.ssid:
                wifi_list.append(result.ssid)
        logger.info(f'Scan results {self._device}: {wifi_list}')
        return wifi_list

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

    def _reload(self):
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
            else:
                self._status_message('Unknown network type', error=True)
        except Exception as e:
            self._status_message(f"Wi-Fi: {e}", error=True)

    def refresh(self):
        with self._lock:
            try:
                self._status_message(self.status)

                ifconfig_output = subprocess.getoutput(f'ifconfig {self._device}')
                logger.debug(f"ifconfig {self._device}: \n" + ifconfig_output)
                interfaces = IfconfigParser(console_output=ifconfig_output)
                iface = interfaces.get_interface(name=self._device)

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


class APInterface(NetworkInterface):
    DEFAULT_AP_INTERFACE_DEVICE = 'uap0'
    DEFAULT_SSID = "ConfigurationAP"
    DEFAULT_PASSPHRASE = ""
    DEFAULT_AP_INTERFACE_MAC = "00:11:22:33:44:55"
    DEFAULT_IP_FORWARD_ENABLE = 1

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

    def __init__(self, device, adapter: NMCliAdapter, config):
        if not device:
            device = config.getint('AP', 'APInterfaceDevice', fallback=self.DEFAULT_AP_INTERFACE_DEVICE)
        super().__init__(device, adapter, config)
        self._connection_type = self.ConnectionType.CONNECTION_TYPE_AP
        self._ssid = self._config.get('AP', 'DefaultAPSSID', fallback=self.DEFAULT_SSID)
        self._passphrase = self._config.get('AP', 'DefaultPassphrase', fallback=self.DEFAULT_PASSPHRASE)
        self._mac = config.get('AP', 'APMAC', fallback=self.DEFAULT_AP_INTERFACE_MAC)
        self._enable_ip_forward = config.getint('AP', 'IPForwardEnable', fallback=self.DEFAULT_IP_FORWARD_ENABLE)
        self._ip_read_only = False

    def refresh(self):
        with self._lock:
            try:
                self._status_message(self.status)

                ifconfig_output = subprocess.getoutput(f'ifconfig {self._device}')
                logger.debug(f"ifconfig {self._device}: \n" + ifconfig_output)
                interfaces = IfconfigParser(console_output=ifconfig_output)
                iface = interfaces.get_interface(name=self._device)

                ipv4_addr = iface.ipv4_addr
                if iface.ipv4_addr is None:
                    ipv4_addr = '0.0.0.0'

                ipv4_mask = iface.ipv4_mask
                if iface.ipv4_mask is None:
                    ipv4_mask = '0.0.0.0'

                ipv4_bcast = iface.ipv4_bcast
                if iface.ipv4_bcast is None:
                    ipv4_bcast = '0.0.0.0'

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
            self._connection_type = self.ConnectionType.from_string(value)

    @property
    def ssid(self):
        with self._lock:
            return self._ssid

    @ssid.setter
    def ssid(self, value):
        with self._lock:
            self._ssid = value

    @property
    def passphrase(self):
        with self._lock:
            return self._passphrase

    @passphrase.setter
    def passphrase(self, value):
        with self._lock:
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

    def _reload(self):
        try:
            if self._connection_type == self.ConnectionType.CONNECTION_TYPE_DISABLED:
                self._status_message('Disabling...')
                self._reset_ap()
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
        except Exception as e:
            self._status_message(f"Wi-Fi AP: {e}", error=True)

class InterfaceManager:
    UPDATE_PERIOD_S = 2
    DEFAULT_ENABLE_AP_AFTER_PERIOD_S = 30

    def __init__(self, config):
        self.previous_connected_state = True
        self.config = config
        self.adapter = NMCliAdapter()
        self.interfaces = []
        self.detect_interfaces()
        self.initialise()
        periodic_update_thread = threading.Thread(target=self.periodic_update)
        periodic_update_thread.daemon = True
        periodic_update_thread.start()

    def detect_interfaces(self):
        devices = self.adapter.device()
        ap_found = False
        for device in devices:
            if device.device_type == 'wifi':
                interface = WiFiInterface(device.device, self.adapter, config=self.config)
                self.interfaces.append(interface)
            elif device.device_type == 'ethernet':
                interface = EthernetInterface(device.device, self.adapter, config=self.config)
                self.interfaces.append(interface)
            elif device.device_type == '__ap':
                ap_found = True
                interface = APInterface(device.device, self.adapter, config=self.config)
                self.interfaces.append(interface)
            else:
                logger.info(f"Skip device {device.device} of unknown type {device.device_type}")
        if not ap_found:
            logger.info("AP interface not found, first run? Creating the interface...")
            interface = APInterface("", self.adapter, config=self.config)
            self.interfaces.append(interface)

    def refresh_interfaces(self):
        connected = False
        for interface in self.interfaces:
            self.interfaces[interface].refresh()
            if self.interfaces[interface].self.interfaces[interface].is_connected:
                if self.interfaces[interface].type == InterfaceTypes.INTERFACE_TYPE_WIFI:
                    connected = True
                elif self.interfaces[interface].type == InterfaceTypes.INTERFACE_TYPE_ETHERNET:
                    connected = True
        if connected != self.previous_connected_state:
            if connected:
                if time.time() - self.last_connected_time
            else:
                self.last_disconnected_time = time.time()
        self.previous_connected_state = connected
        if time.time() - self.last_disconnected_time > self.ENABLE_AP_AFTER_PERIOD_S:
            pass

    def initialise(self):
        for interface in self.interfaces:
            self.interfaces[interface].initialise()

    def periodic_update(self):
        while True:
            self.refresh_interfaces()
            time.sleep(self.UPDATE_PERIOD_S)
