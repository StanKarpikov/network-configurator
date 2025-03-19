from multiprocessing import Process
from pathlib import Path
from flask_socketio import SocketIO, send, emit, join_room, leave_room
from inteface_manager import WlanInterface, LanInterface, APInterface, InterfaceManager
from flask import Flask, make_response, render_template, jsonify
from flask_sock import Sock
from flask import request

root_dir = Path(".")

class NCServer(Process):
    def __init__(self, port: int, manager: InterfaceManager):
        self.port = port
        self.manager = manager
        super().__init__()

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

        @app.route('/api/<interface>/<parameter>', methods=['GET', 'POST'])
        def update_employee(interface: str, parameter: str):
            if interface in self.manager.interfaces:
                if parameter in self.manager.interfaces[interface].parameters:
                    if request.method == 'GET':
                        return self.manager.interfaces[interface][parameter]
                    elif request.method == 'POST':
                        try:
                            self.manager.interfaces[interface][parameter] = request.form
                        except Exception as e:
                            return jsonify({'error': f'Could not process request, internal error: {e}'}), 500
                    else:
                        return jsonify({'error': f'Method {request.method} not allowed'}), 405
                else:
                    return jsonify({'error': f'Unknown parameter {parameter} for interface {interface}. '
                                             f'Acceptable parameters are: {", ".join(self.manager.interfaces[interface].parameters)}'}), 404
            else:
                return jsonify({'error': f'Unknown interface {interface}. Acceptable interfaces are: {", ".join(self.manager.interfaces)}'}), 404

        @socket.on('connect', namespace='/update_namespace')
        def connect():
            join_room('updates')

        @app.route('/update')
        def some_name():
            self.manager.
            emit('message', 'update message', room='updates', namespace='/update_namespace')

        app.run(debug=False, port=self.port)

    def run(self):
        self.start_server()
