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
RETRY_INTERVAL_IN_SECONDS = 1

class BaseNamespace(object):
    'Define client behavior'

    def __init__(self, client, path):
        self._client = client;
        self.path = path
        self._callback_by_event = {}
        self.initialize()

    def initialize(self):
        'Initialize custom variables here; you can override this method'
        pass

    def emit(self, event_name, *args, **kw):
        self._client.emit(event_name, path = self.path, *args, **kw)

    def disconnect(self):
        self._client.disconnect(self.path)

    def on(self, event, callback):
        'Define a callback to handle a custom event emitted by the server'
        self._callback_by_event[event] = callback

    def on_connect(self):
        'Called after server connects; you can override this method'
        _log.debug('%s [connect]', self.path)

    def on_disconnect(self):
        'Called after server disconnects; you can override this method'
        _log.debug('%s [disconnect]', self.path)

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

    def on_error(self, reason):
        'Called after server sends an error; you can override this method'
        _log.info('%s [error] %s', self.path, reason)

    def on_noop(self):
        'Called after server sends a noop; you can override this method'
        _log.info('%s [noop]', self.path)

    def on_ping(self):
        'Called after server sends a ping; you can override this method'
        _log.info('%s [ping]', self.path)

    def on_pong(self):
        'Called after server sends a pong; you can override this method'
        _log.info('%s [pong]', self.path)

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

class SocketIOEvent(object):
    def __init__(self, path, name, args, callback):
        self.path = path;
        self.name = name;
        self.args = args;
        self.callback = callback;

    def __str__(self):
        return str(self.path) + "/" + str(self.name) + "(" + str(self.args) + ")(" + str(self.callback) + ")";

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

        self.__transport = None;

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
        self._transport.connect("");

        # Events that fail to emit due to connection errors will be
        # placed in this 'queue' and re-sent automatically upon
        # reconnect.
        self._event_retry_queue = [];

    def __enter__(self):
        _log.debug("[enter]");
        return self

    def __exit__(self, *exception_pack):
        self.disconnect()
        self._terminate_heartbeat();

    def __del__(self):
        self.disconnect()
        self._terminate_heartbeat();

    def define(self, Namespace, path=''):
        _log.debug("[define] Path: %s" % path);
        namespace = Namespace(self, path)
        self._namespace_by_path[path] = namespace

        if path:
            try:
                self._transport.connect(path);
            except ConnectionError as e:
                _log.warn("[define] Connection error: %s" % str(e));
                self._handle_severed_connection();

        return namespace

    def on(self, event, callback, path=''):
        return self.get_namespace(path).on(event, callback)

    def _emit_event(self, event):
        """Emits an Emittable object.

        This function enables automatically re-emitting events that
        failed due to connection errors.

        """
        self._transport.emit(event.path, event.name, event.args, event.callback);

    def emit(self, event_name, *args, **kw):
        path = kw.get('path', '')
        callback, args = find_callback(args, kw)
        event = SocketIOEvent(path, event_name, args, callback);
        self._event_retry_queue.append(event);
        try:
            #import ipdb; ipdb.set_trace();
            self._emit_event(event);
            self._event_retry_queue.pop();
        except ConnectionError as e:
            _log.warn("[emit] Connection error: %s" % str(e));
            self._handle_severed_connection();

    def reconnect(self):
        """Reconnects the client.

        Reconnects to the server and connects to the previously
        connected set of namespaces.

        """
        _log.debug("  [reconnect attempt]");

        # Reconnect to the server.
        if self.__transport is not None:
            self.__transport.close();        
        self.__transport = None;

        # We call the _create_transport directly ahead of the loop
        # below so that self._tranport will not result in an infinite
        # loop.
        self._create_transport();

        for path in self.reconnect_paths:
            # We avoid reconnecting to the default namespace because
            # socketIO_client connects to that already.
            if (len(self.reconnect_paths) > 1 and path is ''):
                continue;
            _log.debug("Reconnecting to path: %s" % repr(path))
            self._transport.connect(path);
        # Restore paths.
        self._namespace_by_path = copy.copy(self.reconnect_paths);
        self.reconnect_paths = {};

        # Send any pending events.
        for event in self._event_retry_queue:
            _log.debug("[reconnect] Re-emitting event: %s" % str(event));
            self._emit_event(event);

    def _handle_severed_connection(self):
        """Handles severed (unexpectedly terminated) connections

        """
        self._terminate_heartbeat();
        if len(self.reconnect_paths) is 0:
            self.reconnect_paths = copy.copy(self._namespace_by_path);
            
            self._terminate_heartbeat();
            self.__transport = None;

            for namespace in self.reconnect_paths:
                self.disconnect(namespace, skip_transport_disconnect = True);

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

            except ConnectionError as e:
                try:
                    self._handle_severed_connection();
                    warning = Exception('[connection error] %s' % e)
                    warning_screen.throw(warning)
                except StopIteration:
                    _log.warn(warning)

        self._terminate_heartbeat();
        _log.debug("[wait canceled]");

    def _process_events(self):
        for packet in self._transport.recv_packet():
            try:
                self._process_packet(packet)
            except PacketError as e:
                _log.warn('[packet error] %s', e)

    def _get_message_delegate(self, code):
        try:
            return {
                MessageType.CONNECT: self._on_connect,
                MessageType.DISCONNECT: self._on_disconnect,
                MessageType.EVENT: self._on_event,
                MessageType.ACK: self._on_ack,
                MessageType.ERROR: self._on_error,
                MessageType.BINARY_EVENT: self._on_binary_event,
                MessageType.BINARY_ACK: self._on_binary_ack
            }[code]
        except KeyError:
            raise PacketError('unexpected code (%s)' % code)

    def _get_packet_delegate(self, code):
        try:
            return {
                PacketType.OPEN: self._on_open,
                PacketType.CLOSE: self._on_close,
                PacketType.PING: self._on_ping,
                PacketType.PONG: self._on_pong,
                #PacketType.MESSAGE: self._on_message,  Handled by other delegates
                PacketType.UPGRADE: self._on_upgrade,
                PacketType.NOOP: self._on_noop
            }[code]
        except KeyError:
            raise PacketError('unexpected code (%s)' % code)

    def _process_packet(self, packet):
        _log.debug("[process packet] %s" % str(packet));
        path = packet.payload.path if packet.type == PacketType.MESSAGE else "";
        namespace = self.get_namespace(path)
        code = packet.payload.type if packet.type == PacketType.MESSAGE else packet.type;

        delegate = None;
        try:
            if packet.type == PacketType.MESSAGE:
                _log.debug("[process packet] Handling message");
                delegate = self._get_message_delegate(packet.payload.type);
            else:
                delegate = self._get_packet_delegate(packet.type);
        except Exception as e:
            _log.warn("[process packet] Could not find delegate for packet: " + str(e));
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

    def disconnect(self, path='', skip_transport_disconnect = False):
        if self.connected and not skip_transport_disconnect:
            try:
                self._transport.disconnect(path)
            except ConnectionError as e:
                _log.warn("[disconnect] Connection error: %s" % str(e));

        namespace = self._namespace_by_path[path]
        namespace.on_disconnect()
        if path:
            del self._namespace_by_path[path]

    @property
    def connected(self):
        return self.__transport.connected if self.__transport is not None else False;        

    def _create_transport(self):
        _log.debug("[create transport]");
        self.__transport = self._get_transport();

    @property
    def _transport(self):
        try:
            if self.__transport is not None and self.connected:
                return self.__transport
        except AttributeError:
            pass
        warning_screen = _yield_warning_screen(seconds=None)
        for elapsed_time in warning_screen:
            try:
                self._create_transport();
                break
            except ConnectionError as e:
                if not self.wait_for_connection:
                    raise
                try:
                    warning = Exception('[waiting for connection] %s' % e)
                    warning_screen.throw(warning)
                except StopIteration:
                    _log.warn(warning)

                continue;
        # If we disconnected before, self.reconnected_paths will be
        # non-empty.
        while len(self.reconnect_paths) > 0:
            try:
                self.reconnect();
            except ConnectionError as e:
                time.sleep(RETRY_INTERVAL_IN_SECONDS);
                continue;

        return self.__transport

    def _upgrade(self):
        """Attempts to upgrade the connection to a websocket.

        This method will execute the update process outline here:
        https://github.com/Automattic/engine.io-protocol#transport-upgrading

        To summarize, we first send a PING packet with the string
        'probe' appended as data. This signals to the server that we
        want to probe the ability to upgrade. If the server has this
        functionality, it responds with a PONG packet and the 'probe'
        string.

        We then send an UPGRADE packet, restart the heartbeat thread,
        and return.

        """
        websocket = transports.WebsocketTransport(self.session, self.is_secure, self.base_url, **self.kw);
        websocket.send_packet(PacketType.PING, "", "probe");
        for packet in websocket.recv_packet():
            _log.debug("[websocket] Packet: %s" % str(packet));
            if packet.type == PacketType.PONG:
                _log.debug("[PONG] %s" % repr(packet));

                self._terminate_heartbeat();

                # Technically we would need to pause the current
                # transport (which should be polling in this
                # implementation), but since we haven't actually
                # started a polling yet, we can upgrade without that.
                _log.debug("[upgrading] Sending upgrade request");
                websocket.send_packet(PacketType.UPGRADE);
                self._start_heartbeat(websocket);
                return websocket;

    def _terminate_heartbeat(self):
        """Terminates the heartbeat thread.

        """
        if self.heartbeat_terminator is not None:
            self.heartbeat_terminator.set();
            self.heartbeat_thread.join();

    def _start_heartbeat(self, transport):
        """Starts the heartbeat thread.
        
        The heartbeat thread ensures that our connection is never
        severed. This effectively spawns a thread that sits in an
        infinite loop. The thread waits
        self.session.heartbeat_interval / 2 (gleaned from the server)
        seconds, then sends a heartbeat packet (PING).

        The thread is implemented using a multiprocessing.Event to
        perform the wait, so it doesn't waste any cpu cycles while
        it's waiting.

        """

        if self.heartbeat_thread is not None and not self.heartbeat_terminator.is_set():
            _log.warn("[start hearbeat] heartbeat already started... terminating old heartbeat");
            self._terminate_heartbeat();

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
                _log.warn("[websocket] Failed to upgrade to websocket")
                pass;

        return transport

    def get_namespace(self, path=''):
        try:
            return self._namespace_by_path[path]
        except KeyError:
            raise PacketError('unexpected namespace path (%s)' % path)

    #################################################################
    # Handlers for EngineIO packet types (PacketType in parser.py)
    #################################################################

    def _on_open(self, packet, find_event_callback):
        find_event_callback('open')()

    def _on_close(self, packet, find_event_callback):
        find_event_callback('close')()

    def _on_ping(self, packet, find_event_callback):
        find_event_callback('ping')()

    def _on_pong(self, packet, find_event_callback):
        find_event_callback('pong')()

    def _on_upgrade(self, packet, find_event_callback):
        find_event_callback('close')()

    def _on_noop(self, packet, find_event_callback):
        find_event_callback('noop')()

    #################################################################
    # Handlers for SocketIO "packet" types (MessageType in parser.py)
    #################################################################

    def _on_connect(self, packet, find_event_callback):
        find_event_callback('connect')()

    def _on_disconnect(self, packet, find_event_callback):
        find_event_callback('disconnect')()

    def _on_event(self, packet, find_event_callback):
        """This delegate is called when there is an EVENT packet.

        Accoding to the documentation
         (https://github.com/automattic/socket.io-protocol#event), the
         event name is the first entry in the message array, and the
         arguments are the rest of the entries.

        """
        event = packet.payload.message[0];
        args = packet.payload.message[1:] if len(packet.payload.message) > 1 else [];

        _log.debug("[event] %s (%s)" % (repr(event), repr(args)));

        if packet.payload.id is not None:
            args.append(self._prepare_to_send_ack(packet.payload.path, packet.payload.id))
        find_event_callback(event)(*args);

    def _on_ack(self, packet, find_event_callback):
        """Handles ACK from server.

        There are two types of ACKs. The first is when this client
        requests that the server responds with an ACK upon execution
        of a remote function (specified in the server via
        socketio.on()).

        The second type is when the server requests that this client
        acknowledges that a local function has been executed.

        Both are handled the same way from the client's standpoint,
        but in latter case the server will actually send along the
        event name and the args, but they are currently ignored.

        """

        #event = packet.payload.message[0];
        packet_id = packet.payload.id;
        try:
            ack_callback = self._transport.get_ack_callback(str(packet_id))
        except KeyError:
            _log.warn("Could not find callback function for packet id: %d" % packet_id);
            return
        args = packet.payload.message[1:] if len(packet.payload.message) > 1 else [];
        ack_callback(*args)

    def _on_error(self, packet, find_event_callback):
        find_event_callback('error')(packet.payload.message)

    def _on_binary_event(self, packet, find_event_callback):
        raise PacketError("Don't know how to handle binary events yet");

    def _on_binary_ack(self, packet, find_event_callback):
        raise PacketError("Don't know how to handle binary acks yet");

    def _prepare_to_send_ack(self, path, packet_id):
        'Return function that acknowledges the server'
        return lambda *args: _send_ack(self, path, packet_id, *args);

def _send_ack(socketio, path, packet_id, *args):
    try: 
        socketio._transport.ack(path, packet_id, *args);
    except ConnectionError as e:
        _log.warn("[send ack] Connection error: %s" % str(e));
        socketio._handle_severed_connection();                

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
                 % ('https' if is_secure else 'http', base_url, parser.ENGINEIO_PROTOCOL)
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
        except requests.exceptions.ConnectionError as e:
            message = "[heartbeat] disconnected while sending PING";
            _log.warn(message);
        except:
            pass;
    _log.debug("[heartbeat terminated]");
