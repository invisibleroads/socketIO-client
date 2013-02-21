from socketIO_client import SocketIO, BaseNamespace
from time import sleep
from unittest import TestCase


PAYLOAD = {'bbb': 'ccc'}
ON_RESPONSE_CALLED = False


class TestSocketIO(TestCase):

    def test_disconnect(self):
        socketIO = SocketIO('localhost', 8000)
        socketIO.disconnect()
        self.assertEqual(False, socketIO.connected)
        childThreads = [
            socketIO._rhythmicThread,
            socketIO._listenerThread,
        ]
        for childThread in childThreads:
            self.assertEqual(True, childThread.done.is_set())

    def test_emit(self):
        socketIO = SocketIO('localhost', 8000)
        socketIO.define(Namespace)
        socketIO.emit('aaa')
        sleep(0.1)
        self.assertEqual(socketIO.get_namespace().payload, '')

    def test_emit_with_payload(self):
        socketIO = SocketIO('localhost', 8000)
        socketIO.define(Namespace)
        socketIO.emit('aaa', PAYLOAD)
        sleep(0.1)
        self.assertEqual(socketIO.get_namespace().payload, PAYLOAD)

    def test_emit_with_callback(self):
        global ON_RESPONSE_CALLED
        ON_RESPONSE_CALLED = False
        socketIO = SocketIO('localhost', 8000)
        socketIO.emit('aaa', PAYLOAD, on_response)
        socketIO.wait(forCallbacks=True)
        self.assertEqual(ON_RESPONSE_CALLED, True)

    def test_message(self):
        global ON_RESPONSE_CALLED
        ON_RESPONSE_CALLED = False
        socketIO = SocketIO('localhost', 8000)
        socketIO.message(PAYLOAD, on_response)
        socketIO.wait(forCallbacks=True)
        self.assertEqual(ON_RESPONSE_CALLED, True)

    def test_events(self):
        global ON_RESPONSE_CALLED
        ON_RESPONSE_CALLED = False
        socketIO = SocketIO('localhost', 8000)
        socketIO.on('ddd', on_response)
        socketIO.emit('aaa', PAYLOAD)
        sleep(0.1)
        self.assertEqual(ON_RESPONSE_CALLED, True)

    def test_channels(self):
        socketIO = SocketIO('localhost', 8000)
        mainSocket = socketIO.define(Namespace)
        chatSocket = socketIO.define(Namespace, '/chat')
        newsSocket = socketIO.define(Namespace, '/news')
        self.assertNotEqual(mainSocket.get_namespace().payload, PAYLOAD)
        self.assertNotEqual(chatSocket.get_namespace().payload, PAYLOAD)
        self.assertNotEqual(newsSocket.get_namespace().payload, PAYLOAD)
        newsSocket.emit('aaa', PAYLOAD)
        sleep(0.1)
        self.assertEqual(newsSocket.get_namespace().payload, PAYLOAD)

    def test_channels_with_callback(self):
        global ON_RESPONSE_CALLED
        ON_RESPONSE_CALLED = False
        socketIO = SocketIO('localhost', 8000)
        mainSocket = socketIO.get_channel()
        mainSocket.message(PAYLOAD, on_response)
        sleep(0.1)
        self.assertEqual(ON_RESPONSE_CALLED, True)

    def test_delete(self):
        socketIO = SocketIO('localhost', 8000)
        childThreads = [
            socketIO._rhythmicThread,
            socketIO._listenerThread,
        ]
        del socketIO
        for childThread in childThreads:
            self.assertEqual(True, childThread.done.is_set())


class Namespace(BaseNamespace):

    payload = None

    def on_ddd(self, data=''):
        print '[Event] ddd(%s)' % data
        self.payload = data


def on_response(*args):
    global ON_RESPONSE_CALLED
    ON_RESPONSE_CALLED = True
