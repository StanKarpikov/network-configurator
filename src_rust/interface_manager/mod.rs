use std::io::Error;
use actix_web::web::Json;
use config::Config;
use log::{info, warn};
use serde_merge::{mmerge, Map};
use serde_json::Value;
use std::time::SystemTime;

pub struct Interface {
    
}

pub struct Device{
    pub device: String,
    pub device_type: String,
}

pub struct NMCliAdapter {

}

impl NMCliAdapter {
    pub fn device(&self)->Vec<Device>{
        Vec::new()
    }
}

impl Interface {

    pub fn get_conf(&self) -> Result<Map, Error> {
        let config = Map::new();
        Ok(config)
    }
}

pub struct InterfaceManager {
    interfaces:Vec<Interface>,
    last_disconnected_time:SystemTime,
    enable_ap_after_period_s:f32,
    ap_always_on:bool,
    update_period_s:f32,
    check_ethernet_for_connection:bool,
    use_sudo:bool,
    use_whitelist:bool,
    whitelist:Vec<String>,
    use_dedicated_ap:bool,
    dry_run:bool,
    remote_host:bool,
    remote_host_port:i16,
    remote_host_ssh_key:String,
    remote_host_hostname:String,
    ap_interface_idx:usize,
    previous_connected_state:bool,
    def_config:Config,
    adapter:NMCliAdapter,
}

impl InterfaceManager {

    pub fn new(def_config: &Config)-> Result<Self, Error> {
        let interfaces = Vec::new();
        let last_disconnected_time = SystemTime::now();
        let enable_ap_after_period_s = def_config.get("Interfaces.EnableAPAfterBeingDisconnectedForSeconds").unwrap();
        let ap_always_on = def_config.get("Interfaces.AccessPointAlwaysOn").unwrap();
        let update_period_s = def_config.get("Interfaces.UpdatePeriodSec").unwrap();
        let check_ethernet_for_connection = def_config.get("Interfaces.CheckEthernetForConnection").unwrap();
        let use_sudo = def_config.get("Interfaces.UseSudo").unwrap();
        let use_whitelist = def_config.get("Interfaces.InterfaceUseWhitelist").unwrap();
        let whitelist = def_config.get("Interfaces.InterfaceWhitelist").unwrap();
        let use_dedicated_ap = def_config.get("AP.UseDedicatedAP").unwrap();
        let dry_run = def_config.get("Global.DryRun").unwrap();
        let remote_host = def_config.get("RemoteHost.EnableRemoteHost").unwrap();
        let remote_host_port = def_config.get("RemoteHost.HostSSHPort").unwrap();
        let remote_host_ssh_key = def_config.get("RemoteHost.HostSSHKeyFile").unwrap();
        let remote_host_hostname = def_config.get("RemoteHost.HostHostname").unwrap();
        let ap_interface_idx = 0;
        let previous_connected_state = true;
        let def_config = def_config.clone();
        // let adapter =NMCliAdapter().new(use_sudo:use_sudo,
        //                                 dry_run:dry_run,
        //                                 remote_host:remote_host,
        //                                 remote_host_port:remote_host_port,
        //                                 remote_host_ssh_key:remote_host_ssh_key,
        //                                 remote_host_hostname:remote_host_hostname);
        let mut manager = Self {
            interfaces,
            last_disconnected_time,
            enable_ap_after_period_s,
            ap_always_on,
            update_period_s,
            check_ethernet_for_connection,
            use_sudo,
            use_whitelist,
            whitelist,
            use_dedicated_ap,
            dry_run,
            remote_host,
            remote_host_port,
            remote_host_ssh_key,
            remote_host_hostname,
            ap_interface_idx,
            previous_connected_state,
            def_config,
            adapter: NMCliAdapter {},
        };
        manager.detect_interfaces()?;
        Ok(manager)
    }

    fn detect_interfaces(&mut self) -> Result<(), Error> {
        info!("Detecting interfaces...");

        let devices = self.adapter.device();
        let mut ap_found = false;

        for device in devices {
            info!("Found {} type {}", device.device, device.device_type);

            if !self.use_whitelist || self.whitelist.contains(&device.device) {
                match device.device_type.as_str() {
                    "wifi" => {
                        // let interface = WiFiInterface::new(&device.device, &self.adapter, &self.def_config);
                        // self.interfaces.push(interface);
                    }
                    "ethernet" => {
                        // let interface = EthernetInterface::new(&device.device, &self.adapter, &self.def_config);
                        // self.interfaces.push(interface);
                    }
                    "__ap" if self.use_dedicated_ap => {
                        if !ap_found {
                            ap_found = true;
                            // let interface = APInterface::new(&device.device, &self.adapter, &self.def_config);
                            self.ap_interface_idx = Some(self.interfaces.len()).unwrap();
                            // self.interfaces.push(interface);
                        } else {
                            warn!("More than one AP device found: {}, skip", device.device);
                        }
                    }
                    _ => {
                        info!("Skip device {} of unknown type {}", device.device, device.device_type);
                    }
                }
            } else {
                info!("Skip device {}", device.device);
            }
        }

        // Ensure that a dedicated AP interface is created, if needed
        if self.use_dedicated_ap {
            if !ap_found {
                info!("AP interface not found, first run? Creating the interface...");
                // let interface = APInterface::new("", &self.adapter, &self.def_config);
                self.ap_interface_idx = Some(self.interfaces.len()).unwrap();
                // self.interfaces.push(interface);
            } else {
                // info!("Dedicated AP interface found, {} will be used as AP", self.interfaces[self.ap_interface_idx].device);
            }
        } else {
            // Select the first Wi-Fi interface to use as an AP
            for (idx, interface) in self.interfaces.iter().enumerate() {
                // if let InterfaceType::WiFi = interface.interface_type {
                //     self.ap_interface_idx = Some(idx);
                //     info!("Dedicated AP not used, {} will be used as AP", interface.device);
                //     break;
                // }
            }
        }

        Ok(())
    }

    fn refresh_interfaces(&self) -> Result<(), Error> {
        Ok({})
    }

    fn initialise(&self) -> Result<(), Error> {
        Ok({})
    }

    fn periodic_update(&self) -> Result<(), Error> {
        Ok({})
    }

    fn reload(&self) -> Result<(), Error> {
        Ok({})
    }

    #[allow(unused_variables)]
    pub fn load_config(&self, x: Json<Value>) -> Result<(), Error> {
        Ok({})
    }

    pub fn get_conf(&self) -> Result<Map, Error> {
        let mut global_config = Map::new();

        for interface in self.interfaces.iter() {
            let config = interface.get_conf()?;
            global_config = mmerge(&global_config, &config).unwrap();
        }

        Ok(global_config)
    }

    pub fn get_status(&self) -> Result<(), Error> {
        Ok({})
    }
}
