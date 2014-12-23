from collections import namedtuple
import copy
import logging
import json
import multiprocessing
import parser
from parser import Message, Packet, MessageType, PacketType
import requests
import time

try:
    from urllib import parse as parse_url
except ImportError:
    from urlparse import urlparse as parse_url

from .exceptions import ConnectionError, TimeoutError, PacketError
from .transports import _get_response


_SocketIOSession = namedtuple('_SocketIOSession', [
    'id',
    'heartbeat_interval',
    'connection_timeout',
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

        if callback is not None:
            _log.warn("Callback was specified but is not supported.");

        self._transport.emit(self.path, event, args, None)

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
            wait_for_connection=True, **kw):
        self.is_secure, self.base_url = _parse_host(host, port)
        self.wait_for_connection = wait_for_connection
        self._namespace_by_path = {}
        self.kw = kw
        # These two fields work to control the heartbeat thread.
        self.heartbeat_terminator = None;
        self.heartbeat_thread = None;
        # Saved session information.
        self.session = None;
        # This is stores the set of paths (namespaces) that need to be
        # reconnected to.
        self.reconnect_paths = {};
        # This sets of a chain of events that attempts to connect to
        # the server at the base namespace.
        self.define(Namespace)

    def __enter__(self):
        return self

    def __exit__(self, *exception_pack):
        self.disconnect()
        self._terminate_heartbeat();

    def __del__(self):
        self.disconnect()
        self._terminate_heartbeat();

    def _terminate_heartbeat(self):
        if self.heartbeat_terminator is not None:
            self.heartbeat_terminator.set();
            #time.sleep(self.session.heartbeat_interval);
            self.heartbeat_thread.join();

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

    def reconnect(self):
        """Reconnects to a set of namespaces.

        """
        for path in self.reconnect_paths:
            # We avoid reconnecting to the default namespace because
            # socketIO_client connects to that already.
            if (len(self.reconnect_paths) > 1 and path is ''):
                continue;
            _log.debug("Reconnecting to path: %s" % repr(path))
            self._transport.connect(path);
        self.reconnect_paths = {};

    def wait(self, seconds=None, for_callbacks=False):
        """Wait in a loop and process events as defined in the namespaces.

        - Omit seconds, i.e. call wait() without arguments, to wait forever.
        """
        warning_screen = _yield_warning_screen(seconds)
        for elapsed_time in warning_screen:
            try:
                try:
                    self._process_events()
                except TimeoutError:
                    pass
                if self._stop_waiting(for_callbacks):
                    break

                # We will end up here in the case that we
                # disconnected, then reconnected AND we were
                # successful.
                if len(self.reconnect_paths) > 0:
                    self.reconnect();
            except ConnectionError as e:
                try:
                    # This is where we end up if the connection was
                    # severed. The client will disconnect here.
                    if len(self.reconnect_paths) is 0:
                        self.reconnect_paths = copy.deepcopy(self._namespace_by_path);

                    self._terminate_heartbeat();

                    warning = Exception('[connection error] %s' % e)
                    self._transport._connected = False;
                    warning_screen.throw(warning)
                except StopIteration:
                    _log.warn(warning)
                self.disconnect()
        _log.debug("[wait canceled]");

    def _process_events(self):
        for packet in self._transport.recv_packet():
            try:
                self._process_packet(packet)
            except PacketError as e:
                _log.warn('[packet error] %s', e)

    def _process_packet(self, packet):
        code, packet_id, path, data, p = packet
        namespace = self.get_namespace(path)
        delegate = None;
        try:
            delegate = self._get_delegate(code)
        except:
            pass;
        if delegate is not None:
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

    def _upgrade(self):
        websocket = transports.WebsocketTransport(self.session, self.is_secure, self.base_url, **self.kw);
        websocket.send_packet(PacketType.PING, "", "probe");
        for packet in websocket.recv_packet():
            _log.debug("[websocket] Packet: %s" % str(packet));
            (code, packet_id, path, data, p) = packet;            
            if code == PacketType.PONG:
                packet = p;
                _log.debug("[PONG] %s" % repr(packet));

                self.heartbeat_terminator.set();

                # Technically we would need to pause the current
                # transport (which should be polling in this
                # implementation), but since we haven't actually
                # started a polling yet, we can upgrade without that.
                _log.debug("[upgrading] Sending upgrade request");
                websocket.send_packet(PacketType.UPGRADE);
                self._start_heartbeat(websocket);
                return websocket;

    def _start_heartbeat(self, transport):
        _log.debug("[start heartbeat pacemaker]");
        self.heartbeat_terminator = multiprocessing.Event();
        self.heartbeat_thread = multiprocessing.Process(
            target = _make_heartbeat_pacemaker, 
            args = (self.heartbeat_terminator, transport, self.session.heartbeat_interval / 2));
        self.heartbeat_thread.start(); 

    def _get_transport(self):
        self.session = _get_socketIO_session(self.is_secure, self.base_url, **self.kw);

        # Negotiate initial transport
        transport = transports.XHR_PollingTransport(self.session, self.is_secure, self.base_url, **self.kw);
        # Update namespaces
        for path, namespace in self._namespace_by_path.items():
            namespace._transport = transport
            transport.connect(path)
            
        transport.set_timeout(self.session.connection_timeout);

        # Start the heartbeat pacemaker (PING).
        self._start_heartbeat(transport);

        # If websocket is available, upgrade to it immediately.
        # TODO(sean): We could run this on a separate thread for
        # maximum efficiency although that would require some
        # synchronization to ensure buffers are flushed, etc.
        if "websocket" in self.session.server_supported_transports:
            try:
                return self._upgrade();
            except:
                pass;

        return transport

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
        code, packet_id, path, data, p = packet
        packet = p;


        # Accoding to the documentation
        # (https://github.com/automattic/socket.io-protocol#event),
        # the event name is the first entry in the message array, and
        # the arguments are the rest of the entries.
        event = packet.payload.message[0];
        args = packet.payload.message[1:] if len(packet.payload.message) > 1 else [];

        _log.debug("[event] %s (%s)" % (repr(event), repr(args)));

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
    url_pack = parse_url(host)
    is_secure = url_pack.scheme == 'https'
    port = port or url_pack.port or (443 if is_secure else 80)
    base_url = '%s:%d%s/socket.io' % (url_pack.hostname, port, url_pack.path)
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
    server_url = '%s://%s/?EIO=%d&transport=polling' \
                 % ('https' if is_secure else 'http', base_url, parser.ENGINE_PROTOCOL)
    _log.debug('[session] %s', server_url)
    try:
        response = _get_response(requests.get, server_url, **kw)
    except TimeoutError as e:
        raise ConnectionError(e)

    _log.debug("[response] %s", response.text);
    for packet in parser.decode_response(response):
        _log.debug("[decoded] %s", str(packet));
        if packet.type is not parser.PacketType.OPEN:
            _log.warn("Got unexpected packet during connection handshake: %d" % packet.type);
            return None;

    handshake = json.loads(packet.payload);

    return _SocketIOSession(
        id = handshake["sid"],
        heartbeat_interval = int(handshake["pingInterval"]) / 1000,
        connection_timeout = int(handshake["pingTimeout"]) / 1000,
        server_supported_transports = handshake["upgrades"]);

def _make_heartbeat_pacemaker(terminator, transport, heartbeat_interval):
    while True:
        if terminator.wait(heartbeat_interval):
            break;
        _log.debug("[hearbeat]");
        try:
            transport.send_heartbeat();
        except:
            pass;
    _log.debug("[heartbeat terminated]");
