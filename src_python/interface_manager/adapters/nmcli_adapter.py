import logging
import re
import subprocess
import nmcli
from ifconfigparser import IfconfigParser
from .host_adapter import HostController

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class NMCliAdapter:
    def __init__(self, use_sudo: bool = False,
                 dry_run: bool = False,
                 remote_host: bool = False,
                 remote_host_port: int = 22,
                 remote_host_ssh_key: str = "",
                 remote_host_hostname: str = "localhost"):
        self._use_sudo = use_sudo
        if not self._use_sudo:
            nmcli.disable_use_sudo()

        self._dry_run = dry_run
        self._remote_host = remote_host
        if self._remote_host:
            # HostController also redirects nmcli during initialisation
            self._host = HostController(remote_host_port, remote_host_ssh_key, remote_host_hostname)
        else:
            self._host = None

    def run_command(self, command):
        prefix = ''
        if self._use_sudo:
            prefix = 'sudo '
        logger.info(f"Run command {prefix}{command}")
        if self._remote_host:
            self._host.run_host_command(f'{prefix}{command}')
        else:
            return subprocess.getoutput(f'{prefix}{command}')

    @staticmethod
    def device():
        """
        Get a list of network devices

        :return:
        A list of 'device' items that should have properties: 'device_type', 'device';
        device_type can be 'wifi' or 'ethernet'
        device is the network adapter name (eg. wlan0, eth0, etc.)
        """
        device = nmcli.device()
        logger.info(f"nmcli.device: {device}")
        return device

    @staticmethod
    def connection():
        """
        Get a list of connections

        :return:
        A list of 'connection' items that should have properties: 'name';
        """
        connection = nmcli.connection()
        logger.info(f"nmcli.connection: {connection}")
        return connection

    def connection_add(self, conn_type, options, ifname, autoconnect, ssid=None):
        logger.info(f"nmcli.connection.add conn_type={conn_type}, options={options}, ifname={ifname}, autoconnect={autoconnect}, ssid={ssid}")
        if self._dry_run:
            return
        if ssid is None:
            return nmcli.connection.add(conn_type=conn_type, options=options, ifname=ifname, autoconnect=autoconnect)
        else:
            return nmcli.connection.add(conn_type=conn_type, options=options | {"ssid": ssid}, ifname=ifname, autoconnect=autoconnect)

    @staticmethod
    def device_wifi(ifname):
        """

        :param ifname:
        :return:
        result.ssid
        """
        return nmcli.device.wifi(ifname=ifname)

    @staticmethod
    def device_status():
        return nmcli.device.status()

    def connection_modify(self, name, options):
        logger.info(f"nmcli.connection.modify name={name}, options={options}")
        if self._dry_run:
            return
        return nmcli.connection.modify(name=name, options=options)

    def connection_down(self, name, wait, ignore_error=False):
        logger.info(f"nmcli.connection.down name={name} wait={wait}")
        if self._dry_run:
            return
        try:
            return nmcli.connection.down(name=name, wait=wait)
        except Exception as e:
            if ignore_error:
                logger.warning(f"Ignored error: {e}")
                return None
            else:
                raise e

    def connection_up(self, name, wait):
        logger.info(f"nmcli.connection.up name={name} wait={wait}")
        if self._dry_run:
            return
        return nmcli.connection.up(name=name, wait=wait)

    def connection_show(self, name):
        logger.info(f"nmcli.connection.show name={name}")
        if self._dry_run:
            return
        return nmcli.connection.show(name=name)

    # def radio_wifi_off(self):
    #     logger.info(f"nmcli.radio.wifi_off")
    #     if self._dry_run:
    #         return
    #     return nmcli.radio.wifi_off()
    #
    # def radio_wifi_on(self):
    #     logger.info(f"nmcli.radio.wifi_on")
    #     if self._dry_run:
    #         return
    #     return nmcli.radio.wifi_on()

    def device_wifi_connect(self, ssid, password):
        logger.info(f"nmcli.device.wifi_connect ssid={ssid}, password={password}")
        if self._dry_run:
            return
        return nmcli.device.wifi_connect(ssid=ssid, password=password)

    def connection_delete(self, name):
        logger.info(f"nmcli.connection.delete name={name}")
        if self._dry_run:
            return
        return nmcli.connection.delete(name=name)

    def device_wifi_hotspot(self, con_name, ifname, ssid, password):
        logger.info(f"nmcli.device.wifi_hotspot con_name={con_name}, ifname={ifname}, ssid={ssid}, password={password}")
        if self._dry_run:
            return
        nmcli.device.wifi_hotspot(con_name=con_name, ifname=ifname, ssid=ssid, password=password)

    def stop_dnsmasq(self):
        if self._dry_run:
            return
        self.run_command("killall dnsmasq")

    def stop_hostapd(self):
        if self._dry_run:
            return
        self.run_command("killall hostapd")

    def iw_add_interface(self, phy_name, device, device_type):
        if self._dry_run:
            return
        self.run_command(f'iw phy {phy_name} interface add {device} type {device_type}')

    def ip_link_set_dev_address(self, device, mac):
        if self._dry_run:
            return
        self.run_command(f'ip link set dev {device} address {mac}')

    def ip_link_set_up(self, device):
        if self._dry_run:
            return
        self.run_command(f'ip link set {device} up')

    def ip_link_set_down(self, device):
        if self._dry_run:
            return
        self.run_command(f'ip link set {device} down')

    def enable_ip_forward(self, enable_ip_forward):
        if self._dry_run:
            return
        self.run_command(f'sysctl -w net.ipv4.ip_forward= {enable_ip_forward}')

    def ifconfig(self, device):
        ifconfig_output = self.run_command(f'ifconfig {device}')
        interfaces = IfconfigParser(console_output=ifconfig_output)
        iface = interfaces.get_interface(name=device)
        return iface

    def iw_dev_link(self, device):
        iw_output = self.run_command(f'iw dev {device} link')
        match = re.search(r"SSID:\s*(.+)", iw_output)
        if match:
            ssid = match.group(1)
        else:
            ssid = ""
        return ssid
