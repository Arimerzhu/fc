"""XML-RPC transport with configurable timeout."""

from xmlrpc.client import Transport


class _TimeoutTransport(Transport):
    """XML-RPC transport with a configurable socket timeout."""

    def __init__(self, timeout: float = 30, **kwargs):
        super().__init__(**kwargs)
        self._timeout = timeout

    def make_connection(self, host):
        conn = super().make_connection(host)
        conn.timeout = self._timeout
        return conn
