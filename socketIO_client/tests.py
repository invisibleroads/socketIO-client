from socketIO_client import SocketIO, BaseNamespace
from time import sleep
from unittest import TestCase


ON_RESPONSE_CALLED = False
PORT = 8000
PAYLOAD = {'xxx': 'yyy'}


class TestSocketIO(TestCase):

    def setUp(self):
        global ON_RESPONSE_CALLED
        ON_RESPONSE_CALLED = False
        self.socketIO = SocketIO('localhost', PORT)

    def tearDown(self):
        del self.socketIO

    def test_emit(self):
        self.socketIO.define(Namespace)
        self.socketIO.emit('aaa')
        sleep(0.1)
        self.assertEqual(self.socketIO.get_namespace().payload, '')

    def test_emit_with_payload(self):
        self.socketIO.define(Namespace)
        self.socketIO.emit('aaa', PAYLOAD)
        sleep(0.1)
        self.assertEqual(self.socketIO.get_namespace().payload, PAYLOAD)

    def test_emit_with_callback(self):
        self.socketIO.emit('aaa', PAYLOAD, on_response)
        self.socketIO.wait(forCallbacks=True)
        self.assertEqual(ON_RESPONSE_CALLED, True)

    def test_message(self):
        self.socketIO.message(PAYLOAD, on_response)
        self.socketIO.wait(forCallbacks=True)
        self.assertEqual(ON_RESPONSE_CALLED, True)

    def test_events(self):
        self.socketIO.on('aaa_response', on_response)
        self.socketIO.emit('aaa', PAYLOAD)
        sleep(0.1)
        self.assertEqual(ON_RESPONSE_CALLED, True)

    def test_namespaces(self):
        mainNamespace = self.socketIO.define(Namespace)
        chatNamespace = self.socketIO.define(Namespace, '/chat')
        newsNamespace = self.socketIO.define(Namespace, '/news')
        self.assertNotEqual(mainNamespace.payload, PAYLOAD)
        self.assertNotEqual(chatNamespace.payload, PAYLOAD)
        self.assertNotEqual(newsNamespace.payload, PAYLOAD)
        newsNamespace.emit('aaa', PAYLOAD)
        sleep(0.1)
        self.assertEqual(newsNamespace.payload, PAYLOAD)

    def test_namespaces_with_callback(self):
        mainNamespace = self.socketIO.get_namespace()
        mainNamespace.message(PAYLOAD, on_response)
        sleep(0.1)
        self.assertEqual(ON_RESPONSE_CALLED, True)

    def test_disconnect(self):
        childThreads = [
            self.socketIO._rhythmicThread,
            self.socketIO._listenerThread,
        ]
        self.socketIO.disconnect()
        for childThread in childThreads:
            self.assertEqual(True, childThread.done.is_set())
        self.assertEqual(False, self.socketIO.connected)


class Namespace(BaseNamespace):

    payload = None

    def on_aaa_response(self, data=''):
        print '[Event] aaa_response(%s)' % data
        self.payload = data


def on_response(*args):
    global ON_RESPONSE_CALLED
    ON_RESPONSE_CALLED = True
