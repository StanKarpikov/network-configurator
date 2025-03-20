import subprocess
import nmcli
from ifconfigparser import IfconfigParser
from .host_adapter import HostController


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
        if self._remote_host:
            self._host.run_host_command("killall dnsmasq")
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
        return nmcli.device()

    @staticmethod
    def connection():
        """
        Get a list of connections

        :return:
        A list of 'connection' items that should have properties: 'name';
        """
        return nmcli.connection()

    def connection_add(self, conn_type, options, ifname, autoconnect):
        if self._dry_run:
            return
        return nmcli.connection.add(conn_type, options, ifname, autoconnect)

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
        if self._dry_run:
            return
        return nmcli.connection.modify(name=name, options=options)

    def connection_down(self, name):
        if self._dry_run:
            return
        return nmcli.connection.down(name=name)

    def connection_up(self, name):
        if self._dry_run:
            return
        return nmcli.connection.up(name=name)

    def radio_wifi_off(self):
        if self._dry_run:
            return
        return nmcli.radio.wifi_off()

    def radio_wifi_on(self):
        if self._dry_run:
            return
        return nmcli.radio.wifi_on()

    def device_wifi_connect(self, ssid, password):
        if self._dry_run:
            return
        return nmcli.device.wifi_connect(ssid=ssid, password=password)

    def connection_delete(self, name):
        if self._dry_run:
            return
        return nmcli.connection.delete()

    def device_wifi_hotspot(self, con_name, ifname, ssid, password):
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

    def enable_ip_forward(self, enable_ip_forward):
        if self._dry_run:
            return
        self.run_command(f'sysctl -w net.ipv4.ip_forward= {enable_ip_forward}')

    def ifconfig(self, device):
        ifconfig_output = self.run_command(f'ifconfig {device}')
        interfaces = IfconfigParser(console_output=ifconfig_output)
        iface = interfaces.get_interface(name=device)
        return iface
