import logging
import time

from .symmetries import NullHandler


LOG = logging.getLogger('socketIO-client')
LOG.addHandler(NullHandler())


class LoggingMixin(object):

    def _log(self, level, msg, *attrs):
        LOG.log(level, '%s %s' % (self._log_name, msg), *attrs)

    def _debug(self, msg, *attrs):
        self._log(logging.DEBUG, msg, *attrs)

    def _info(self, msg, *attrs):
        self._log(logging.INFO, msg, *attrs)

    def _warn(self, msg, *attrs):
        self._log(logging.WARNING, msg, *attrs)

    def _yield_warning_screen(self, seconds=None):
        last_warning = None
        for elapsed_time in _yield_elapsed_time(seconds):
            try:
                yield elapsed_time
            except Exception as warning:
                warning = str(warning)
                if last_warning != warning:
                    last_warning = warning
                    self._warn(warning)
                time.sleep(1)


def _yield_elapsed_time(seconds=None):
    start_time = time.time()
    if seconds is None:
        while True:
            yield _get_elapsed_time(start_time)
    while _get_elapsed_time(start_time) < seconds:
        yield _get_elapsed_time(start_time)


def _get_elapsed_time(start_time):
    return time.time() - start_time
