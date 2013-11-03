import logging
import json
import requests
import socket
import time
import websocket
from collections import namedtuple


_Session = namedtuple('_Session', [
    'id',
    'heartbeat_timeout',
    'server_supported_transports',
])
_log = logging.getLogger(__name__)
TRANSPORTS = 'websocket', 'xhr-polling', 'jsonp-polling'
PROTOCOL_VERSION = 1


class BaseNamespace(object):
    'Define client behavior'

    def __init__(self, _transport, path):
        self._transport = _transport
        self._path = path
        self._callback_by_event = {}
        self.initialize()

    def initialize(self):
        'Initialize custom variables here; you can override this method'
        pass

    def message(self, data='', callback=None):
        self._transport.message(self._path, data, callback)

    def emit(self, event, *args, **kw):
        callback, args = find_callback(args, kw)
        self._transport.emit(self._path, event, args, callback)

    def on(self, event, callback):
        'Define a callback to handle a custom event emitted by the server'
        self._callback_by_event[event] = callback

    def on_connect(self):
        'Called after server connects; you can override this method'
        _log.debug('[connect]')

    def on_disconnect(self):
        'Called after server disconnects; you can override this method'
        _log.debug('[disconnect]')

    def on_heartbeat(self):
        'Called after server sends a heartbeat; you can override this method'
        _log.debug('[heartbeat]')

    def on_message(self, data):
        'Called after server sends a message; you can override this method'
        _log.info('[message] %s', data)

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
        _log.info('[event] %s(%s)', event, ', '.join(arguments))

    def on_error(self, reason, advice):
        'Called after server sends an error; you can override this method'
        _log.info('[error] %s', advice)

    def on_noop(self):
        'Called after server sends a noop; you can override this method'
        _log.info('[noop]')

    def on_open(self, *args):
        _log.info('[open] %s', args)

    def on_close(self, *args):
        _log.info('[close] %s', args)

    def on_retry(self, *args):
        _log.info('[retry] %s', args)

    def on_reconnect(self, *args):
        _log.info('[reconnect] %s', args)

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

    def __init__(
            self, host, port, Namespace=BaseNamespace, secure=False,
            wait_for_connection=True, transports=TRANSPORTS, **kw):
        """
        Create a socket.io client that connects to a socket.io server
        at the specified host and port.
        - Define the behavior of the client by specifying a custom Namespace.
        - Set secure=True to use HTTPS / WSS.
        - Set wait_for_connection=True to block until we have a connection.
        - List the transports you want to use (%s).
        - Pass query params, headers, cookies, proxies as keyword arguments.

        SocketIO('localhost', 8000, proxies={
            'https': 'https://proxy.example.com:8080'})
        """ % ', '.join(TRANSPORTS)
        self.base_url = '%s:%d/socket.io/%s' % (host, port, PROTOCOL_VERSION)
        self.secure = secure
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
        try:
            warning_screen = _yield_warning_screen(seconds, sleep=1)
            for elapsed_time in warning_screen:
                try:
                    if for_callbacks and not self._transport.has_ack_callback:
                        break
                    try:
                        self._process_packet(self._transport.recv_packet())
                    except _TimeoutError:
                        pass
                    except _PacketError as error:
                        _log.warn('[packet error] %s', error)
                    self.heartbeat_pacemaker.send(elapsed_time)
                except SocketIOConnectionError as error:
                    self.disconnect()
                    warning = Exception('[connection error] %s' % error)
                    warning_screen.throw(warning)
        except KeyboardInterrupt:
            pass

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
        warning_screen = _yield_warning_screen(seconds=None, sleep=1)
        for elapsed_time in warning_screen:
            try:
                self.__transport = self._get_transport()
                break
            except SocketIOConnectionError as error:
                if not self.wait_for_connection:
                    raise
                warning = Exception('[waiting for connection] %s' % error)
                warning_screen.throw(warning)
        return self.__transport

    def _get_transport(self):
        self.session = _get_session(self.secure, self.base_url, **self.kw)
        _log.debug('[transports available] %s', ' '.join(
            self.session.server_supported_transports))
        # Initialize heartbeat_pacemaker
        self.heartbeat_pacemaker = self._make_heartbeat_pacemaker(
            heartbeat_interval=self.session.heartbeat_timeout - 2)
        self.heartbeat_pacemaker.next()
        # Negotiate transport
        transport = _negotiate_transport(
            self.client_supported_transports, self.session,
            self.secure, self.base_url, **self.kw)
        # Update namespaces
        for namespace in self._namespace_by_path.values():
            namespace._transport = transport
        return transport

    def _make_heartbeat_pacemaker(self, heartbeat_interval):
        heartbeat_time = 0
        while True:
            elapsed_time = (yield)
            if elapsed_time - heartbeat_time > heartbeat_interval:
                heartbeat_time = elapsed_time
                self._transport.send_heartbeat()

    def _process_packet(self, packet):
        code, packet_id, path, data = packet
        namespace = self.get_namespace(path)
        delegate = self._get_delegate(code)
        delegate(packet_id, data, namespace._find_event_callback)

    def get_namespace(self, path=''):
        try:
            return self._namespace_by_path[path]
        except KeyError:
            raise _PacketError('unexpected namespace path (%s)' % path)

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
            raise _PacketError('unexpected code (%s)' % code)

    def _on_disconnect(self, packet_id, data, find_event_callback):
        find_event_callback('disconnect')()

    def _on_connect(self, packet_id, data, find_event_callback):
        find_event_callback('connect')()

    def _on_heartbeat(self, packet_id, data, find_event_callback):
        find_event_callback('heartbeat')()

    def _on_message(self, packet_id, data, find_event_callback):
        args = [data]
        if packet_id:
            args.append(self._prepare_to_send_ack(packet_id))
        find_event_callback('message')(*args)

    def _on_json(self, packet_id, data, find_event_callback):
        args = [json.loads(data)]
        if packet_id:
            args.append(self._prepare_to_send_ack(packet_id))
        find_event_callback('message')(*args)

    def _on_event(self, packet_id, data, find_event_callback):
        value_by_name = json.loads(data)
        event = value_by_name['name']
        args = value_by_name.get('args', [])
        if packet_id:
            args.append(self._prepare_to_send_ack(packet_id))
        find_event_callback(event)(*args)

    def _on_ack(self, packet_id, data, find_event_callback):
        data_parts = data.split('+', 1)
        packet_id = data_parts[0]
        try:
            ack_callback = self._transport.get_ack_callback(packet_id)
        except KeyError:
            return
        args = json.loads(data_parts[1]) if len(data_parts) > 1 else []
        ack_callback(*args)

    def _on_error(self, packet_id, data, find_event_callback):
        reason, advice = data.split('+', 1)
        find_event_callback('error')(reason, advice)

    def _on_noop(self, packet_id, data, find_event_callback):
        find_event_callback('noop')()

    def _prepare_to_send_ack(self, packet_id):
        'Return function that acknowledges the server'
        return lambda *args: self._transport.ack(packet_id, *args)


class SocketIOError(Exception):
    pass


class _TimeoutError(Exception):
    pass


class _PacketError(SocketIOError):
    pass


class SocketIOConnectionError(SocketIOError):
    pass


class _AbstractTransport(object):

    def __init__(self):
        self._packet_id = 0
        self._callback_by_packet_id = {}

    def disconnect(self, path=''):
        if not self.connected:
            return
        if path:
            self.send_packet(0, path)
        else:
            self.connection.close()

    def connect(self, path):
        self.send_packet(1, path)

    def send_heartbeat(self):
        self.send_packet(2)

    def message(self, path, data, callback):
        if isinstance(data, basestring):
            code = 3
        else:
            code = 4
            data = json.dumps(data, ensure_ascii=False)
        self.send_packet(code, path, data, callback)

    def emit(self, path, event, args, callback):
        data = json.dumps(dict(name=event, args=args), ensure_ascii=False)
        self.send_packet(5, path, data, callback)

    def ack(self, packet_id, *args):
        packet_id = packet_id.rstrip('+')
        data = '%s+%s' % (
            packet_id,
            json.dumps(args, ensure_ascii=False),
        ) if args else packet_id
        self.send_packet(6, data=data)

    def noop(self):
        self.send_packet(8)

    def send_packet(self, code, path='', data='', callback=None):
        packet_id = self.set_ack_callback(callback) if callback else ''
        packet_parts = str(code), packet_id, path, data
        packet_text = ':'.join(packet_parts)
        self.send(packet_text)
        _log.debug('[packet sent] %s', packet_text)

    def recv_packet(self):
        code, packet_id, path, data = None, None, None, None
        packet_text = self.recv()
        _log.debug('[packet received] %s', packet_text)
        try:
            packet_parts = packet_text.split(':', 3)
        except AttributeError:
            raise _PacketError('invalid packet (%s)' % packet_text)
        packet_count = len(packet_parts)
        if 4 == packet_count:
            code, packet_id, path, data = packet_parts
        elif 3 == packet_count:
            code, packet_id, path = packet_parts
        elif 1 == packet_count:
            code = packet_parts[0]
        return code, packet_id, path, data

    def set_ack_callback(self, callback):
        'Set callback to be called after server sends an acknowledgment'
        self._packet_id += 1
        self._callback_by_packet_id[str(self._packet_id)] = callback
        return '%s+' % self._packet_id

    def get_ack_callback(self, packet_id):
        'Get callback to be called after server sends an acknowledgment'
        callback = self._callback_by_packet_id[packet_id]
        del self._callback_by_packet_id[packet_id]
        return callback

    @property
    def has_ack_callback(self):
        return True if self._callback_by_packet_id else False


class _WebsocketTransport(_AbstractTransport):

    def __init__(self, session, secure, base_url, **kw):
        super(_WebsocketTransport, self).__init__()
        url = '%s://%s/websocket/%s' % (
            'wss' if secure else 'ws',
            base_url, session.id)
        _log.debug('[transport selected] %s', url)
        try:
            self.connection = websocket.create_connection(url)
        except socket.timeout as error:
            raise SocketIOConnectionError(error)
        except socket.error as error:
            raise SocketIOConnectionError(error)
        self.connection.settimeout(1)

    @property
    def connected(self):
        return self.connection.connected

    def recv(self):
        try:
            return self.connection.recv()
        except socket.timeout:
            raise _TimeoutError
        except socket.error as error:
            raise SocketIOConnectionError(error)
        except websocket.WebSocketConnectionClosedException:
            raise SocketIOConnectionError('server closed connection')

    def send(self, packet_text):
        try:
            self.connection.send(packet_text)
        except socket.error:
            raise SocketIOConnectionError('could not send %s' % packet_text)


def find_callback(args, kw=None):
    'Return callback whether passed as a last argument or as a keyword'
    if args and callable(args[-1]):
        return args[-1], args[:-1]
    try:
        return kw['callback'], args
    except (KeyError, TypeError):
        return None, args


def _yield_warning_screen(seconds=None, sleep=0):
    last_warning = None
    for elapsed_time in _yield_elapsed_time(seconds):
        try:
            yield elapsed_time
        except Exception as warning:
            warning = str(warning)
            if last_warning != warning:
                last_warning = warning
                _log.warn(warning)
            time.sleep(sleep)


def _yield_elapsed_time(seconds=None):
    if seconds is None:
        while True:
            yield float('inf')
    start_time = time.time()
    while time.time() - start_time < seconds:
        yield time.time() - start_time


def _get_session(secure, base_url, **kw):
    server_url = '%s://%s/' % ('https' if secure else 'http', base_url)
    try:
        response = requests.get(server_url, **kw)
    except requests.exceptions.ConnectionError:
        raise SocketIOConnectionError('could not start connection')
    status = response.status_code
    if 200 != status:
        raise SocketIOConnectionError('unexpected status code (%s)' % status)
    response_parts = response.text.split(':')
    return _Session(
        id=response_parts[0],
        heartbeat_timeout=int(response_parts[1]),
        server_supported_transports=response_parts[3].split(','))


def _negotiate_transport(
        client_supported_transports, session,
        secure, base_url, **kw):
    server_supported_transports = session.server_supported_transports
    for supported_transport in client_supported_transports:
        if supported_transport in server_supported_transports:
            return {
                'websocket': _WebsocketTransport,
                # 'xhr-polling':
                # 'jsonp-polling':
            }[supported_transport](session, secure, base_url, **kw)
    raise SocketIOError(' '.join([
        'could not negotiate a transport:',
        'client supports %s but' % ', '.join(client_supported_transports),
        'server supports %s' % ', '.join(server_supported_transports),
    ]))


if __name__ == '__main__':
    requests_log = logging.getLogger('requests')
    requests_log.setLevel(logging.WARNING)
    logging.basicConfig(level=logging.DEBUG)
    socketIO = SocketIO('localhost', 8000)
    socketIO.emit('aaa')
    socketIO.wait()
