from socketIOClient import SocketIO, BaseNamespace
from time import sleep
from unittest import TestCase


PAYLOAD = {'bbb': 'ccc'}
ON_RESPONSE_CALLED = False


class TestSocketIO(TestCase):

    def test_emit(self):
        socketIO = SocketIO('localhost', 8000, Namespace)
        socketIO.emit('aaa', PAYLOAD)
        sleep(0.5)
        self.assertEqual(socketIO.namespace.payload, PAYLOAD)

    def test_emit_with_callback(self):
        global ON_RESPONSE_CALLED
        ON_RESPONSE_CALLED = False
        socketIO = SocketIO('localhost', 8000)
        socketIO.emit('aaa', PAYLOAD, on_response)
        socketIO.wait()
        self.assertEqual(ON_RESPONSE_CALLED, True)

    def test_events(self):
        global ON_RESPONSE_CALLED
        ON_RESPONSE_CALLED = False
        socketIO = SocketIO('localhost', 8000)
        socketIO.on('ddd', on_response)
        socketIO.emit('aaa', PAYLOAD)
        sleep(0.5)
        self.assertEqual(ON_RESPONSE_CALLED, True)

    def test_channels(self):
        mainSocket = SocketIO('localhost', 8000, Namespace)
        chatSocket = mainSocket.connect('/chat', Namespace)
        newsSocket = mainSocket.connect('/news', Namespace)
        newsSocket.emit('aaa', PAYLOAD)
        sleep(0.5)
        self.assertNotEqual(mainSocket.namespace.payload, PAYLOAD)
        self.assertNotEqual(chatSocket.namespace.payload, PAYLOAD)
        self.assertEqual(newsSocket.namespace.payload, PAYLOAD)


class Namespace(BaseNamespace):

    payload = None

    def on_ddd(self, data):
        self.payload = data


def on_response(*args):
    global ON_RESPONSE_CALLED
    ON_RESPONSE_CALLED = True
