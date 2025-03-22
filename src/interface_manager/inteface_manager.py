import json
import logging
import os
import threading
import time
import tempfile
from pathlib import Path

from .adapters.nmcli_adapter import NMCliAdapter

from .ap_interface import APInterface
from .ethernet_interface import EthernetInterface
from .network_interface_base import InterfaceTypes
from .wifi_interface import WiFiInterface

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class InterfaceManager:

    def __init__(self, def_config):
        self._conf = {}
        self.last_disconnected_time = time.time()
        self._enable_ap_after_period_s = def_config.getint('Interfaces', 'EnableAPAfterBeingDisconnectedForSeconds')
        self._ap_always_on = def_config.getboolean('Interfaces', 'AccessPointAlwaysOn')
        self._update_period_s = def_config.getfloat('Interfaces', 'UpdatePeriodSec')
        self._use_sudo = def_config.getboolean('Interfaces', 'UseSudo')
        self._use_whitelist = def_config.getboolean('Interfaces', 'InterfaceUseWhitelist')
        self._whitelist = def_config.get('Interfaces', 'InterfaceWhitelist')
        self._use_dedicated_ap = def_config.getboolean('AP', 'UseDedicatedAP')
        self._dry_run = def_config.getboolean('Global', 'DryRun')
        self._remote_host = def_config.getboolean('RemoteHost', 'EnableRemoteHost')
        self._remote_host_port = def_config.getint('RemoteHost', 'HostSSHPort')
        self._remote_host_ssh_key = def_config.get('RemoteHost', 'HostSSHKeyFile')
        self._remote_host_hostname = def_config.get('RemoteHost', 'HostHostname')
        self.ap_interface_idx = 0
        self.previous_connected_state = True
        self.def_config = def_config
        self.adapter = NMCliAdapter(use_sudo=self._use_sudo, dry_run=self._dry_run,
                                    remote_host=self._remote_host,
                                    remote_host_port=self._remote_host_port,
                                    remote_host_ssh_key=self._remote_host_ssh_key,
                                    remote_host_hostname=self._remote_host_hostname)
        self.interfaces = []
        self.detect_interfaces()
        self.initialise()
        periodic_update_thread = threading.Thread(target=self.periodic_update)
        periodic_update_thread.daemon = True
        periodic_update_thread.start()

    def detect_interfaces(self):
        logger.info("Detecting interfaces...")
        devices = self.adapter.device()
        ap_found = False
        for device in devices:
            logger.info(f"Found {device.device} type {device.device_type}")
            if not self._use_whitelist or (device.device in self._whitelist):
                if device.device_type == 'wifi':
                    interface = WiFiInterface(device.device, self.adapter, def_config=self.def_config)
                    self.interfaces.append(interface)
                elif device.device_type == 'ethernet':
                    interface = EthernetInterface(device.device, self.adapter, def_config=self.def_config)
                    self.interfaces.append(interface)
                elif device.device_type == '__ap' and self._use_dedicated_ap:
                    if not ap_found:
                        ap_found = True
                        interface = APInterface(device.device, self.adapter, def_config=self.def_config)
                        self.ap_interface_idx = len(self.interfaces)
                        self.interfaces.append(interface)
                    else:
                        logger.warning(f"More than one AP device found: {device.device}, skip")
                else:
                    logger.info(f"Skip device {device.device} of unknown type {device.device_type}")
            else:
                logger.info(f"Skip device {device.device}")
        if self._use_dedicated_ap:
            # If a dedicated AP is used, ensure that the interface is created
            if not ap_found:
                logger.info("AP interface not found, first run? Creating the interface...")
                interface = APInterface("", self.adapter, def_config=self.def_config)
                self.ap_interface_idx = len(self.interfaces)
                self.interfaces.append(interface)
            else:
                logger.info(f"Dedicated AP interface found, {self.interfaces[self.ap_interface_idx].device} will be used as AP")
        else:
            # If a dedicated AP is not used, select the first WiFi interface to use as an AP
            for idx, interface in enumerate(self.interfaces):
                if interface.type == InterfaceTypes.INTERFACE_TYPE_WIFI:
                    self.ap_interface_idx = idx
                    logger.info(f"Dedicated AP not used, {interface.device} will be used as AP")
                    break

    def refresh_interfaces(self):
        connected = False
        for interface in self.interfaces:
            interface.refresh()
            if interface.status == 'connected':
                if interface.type == InterfaceTypes.INTERFACE_TYPE_WIFI:
                    connected = True
                elif interface.type == InterfaceTypes.INTERFACE_TYPE_ETHERNET:
                    connected = True
        if connected != self.previous_connected_state:
            if connected:
                if not self._ap_always_on:
                    self.interfaces[self.ap_interface_idx].connection_type = APInterface.ConnectionType.CONNECTION_TYPE_DISABLED.value
            else:
                self.last_disconnected_time = time.time()
        self.previous_connected_state = connected
        if not connected:
            if time.time() - self.last_disconnected_time > self._enable_ap_after_period_s:
                if self.interfaces[self.ap_interface_idx].connection_type != APInterface.ConnectionType.CONNECTION_TYPE_AP.value:
                    logger.warning("Detected broken connection, set up hotspot")
                    self.interfaces[self.ap_interface_idx].connection_type = APInterface.ConnectionType.CONNECTION_TYPE_AP.value
                    self.interfaces[self.ap_interface_idx].ssid = self.def_config.get('AP', 'DefaultAPSSID')
                    self.interfaces[self.ap_interface_idx].passphrase = self.def_config.get('AP', 'DefaultAPPassphrase')
                    self.interfaces[self.ap_interface_idx].reload()

    def initialise(self):
        for interface in self.interfaces:
            interface.initialise()

    def periodic_update(self):
        while True:
            try:
                self.refresh_interfaces()
            except Exception as e:
                logger.error(f"Exception while refreshing: {e}")
            time.sleep(self._update_period_s)

    def reload(self):
        for interface in self.interfaces:
            interface.reload()

    def load_config(self, config):
        for interface in self.interfaces:
            interface.load_config(config)

    def get_conf(self):
        self._conf = {}
        for interface in self.interfaces:
            self._conf |= interface.get_config()
        return self._conf

    def get_status(self):
        status = {}
        for interface in self.interfaces:
            status |= interface.get_status()
        return status
