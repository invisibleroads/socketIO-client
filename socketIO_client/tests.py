from socketIO_client import SocketIO, BaseNamespace
from time import sleep
from unittest import TestCase


from socketio import socketio_manage
from socketio.namespace import BaseNamespace as SIOBaseNameSpace
from socketio.server import SocketIOServer

from multiprocessing import Process


class SIONamespace(SIOBaseNameSpace):

    def on_aaa(self, *args):
        self.socket.send_packet(dict(
            type='event',
            name='ddd',
            args=args,
            endpoint=self.ns_name))


class Application(object):

    def __call__(self, environ, start_response):
        socketio_manage(environ, {
            '': SIONamespace,
            '/chat': SIONamespace,
            '/news': SIONamespace,
        })


socketIOServer = SocketIOServer(('0.0.0.0', 8000), Application())

p = Process(target=socketIOServer.serve_forever)


def setup_module(module):
    p.start()


def teardown_module(module):
    p.terminate()


PAYLOAD = {'bbb': 'ccc'}
ON_RESPONSE_CALLED = False


class TestSocketIO(TestCase):

    def test_disconnect(self):
        socketIO = SocketIO('localhost', 8000)
        socketIO.disconnect()
        self.assertEqual(socketIO.connected, False)

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
        socketIO.wait(forCallbacks=True)
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
