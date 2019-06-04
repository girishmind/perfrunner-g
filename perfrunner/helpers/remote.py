from fabric import state
from fabric.api import run, settings

from logger import logger
from perfrunner.remote.linux import RemoteLinux
from perfrunner.remote.windows import RemoteWindows
from perfrunner.settings import ClusterSpec


class RemoteHelper:

    def __new__(cls, cluster_spec: ClusterSpec, verbose: bool = False):
        if not cluster_spec.ssh_credentials:
            return None

        state.env.user, state.env.password = cluster_spec.ssh_credentials
        state.output.running = verbose
        state.output.stdout = verbose

        os = cls.detect_os(cluster_spec)
        if os == 'Cygwin':
            return RemoteWindows(cluster_spec, os)
        else:
            return RemoteLinux(cluster_spec, os)

    @staticmethod
    def detect_os(cluster_spec: ClusterSpec):
        logger.info('Detecting OS')
        with settings(host_string=cluster_spec.servers[0]):
            os = run('python -c "import platform; print platform.dist()[0]"')
        if os:
            return os
        else:
            return 'Cygwin'
