import json
import logging
import requests
import threading
import time
from collections import namedtuple

from .compat import get_byte, get_character, get_unicode
from .exceptions import PacketError, TimeoutError
from .transports import _get_response


__version__ = '0.6.1'
_log = logging.getLogger(__name__)
EngineIOData = namedtuple('EngineIOData', ['data'])
SocketIOData = namedtuple('SocketIOData', ['path', 'ack_id', 'event', 'args'])
TRANSPORTS = []
RETRY_INTERVAL_IN_SECONDS = 1


class EngineIONamespace(object):
    'Define engine.io client behavior'

    def __init__(self, io):
        self._io = io
        self._callback_by_event = {}
        self.initialize()

    def initialize(self):
        'Initialize custom variables here; you can override this method'
        pass

    def on_event(self, event, *args):
        """
        Called after server sends an event; you can override this method.
        Called only if a custom event handler does not exist,
        such as one defined by namespace.on('my_event', my_function).
        """
        callback, args = find_callback(args)
        if callback:
            callback(*args)

    def _find_packet_callback(self, event):
        # Check callbacks defined by on()
        try:
            return self._callback_by_event[event]
        except KeyError:
            pass
        # Check callbacks defined explicitly or use on_event()
        return getattr(
            self, 'on_' + event.replace(' ', '_'),
            lambda *args: self.on_event(event, *args))


class SocketIONamespace(EngineIONamespace):
    'Define socket.io client behavior'

    def __init__(self, io, path):
        self.path = path
        super(SocketIONamespace, self).__init__(io)

    def on_connect(self):
        'Called after server connects; you can override this method'

    def on_reconnect(self):
        'Called after server reconnects; you can override this method'

    def on_disconnect(self):
        'Called after server disconnects; you can override this method'

    def _find_packet_callback(self, event):
        # Interpret events
        if event == 'connect':
            if not hasattr(self, '_was_connected'):
                self._was_connected = True
            else:
                event = 'reconnect'
        return super(SocketIONamespace, self)._find_packet_callback(event)


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

    _engineIO_protocol = 3
    _engineIO_request_index = 0

    def __init__(
            self,
            host, port=None, Namespace=None,
            wait_for_connection=True, transports=TRANSPORTS,
            resource='engine.io', **kw):
        self._url = 'http://%s:%s/%s/' % (host, port, resource)
        self._http_session = requests.Session()
        print(self._url)

        response = self._http_session.get(self._url, params={
            'EIO': self._engineIO_protocol,
            'transport': 'polling',
            't': self._get_timestamp(),
        })
        print(response.url)

        engineIO_packets = _decode_content(response.content)
        engineIO_packet_type, engineIO_packet_data = engineIO_packets[0]
        assert engineIO_packet_type == 0
        value_by_name = json.loads(get_unicode(engineIO_packet_data))
        print(value_by_name)
        # value_by_name['upgrades']
        self._ping_interval = value_by_name['pingInterval'] / float(1000)
        self._ping_timeout = value_by_name['pingTimeout'] / float(1000)
        self._session_id = value_by_name['sid']

        if Namespace:
            self.define(Namespace)

        self._heartbeat_thread = HeartbeatThread(
            send_heartbeat=self._ping,
            relax_interval_in_seconds=self._ping_interval,
            hurry_interval_in_seconds=1)
        self._heartbeat_thread.start()

    def define(self, Namespace):
        self._namespace = namespace = Namespace(self)
        return namespace

    def get_namespace(self):
        try:
            return self._namespace
        except AttributeError:
            raise PacketError('undefined engine.io namespace')

    def wait(self, seconds=None):
        self._heartbeat_thread.hurry()
        warning_screen = _yield_warning_screen(seconds)
        for elapsed_time in warning_screen:
            try:
                self._process_packets()
            except TimeoutError:
                pass
        self._heartbeat_thread.relax()

    def _process_packets(self):
        for engineIO_packet in self._recv_packet():
            try:
                self._process_packet(engineIO_packet)
            except PacketError as e:
                self._log(logging.WARNING, '[packet error] %s', e)

    def _process_packet(self, packet):
        engineIO_packet_type, engineIO_packet_data = packet
        print('engineIO_packet_type = %s' % engineIO_packet_type)
        engineIO_packet_data_parsed = _parse_engineIO_data(
            engineIO_packet_data)
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
        delegate(engineIO_packet_data_parsed, namespace._find_packet_callback)
        if engineIO_packet_type is 4:
            return engineIO_packet_data

    def _on_open(self, data_parsed, find_packet_callback):
        pass

    def _on_close(self, data_parsed, find_packet_callback):
        pass

    def _on_ping(self, data_parsed, find_packet_callback):
        pass

    def _on_pong(self, data_parsed, find_packet_callback):
        pass

    def _on_message(self, data_parsed, find_packet_callback):
        pass

    def _on_upgrade(self, data_parsed, find_packet_callback):
        pass

    def _on_noop(self, data_parsed, find_packet_callback):
        pass

    def _get_timestamp(self):
        timestamp = '%s-%s' % (
            int(time.time() * 1000), self._engineIO_request_index)
        self._engineIO_request_index += 1
        return timestamp

    def _message(self, engineIO_packet_data):
        engineIO_packet_type = 4
        response = self._http_session.post(self._url, params={
            'EIO': self._engineIO_protocol,
            'transport': 'polling',
            't': self._get_timestamp(),
            'sid': self._session_id,
        }, data=_encode_content([
            (engineIO_packet_type, engineIO_packet_data),
        ]), headers={
            'content-type': 'application/octet-stream',
        })
        print('message()')
        engineIO_packets = _decode_content(response.content)
        for engineIO_packet_type, engineIO_packet_data in engineIO_packets:
            socketIO_packet_type = int(get_character(engineIO_packet_data, 0))
            socketIO_packet_data = engineIO_packet_data[1:]
            print('engineIO_packet_type = %s' % engineIO_packet_type)
            print('socketIO_packet_type = %s' % socketIO_packet_type)
            print('socketIO_packet_data = %s' % socketIO_packet_data)

    def _ping(self):
        engineIO_packet_type = 2
        engineIO_packet_data = ''
        response = self._http_session.post(self._url, params={
            'EIO': self._engineIO_protocol,
            'transport': 'polling',
            't': self._get_timestamp(),
            'sid': self._session_id,
        }, data=_encode_content([
            (engineIO_packet_type, engineIO_packet_data),
        ]), headers={
            'content-type': 'application/octet-stream',
        })
        print('ping()')
        engineIO_packets = _decode_content(response.content)
        for engineIO_packet_type, engineIO_packet_data in engineIO_packets:
            socketIO_packet_type = int(get_character(engineIO_packet_data, 0))
            socketIO_packet_data = engineIO_packet_data[1:]
            print('engineIO_packet_type = %s' % engineIO_packet_type)
            print('socketIO_packet_type = %s' % socketIO_packet_type)
            print('socketIO_packet_data = %s' % socketIO_packet_data)

    def _recv_packet(self):
        response = _get_response(
            self._http_session.get,
            self._url,
            params={
                'EIO': self._engineIO_protocol,
                'transport': 'polling',
                't': self._get_timestamp(),
                'sid': self._session_id,
            },
            timeout=self._ping_timeout)
        for engineIO_packet in _decode_content(response.content):
            yield engineIO_packet

    def _log(self, level, msg, *attrs):
        _log.log(level, '%s: %s' % (self._url, msg), *attrs)


class SocketIO(EngineIO):

    def __init__(
            self,
            host, port=None, Namespace=None,
            wait_for_connection=True, transports=TRANSPORTS,
            resource='socket.io', **kw):
        self._namespace_by_path = {}
        super(SocketIO, self).__init__(
            host, port, Namespace,
            wait_for_connection, transports,
            resource, **kw)

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

    def emit(self, event, *args, **kw):
        socketIO_packet_type = 2
        socketIO_packet_data = json.dumps([event])
        self._message(str(socketIO_packet_type) + socketIO_packet_data)

    def on(self, event, callback):
        pass

    def _process_packet(self, packet):
        engineIO_packet_data = super(SocketIO, self)._process_packet(packet)
        if engineIO_packet_data is None:
            return
        socketIO_packet_type = int(get_character(engineIO_packet_data, 0))
        socketIO_packet_data = engineIO_packet_data[1:]
        print('socketIO_packet_type = %s' % socketIO_packet_type)
        socketIO_packet_data_parsed = _parse_socketIO_data(
            socketIO_packet_data)
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
        delegate(socketIO_packet_data_parsed, namespace._find_packet_callback)
        return socketIO_packet_data

    def _on_connect(self, data_parsed, find_packet_callback):
        find_packet_callback('connect')()

    def _on_disconnect(self, data_parsed, find_packet_callback):
        find_packet_callback('disconnect')()

    def _on_event(self, data_parsed, find_packet_callback):
        args = data_parsed.args
        if data_parsed.ack_id:
            args.append(self._prepare_to_send_ack(
                data_parsed.path, data_parsed.ack_id))
        find_packet_callback(data_parsed.event)(*args)

    def _on_ack(self, data_parsed, find_packet_callback):
        pass

    def _on_error(self, data_parsed, find_packet_callback):
        pass

    def _on_binary_event(self, data_parsed, find_packet_callback):
        pass

    def _on_binary_ack(self, data_parsed, find_packet_callback):
        pass

    def _prepare_to_send_ack(self, path, ack_id):
        'Return function that acknowledges the server'
        return lambda *args: self._ack(path, ack_id, *args)


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
        while not self._stop.is_set():
            self._send_heartbeat()
            if self._adrenaline.is_set():
                interval_in_seconds = self._hurry_interval_in_seconds
            else:
                interval_in_seconds = self._relax_interval_in_seconds
            self._rest.wait(interval_in_seconds)

    def relax(self):
        self._adrenaline.clear()

    def hurry(self):
        self._adrenaline.set()

    def stop(self):
        self._stop.set()


def find_callback(args, kw=None):
    'Return callback whether passed as a last argument or as a keyword'
    if args and callable(args[-1]):
        return args[-1], args[:-1]
    try:
        return kw['callback'], args
    except (KeyError, TypeError):
        return None, args


def _decode_content(content):
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


def _encode_content(packets):
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


def _parse_engineIO_data(data):
    return EngineIOData(data=get_unicode(data))


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
    if data:
        x = json.loads(data)
        event = x[0]
        args = x[1:]
    else:
        event = ''
        args = []
    return SocketIOData(path=path, ack_id=ack_id, event=event, args=args)


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
