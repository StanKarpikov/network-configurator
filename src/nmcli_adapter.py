import nmcli

class NMCliAdapter:
    def __init__(self):
        pass

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

    @staticmethod
    def connection_add(conn_type, options, ifname, autoconnect):
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

    @staticmethod
    def connection_modify(name, options):
        return nmcli.connection.modify(name=name, options=options)

    @staticmethod
    def connection_down(name):
        return nmcli.connection.down(name=name)

    @staticmethod
    def connection_up(name):
        return nmcli.connection.up(name=name)

    @staticmethod
    def radio_wifi_off():
        return nmcli.radio.wifi_off()

    @staticmethod
    def radio_wifi_on():
        return nmcli.radio.wifi_on()

    @staticmethod
    def device_wifi_connect(ssid, password):
        return nmcli.device.wifi_connect(ssid=ssid, password=password)

    @staticmethod
    def connection_delete(name):
        return nmcli.connection.delete()

    @staticmethod
    def device_wifi_hotspot(con_name, ifname, ssid, password):
        nmcli.device.wifi_hotspot(con_name=con_name, ifname=ifname, ssid=ssid, password=password)

    @staticmethod
    def stop_dnsmasq():
        # self.host.run_host_command("killall dnsmasq")
        pass

    @staticmethod
    def stop_hostapd():
        # self.host.run_host_command("killall hostapd")
        pass

    @staticmethod
    def iw_add_interface(phy_name, device, device_type):
        f'iw phy {phy_name} interface add {device} type {device_type}'

    @staticmethod
    def ip_link_set_dev_address(device, mac):
        f'ip link set dev {device} address {mac}'

    @staticmethod
    def ip_link_set_up(device):
        f'ip link set {device} up'

    @staticmethod
    def enable_ip_forward(enable_ip_forward):
        f'echo {enable_ip_forward} > /proc/sys/net/ipv4/ip_forward'

