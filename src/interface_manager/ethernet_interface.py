import logging
from enum import Enum
from netaddr import IPAddress
from .network_interface_base import InterfaceTypes, NetworkInterface

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class EthernetInterface(NetworkInterface):
    WAIT_FOR_CONNECTION_UP_S = 5

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

    def __init__(self, device, adapter, def_config):
        super().__init__(device, adapter, def_config)
        self.static_ip_connection = f'static-ip-{self._device}'
        self.dynamic_ip_connection = f'dynamic-ip-{self._device}'
        self.dhcp_server_connection = f'dhcp-server-{self._device}'
        self._load_defaults()

    def _load_defaults(self):
        self._connection_type = self.ConnectionType.from_string(self._def_config.get('Ethernet', 'DefaultEthernetConnectionType'))
        self._ip = self._def_config.get('Ethernet', 'DefaultEthernetIP')
        self._mask = self._def_config.get('Ethernet', 'DefaultEthernetMask')
        self._route = self._def_config.get('Ethernet', 'DefaultEthernetRoute')

    def load_config(self, config):
        with self._lock:
            try:
                cfg = config[self._device]
                parameters = ["connection_type", "ip", "mask", "route"]
                for parameter in parameters:
                    if parameter not in cfg:
                        raise Exception(f"Configuration missing parameters: {parameter}")
                self._connection_type = self.ConnectionType.from_string(cfg["connection_type"])
                self._ip = cfg["ip"]
                self._mask = cfg["mask"]
                self._route = cfg["route"]
                logger.info(f"Update parameters for {self._device}: {self._connection_type} | IP {self._ip} | Mask {self._mask} | Route {self._route}")
                self.reload()
            except Exception as e:
                logger.warning(f"Failed to apply configuration {config} for {self._device}: ({e})")
                raise Exception(f"Failed to apply configuration {config} for {self._device}: ({e})")
            self.reload()

    def get_config(self):
        with self._lock:
            conf = {
                self._device: {
                    "type": self.type.value,
                    "connection_type": self._connection_type.value,
                    "ip": self._ip,
                    "mask": self._mask,
                    "route": self._route
                }
            }
            return conf

    def initialise(self):
        connections = self._adapter.connection()

        static_ip_found = False
        dynamic_ip_found = False
        dhcp_found = False
        enabled = False
        for connection in connections:
            if connection.name == self.static_ip_connection:
                if static_ip_found:
                    logger.warning(f"More than one connection {connection.name} found, remove")
                    self._adapter.connection_down(name=connection.name, wait=self.WAIT_FOR_CONNECTION_UP_S)
                    self._adapter.connection_delete(name=connection.name)
                    continue
                static_ip_found = True
                status = self._adapter.connection_show(name=connection.name)
                logger.info(f"Found connection {connection.name}, status autoconnect {status['connection.autoconnect']}")
                if status['connection.autoconnect'] == 'yes':
                    enabled = True
                    self._connection_type = self.ConnectionType.CONNECTION_TYPE_STATIC_IP
            elif connection.name == self.dynamic_ip_connection:
                if dynamic_ip_found:
                    logger.warning(f"More than one connection {connection.name} found, remove")
                    self._adapter.connection_down(name=connection.name, wait=self.WAIT_FOR_CONNECTION_UP_S)
                    self._adapter.connection_delete(name=connection.name)
                    continue
                dynamic_ip_found = True
                status = self._adapter.connection_show(name=connection.name)
                logger.info(f"Found connection {connection.name}, status autoconnect {status['connection.autoconnect']}")
                if status['connection.autoconnect'] == 'yes':
                    enabled = True
                    self._connection_type = self.ConnectionType.CONNECTION_TYPE_DYNAMIC_IP
            elif connection.name == self.dhcp_server_connection:
                if dhcp_found:
                    logger.warning(f"More than one connection {connection.name} found, remove")
                    self._adapter.connection_down(name=connection.name, wait=self.WAIT_FOR_CONNECTION_UP_S)
                    self._adapter.connection_delete(name=connection.name)
                    continue
                dhcp_found = True
                status = self._adapter.connection_show(name=connection.name)
                logger.info(f"Found connection {connection.name}, status autoconnect {status['connection.autoconnect']}")
                if status['connection.autoconnect'] == 'yes':
                    enabled = True
                    self._connection_type = self.ConnectionType.CONNECTION_TYPE_DHCP_SERVER

        if not enabled:
            self._connection_type = self.ConnectionType.CONNECTION_TYPE_DISABLED

        if not static_ip_found:
            logger.info(f"{self._device} Static IP connection {self.static_ip_connection} not found, create")
            self._adapter.connection_add(conn_type='ethernet', options={'con-name': self.static_ip_connection}, ifname=self._device, autoconnect=False)
        if not dynamic_ip_found:
            logger.info(f"{self._device} Dynamic connection {self.dynamic_ip_connection} not found, create")
            self._adapter.connection_add(conn_type='ethernet', options={'con-name': self.dynamic_ip_connection}, ifname=self._device, autoconnect=False)
        if not dhcp_found:
            logger.info(f"{self._device} DHCP connection {self.dhcp_server_connection} not found, create")
            self._adapter.connection_add(conn_type='ethernet', options={'con-name': self.dhcp_server_connection}, ifname=self._device, autoconnect=False)
            self._ip = self._def_config.get('Ethernet', 'DefaultEthernetIP')
            self._mask = self._def_config.get('Ethernet', 'DefaultEthernetMask')
            self._route = self._def_config.get('Ethernet', 'DefaultEthernetRoute')
            mask_bits = IPAddress(self._mask).netmask_bits()
            self._adapter.connection_modify(name=self.dhcp_server_connection, options={'ipv4.addresses': f'{self._ip}/{mask_bits}'})
            self._adapter.connection_modify(name=self.dhcp_server_connection, options={'ipv4.gateway': self._route})
        self.refresh()

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

                if self._connection_type == self.ConnectionType.CONNECTION_TYPE_DYNAMIC_IP:
                    self._ip = ipv4_addr
                    self._mask = ipv4_mask
                    self._route = ipv4_bcast

            except Exception as e:
                self._status_message(f'Error checking {self._device}: {e}', error=True)

    def reload(self):
        logging.info(f"Reload {self._device}...")
        with self._lock:
            try:
                self._update_pending = True
                mask_bits = IPAddress(self._mask).netmask_bits()
                if self._connection_type == self.ConnectionType.CONNECTION_TYPE_DISABLED:
                    self._status_message('Disabling...')
                    self._adapter.connection_modify(name=self.dynamic_ip_connection, options={'connection.autoconnect': 'no'})
                    self._adapter.connection_down(name=self.dynamic_ip_connection, wait=self.WAIT_FOR_CONNECTION_UP_S, ignore_error=True)
                    self._adapter.connection_modify(name=self.static_ip_connection, options={'connection.autoconnect': 'no'})
                    self._adapter.connection_down(name=self.static_ip_connection, wait=self.WAIT_FOR_CONNECTION_UP_S, ignore_error=True)
                    self._adapter.connection_modify(name=self.dhcp_server_connection, options={'connection.autoconnect': 'no'})
                    self._adapter.connection_down(name=self.dhcp_server_connection, wait=self.WAIT_FOR_CONNECTION_UP_S, ignore_error=True)
                    self._ip_read_only = True
                    self._update_pending = False
                    self._status_message('Disabled')
                elif self._connection_type == self.ConnectionType.CONNECTION_TYPE_STATIC_IP:
                    self._status_message('Setting static IP...')
                    self._adapter.connection_modify(name=self.dynamic_ip_connection, options={'connection.autoconnect': 'no'})
                    self._adapter.connection_down(name=self.dynamic_ip_connection, wait=self.WAIT_FOR_CONNECTION_UP_S, ignore_error=True)
                    self._adapter.connection_modify(name=self.dhcp_server_connection, options={'connection.autoconnect': 'no'})
                    self._adapter.connection_down(name=self.dhcp_server_connection, wait=self.WAIT_FOR_CONNECTION_UP_S, ignore_error=True)
                    self._adapter.connection_modify(name=self.static_ip_connection, options={'ipv4.method': 'manual'})
                    self._adapter.connection_modify(name=self.static_ip_connection, options={'ipv4.addresses': f'{self._ip}/{mask_bits}'})
                    self._adapter.connection_modify(name=self.static_ip_connection, options={'ipv4.gateway': self._route})
                    self._adapter.connection_modify(name=self.static_ip_connection, options={'connection.autoconnect': 'yes'})
                    self._adapter.connection_modify(name=self.static_ip_connection, options={'ipv4.dns': "8.8.8.8 4.4.4.4"})
                    self._adapter.connection_modify(name=self.static_ip_connection, options={'ipv6.method': 'disabled'})
                    self._adapter.connection_up(name=self.static_ip_connection, wait=self.WAIT_FOR_CONNECTION_UP_S)
                    self._ip_read_only = False
                    self._update_pending = False
                    self._status_message('Configured')
                elif self._connection_type == self.ConnectionType.CONNECTION_TYPE_DYNAMIC_IP:
                    self._status_message('Setting dynamic IP...')
                    self._adapter.connection_modify(name=self.static_ip_connection, options={'connection.autoconnect': 'no'})
                    self._adapter.connection_down(name=self.static_ip_connection, wait=self.WAIT_FOR_CONNECTION_UP_S, ignore_error=True)
                    self._adapter.connection_modify(name=self.dhcp_server_connection, options={'connection.autoconnect': 'no'})
                    self._adapter.connection_down(name=self.dhcp_server_connection, wait=self.WAIT_FOR_CONNECTION_UP_S, ignore_error=True)
                    self._adapter.connection_modify(name=self.dynamic_ip_connection, options={'ipv4.method': 'auto'})
                    self._adapter.connection_modify(name=self.dynamic_ip_connection, options={'ipv6.method': 'auto'})
                    self._adapter.connection_modify(name=self.dynamic_ip_connection, options={'connection.autoconnect': 'yes'})
                    self._adapter.connection_up(name=self.dynamic_ip_connection, wait=self.WAIT_FOR_CONNECTION_UP_S)
                    self._ip_read_only = True
                    self._update_pending = False
                    self._status_message('Configured')
                elif self._connection_type == self.ConnectionType.CONNECTION_TYPE_DHCP_SERVER:
                    self._status_message('Setting DHCP server...')
                    self._adapter.connection_modify(name=self.dynamic_ip_connection, options={'connection.autoconnect': 'no'})
                    self._adapter.connection_down(name=self.dynamic_ip_connection, wait=self.WAIT_FOR_CONNECTION_UP_S, ignore_error=True)
                    self._adapter.connection_modify(name=self.static_ip_connection, options={'connection.autoconnect': 'no'})
                    self._adapter.connection_down(name=self.static_ip_connection, wait=self.WAIT_FOR_CONNECTION_UP_S, ignore_error=True)
                    self._adapter.connection_modify(name=self.dhcp_server_connection, options={'ipv6.method': 'disabled'})
                    self._adapter.connection_modify(name=self.dhcp_server_connection, options={'ipv4.method': 'shared'})
                    self._adapter.connection_modify(name=self.dhcp_server_connection, options={'ipv4.addresses': f'{self._ip}/{mask_bits}'})
                    self._adapter.connection_modify(name=self.dhcp_server_connection, options={'ipv4.gateway': self._route})
                    self._adapter.connection_modify(name=self.dhcp_server_connection, options={'connection.autoconnect': 'yes'})
                    self._adapter.connection_up(name=self.dhcp_server_connection, wait=self.WAIT_FOR_CONNECTION_UP_S)
                    self._ip_read_only = False
                    self._update_pending = False
                    self._status_message('Configured')
                else:
                    self._update_pending = False
                    self._status_message('Unknown network type', error=True)
            except Exception as e:
                self._status_message(f"LAN: {e}", error=True)
