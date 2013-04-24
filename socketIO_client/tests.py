from socketIO_client import SocketIO, BaseNamespace, find_callback
from time import sleep
from unittest import TestCase


PORT = 8000
PAYLOAD = {'xxx': 'yyy'}


class TestSocketIO(TestCase):

    def setUp(self):
        self.socketIO = SocketIO('localhost', PORT)
        self.called_on_response = False

    def tearDown(self):
        del self.socketIO

    def on_response(self, *args):
        self.called_on_response = True
        callback, args = find_callback(args)
        if callback:
            callback(*args)

    def test_disconnect(self):
        childThreads = [
            self.socketIO._rhythmicThread,
            self.socketIO._listenerThread,
        ]
        self.socketIO.disconnect()
        for childThread in childThreads:
            self.assertEqual(True, childThread.done.is_set())
        self.assertEqual(False, self.socketIO.connected)

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
        self.socketIO.emit('aaa', PAYLOAD, self.on_response)
        self.socketIO.wait(seconds=0.1, forCallbacks=True)
        self.assertEqual(self.called_on_response, True)

    def test_emit_with_event(self):
        self.socketIO.on('aaa_response', self.on_response)
        self.socketIO.emit('aaa', PAYLOAD)
        sleep(0.1)
        self.assertEqual(self.called_on_response, True)

    def test_message(self):
        self.socketIO.message(PAYLOAD, self.on_response)
        self.socketIO.wait(seconds=0.1, forCallbacks=True)
        self.assertEqual(self.called_on_response, True)

    def test_ack(self):
        self.socketIO.on('bbb_response', self.on_response)
        self.socketIO.emit('bbb', PAYLOAD)
        sleep(0.1)
        self.assertEqual(self.called_on_response, True)

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
        mainNamespace.message(PAYLOAD, self.on_response)
        sleep(0.1)
        self.assertEqual(self.called_on_response, True)


class Namespace(BaseNamespace):

    payload = None

    def on_aaa_response(self, data=''):
        print '[Event] aaa_response(%s)' % data
        self.payload = data
