import socket
from json import dumps, loads
from threading import Thread, Event
from time import sleep
from urllib import urlopen
from websocket import WebSocketConnectionClosedException, create_connection


PROTOCOL = 1  # socket.io protocol version


class BaseNamespace(object):  # pragma: no cover
    'Define socket.io behavior'

    def __init__(self, _socketIO, path):
        self._socketIO = _socketIO
        self._path = path
        self._callbackByEvent = {}
        self.initialize()

    def initialize(self):
        'Initialize custom variables here; you can override this method'
        pass

    def on_connect(self):
        'Called when socket is connecting; you can override this method'
        pass

    def on_disconnect(self):
        'Called when socket is disconnecting; you can override this method'
        pass

    def on_error(self, reason, advice):
        'Called when server sends an error; you can override this method'
        print '[Error] %s' % advice

    def on_message(self, data):
        'Called when server sends a message; you can override this method'
        print '[Message] %s' % data

    def on_event(self, event, *args):
        """
        Called when server emits an event; you can override this method.
        Called only if the program cannot find a more specific event handler,
        such as one defined by namespace.on('my_event', my_function).
        """
        callback, args = find_callback(args)
        arguments = [repr(_) for _ in args]
        if callback:
            arguments.append('callback(*args)')
            callback(*args)
        print '[Event] %s(%s)' % (event, ', '.join(arguments))

    def on_open(self, *args):
        print '[Open]', args

    def on_close(self, *args):
        print '[Close]', args

    def on_retry(self, *args):
        print '[Retry]', args

    def on_reconnect(self, *args):
        print '[Reconnect]', args

    def message(self, data='', callback=None):
        self._socketIO.message(data, callback, path=self._path)

    def emit(self, event, *args, **kw):
        kw['path'] = self._path
        self._socketIO.emit(event, *args, **kw)

    def on(self, event, callback):
        'Define a callback to handle a custom event emitted by the server'
        self._callbackByEvent[event] = callback

    def _get_eventCallback(self, event):
        # Check callbacks defined by on()
        try:
            return self._callbackByEvent[event]
        except KeyError:
            pass
        # Check callbacks defined explicitly or use on_event()
        callback = lambda *args: self.on_event(event, *args)
        return getattr(self, 'on_' + event.replace(' ', '_'), callback)


class SocketIO(object):

    def __init__(self, host, port, secure=False, proxies=None):
        """
        Create a socket.io client that connects to a socket.io server
        at the specified host and port.  Set secure=True to use HTTPS / WSS.

        SocketIO('localhost', 8000, secure=True,
            proxies={'https': 'https://proxy.example.com:8080'})
        """
        self._socketIO = _SocketIO(host, port, secure, proxies)
        self._namespaceByPath = {}
        self.define(BaseNamespace)  # Define default namespace

        self._rhythmicThread = _RhythmicThread(
            self._socketIO.heartbeatInterval,
            self._socketIO.send_heartbeat)
        self._rhythmicThread.start()

        self._listenerThread = _ListenerThread(
            self._socketIO,
            self._namespaceByPath)
        self._listenerThread.start()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.disconnect()

    def __del__(self):
        self.disconnect(close=False)

    @property
    def connected(self):
        return self._socketIO.connected

    def disconnect(self, path='', close=True):
        if self.connected:
            self._socketIO.disconnect(path, close)
        if path:
            del self._namespaceByPath[path]
        else:
            self._rhythmicThread.cancel()
            self._listenerThread.cancel()

    def define(self, Namespace, path=''):
        if path:
            self._socketIO.connect(path)
        namespace = Namespace(self._socketIO, path)
        self._namespaceByPath[path] = namespace
        return namespace

    def get_namespace(self, path=''):
        return self._namespaceByPath[path]

    def on(self, event, callback, path=''):
        return self.get_namespace(path).on(event, callback)

    def message(self, data='', callback=None, path=''):
        self._socketIO.message(data, callback, path)

    def emit(self, event, *args, **kw):
        self._socketIO.emit(event, *args, **kw)

    def wait(self, seconds=None):
        if seconds:
            self._listenerThread.wait(seconds)
        else:
            try:
                while self.connected:
                    sleep(1)
            except KeyboardInterrupt:
                pass

    def wait_for_callbacks(self, seconds=None):
        self._listenerThread.wait_for_callbacks(seconds)


class _RhythmicThread(Thread):
    'Execute call every few seconds'

    daemon = True

    def __init__(self, intervalInSeconds, call, *args, **kw):
        super(_RhythmicThread, self).__init__()
        self.intervalInSeconds = intervalInSeconds
        self.call = call
        self.args = args
        self.kw = kw
        self.done = Event()

    def run(self):
        while not self.done.is_set():
            self.call(*self.args, **self.kw)
            self.done.wait(self.intervalInSeconds)

    def cancel(self):
        self.done.set()


class _ListenerThread(Thread):
    'Process messages from socket.io server'

    daemon = True

    def __init__(self, _socketIO, _namespaceByPath):
        super(_ListenerThread, self).__init__()
        self._socketIO = _socketIO
        self._namespaceByPath = _namespaceByPath
        self.done = Event()
        self.ready = Event()
        self.ready.set()

    def cancel(self):
        self.done.set()

    def wait(self, seconds):
        self.done.wait(seconds)

    def wait_for_callbacks(self, seconds):
        self.ready.clear()
        self.ready.wait(seconds)

    def get_ackCallback(self, packetID):
        return lambda *args: self._socketIO.ack(packetID, *args)

    def run(self):
        while not self.done.is_set():
            try:
                code, packetID, path, data = self._socketIO.recv_packet()
            except SocketIOConnectionError, error:
                print error
                return
            except SocketIOPacketError, error:
                print error
                continue
            try:
                namespace = self._namespaceByPath[path]
            except KeyError:
                print 'Received unexpected path (%s)' % path
                continue
            try:
                delegate = {
                    '0': self.on_disconnect,
                    '1': self.on_connect,
                    '2': self.on_heartbeat,
                    '3': self.on_message,
                    '4': self.on_json,
                    '5': self.on_event,
                    '6': self.on_ack,
                    '7': self.on_error,
                }[code]
            except KeyError:
                print 'Received unexpected code (%s)' % code
                continue
            delegate(packetID, namespace._get_eventCallback, data)

    def on_disconnect(self, packetID, get_eventCallback, data):
        get_eventCallback('disconnect')()

    def on_connect(self, packetID, get_eventCallback, data):
        get_eventCallback('connect')()

    def on_heartbeat(self, packetID, get_eventCallback, data):
        pass

    def on_message(self, packetID, get_eventCallback, data):
        args = [data]
        if packetID:
            args.append(self.get_ackCallback(packetID))
        get_eventCallback('message')(*args)

    def on_json(self, packetID, get_eventCallback, data):
        args = [loads(data)]
        if packetID:
            args.append(self.get_ackCallback(packetID))
        get_eventCallback('message')(*args)

    def on_event(self, packetID, get_eventCallback, data):
        valueByName = loads(data)
        event = valueByName['name']
        args = valueByName.get('args', [])
        if packetID:
            args.append(self.get_ackCallback(packetID))
        get_eventCallback(event)(*args)

    def on_ack(self, packetID, get_eventCallback, data):
        dataParts = data.split('+', 1)
        messageID = int(dataParts[0])
        args = loads(dataParts[1]) if len(dataParts) > 1 else []
        callback = self._socketIO.get_messageCallback(messageID)
        if not callback:
            return
        callback(*args)
        if not self._socketIO.has_messageCallback:
            self.ready.set()

    def on_error(self, packetID, get_eventCallback, data):
        reason, advice = data.split('+', 1)
        get_eventCallback('error')(reason, advice)


class _SocketIO(object):
    'Low-level interface to remove cyclic references in child threads'

    messageID = 0

    def __init__(self, host, port, secure, proxies):
        baseURL = '%s:%d/socket.io/%s' % (host, port, PROTOCOL)
        targetScheme = 'https' if secure else 'http'
        targetURL = '%s://%s/' % (targetScheme, baseURL)
        try:
            response = urlopen(targetURL, proxies=proxies)
        except IOError:  # pragma: no cover
            raise SocketIOError('Could not start connection')
        if 200 != response.getcode():  # pragma: no cover
            raise SocketIOError('Could not establish connection')
        responseParts = response.readline().split(':')
        sessionID = responseParts[0]
        heartbeatTimeout = int(responseParts[1])
        # connectionTimeout = int(responseParts[2])
        supportedTransports = responseParts[3].split(',')
        if 'websocket' not in supportedTransports:
            raise SocketIOError('Could not parse handshake')
        socketScheme = 'wss' if secure else 'ws'
        socketURL = '%s://%s/websocket/%s' % (socketScheme, baseURL, sessionID)
        self.connection = create_connection(socketURL)
        self.heartbeatInterval = heartbeatTimeout - 2
        self.callbackByMessageID = {}

    def __del__(self):
        self.disconnect(close=False)

    def disconnect(self, path='', close=True):
        if not self.connected:
            return
        if path:
            self.send_packet(0, path)
        elif close:
            self.connection.close()

    def connect(self, path):
        self.send_packet(1, path)

    def send_heartbeat(self):
        try:
            self.send_packet(2)
        except SocketIOPacketError:
            print 'Could not send heartbeat'
            pass

    def message(self, data, callback, path):
        if isinstance(data, basestring):
            code = 3
            packetData = data
        else:
            code = 4
            packetData = dumps(data, ensure_ascii=False)
        self.send_packet(code, path, packetData, callback)

    def emit(self, event, *args, **kw):
        callback, args = find_callback(args, kw)
        packetData = dumps(dict(name=event, args=args), ensure_ascii=False)
        path = kw.get('path', '')
        self.send_packet(5, path, packetData, callback)

    def ack(self, packetID, *args):
        packetID = packetID.rstrip('+')
        packetData = '%s+%s' % (
            packetID,
            dumps(args, ensure_ascii=False),
        ) if args else packetID
        self.send_packet(6, data=packetData)

    def set_messageCallback(self, callback):
        'Set callback that will be called after receiving an acknowledgment'
        self.messageID += 1
        self.callbackByMessageID[self.messageID] = callback
        return '%s+' % self.messageID

    def get_messageCallback(self, messageID):
        try:
            callback = self.callbackByMessageID[messageID]
            del self.callbackByMessageID[messageID]
            return callback
        except KeyError:
            return

    @property
    def has_messageCallback(self):
        return True if self.callbackByMessageID else False

    def recv_packet(self):
        try:
            packet = self.connection.recv()
        except WebSocketConnectionClosedException:
            text = 'Lost connection (Connection closed)'
            raise SocketIOConnectionError(text)
        except socket.timeout:
            text = 'Lost connection (Connection timed out)'
            raise SocketIOConnectionError(text)
        except socket.error:
            text = 'Lost connection'
            raise SocketIOConnectionError(text)
        try:
            packetParts = packet.split(':', 3)
        except AttributeError:
            raise SocketIOPacketError('Received invalid packet (%s)' % packet)
        packetCount = len(packetParts)
        code, packetID, path, data = None, None, None, None
        if 4 == packetCount:
            code, packetID, path, data = packetParts
        elif 3 == packetCount:
            code, packetID, path = packetParts
        elif 1 == packetCount:
            code = packetParts[0]
        return code, packetID, path, data

    def send_packet(self, code, path='', data='', callback=None):
        packetID = self.set_messageCallback(callback) if callback else ''
        packetParts = [str(code), packetID, path, data]
        try:
            packet = ':'.join(packetParts)
            self.connection.send(packet)
        except socket.error:
            raise SocketIOPacketError('Could not send packet')

    @property
    def connected(self):
        return self.connection.connected


class SocketIOError(Exception):
    pass


class SocketIOConnectionError(SocketIOError):
    pass


class SocketIOPacketError(SocketIOError):
    pass


def find_callback(args, kw=None):
    'Return callback whether passed as a last argument or as a keyword'
    if args and callable(args[-1]):
        return args[-1], args[:-1]
    try:
        return kw['callback'], args
    except (KeyError, TypeError):
        return None, args
