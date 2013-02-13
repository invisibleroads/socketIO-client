import socket
from anyjson import dumps, loads
from threading import Event, Thread
from time import sleep
from urllib import urlopen
from websocket import WebSocketConnectionClosedException, create_connection


PROTOCOL = 1  # SocketIO protocol version


class BaseNamespace(object):  # pragma: no cover

    def __init__(self, _socketIO):
        self._socketIO = _socketIO

    def on_connect(self):
        pass

    def on_disconnect(self):
        pass

    def on_error(self, reason, advice):
        print '[Error] %s' % advice

    def on_message(self, messageData):
        print '[Message] %s' % messageData

    def on_(self, eventName, *eventArguments):
        print '[Event] %s%s' % (eventName, eventArguments)

    def on_open(self, *args):
        print '[Open]', args

    def on_close(self, *args):
        print '[Close]', args

    def on_retry(self, *args):
        print '[Retry]', args

    def on_reconnect(self, *args):
        print '[Reconnect]', args


class SocketIO(object):

    def __init__(self, host, port, secure=False, proxies=None):
        self._socketIO = _SocketIO(host, port, secure, proxies)
        self._channelByPath = {}

        self._rhythmicThread = _RhythmicThread(
            self._socketIO.heartbeatTimeout,
            self._socketIO.send_heartbeat)
        self._rhythmicThread.start()

        self._listenerThread = _ListenerThread(
            self._socketIO,
            self._channelByPath)
        self._listenerThread.start()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.disconnect()

    def __del__(self):
        self.disconnect()

    @property
    def connected(self):
        return self._socketIO.connection.connected

    def disconnect(self, channelPath=''):
        self._socketIO.disconnect(channelPath)
        if channelPath:
            del self._channelByPath[channelPath]
        else:
            self._rhythmicThread.cancel()
            self._listenerThread.cancel()

    def define(self, Namespace, channelPath=''):
        self._socketIO.connect(channelPath)
        channel = Channel(self._socketIO, Namespace, channelPath)
        self._channelByPath[channelPath] = channel
        return channel

    def get_namespace(self, channelPath=''):
        return self._channelByPath[channelPath].get_namespace()

    def on(self, eventName, eventCallback):
        self._callbackByEvent[eventName] = callback

    def message(self, messageData, callback=None, channelName=''):
        if isinstance(messageData, basestring):
            code = 3
            data = messageData
        else:
            code = 4
            data = dumps(messageData)
        self._send_packet(code, channelName, data, callback)

    def emit(self, eventName, *eventArguments):
        self._socketIO.emit(eventName, *eventArguments)
        code = 5
        callback = None
        if eventArguments and callable(eventArguments[-1]):
            callback = eventArguments[-1]
            eventArguments = eventArguments[:-1]
        channelName = eventKeywords.get('channelName', '')
        data = dumps(dict(name=eventName, args=eventArguments))
        self._send_packet(code, channelName, data, callback)

    def wait(self, seconds=None, forCallbacks=False):
        if forCallbacks:
            self.__listenerThread.wait_for_callbacks(seconds)
        elif seconds:
            sleep(seconds)
        else:
            try:
                while self._socketIO.connected:
                    sleep(1)
            except KeyboardInterrupt:
                pass


class _RhythmicThread(Thread):
    'Execute call every few seconds'

    daemon = True

    def __init__(self, intervalInSeconds, call, *args, **kw):
        super(_RhythmicThread, self).__init__()
        self.intervalInSeconds = intervalInSeconds
        self.call
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
    'Process messages from SocketIO server'

    daemon = True

    def __init__(self, _socketIO, _channelByPath):
        super(_ListenerThread, self).__init__()
        self._socketIO = _socketIO
        self._channelByPath = _channelByPath
        self.done = Event()
        self.waiting = Event()

    def cancel(self):
        self.done.set()

    def wait_for_callbacks(self, seconds):
        self.waiting.set()
        # Block callingThread until listenerThread terminates
        self.join(seconds)

    def run(self):
        while not self.done.is_set():
            try:
                code, packetID, channelPath, data = self._socketIO.recv_packet()
            except SocketIOConnectionError, error:
                print error
                return
            except SocketIOPacketError, error:
                print error
                continue
            channel = self._channelByPath[channelPath]
            try:
                delegate = {
                    0: self.on_disconnect,
                    1: self.on_connect,
                    2: self.on_heartbeat,
                    3: self.on_message,
                    4: self.on_json,
                    5: self.on_event,
                    6: self.on_acknowledgment,
                    7: self.on_error,
                }[code]
            except KeyError:
                continue
            delegate(packetID, channel._get_eventCallback, data)

    def on_disconnect(self, packetID, get_eventCallback, data):
        get_eventCallback('disconnect')()

    def on_connect(self, packetID, get_eventCallback, data):
        get_eventCallback('connect')()

    def on_heartbeat(self, packetID, get_eventCallback, data):
        get_eventCallback('heartbeat')()

    def on_message(self, packetID, get_eventCallback, data):
        get_eventCallback('message')(data)

    def on_json(self, packetID, get_eventCallback, data):
        get_eventCallback('message')(loads(data))

    def on_event(self, packetID, get_eventCallback, data):
        valueByName = loads(data)
        eventName = valueByName['name']
        eventArguments = valueByName['args']
        get_eventCallback(eventName)(*eventArguments)

    def on_acknowledgment(self, packetID, get_eventCallback, data):
        dataParts = data.split('+', 1)
        messageID = int(dataParts[0])
        arguments = loads(dataParts[1]) or []
        callback = self._socketIO.get_messageCallback(messageID)
        if not callback:
            return
        callback(*arguments)
        if self.waiting.is_set() and not self._socketIO.has_messageCallback:
            self.cancel()

    def on_error(self, packetID, get_eventCallback, data):
        reason, advice = data.split('+', 1)
        get_eventCallback('error')(reason, advice)


class _SocketIO(object):
    'Low-level interface to remove cyclic references in child threads'

    messageID = 0
    self.callbackByMessageID = {}
    self.callbackByEvent = {}


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
            raise SocketIOError('Could not parse handshake')  # pragma: no cover
        socketScheme = 'wss' if secure else 'ws'
        socketURL = '%s://%s/websocket/%s' % (socketScheme, baseURL, sessionID)
        self.connection = create_connection(socketURL)
        self.heartbeatInterval = heartbeatTimeout - 2

    def __del__(self):
        self.connection.close()

    def get_channel(self, channelPath):

    def get_channel(self, channelName):
        return self.channelByName[channelName]
        pass

    def recv_packet(self):
        code, packetID, channelName, data = -1, None, None, None
        try:
            packet = self.connection.recv()
        except WebSocketConnectionClosedException:
            raise SocketIOConnectionError('Lost connection (Connection closed)')
        except socket.timeout:
            raise SocketIOConnectionError('Lost connection (Connection timed out)')
        try:
            packetParts = packet.split(':', 3)
        except AttributeError:
            raise SocketIOPacketError('Received invalid packet (%s)' % packet)
        packetCount = len(packetParts)
        if 4 == packetCount:
            code, packetID, channelName, data = packetParts
        elif 3 == packetCount:
            code, packetID, channelName = packetParts
        elif 1 == packetCount:  # pragma: no cover
            code = packetParts[0]
        return int(code), packetID, channelName, data

    def send_packet(self, code, channelName='', data='', callback=None):
        callbackNumber = self.set_messageCallback(callback) if callback else ''
        packetParts = [str(code), callbackNumber, channelName, data]
        try:
            self.connection.send(':'.join(packetParts))
        except socket.error:
            raise SocketIOPacketError('Could not send packet')

    def disconnect(self, channelPath):
        self.send_packet(0, channelPath)

    def connect(self, channelPath):
        self.send_packet(1, channelPath)

    def send_heartbeat(self):
        try:
            self.send_packet(2)
        except SocketIOPacketError:
            print 'Could not send heartbeat'
            pass

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


class Channel(object):

    def __init__(self, _socketIO, Namespace, channelPath):
        self._socketIO = _socketIO
        self._namespace = Namespace(_socketIO)
        self._channelPath = channelPath
        self._callbackByEvent = {}

    def on(self, eventName, eventCallback):
        self._callbackByEvent[eventName] = eventCallback

    def message(self, messageData, messageCallback=None):
        self._socketIO.message(messageData, messageCallback, channelPath=self._channelPath)

    def emit(self, eventName, *eventArguments):
        self._socketIO.emit(eventName, *eventArguments, channelPath=self._channelPath)

    def get_namespace(self):
        return self._namespace

    def _get_eventCallback(self, eventName):
        # Check callbacks defined by on()
        try:
            return self._callbackByEvent[eventName]
        except KeyError:
            pass
        # Check callbacks defined explicitly or use on_()
        defaultCallback = lambda *eventArguments: self.get_namespace().on_(eventName, *eventArguments)
        return getattr(self, 'on_' + eventName.replace(' ', '_'), defaultCallback)


class SocketIOError(Exception):
    pass


class SocketIOConnectionError(SocketIOError):
    pass


class SocketIOPacketError(SocketIOError):
    pass
