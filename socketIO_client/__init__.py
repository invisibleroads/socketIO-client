import json
import logging
import requests
import threading
import time
from collections import namedtuple

from . import transports
from .compat import get_byte, get_character, get_unicode, parse_url
from .exceptions import ConnectionError, TimeoutError, PacketError


__version__ = '0.6.1'
_log = logging.getLogger(__name__)
SocketIOData = namedtuple('SocketIOData', ['path', 'ack_id', 'args'])
TRANSPORTS = []
RETRY_INTERVAL_IN_SECONDS = 1


class EngineIONamespace(object):
    'Define engine.io client behavior'

    def __init__(self, io):
        self._io = io
        self._callback_by_event = {}
        self.initialize()

    def initialize(self):
        """Initialize custom variables here.
        You can override this method."""

    def on(self, event, callback):
        'Define a callback to handle an event emitted by the server'
        self._callback_by_event[event] = callback

    def on_open(self):
        """Called after engine.io connects.
        You can override this method."""

    def on_close(self):
        """Called after engine.io disconnects.
        You can override this method."""

    def on_ping(self, data):
        """Called after engine.io sends a ping packet.
        You can override this method."""

    def on_pong(self, data):
        """Called after engine.io sends a pong packet.
        You can override this method."""

    def on_message(self, data):
        """Called after engine.io sends a message packet.
        You can override this method."""

    def on_upgrade(self):
        """Called after engine.io sends an upgrade packet.
        You can override this method."""

    def on_noop(self):
        """Called after engine.io sends a noop packet.
        You can override this method."""

    def _find_packet_callback(self, event):
        # Check callbacks defined by on()
        try:
            return self._callback_by_event[event]
        except KeyError:
            pass
        # Check callbacks defined explicitly
        return getattr(self, 'on_' + event)


class SocketIONamespace(EngineIONamespace):
    'Define socket.io client behavior'

    def __init__(self, io, path):
        self.path = path
        super(SocketIONamespace, self).__init__(io)

    def on_connect(self):
        """Called after socket.io connects.
        You can override this method."""

    def on_reconnect(self):
        """Called after socket.io reconnects.
        You can override this method."""

    def on_disconnect(self):
        """Called after socket.io disconnects.
        You can override this method."""

    def on_event(self, event, *args):
        """
        Called if there is no matching event handler.
        You can override this method.
        There are three ways to define an event handler:

        - Call socketIO.on()

            socketIO = SocketIO('localhost', 8000)
            socketIO.on('my_event', my_function)

        - Call namespace.on()

            namespace = socketIO.get_namespace()
            namespace.on('my_event', my_function)

        - Define namespace.on_xxx

            class Namespace(SocketIONamespace):

                def on_my_event(self, *args):
                    my_function(*args)

            socketIO.define(Namespace)"""

    def on_error(self, data):
        """Called after socket.io sends an error packet.
        You can override this method."""

    def _find_packet_callback(self, event):
        # Interpret events
        if event == 'connect':
            if not hasattr(self, '_was_connected'):
                self._was_connected = True
            else:
                event = 'reconnect'
        # Check callbacks defined by on()
        try:
            return self._callback_by_event[event]
        except KeyError:
            pass
        # Check callbacks defined explicitly or use on_event()
        return getattr(
            self, 'on_' + event.replace(' ', '_'),
            lambda *args: self.on_event(event, *args))


class LoggingMixin(object):

    def _log(self, level, msg, *attrs):
        _log.log(level, '%s: %s' % (self._io._url, msg), *attrs)


class LoggingEngineIONamespace(EngineIONamespace, LoggingMixin):

    def on_event(self, event, *args):
        callback, args = find_callback(args)
        arguments = [repr(_) for _ in args]
        if callback:
            arguments.append('callback(*args)')
        self._log(
            logging.INFO, '[event] %s(%s)',
            event, ', '.join(arguments))
        super(LoggingEngineIONamespace, self).on_event(event, *args)


class LoggingSocketIONamespace(SocketIONamespace, LoggingMixin):

    def on_event(self, event, *args):
        callback, args = find_callback(args)
        arguments = [repr(_) for _ in args]
        if callback:
            arguments.append('callback(*args)')
        self._log(
            logging.INFO, '%s [event] %s(%s)', self.path,
            event, ', '.join(arguments))
        super(LoggingSocketIONamespace, self).on_event(event, *args)

    def on_connect(self):
        self._log(logging.DEBUG, '%s [connect]', self.path)
        super(LoggingSocketIONamespace, self).on_connect()

    def on_reconnect(self):
        self._log(logging.DEBUG, '%s [reconnect]', self.path)
        super(LoggingSocketIONamespace, self).on_reconnect()

    def on_disconnect(self):
        self._log(logging.DEBUG, '%s [disconnect]', self.path)
        super(LoggingSocketIONamespace, self).on_disconnect()


class EngineIO(object):

    _engineIO_request_index = 0

    def __init__(
            self,
            host, port=None, Namespace=None,
            wait_for_connection=True, transports=TRANSPORTS,
            resource='engine.io', **kw):
        self._is_secure, self._url = _parse_host(host, port, resource)
        self._wait_for_connection = wait_for_connection
        self._client_transports = transports
        self._kw = kw
        self._http_session = requests.Session()
        if Namespace:
            self.define(Namespace)

    def __enter__(self):
        return self

    def __exit__(self, *exception_pack):
        self.close()

    def __del__(self):
        self.close()

    @property
    def connected(self):
        try:
            transport = self.__transport
        except AttributeError:
            return False
        else:
            return transport.connected

    def on(self, event, callback):
        try:
            namespace = self.get_namespace()
        except PacketError:
            namespace = self.define(EngineIONamespace)
        return namespace.on(event, callback)

    def define(self, Namespace):
        self._namespace = namespace = Namespace(self)
        return namespace

    def get_namespace(self):
        try:
            return self._namespace
        except AttributeError:
            raise PacketError('undefined engine.io namespace')

    def wait(self, seconds=None, **kw):
        'Wait in a loop and react to events as defined in the namespaces'
        self._heartbeat_thread.hurry()
        warning_screen = _yield_warning_screen(seconds)
        for elapsed_time in warning_screen:
            if self._should_stop_waiting(**kw):
                break
            try:
                try:
                    self._process_packets()
                except TimeoutError:
                    pass
            except ConnectionError as e:
                try:
                    warning = Exception('[connection error] %s' % e)
                    warning_screen.throw(warning)
                except StopIteration:
                    self._log(logging.WARNING, warning)
                try:
                    namespace = self.get_namespace()
                    namespace.on_disconnect()
                except PacketError:
                    pass
        self._heartbeat_thread.relax()

    def _should_stop_waiting(self):
        # Use __transport to make sure that we do not reconnect inadvertently
        return self.__transport._wants_to_disconnect

    def _process_packets(self):
        for engineIO_packet in self._transport.recv_packet():
            try:
                self._process_packet(engineIO_packet)
            except PacketError as e:
                self._log(logging.WARNING, '[packet error] %s', e)

    def _process_packet(self, packet):
        engineIO_packet_type, engineIO_packet_data = packet
        print('engineIO_packet_type = %s' % engineIO_packet_type)
        # Launch callbacks
        namespace = self.get_namespace()
        try:
            delegate = {
                0: self._on_open,
                1: self._on_close,
                2: self._on_ping,
                3: self._on_pong,
                4: self._on_message,
                5: self._on_upgrade,
                6: self._on_noop,
            }[engineIO_packet_type]
        except KeyError:
            raise PacketError(
                'unexpected engine.io packet type (%s)' % engineIO_packet_type)
        delegate(engineIO_packet_data, namespace._find_packet_callback)
        if engineIO_packet_type is 4:
            return engineIO_packet_data

    def _on_open(self, data, find_packet_callback):
        find_packet_callback('open')()

    def _on_close(self, data, find_packet_callback):
        find_packet_callback('close')()

    def _on_ping(self, data, find_packet_callback):
        self._pong(data)
        find_packet_callback('ping')(data)

    def _on_pong(self, data, find_packet_callback):
        find_packet_callback('pong')(data)

    def _on_message(self, data, find_packet_callback):
        find_packet_callback('message')(data)

    def _on_upgrade(self, data, find_packet_callback):
        find_packet_callback('upgrade')()

    def _on_noop(self, data, find_packet_callback):
        find_packet_callback('noop')()

    def _get_timestamp(self):
        timestamp = '%s-%s' % (
            int(time.time() * 1000), self._engineIO_request_index)
        self._engineIO_request_index += 1
        return timestamp

    def _message(self, engineIO_packet_data):
        engineIO_packet_type = 4
        self._transport.send_packet(engineIO_packet_type, engineIO_packet_data)

    def _ping(self, engineIO_packet_data=''):
        engineIO_packet_type = 2
        self._transport.send_packet(engineIO_packet_type, engineIO_packet_data)

    def _pong(self, engineIO_packet_data=''):
        engineIO_packet_type = 3
        self._transport.send_packet(engineIO_packet_type, engineIO_packet_data)

    @property
    def _transport(self):
        try:
            if self.connected:
                return self.__transport
        except AttributeError:
            pass
        self._get_engineIO_session()
        self._negotiate_transport()
        self._reset_heartbeat()
        self._connect_namespaces()
        return self.__transport

    def _get_engineIO_session(self):
        url = '%s://%s/' % ('https' if self.is_secure else 'http', self._url)
        warning_screen = _yield_warning_screen()
        for elapsed_time in warning_screen:
            try:
                engineIO_packet_type, engineIO_packet_data = next(
                    XHR_PollingTransport().recv_packet())

                response = _get_response(self._http_session.get, url, params={
                    'EIO': self._engineIO_protocol,
                    'transport': 'polling',
                    't': self._get_timestamp(),
                }, **self._kw)
            except (TimeoutError, ConnectionError) as e:
                if not self._wait_for_connection:
                    raise
                warning = Exception('[waiting for connection] %s' % e)
                warning_screen.throw(warning)
        engineIO_packets = _decode_engineIO_content(response.content)
        engineIO_packet_type, engineIO_packet_data = engineIO_packets[0]
        assert engineIO_packet_type == 0
        value_by_name = json.loads(get_unicode(engineIO_packet_data))
        self._session_id = value_by_name['sid']
        self._ping_interval = value_by_name['pingInterval'] / float(1000)
        self._ping_timeout = value_by_name['pingTimeout'] / float(1000)
        self._transport_upgrades = value_by_name['upgrades']

    def _negotiate_transport(self):
        self.__transport = self._get_transport('xhr-polling')

    def _reset_heartbeat(self):
        try:
            self._heartbeat_thread.stop()
        except AttributeError:
            pass
        self._heartbeat_thread = HeartbeatThread(
            send_heartbeat=self.__transport._ping,
            relax_interval_in_seconds=self._ping_interval,
            hurry_interval_in_seconds=1)
        self._heartbeat_thread.start()

    def _connect_namespaces(self):
        pass

    def _get_transport(self, transport_name):
        self._log(logging.DEBUG, '[transport chosen] %s', transport_name)
        return {
            'xhr-polling': transports.XHR_PollingTransport,
        }[transport_name]()

    def _log(self, level, msg, *attrs):
        _log.log(level, '%s: %s' % (self._url, msg), *attrs)


class SocketIO(EngineIO):
    """Create a socket.io client that connects to a socket.io server
    at the specified host and port.

    - Define the behavior of the client by specifying a custom Namespace.
    - Prefix host with https:// to use SSL.
    - Set wait_for_connection=True to block until we have a connection.
    - Specify desired transports=['websocket', 'xhr-polling'].
    - Pass query params, headers, cookies, proxies as keyword arguments.

    SocketIO(
        'localhost', 8000,
        params={'q': 'qqq'},
        headers={'Authorization': 'Basic ' + b64encode('username:password')},
        cookies={'a': 'aaa'},
        proxies={'https': 'https://proxy.example.com:8080'})
    """

    def __init__(
            self,
            host, port=None, Namespace=None,
            wait_for_connection=True, transports=TRANSPORTS,
            resource='socket.io', **kw):
        self._namespace_by_path = {}
        self._callback_by_ack_id = {}
        self._ack_id = 0
        super(SocketIO, self).__init__(
            host, port, Namespace,
            wait_for_connection, transports,
            resource, **kw)

    def __exit__(self, *exception_pack):
        self.disconnect()
        super(SocketIO, self).__exit__(*exception_pack)

    def __del__(self):
        self.disconnect()
        super(SocketIO, self).__del__()

    def on(self, event, callback, path=''):
        try:
            namespace = self.get_namespace(path)
        except PacketError:
            namespace = self.define(SocketIONamespace, path)
        return namespace.on(event, callback)

    def define(self, Namespace, path=''):
        if path:
            self._connect(path)
        self._namespace_by_path[path] = namespace = Namespace(self, path)
        return namespace

    def get_namespace(self, path=''):
        try:
            return self._namespace_by_path[path]
        except KeyError:
            raise PacketError('undefined socket.io namespace (%s)' % path)

    def wait(self, seconds=None, for_callbacks=False):
        super(SocketIO, self).wait(seconds, for_callbacks=for_callbacks)

    def wait_for_callbacks(self, seconds=None):
        self.wait(seconds, for_callbacks=True)

    def _should_stop_waiting(self, for_callbacks):
        # Use __transport to make sure that we do not reconnect inadvertently
        if for_callbacks and not self.__transport.has_ack_callback:
            return True
        return super(SocketIO, self)._should_stop_waiting()

    def emit(self, event, *args, **kw):
        path = kw.get('path', '')
        callback, args = find_callback(args, kw)
        self._emit(path, event, args, callback)

    def _emit(self, path, event, args, callback):
        socketIO_packet_type = 2

        socketIO_packet_data = json.dumps([event] + list(args))
        if callback:
            ack_id = self._set_ack_callback(callback) if callback else ''
            socketIO_packet_data = str(ack_id) + socketIO_packet_data
        if path:
            socketIO_packet_data = path + ',' + socketIO_packet_data

        self._message(str(socketIO_packet_type) + socketIO_packet_data)

    def _set_ack_callback(self, callback):
        self._ack_id += 1
        self._callback_by_ack_id[self._ack_id] = callback
        return self._ack_id

    def send(self, data='', callback=None):
        args = [data]
        if callback:
            args.append(callback)
        self.emit('message', *args)

    def _process_packet(self, packet):
        engineIO_packet_data = super(SocketIO, self)._process_packet(packet)
        if engineIO_packet_data is None:
            return
        socketIO_packet_type = int(get_character(engineIO_packet_data, 0))
        socketIO_packet_data = engineIO_packet_data[1:]
        print('socketIO_packet_type = %s' % socketIO_packet_type)
        # Launch callbacks
        namespace = self.get_namespace()
        try:
            delegate = {
                0: self._on_connect,
                1: self._on_disconnect,
                2: self._on_event,
                3: self._on_ack,
                4: self._on_error,
                5: self._on_binary_event,
                6: self._on_binary_ack,
            }[socketIO_packet_type]
        except KeyError:
            raise PacketError(
                'unexpected socket.io packet type (%s)' % socketIO_packet_type)
        delegate(socketIO_packet_data, namespace._find_packet_callback)
        return socketIO_packet_data

    def _on_connect(self, data, find_packet_callback):
        find_packet_callback('connect')()

    def _on_disconnect(self, data, find_packet_callback):
        find_packet_callback('disconnect')()

    def _on_event(self, data, find_packet_callback):
        data_parsed = _parse_socketIO_data(data)
        args = data_parsed.args
        try:
            event = args.pop(0)
        except IndexError:
            raise PacketError('missing event name')
        if data_parsed.ack_id:
            args.append(self._prepare_to_send_ack(
                data_parsed.path, data_parsed.ack_id))
        find_packet_callback(event)(*args)

    def _on_ack(self, data, find_packet_callback):
        data_parsed = _parse_socketIO_data(data)
        try:
            ack_callback = self._get_ack_callback(data_parsed.ack_id)
        except KeyError:
            return
        ack_callback(*data_parsed.args)

    def _get_ack_callback(self, ack_id):
        return self._callback_by_ack_id.pop(ack_id)

    def _on_error(self, data, find_packet_callback):
        find_packet_callback('error')(data)

    def _on_binary_event(self, data, find_packet_callback):
        self._log(logging.WARNING, '[not implemented] binary event')

    def _on_binary_ack(self, data, find_packet_callback):
        self._log(logging.WARNING, '[not implemented] binary ack')

    def _prepare_to_send_ack(self, path, ack_id):
        'Return function that acknowledges the server'
        return lambda *args: self._ack(path, ack_id, *args)

    def _connect_namespaces(self):
        for path, namespace in self._namespace_by_path.items():
            namespace._transport = self.__transport
            if path:
                self.__transport.connect(path)


class HeartbeatThread(threading.Thread):

    daemon = True

    def __init__(
            self, send_heartbeat,
            relax_interval_in_seconds,
            hurry_interval_in_seconds):
        super(HeartbeatThread, self).__init__()
        self._send_heartbeat = send_heartbeat
        self._relax_interval_in_seconds = relax_interval_in_seconds
        self._hurry_interval_in_seconds = hurry_interval_in_seconds
        self._adrenaline = threading.Event()
        self._rest = threading.Event()
        self._stop = threading.Event()

    def run(self):
        try:
            while not self._stop.is_set():
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
            pass

    def relax(self):
        self._adrenaline.clear()

    def hurry(self):
        self._adrenaline.set()
        self._rest.set()
        self._rest.clear()

    def stop(self):
        self._rest.set()
        self._stop.set()


def find_callback(args, kw=None):
    'Return callback whether passed as a last argument or as a keyword'
    if args and callable(args[-1]):
        return args[-1], args[:-1]
    try:
        return kw['callback'], args
    except (KeyError, TypeError):
        return None, args


def _parse_host(host, port, resource):
    if not host.startswith('http'):
        host = 'http://' + host
    url_pack = parse_url(host)
    is_secure = url_pack.scheme == 'https'
    port = port or url_pack.port or (443 if is_secure else 80)
    url = '%s:%d%s/%s' % (url_pack.hostname, port, url_pack.path, resource)
    return is_secure, url


def _decode_engineIO_content(content):
    packets = []
    content_index = 0
    content_length = len(content)
    while content_index < content_length:
        try:
            content_index, packet_length = _read_packet_length(
                content, content_index)
        except IndexError:
            break
        content_index, packet_string = _read_packet_string(
            content, content_index, packet_length)
        packet_type = int(get_character(packet_string, 0))
        packet_data = packet_string[1:]
        packets.append((packet_type, packet_data))
    return packets


def _encode_engineIO_content(packets):
    parts = []
    for packet_type, packet_data in packets:
        packet_string = str(packet_type) + str(packet_data)
        parts.append(_make_packet_header(packet_string) + packet_string)
    return ''.join(parts)


def _read_packet_length(content, content_index):
    while get_byte(content, content_index) != 0:
        content_index += 1
    content_index += 1
    packet_length_string = ''
    byte = get_byte(content, content_index)
    while byte != 255:
        packet_length_string += str(byte)
        content_index += 1
        byte = get_byte(content, content_index)
    return content_index, int(packet_length_string)


def _read_packet_string(content, content_index, packet_length):
    while get_byte(content, content_index) == 255:
        content_index += 1
    packet_string = content[content_index:content_index + packet_length]
    return content_index + packet_length, packet_string


def _make_packet_header(packet_string):
    length_string = str(len(packet_string))
    header_digits = [0]
    for i in range(len(length_string)):
        header_digits.append(ord(length_string[i]) - 48)
    header_digits.append(255)
    return ''.join(chr(x) for x in header_digits)


def _parse_socketIO_data(data):
    data = get_unicode(data)
    if data.startswith('/'):
        try:
            path, data = data.split(',', 1)
        except ValueError:
            path = data
            data = ''
    else:
        path = ''
    try:
        ack_id = int(data[0])
        data = data[1:]
    except (ValueError, IndexError):
        ack_id = None
    try:
        args = json.loads(data)
    except ValueError:
        args = []
    return SocketIOData(path=path, ack_id=ack_id, args=args)


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
