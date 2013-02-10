import sys
import traceback

import socket
from anyjson import dumps, loads
from functools import partial
from threading import Thread, Event
from time import sleep
from urllib import urlopen
from websocket import WebSocketConnectionClosedException, create_connection


__version__ = '0.4'


PROTOCOL = 1  # SocketIO protocol version


class BaseNamespace(object):  # pragma: no cover

    def __init__(self, socketIO):
        self.socketIO = socketIO

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

    _messageID = 0

    def __init__(self, host, port, Namespace=BaseNamespace, secure=False, proxies=None):
        self._host = host
        self._port = int(port)
        self._namespace = Namespace(self)
        self._secure = secure
        self._proxies = proxies
        self._connect()

        heartbeatInterval = self._heartbeatTimeout - 2
        self._heartbeatThread = RhythmicThread(heartbeatInterval, self._send_heartbeat)
        self._heartbeatThread.start()

        self._channelByName = {}
        self._callbackByEvent = {}
        self._namespaceThread = ListenerThread(self._recv_packet, self._get_callback)
        self._namespaceThread.start()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.__del__()

    def __del__(self):
        self._heartbeatThread.cancel()
        self._namespaceThread.cancel()
        self._connection.close()

    def _connect(self):
        baseURL = '%s:%d/socket.io/%s' % (self._host, self._port, PROTOCOL)
        try:
            response = urlopen('%s://%s/' % (
                'https' if self._secure else 'http', baseURL),
                proxies=self._proxies)
        except IOError:  # pragma: no cover
            raise SocketIOError('Could not start connection')
        if 200 != response.getcode():  # pragma: no cover
            raise SocketIOError('Could not establish connection')
        responseParts = response.readline().split(':')
        self._sessionID = responseParts[0]
        self._heartbeatTimeout = int(responseParts[1])
        self._connectionTimeout = int(responseParts[2])
        self._supportedTransports = responseParts[3].split(',')
        if 'websocket' not in self._supportedTransports:
            raise SocketIOError('Could not parse handshake')  # pragma: no cover
        socketURL = '%s://%s/websocket/%s' % (
            'wss' if self._secure else 'ws', baseURL, self._sessionID)
        self._connection = create_connection(socketURL)

    def _recv_packet(self):
        code, packetID, channelName, data = -1, None, None, None
        try:
            packet = self._connection.recv()
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

    def _send_packet(self, code, channelName='', data='', callback=None):
        callbackNumber = self._set_callback(callback) if callback else ''
        packetParts = [str(code), callbackNumber, channelName, data]
        try:
            self._connection.send(':'.join(packetParts))
        except socket.error:
            raise SocketIOPacketError('Could not send packet')

    def disconnect(self, channelName=''):
        self._send_packet(0, channelName)
        if channelName:
            del self._channelByName[channelName]
        else:
            self.__del__()

    @property
    def connected(self):
        return self._connection.connected

    def connect(self, channelName, Namespace=BaseNamespace):
        channel = Channel(self, channelName, Namespace)
        self._channelByName[channelName] = channel
        self._send_packet(1, channelName)
        return channel

    def _send_heartbeat(self):
        try:
            self._send_packet(2)
        except SocketIOPacketError:
            print 'Could not send heartbeat'
            pass

    def message(self, messageData, callback=None, channelName=''):
        if isinstance(messageData, basestring):
            code = 3
            data = messageData
        else:
            code = 4
            data = dumps(messageData)
        self._send_packet(code, channelName, data, callback)

    def emit(self, eventName, *eventArguments, **eventKeywords):
        code = 5
        callback = None
        if eventArguments and callable(eventArguments[-1]):
            callback = eventArguments[-1]
            eventArguments = eventArguments[:-1]
        channelName = eventKeywords.get('channelName', '')
        data = dumps(dict(name=eventName, args=eventArguments))
        self._send_packet(code, channelName, data, callback)

    def _get_callback(self, channelName, eventName):
        'Get callback associated with channelName and eventName'
        socketIO = self._channelByName[channelName] if channelName else self
        try:
            return socketIO._callbackByEvent[eventName]
        except KeyError:
            pass

        def callback_(*eventArguments):
            return socketIO._namespace.on_(eventName, *eventArguments)
        callbackName = 'on_' + eventName.replace(' ', '_')
        return getattr(socketIO._namespace, callbackName, callback_)

    def _set_callback(self, callback):
        'Set callback that will be called after receiving an acknowledgment'
        self._messageID += 1
        self._namespaceThread.set_callback(self._messageID, callback)
        return '%s+' % self._messageID

    def on(self, eventName, callback):
        self._callbackByEvent[eventName] = callback

    def wait(self, seconds=None, forCallbacks=False):
        if forCallbacks:
            self._namespaceThread.wait_for_callbacks(seconds)
        elif seconds:
            sleep(seconds)
        else:
            try:
                while self.connected:
                    sleep(1)
            except KeyboardInterrupt:
                pass


class Channel(object):

    def __init__(self, socketIO, channelName, Namespace):
        self._socketIO = socketIO
        self._channelName = channelName
        self._namespace = Namespace(self)
        self._callbackByEvent = {}

    def disconnect(self):
        self._socketIO.disconnect(self._channelName)

    def emit(self, eventName, *eventArguments):
        self._socketIO.emit(eventName, *eventArguments, channelName=self._channelName)

    def message(self, messageData, callback=None):
        self._socketIO.message(messageData, callback, channelName=self._channelName)

    def on(self, eventName, eventCallback):
        self._callbackByEvent[eventName] = eventCallback


class ListenerThread(Thread):
    'Process messages from SocketIO server'

    daemon = True

    def __init__(self, recv_packet, get_callback):
        super(ListenerThread, self).__init__()
        self.done = Event()
        self.waitingForCallbacks = Event()
        self.callbackByMessageID = {}
        self.recv_packet = recv_packet
        self.get_callback = get_callback

    def run(self):
        try:
            while not self.done.is_set():
                try:
                    code, packetID, channelName, data = self.recv_packet()
                except SocketIOConnectionError, error:
                    print error
                    return
                except SocketIOPacketError, error:
                    print error
                    continue
                get_channel_callback = partial(self.get_callback, channelName)
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
                delegate(packetID, get_channel_callback, data)
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            open('tracebacks.log', 'a+t').write('\n'.join(traceback.format_tb(exc_traceback)))

    def cancel(self):
        self.done.set()

    def wait_for_callbacks(self, seconds):
        self.waitingForCallbacks.set()
        self.join(seconds)

    def set_callback(self, messageID, callback):
        self.callbackByMessageID[messageID] = callback

    def on_disconnect(self, packetID, get_channel_callback, data):
        get_channel_callback('disconnect')()

    def on_connect(self, packetID, get_channel_callback, data):
        get_channel_callback('connect')()

    def on_heartbeat(self, packetID, get_channel_callback, data):
        pass

    def on_message(self, packetID, get_channel_callback, data):
        get_channel_callback('message')(data)

    def on_json(self, packetID, get_channel_callback, data):
        get_channel_callback('message')(loads(data))

    def on_event(self, packetID, get_channel_callback, data):
        valueByName = loads(data)
        eventName = valueByName['name']
        eventArguments = valueByName['args']
        get_channel_callback(eventName)(*eventArguments)

    def on_acknowledgment(self, packetID, get_channel_callback, data):
        dataParts = data.split('+', 1)
        messageID = int(dataParts[0])
        arguments = loads(dataParts[1]) or []
        try:
            callback = self.callbackByMessageID[messageID]
        except KeyError:
            pass
        else:
            del self.callbackByMessageID[messageID]
            callback(*arguments)
            callbackCount = len(self.callbackByMessageID)
            if self.waitingForCallbacks.is_set() and not callbackCount:
                self.cancel()

    def on_error(self, packetID, get_channel_callback, data):
        reason, advice = data.split('+', 1)
        get_channel_callback('error')(reason, advice)


class RhythmicThread(Thread):
    'Execute call every few seconds'

    daemon = True

    def __init__(self, intervalInSeconds, call, *args, **kw):
        super(RhythmicThread, self).__init__()
        self.intervalInSeconds = intervalInSeconds
        self.call = call
        self.args = args
        self.kw = kw
        self.done = Event()

    def run(self):
        try:
            while not self.done.is_set():
                self.call(*self.args, **self.kw)
                self.done.wait(self.intervalInSeconds)
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            open('tracebacks.log', 'a+t').write('\n'.join(traceback.format_tb(exc_traceback)))

    def cancel(self):
        self.done.set()


class SocketIOError(Exception):
    pass


class SocketIOConnectionError(SocketIOError):
    pass


class SocketIOPacketError(SocketIOError):
    pass
