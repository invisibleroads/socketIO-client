from .exceptions import ConnectionError, TimeoutError, PacketError
from .heartbeats import HeartbeatThread
from .logs import LoggingMixin
from .namespaces import (
    EngineIONamespace, SocketIONamespace, LoggingSocketIONamespace,
    find_callback)
from .parsers import (
    parse_host, parse_engineIO_session,
    format_socketIO_packet_data, parse_socketIO_packet_data,
    get_namespace_path)
from .symmetries import get_character
from .transports import (
    WebsocketTransport, XHR_PollingTransport, prepare_http_session, TRANSPORTS)


__all__ = 'SocketIO', 'SocketIONamespace'
__version__ = '0.6.3'
BaseNamespace = SocketIONamespace
LoggingNamespace = LoggingSocketIONamespace


def retry(f):
    def wrap(*args, **kw):
        self = args[0]
        try:
            return f(*args, **kw)
        except (TimeoutError, ConnectionError):
            self._opened = False
            return f(*args, **kw)
    return wrap


class EngineIO(LoggingMixin):

    def __init__(
            self, host, port=None, Namespace=EngineIONamespace,
            wait_for_connection=True, transports=TRANSPORTS,
            resource='engine.io', hurry_interval_in_seconds=1, **kw):
        self._is_secure, self._url = parse_host(host, port, resource)
        self._wait_for_connection = wait_for_connection
        self._client_transports = transports
        self._hurry_interval_in_seconds = hurry_interval_in_seconds
        self._http_session = prepare_http_session(kw)

        self._log_name = self._url
        self._wants_to_close = False
        self._opened = False

        if Namespace:
            self.define(Namespace)
        self._transport

    # Connect

    @property
    def _transport(self):
        if self._opened:
            return self._transport_instance
        self._engineIO_session = self._get_engineIO_session()
        self._negotiate_transport()
        self._connect_namespaces()
        self._opened = True
        self._reset_heartbeat()
        return self._transport_instance

    def _get_engineIO_session(self):
        warning_screen = self._yield_warning_screen()
        for elapsed_time in warning_screen:
            transport = XHR_PollingTransport(
                self._http_session, self._is_secure, self._url)
            try:
                engineIO_packet_type, engineIO_packet_data = next(
                    transport.recv_packet())
                break
            except (TimeoutError, ConnectionError) as e:
                if not self._wait_for_connection:
                    raise
                warning = Exception('[waiting for connection] %s' % e)
                warning_screen.throw(warning)
        assert engineIO_packet_type == 0  # engineIO_packet_type == open
        return parse_engineIO_session(engineIO_packet_data)

    def _negotiate_transport(self):
        self._transport_instance = self._get_transport('xhr-polling')
        self.transport_name = 'xhr-polling'
        is_ws_client = 'websocket' in self._client_transports
        is_ws_server = 'websocket' in self._engineIO_session.transport_upgrades
        if is_ws_client and is_ws_server:
            try:
                transport = self._get_transport('websocket')
                transport.send_packet(2, 'probe')
                for packet_type, packet_data in transport.recv_packet():
                    if packet_type == 3 and packet_data == b'probe':
                        transport.send_packet(5, '')
                        self._transport_instance = transport
                        self.transport_name = 'websocket'
                    else:
                        self._warn('unexpected engine.io packet')
            except Exception:
                pass
        self._debug('[transport selected] %s', self.transport_name)

    def _reset_heartbeat(self):
        try:
            self._heartbeat_thread.halt()
            hurried = self._heartbeat_thread.hurried
        except AttributeError:
            hurried = False
        ping_interval = self._engineIO_session.ping_interval
        if self.transport_name.endswith('-polling'):
            # Use ping/pong to unblock recv for polling transport
            hurry_interval_in_seconds = self._hurry_interval_in_seconds
        else:
            # Use timeout to unblock recv for websocket transport
            hurry_interval_in_seconds = ping_interval
        self._heartbeat_thread = HeartbeatThread(
            send_heartbeat=self._ping,
            relax_interval_in_seconds=ping_interval,
            hurry_interval_in_seconds=hurry_interval_in_seconds)
        self._heartbeat_thread.start()
        if hurried:
            self._heartbeat_thread.hurry()
        self._debug('[heartbeat reset]')

    def _connect_namespaces(self):
        pass

    def _get_transport(self, transport_name):
        SelectedTransport = {
            'xhr-polling': XHR_PollingTransport,
            'websocket': WebsocketTransport,
        }[transport_name]
        return SelectedTransport(
            self._http_session, self._is_secure, self._url,
            self._engineIO_session)

    def __enter__(self):
        return self

    def __exit__(self, *exception_pack):
        self._close()

    def __del__(self):
        self._close()

    # Define

    def define(self, Namespace):
        self._namespace = namespace = Namespace(self)
        return namespace

    def on(self, event, callback):
        try:
            namespace = self.get_namespace()
        except PacketError:
            namespace = self.define(EngineIONamespace)
        return namespace.on(event, callback)

    def get_namespace(self):
        try:
            return self._namespace
        except AttributeError:
            raise PacketError('undefined engine.io namespace')

    # Act

    def send(self, engineIO_packet_data):
        self._message(engineIO_packet_data)

    def _open(self):
        engineIO_packet_type = 0
        self._transport_instance.send_packet(engineIO_packet_type)

    def _close(self):
        self._wants_to_close = True
        try:
            self._heartbeat_thread.halt()
        except AttributeError:
            pass
        if not self._opened:
            return
        engineIO_packet_type = 1
        try:
            self._transport_instance.send_packet(engineIO_packet_type)
        except (TimeoutError, ConnectionError):
            pass
        self._opened = False

    def _ping(self, engineIO_packet_data=''):
        engineIO_packet_type = 2
        self._transport_instance.send_packet(
            engineIO_packet_type, engineIO_packet_data)

    def _pong(self, engineIO_packet_data=''):
        engineIO_packet_type = 3
        self._transport_instance.send_packet(
            engineIO_packet_type, engineIO_packet_data)

    @retry
    def _message(self, engineIO_packet_data, with_transport_instance=False):
        engineIO_packet_type = 4
        if with_transport_instance:
            transport = self._transport_instance
        else:
            transport = self._transport
        transport.send_packet(engineIO_packet_type, engineIO_packet_data)
        self._debug('[socket.io packet sent] %s', engineIO_packet_data)

    def _upgrade(self):
        engineIO_packet_type = 5
        self._transport_instance.send_packet(engineIO_packet_type)

    def _noop(self):
        engineIO_packet_type = 6
        self._transport_instance.send_packet(engineIO_packet_type)

    # React

    def wait(self, seconds=None, **kw):
        'Wait in a loop and react to events as defined in the namespaces'
        # Use ping/pong to unblock recv for polling transport
        self._heartbeat_thread.hurry()
        # Use timeout to unblock recv for websocket transport
        self._transport.set_timeout(seconds=1)
        # Listen
        warning_screen = self._yield_warning_screen(seconds)
        for elapsed_time in warning_screen:
            if self._should_stop_waiting(**kw):
                break
            try:
                try:
                    self._process_packets()
                except TimeoutError:
                    pass
            except ConnectionError as e:
                self._opened = False
                try:
                    warning = Exception('[connection error] %s' % e)
                    warning_screen.throw(warning)
                except StopIteration:
                    self._warn(warning)
                try:
                    namespace = self.get_namespace()
                    namespace.on_disconnect()
                except PacketError:
                    pass
        self._heartbeat_thread.relax()
        self._transport.set_timeout()

    def _should_stop_waiting(self):
        return self._wants_to_close

    def _process_packets(self):
        for engineIO_packet in self._transport.recv_packet():
            try:
                self._process_packet(engineIO_packet)
            except PacketError as e:
                self._warn('[packet error] %s', e)

    def _process_packet(self, packet):
        engineIO_packet_type, engineIO_packet_data = packet
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
        delegate(engineIO_packet_data, namespace)
        if engineIO_packet_type is 4:
            return engineIO_packet_data

    def _on_open(self, data, namespace):
        namespace._find_packet_callback('open')()

    def _on_close(self, data, namespace):
        namespace._find_packet_callback('close')()

    def _on_ping(self, data, namespace):
        self._pong(data)
        namespace._find_packet_callback('ping')(data)

    def _on_pong(self, data, namespace):
        namespace._find_packet_callback('pong')(data)

    def _on_message(self, data, namespace):
        namespace._find_packet_callback('message')(data)

    def _on_upgrade(self, data, namespace):
        namespace._find_packet_callback('upgrade')()

    def _on_noop(self, data, namespace):
        namespace._find_packet_callback('noop')()


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
            self, host, port=None, Namespace=SocketIONamespace,
            wait_for_connection=True, transports=TRANSPORTS,
            resource='socket.io', hurry_interval_in_seconds=1, **kw):
        self._namespace_by_path = {}
        self._callback_by_ack_id = {}
        self._ack_id = 0
        super(SocketIO, self).__init__(
            host, port, Namespace, wait_for_connection, transports,
            resource, hurry_interval_in_seconds, **kw)

    # Connect

    @property
    def connected(self):
        return self._opened

    def _connect_namespaces(self):
        for path, namespace in self._namespace_by_path.items():
            namespace._transport = self._transport_instance
            if path:
                self.connect(path, with_transport_instance=True)

    def __exit__(self, *exception_pack):
        self.disconnect()
        super(SocketIO, self).__exit__(*exception_pack)

    def __del__(self):
        self.disconnect()
        super(SocketIO, self).__del__()

    # Define

    def define(self, Namespace, path=''):
        self._namespace_by_path[path] = namespace = Namespace(self, path)
        if path:
            self.connect(path)
            self.wait(for_connect=True)
        return namespace

    def on(self, event, callback, path=''):
        try:
            namespace = self.get_namespace(path)
        except PacketError:
            namespace = self.define(SocketIONamespace, path)
        return namespace.on(event, callback)

    def get_namespace(self, path=''):
        try:
            return self._namespace_by_path[path]
        except KeyError:
            raise PacketError('undefined socket.io namespace (%s)' % path)

    # Act

    def connect(self, path, with_transport_instance=False):
        socketIO_packet_type = 0
        socketIO_packet_data = format_socketIO_packet_data(path)
        self._message(
            str(socketIO_packet_type) + socketIO_packet_data,
            with_transport_instance)

    def disconnect(self, path=''):
        if not path or not self._opened:
            self._close()
        elif path:
            socketIO_packet_type = 1
            socketIO_packet_data = format_socketIO_packet_data(path)
            try:
                self._message(str(socketIO_packet_type) + socketIO_packet_data)
            except (TimeoutError, ConnectionError):
                pass
        try:
            namespace = self._namespace_by_path.pop(path)
            namespace.on_disconnect()
        except KeyError:
            pass

    def emit(self, event, *args, **kw):
        path = kw.get('path', '')
        callback, args = find_callback(args, kw)
        ack_id = self._set_ack_callback(callback) if callback else None
        args = [event] + list(args)
        socketIO_packet_type = 2
        socketIO_packet_data = format_socketIO_packet_data(path, ack_id, args)
        self._message(str(socketIO_packet_type) + socketIO_packet_data)

    def send(self, data='', callback=None, **kw):
        path = kw.get('path', '')
        args = [data]
        if callback:
            args.append(callback)
        self.emit('message', *args, path=path)

    def _ack(self, path, ack_id, *args):
        socketIO_packet_type = 3
        socketIO_packet_data = format_socketIO_packet_data(path, ack_id, args)
        self._message(str(socketIO_packet_type) + socketIO_packet_data)

    # React

    def wait_for_callbacks(self, seconds=None):
        self.wait(seconds, for_callbacks=True)

    def _should_stop_waiting(self, for_connect=False, for_callbacks=False):
        if for_connect:
            for namespace in self._namespace_by_path.values():
                is_namespace_connected = getattr(
                    namespace, '_connected', False)
                if not is_namespace_connected:
                    return False
            return True
        if for_callbacks and not self._has_ack_callback:
            return True
        return super(SocketIO, self)._should_stop_waiting()

    def _process_packet(self, packet):
        engineIO_packet_data = super(SocketIO, self)._process_packet(packet)
        if engineIO_packet_data is None:
            return
        self._debug('[socket.io packet received] %s', engineIO_packet_data)
        socketIO_packet_type = int(get_character(engineIO_packet_data, 0))
        socketIO_packet_data = engineIO_packet_data[1:]
        # Launch callbacks
        path = get_namespace_path(socketIO_packet_data)
        namespace = self.get_namespace(path)
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
        delegate(socketIO_packet_data, namespace)
        return socketIO_packet_data

    def _on_connect(self, data, namespace):
        namespace._connected = True
        namespace._find_packet_callback('connect')()

    def _on_disconnect(self, data, namespace):
        namespace._connected = False
        namespace._find_packet_callback('disconnect')()

    def _on_event(self, data, namespace):
        data_parsed = parse_socketIO_packet_data(data)
        args = data_parsed.args
        try:
            event = args.pop(0)
        except IndexError:
            raise PacketError('missing event name')
        if data_parsed.ack_id is not None:
            args.append(self._prepare_to_send_ack(
                data_parsed.path, data_parsed.ack_id))
        namespace._find_packet_callback(event)(*args)

    def _on_ack(self, data, namespace):
        data_parsed = parse_socketIO_packet_data(data)
        try:
            ack_callback = self._get_ack_callback(data_parsed.ack_id)
        except KeyError:
            return
        ack_callback(*data_parsed.args)

    def _on_error(self, data, namespace):
        namespace._find_packet_callback('error')(data)

    def _on_binary_event(self, data, namespace):
        self._warn('[not implemented] binary event')

    def _on_binary_ack(self, data, namespace):
        self._warn('[not implemented] binary ack')

    def _prepare_to_send_ack(self, path, ack_id):
        'Return function that acknowledges the server'
        return lambda *args: self._ack(path, ack_id, *args)

    def _set_ack_callback(self, callback):
        self._ack_id += 1
        self._callback_by_ack_id[self._ack_id] = callback
        return self._ack_id

    def _get_ack_callback(self, ack_id):
        return self._callback_by_ack_id.pop(ack_id)

    @property
    def _has_ack_callback(self):
        return True if self._callback_by_ack_id else False
