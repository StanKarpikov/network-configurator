import logging
import subprocess
import nmcli
from nmcli import SystemCommand, ConnectionControl, DeviceControl, GeneralControl, NetworkingControl, RadioControl
from paramiko.client import SSHClient
from paramiko.ssh_exception import SSHException

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class HostController:

    def __init__(self,
                 remote_host_port: int = 22,
                 remote_host_ssh_key: str = "",
                 remote_host_hostname: str = "localhost"):
        self.remote_host_port = remote_host_port
        self.remote_host_ssh_key = remote_host_ssh_key
        self.remote_host_hostname = remote_host_hostname
        self.client: SSHClient | None = None
        self.init_nmcli_interface()

    def ssh_connect(self):
        if self.client is None:
            try:
                self.client = SSHClient()
                self.client.load_system_host_keys()
                ssh_port = int(self.remote_host_port)
                key_file = self.remote_host_ssh_key
                hostname = self.remote_host_hostname
                self.client.connect(hostname=hostname, port=ssh_port, key_filename=key_file)
                logger.info('SSH Host connected')
            except Exception as e:
                logger.error(f'Error connecting to the host: {e}')

    def run(self, *popenargs, input=None, capture_output=False, timeout=None, check=False, **kwargs):
        # logger.debug(f"Run nmcli with [{popenargs}] and [{kwargs}]")
        # input and timeout are unused
        command = ''
        for arg in popenargs[0]:
            if ' ' in arg:
                command += f'"{arg}"'
            else:
                command += arg
            command += ' '
        command = command[:-1]

        try:
            retcode, stdout, stderr = self.run_host_command(command)
        except SSHException:  # Including KeyboardInterrupt, communicate handled that.
            raise

        if check and retcode:
            raise subprocess.CalledProcessError(retcode, command,
                                                output=stdout, stderr=stderr)
        return subprocess.CompletedProcess(command, retcode, stdout, stderr)

    def run_host_command(self, command):
        self.ssh_connect()
        logger.debug(f'SSH: {command}')
        _, stdout, stderr = self.client.exec_command(command)
        retcode = stdout.channel.recv_exit_status()
        stdout = stdout.read()
        stderr = stderr.read()
        logger.debug(f'retcode: {retcode}')
        logger.debug(f'OUT {stdout.decode("utf-8")}')
        logger.debug(f'ERR {stderr.decode("utf-8")}')
        return retcode, stdout, stderr

    def init_nmcli_interface(self):
        nmcli._syscmd = SystemCommand(subprocess_run=self.run)
        nmcli.connection = ConnectionControl(nmcli._syscmd)
        nmcli.device = DeviceControl(nmcli._syscmd)
        nmcli.general = GeneralControl(nmcli._syscmd)
        nmcli.networking = NetworkingControl(nmcli._syscmd)
        nmcli.radio = RadioControl(nmcli._syscmd)
