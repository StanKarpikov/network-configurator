import argparse
from pathlib import Path
from flask_socketio import SocketIO, send, emit, join_room, leave_room
from inteface_manager import WlanInterface, LanInterface, InterfaceManager
from flask import Flask, render_template, jsonify
from flask import request

DEFAULT_CONFIG = """
[Global]
ParametersConfigFile = /etc/network_configurator/net_parameters.json

[Server]
EnableServer = True
Port = 50000

[Interfaces]
EnableAPAfterBeingDisconnectedForSeconds = 30
UseSudo = True
AccessPointAlwaysOn = True

[AP]
APInterfaceDevice = uap0
DefaultAPSSID = ConfigurationTest
DefaultPassphrase = 012345678
APMAC = 00:11:22:33:44:55
IPForwardEnable = 1
DefaultAPConnectionType = "ap"
DefaultAPIP = "192.168.33.1"
DefaultAPMask = "255.255.255.0"
DefaultAPRoute = "192.168.33.1"
        
[WiFi]
DefaultWiFiConnectionType = "station"
DefaultWiFiIP = "0.0.0.0"
DefaultWiFiMask = "255.255.255.0"
DefaultWiFiRoute = "0.0.0.0"
DefaultWiFiSSID = ""
DefaultWiFiPassphrase = ""

[Ethernet]
DefaultEthernetConnectionType = "dynamic_ip"
DefaultEthernetIP = "0.0.0.0"
DefaultEthernetMask = "255.255.255.0"
DefaultEthernetRoute = "0.0.0.0"

"""

root_dir = Path(".")

class NetworkConfigurationService:
    def __init__(self, def_config):
        self.manager = InterfaceManager(def_config=def_config)
        self._start_server = def_config.getboolean('Server', 'EnableServer')
        self._port = def_config.getint('Server', 'Port')

    def start_server(self):
        app = Flask(__name__,
                    static_folder=root_dir / 'static',
                    template_folder=root_dir / 'templates')
        socket = SocketIO(app, cors_allowed_origins="*", SameSite=None)

        @app.route('/scripts.js')
        def scripts():
            return render_template('scripts.js')

        @app.route('/')
        def index():
            return render_template('index.html')

        @app.route('/api/update', methods=['POST'])
        def update_control():
            self.manager.reload()
            return "", 200

        @app.route('/api/status', methods=['GET'])
        def status_control():
            return jsonify(self.manager.get_status()), 200

        @app.route('/api/config', methods=['GET'])
        def config_control():
            return jsonify(self.manager.get_conf()), 200

        @app.route('/api/interfaces', methods=['GET'])
        def interfaces_control():
            return jsonify(self.manager.interfaces), 200

        @app.route('/api/param/<interface>/<parameter>', methods=['GET', 'POST'])
        def parameter_control(interface: str, parameter: str):
            if interface in self.manager.interfaces:
                if parameter in self.manager.interfaces[interface].parameters:
                    if request.method == 'GET':
                        return jsonify(self.manager.interfaces[interface][parameter]), 200
                    elif request.method == 'POST':
                        try:
                            self.manager.interfaces[interface][parameter] = request.form
                            return jsonify(self.manager.interfaces[interface][parameter]), 200
                        except Exception as e:
                            return jsonify({'error': f'Could not process request, internal error: {e}'}), 500
                    else:
                        return jsonify({'error': f'Method {request.method} not allowed'}), 405
                else:
                    return jsonify({'error': f'Unknown parameter {parameter} for interface {interface}. '
                                             f'Acceptable parameters are: {", ".join(self.manager.interfaces[interface].parameters)}'}), 404
            else:
                return jsonify({'error': f'Unknown interface {interface}. Acceptable interfaces are: {", ".join(self.manager.interfaces)}'}), 404

        app.run(debug=False, port=self._port)

    def run(self):
        self.start_server()


def main():
    parser = argparse.ArgumentParser("Network Configuration Service")
    parser.add_argument("--conf", help="Default Configuration File", type=str, default="/etc/network_conf_service.conf")
    args = parser.parse_args()
    NetworkConfigurationService(args.conf)


if __name__ == "__main__":
    main()
