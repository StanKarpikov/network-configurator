# Yet Another Captive Portal Implementation

`Network-Configurator` is a minimal captive portal implementation that can be used to configure network settings (Wi-Fi and Ethernet) on IoT devices, primarly targeted Raspberry Pi Linux with NetworkManager. However, it can be easily adapted to other platforms by replacing the adapter component.

**TODO:**

- Python project is done
- Rust and Go implementation is **work in progress**


See `network-configuration.default.conf` for details about the configuration options.

`src_python` contains Python source code.
`recipes-network` provide an example of Yocto recipes, the root folder could be imported as `meta-network-configurator` layer since it contains the `conf` folder with layer settings.
`static` contains web interface sources in plain JS without any additional libraries required.

## Differences with Other Captive Portal Implementations

- **Simple, yet feature-rich**: Simple web pages with no external libraries or components, no websockets to simplify use with a proxy
- **Multiple interfaces**: Automatically detects and shows all WiFi and Ethernet interfaces available on the device, allowing to configure them
- **Proxy**: Can be used behind a proxy
- **Container-Friendly**: Can be used inside a container (Docker, Podman) and accessing the host NetworkManager via SSH.
- **Yocto-Ready**: Repository is set up as a Yocto layer with the nesessary sudoers and systemd files

Similar projects:

- [https://github.com/balena-os/wifi-connect](https://github.com/balena-os/wifi-connect)
- [https://github.com/smartheim/wifi-captive-rs](https://github.com/smartheim/wifi-captive-rs)

## Operation

During first run the configurator will create the following connections for each detected interface:

For Ethernet connections:

- `static-ip-{adapter}` (for example `static-ip-eth0`) for static IP connection
- `dynamic-ip-{adapter}` for dynamic IP
- `dhcp-server-{adapter}` for DHCP servers

For Wi-Fi connections:

- `hotspot-{adapter}` (for example `hotspot-wlan0`)

These connections always exist, and the configurator switches between them by setting the `connection.autoconnect` flag to `yes` or `no`. This allows to retrieve the configuration after restart, so no other configuration files are used. All information is retrieved from the NetworkManager.

## Dedicated AP Mode (TODO)

## Adapting to Other Platforms (other than NetworkManager)

`src_python/interface_manager/adapters` contain the translation layer that calls system functions to configure the interfaces. It can be replaced with another implementation if needed.
