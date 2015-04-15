import logging
from threading import Thread, Event

from .exceptions import ConnectionError, TimeoutError


class HeartbeatThread(Thread):

    daemon = True

    def __init__(
            self, send_heartbeat,
            relax_interval_in_seconds,
            hurry_interval_in_seconds):
        super(HeartbeatThread, self).__init__()
        self._send_heartbeat = send_heartbeat
        self._relax_interval_in_seconds = relax_interval_in_seconds
        self._hurry_interval_in_seconds = hurry_interval_in_seconds
        self._adrenaline = Event()
        self._rest = Event()
        self._halt = Event()

    def run(self):
        try:
            while not self._halt.is_set():
                try:
                    self._send_heartbeat()
                except TimeoutError:
                    pass
                if self._adrenaline.is_set():
                    interval_in_seconds = self._hurry_interval_in_seconds
                else:
                    interval_in_seconds = self._relax_interval_in_seconds
                self._rest.wait(interval_in_seconds)
        except ConnectionError:
            logging.debug('[heartbeat connection error]')

    def relax(self):
        self._adrenaline.clear()

    def hurry(self):
        self._adrenaline.set()
        self._rest.set()
        self._rest.clear()

    @property
    def hurried(self):
        return self._adrenaline.is_set()

    def halt(self):
        self._rest.set()
        self._halt.set()
