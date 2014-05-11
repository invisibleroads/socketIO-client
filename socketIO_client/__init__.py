import logging
import json
import requests
import time
from collections import namedtuple
try:
	from urlparse import urlparse
except ImportError:
	from urllib.parse import urlparse

from .exceptions import ConnectionError, TimeoutError, PacketError
from .transports import _get_response, _negotiate_transport, TRANSPORTS


_SocketIOSession = namedtuple('_SocketIOSession', [
    'id',
    'heartbeat_timeout',
    'server_supported_transports',
])
_log = logging.getLogger(__name__)
PROTOCOL_VERSION = 1
RETRY_INTERVAL_IN_SECONDS = 1


class BaseNamespace(object):
    'Define client behavior'

    def __init__(self, _transport, path):
        self._transport = _transport
        self.path = path
        self._callback_by_event = {}
        self.initialize()

    def initialize(self):
        'Initialize custom variables here; you can override this method'
        pass

    def message(self, data='', callback=None):
        self._transport.message(self.path, data, callback)

    def emit(self, event, *args, **kw):
        callback, args = find_callback(args, kw)
        self._transport.emit(self.path, event, args, callback)

    def disconnect(self):
        self._transport.disconnect(self.path)

    def on(self, event, callback):
        'Define a callback to handle a custom event emitted by the server'
        self._callback_by_event[event] = callback

    def on_connect(self):
        'Called after server connects; you can override this method'
        _log.debug('%s [connect]', self.path)

    def on_disconnect(self):
        'Called after server disconnects; you can override this method'
        _log.debug('%s [disconnect]', self.path)

    def on_heartbeat(self):
        'Called after server sends a heartbeat; you can override this method'
        _log.debug('%s [heartbeat]', self.path)

    def on_message(self, data):
        'Called after server sends a message; you can override this method'
        _log.info('%s [message] %s', self.path, data)

    def on_event(self, event, *args):
        """
        Called after server sends an event; you can override this method.
        Called only if a custom event handler does not exist,
        such as one defined by namespace.on('my_event', my_function).
        """
        callback, args = find_callback(args)
        arguments = [repr(_) for _ in args]
        if callback:
            arguments.append('callback(*args)')
            callback(*args)
        _log.info('%s [event] %s(%s)', self.path, event, ', '.join(arguments))

    def on_error(self, reason, advice):
        'Called after server sends an error; you can override this method'
        _log.info('%s [error] %s', self.path, advice)

    def on_noop(self):
        'Called after server sends a noop; you can override this method'
        _log.info('%s [noop]', self.path)

    def on_open(self, *args):
        _log.info('%s [open] %s', self.path, args)

    def on_close(self, *args):
        _log.info('%s [close] %s', self.path, args)

    def on_retry(self, *args):
        _log.info('%s [retry] %s', self.path, args)

    def on_reconnect(self, *args):
        _log.info('%s [reconnect] %s', self.path, args)

    def _find_event_callback(self, event):
        # Check callbacks defined by on()
        try:
            return self._callback_by_event[event]
        except KeyError:
            pass
        # Check callbacks defined explicitly or use on_event()
        return getattr(
            self,
            'on_' + event.replace(' ', '_'),
            lambda *args: self.on_event(event, *args))


class SocketIO(object):
    """Create a socket.io client that connects to a socket.io server
    at the specified host and port.

    - Define the behavior of the client by specifying a custom Namespace.
    - Prefix host with https:// to use SSL.
    - Set wait_for_connection=True to block until we have a connection.
    - Specify the transports you want to use.
    - Pass query params, headers, cookies, proxies as keyword arguments.

    SocketIO('localhost', 8000,
        params={'q': 'qqq'},
        headers={'Authorization': 'Basic ' + b64encode('username:password')},
        cookies={'a': 'aaa'},
        proxies={'https': 'https://proxy.example.com:8080'})
    """

    def __init__(
            self, host, port=None, Namespace=BaseNamespace,
            wait_for_connection=True, transports=TRANSPORTS, **kw):
        self.is_secure, self.base_url = _parse_host(host, port)
        self.wait_for_connection = wait_for_connection
        self._namespace_by_path = {}
        self.client_supported_transports = transports
        self.kw = kw
        self.define(Namespace)

    def __enter__(self):
        return self

    def __exit__(self, *exception_pack):
        self.disconnect()

    def __del__(self):
        self.disconnect()

    def define(self, Namespace, path=''):
        if path:
            self._transport.connect(path)
        namespace = Namespace(self._transport, path)
        self._namespace_by_path[path] = namespace
        return namespace

    def on(self, event, callback, path=''):
        return self.get_namespace(path).on(event, callback)

    def message(self, data='', callback=None, path=''):
        self._transport.message(path, data, callback)

    def emit(self, event, *args, **kw):
        path = kw.get('path', '')
        callback, args = find_callback(args, kw)
        self._transport.emit(path, event, args, callback)

    def wait(self, seconds=None, for_callbacks=False):
        """Wait in a loop and process events as defined in the namespaces.

        - Omit seconds, i.e. call wait() without arguments, to wait forever.
        """
        try:
            warning_screen = _yield_warning_screen(seconds)
            for elapsed_time in warning_screen:
                try:
                    try:
                        self._process_events()
                    except TimeoutError:
                        pass
                    if self._stop_waiting(for_callbacks):
                        break
                    self.heartbeat_pacemaker.send(elapsed_time)
                except ConnectionError as e:
                    try:
                        warning = Exception('[connection error] %s' % e)
                        warning_screen.throw(warning)
                    except StopIteration:
                        _log.warn(warning)
                    self.disconnect()
        except KeyboardInterrupt:
            pass

    def _process_events(self):
        for packet in self._transport.recv_packet():
            try:
                self._process_packet(packet)
            except PacketError as e:
                _log.warn('[packet error] %s', e)

    def _process_packet(self, packet):
        code, packet_id, path, data = packet
        namespace = self.get_namespace(path)
        delegate = self._get_delegate(code)
        delegate(packet, namespace._find_event_callback)

    def _stop_waiting(self, for_callbacks):
        # Use __transport to make sure that we do not reconnect inadvertently
        if for_callbacks and not self.__transport.has_ack_callback:
            return True
        if self.__transport._wants_to_disconnect:
            return True
        return False

    def wait_for_callbacks(self, seconds=None):
        self.wait(seconds, for_callbacks=True)

    def disconnect(self, path=''):
        if self.connected:
            self._transport.disconnect(path)
            namespace = self._namespace_by_path[path]
            namespace.on_disconnect()
        if path:
            del self._namespace_by_path[path]

    @property
    def connected(self):
        return self.__transport.connected

    @property
    def _transport(self):
        try:
            if self.connected:
                return self.__transport
        except AttributeError:
            pass
        warning_screen = _yield_warning_screen(seconds=None)
        for elapsed_time in warning_screen:
            try:
                self.__transport = self._get_transport()
                break
            except ConnectionError as e:
                if not self.wait_for_connection:
                    raise
                try:
                    warning = Exception('[waiting for connection] %s' % e)
                    warning_screen.throw(warning)
                except StopIteration:
                    _log.warn(warning)
        return self.__transport

    def _get_transport(self):
        socketIO_session = _get_socketIO_session(
            self.is_secure, self.base_url, **self.kw)
        _log.debug('[transports available] %s', ' '.join(
            socketIO_session.server_supported_transports))
        # Initialize heartbeat_pacemaker
        self.heartbeat_pacemaker = self._make_heartbeat_pacemaker(
            heartbeat_interval=socketIO_session.heartbeat_timeout / 2)
        next(self.heartbeat_pacemaker)
        # Negotiate transport
        transport = _negotiate_transport(
            self.client_supported_transports, socketIO_session,
            self.is_secure, self.base_url, **self.kw)
        # Update namespaces
        for path, namespace in self._namespace_by_path.items():
            namespace._transport = transport
            transport.connect(path)
        return transport

    def _make_heartbeat_pacemaker(self, heartbeat_interval):
        heartbeat_time = 0
        while True:
            elapsed_time = (yield)
            if elapsed_time - heartbeat_time > heartbeat_interval:
                heartbeat_time = elapsed_time
                self._transport.send_heartbeat()

    def get_namespace(self, path=''):
        try:
            return self._namespace_by_path[path]
        except KeyError:
            raise PacketError('unexpected namespace path (%s)' % path)

    def _get_delegate(self, code):
        try:
            return {
                '0': self._on_disconnect,
                '1': self._on_connect,
                '2': self._on_heartbeat,
                '3': self._on_message,
                '4': self._on_json,
                '5': self._on_event,
                '6': self._on_ack,
                '7': self._on_error,
                '8': self._on_noop,
            }[code]
        except KeyError:
            raise PacketError('unexpected code (%s)' % code)

    def _on_disconnect(self, packet, find_event_callback):
        find_event_callback('disconnect')()

    def _on_connect(self, packet, find_event_callback):
        find_event_callback('connect')()

    def _on_heartbeat(self, packet, find_event_callback):
        find_event_callback('heartbeat')()

    def _on_message(self, packet, find_event_callback):
        code, packet_id, path, data = packet
        args = [data]
        if packet_id:
            args.append(self._prepare_to_send_ack(path, packet_id))
        find_event_callback('message')(*args)

    def _on_json(self, packet, find_event_callback):
        code, packet_id, path, data = packet
        args = [json.loads(data)]
        if packet_id:
            args.append(self._prepare_to_send_ack(path, packet_id))
        find_event_callback('message')(*args)

    def _on_event(self, packet, find_event_callback):
        code, packet_id, path, data = packet
        value_by_name = json.loads(data)
        event = value_by_name['name']
        args = value_by_name.get('args', [])
        if packet_id:
            args.append(self._prepare_to_send_ack(path, packet_id))
        find_event_callback(event)(*args)

    def _on_ack(self, packet, find_event_callback):
        code, packet_id, path, data = packet
        data_parts = data.split('+', 1)
        packet_id = data_parts[0]
        try:
            ack_callback = self._transport.get_ack_callback(packet_id)
        except KeyError:
            return
        args = json.loads(data_parts[1]) if len(data_parts) > 1 else []
        ack_callback(*args)

    def _on_error(self, packet, find_event_callback):
        code, packet_id, path, data = packet
        reason, advice = data.split('+', 1)
        find_event_callback('error')(reason, advice)

    def _on_noop(self, packet, find_event_callback):
        find_event_callback('noop')()

    def _prepare_to_send_ack(self, path, packet_id):
        'Return function that acknowledges the server'
        return lambda *args: self._transport.ack(path, packet_id, *args)


def find_callback(args, kw=None):
    'Return callback whether passed as a last argument or as a keyword'
    if args and callable(args[-1]):
        return args[-1], args[:-1]
    try:
        return kw['callback'], args
    except (KeyError, TypeError):
        return None, args


def _parse_host(host, port):
    if not host.startswith('http'):
        host = 'http://' + host
    url_pack = urlparse(host)
    is_secure = url_pack.scheme == 'https'
    port = port or url_pack.port or (443 if is_secure else 80)
    base_url = '%s:%d%s/socket.io/%s' % (
        url_pack.hostname, port, url_pack.path, PROTOCOL_VERSION)
    return is_secure, base_url


def _yield_warning_screen(seconds=None):
    last_warning = None
    for elapsed_time in _yield_elapsed_time(seconds):
        try:
            yield elapsed_time
        except Exception as warning:
            warning = str(warning)
            if last_warning != warning:
                last_warning = warning
                _log.warn(warning)
            time.sleep(RETRY_INTERVAL_IN_SECONDS)


def _yield_elapsed_time(seconds=None):
    start_time = time.time()
    if seconds is None:
        while True:
            yield time.time() - start_time
    while time.time() - start_time < seconds:
        yield time.time() - start_time


def _get_socketIO_session(is_secure, base_url, **kw):
    server_url = '%s://%s/' % ('https' if is_secure else 'http', base_url)
    try:
        response = _get_response(requests.get, server_url, **kw)
    except TimeoutError as e:
        raise ConnectionError(e)
    response_parts = response.text.split(':')
    return _SocketIOSession(
        id=response_parts[0],
        heartbeat_timeout=int(response_parts[1]),
        server_supported_transports=response_parts[3].split(','))
