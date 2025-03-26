import os
import argparse
import logging
import time
from pathlib import Path
from flask import request
from configparser import ConfigParser
from flask import Flask, render_template, jsonify

from interface_manager.inteface_manager import InterfaceManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger_werkzeug = logging.getLogger("werkzeug")
logger_werkzeug.setLevel(logging.INFO)

VERSION = "1.0"

USE_FULL_BACKTRACE = True

DEFAULT_CONFIG = "network-configuration.default.conf"

DESCRIPTION = f"""

"""

root_dir = Path(".")

class ReverseProxied(object):

    def __init__(self, app, script_name=None, scheme=None, server=None):
        self.app = app
        self.script_name = script_name
        self.scheme = scheme
        self.server = server

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '') or self.script_name
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]
        scheme = environ.get('HTTP_X_SCHEME', '') or self.scheme
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        server = environ.get('HTTP_X_FORWARDED_SERVER', '') or self.server
        if server:
            environ['HTTP_HOST'] = server
        return self.app(environ, start_response)


class NetworkConfigurationService:
    def __init__(self, def_config):
        self.manager = InterfaceManager(def_config=def_config)
        self._start_server = def_config.getboolean('Server', 'EnableServer')
        self._port = def_config.getint('Server', 'Port')
        self._address = def_config.get('Server', 'Address')
        self._ap_hide_in_ui = def_config.getboolean('AP', 'APHideInUI')
        self._ap_interface = def_config.get('AP', 'APInterfaceDevice')
        self._reverse_proxy_path = def_config.get('Server', 'ReverseProxyPath')
        if self._start_server:
            self.start_server()
        else:
            # Just sleep indefinetely
            while True:
                time.sleep(100)

    def start_server(self):
        app = Flask(__name__,
                    static_folder=root_dir / 'static')
        app.wsgi_app = ReverseProxied(app.wsgi_app, script_name=self._reverse_proxy_path)

        @app.route('/')
        def index():
            return app.send_static_file('index.html')

        @app.route('/api/status', methods=['GET'])
        def status_control():
            return jsonify(self.manager.get_status()), 200

        @app.route('/api/config', methods=['GET', 'POST'])
        def config_control():
            if request.method == 'GET':
                conf = self.manager.get_conf()
                if self._ap_hide_in_ui:
                    try:
                        conf.pop(self._ap_interface)
                    except:
                        pass
                return jsonify(conf), 200
            elif request.method == 'POST':
                config = request.get_json()
                logger.info(f"Received config: {config}")
                self.manager.load_config(config)
                return jsonify("OK"), 200

        @app.route('/api/<interface_id>/config', methods=['GET', 'POST'])
        def config_interface_control(interface_id):
            try:
                for interface in self.manager.interfaces:
                    if interface_id == interface.device:
                        if request.method == 'GET':
                            return jsonify(interface.get_conf()), 200
                        elif request.method == 'POST':
                            config = request.get_json()
                            logger.info(f"Received config: {config}")
                            interface.load_config({interface_id: config})
                            return jsonify("OK"), 200
                return jsonify({'error': f'Interface {interface_id} not found. Acceptable interfaces are: {", ".join(self.manager.interfaces)}'}), 404
            except Exception as e:
                return jsonify({'error': f'{e}'}), 500

        @app.route('/api/interfaces', methods=['GET'])
        def interfaces_control():
            interfaces = []
            for interface in self.manager.interfaces:
                if self._ap_hide_in_ui and interface.device == self._ap_interface:
                    continue
                interfaces.append(interface.device)
            return jsonify(interfaces), 200

        @app.route('/api/param/<interface_id>/<parameter>', methods=['GET', 'POST'])
        def parameter_control(interface_id: str, parameter: str):
            try:
                for interface in self.manager.interfaces:
                    if interface_id == interface.device:
                        if parameter in interface.parameters():
                            if request.method == 'GET':
                                return jsonify(interface[parameter]), 200
                            elif request.method == 'POST':
                                try:
                                    interface[parameter] = request.form.to_dict(flat=False)
                                    return jsonify(interface[parameter]), 200
                                except Exception as e:
                                    return jsonify({'error': f'Could not process request, internal error: {e}'}), 500
                            else:
                                return jsonify({'error': f'Method {request.method} not allowed'}), 405
                        else:
                            return jsonify({'error': f'Unknown parameter {parameter} for interface {interface_id}. '
                                                     f'Acceptable parameters are: {", ".join(interface.parameters())}'}), 404
                    return jsonify({'error': f'Interface {interface_id} not found. Acceptable interfaces are: {", ".join(self.manager.interfaces)}'}), 404
            except Exception as e:
                return jsonify({'error': f'{e}'}), 500

        app.run(debug=False, port=self._port, host=self._address)

    def run(self):
        self.start_server()


def main():
    parser = argparse.ArgumentParser(prog=f"Network Configuration Service {VERSION}",
                                     description=DESCRIPTION)
    parser.add_argument("-c", "--conf", help="Configuration file", type=str, required=False)
    args = parser.parse_args()

    try:
        def_config = ConfigParser()
        def_config.read(DEFAULT_CONFIG)
        if os.path.isfile(args.conf):
            def_config.read(args.conf)
        else:
            logger.warning("Configuration file not provided, using default configuration")

        NetworkConfigurationService(def_config)
    except Exception as e:
        logger.error(f"Exception: {e}")
        if USE_FULL_BACKTRACE:
            raise e


if __name__ == "__main__":
    main()
