"""Prometheus server configuration class is defined here."""

from threading import Thread
from wsgiref.simple_server import WSGIServer

from prometheus_client import start_http_server


class PrometheusServer:  # pylint: disable=too-few-public-methods

    def __init__(self, port: int = 9090, host: str = "0.0.0.0"):
        self._host = host
        self._port = port
        self._server: WSGIServer
        self._thread: Thread

        self._server, self._thread = start_http_server(self._port)

    def shutdown(self):
        if self._server is not None:
            self._server.shutdown()
            self._server = None
