from socketIO_client import SocketIO, BaseNamespace, find_callback
from unittest import TestCase


HOST = 'localhost'
PORT = 8000
DATA = 'xxx'
PAYLOAD = {'xxx': 'yyy'}


class TestSocketIO(TestCase):

    def setUp(self):
        self.socketIO = SocketIO(HOST, PORT)
        self.called_on_response = False

    def tearDown(self):
        del self.socketIO

    def on_response(self, *args):
        self.called_on_response = True
        for arg in args:
            if isinstance(arg, dict):
                self.assertEqual(arg, PAYLOAD)
            else:
                self.assertEqual(arg, DATA)

    def is_connected(self, socketIO, connected):
        childThreads = [
            socketIO._rhythmicThread,
            socketIO._listenerThread,
        ]
        for childThread in childThreads:
            self.assertEqual(not connected, childThread.done.is_set())
        self.assertEqual(connected, socketIO.connected)

    def test_disconnect(self):
        'Terminate child threads after disconnect'
        self.is_connected(self.socketIO, True)
        self.socketIO.disconnect()
        self.is_connected(self.socketIO, False)
        # Use context manager
        with SocketIO(HOST, PORT) as self.socketIO:
            self.is_connected(self.socketIO, True)
        self.is_connected(self.socketIO, False)

    def test_message(self):
        'Message'
        self.socketIO.define(Namespace)
        self.socketIO.message()
        self.socketIO.wait(0.1)
        namespace = self.socketIO.get_namespace()
        self.assertEqual(namespace.response, 'message_response')

    def test_message_with_data(self):
        'Message with data'
        self.socketIO.define(Namespace)
        self.socketIO.message(DATA)
        self.socketIO.wait(0.1)
        namespace = self.socketIO.get_namespace()
        self.assertEqual(namespace.response, DATA)

    def test_message_with_payload(self):
        'Message with payload'
        self.socketIO.define(Namespace)
        self.socketIO.message(PAYLOAD)
        self.socketIO.wait(0.1)
        namespace = self.socketIO.get_namespace()
        self.assertEqual(namespace.response, PAYLOAD)

    def test_message_with_callback(self):
        'Message with callback'
        self.socketIO.message(callback=self.on_response)
        self.socketIO.wait_for_callbacks(seconds=0.1)
        self.assertEqual(self.called_on_response, True)

    def test_message_with_callback_with_data(self):
        'Message with callback with data'
        self.socketIO.message(DATA, self.on_response)
        self.socketIO.wait_for_callbacks(seconds=0.1)
        self.assertEqual(self.called_on_response, True)

    def test_emit(self):
        'Emit'
        self.socketIO.define(Namespace)
        self.socketIO.emit('emit')
        self.socketIO.wait(0.1)
        self.assertEqual(self.socketIO.get_namespace().argsByEvent, {
            'emit_response': (),
        })

    def test_emit_with_payload(self):
        'Emit with payload'
        self.socketIO.define(Namespace)
        self.socketIO.emit('emit_with_payload', PAYLOAD)
        self.socketIO.wait(0.1)
        self.assertEqual(self.socketIO.get_namespace().argsByEvent, {
            'emit_with_payload_response': (PAYLOAD,),
        })

    def test_emit_with_multiple_payloads(self):
        'Emit with multiple payloads'
        self.socketIO.define(Namespace)
        self.socketIO.emit('emit_with_multiple_payloads', PAYLOAD, PAYLOAD)
        self.socketIO.wait(0.1)
        self.assertEqual(self.socketIO.get_namespace().argsByEvent, {
            'emit_with_multiple_payloads_response': (PAYLOAD, PAYLOAD),
        })

    def test_emit_with_callback(self):
        'Emit with callback'
        self.socketIO.emit('emit_with_callback', self.on_response)
        self.socketIO.wait_for_callbacks(seconds=0.1)
        self.assertEqual(self.called_on_response, True)

    def test_emit_with_callback_with_payload(self):
        'Emit with callback with payload'
        self.socketIO.emit('emit_with_callback_with_payload',
                           self.on_response)
        self.socketIO.wait_for_callbacks(seconds=0.1)
        self.assertEqual(self.called_on_response, True)

    def test_emit_with_callback_with_multiple_payloads(self):
        'Emit with callback with multiple payloads'
        self.socketIO.emit('emit_with_callback_with_multiple_payloads',
                           self.on_response)
        self.socketIO.wait_for_callbacks(seconds=0.1)
        self.assertEqual(self.called_on_response, True)

    def test_emit_with_event(self):
        'Emit to trigger an event'
        self.socketIO.on('emit_with_event_response', self.on_response)
        self.socketIO.emit('emit_with_event', PAYLOAD)
        self.socketIO.wait_for_callbacks(0.1)
        self.assertEqual(self.called_on_response, True)

    def test_ack(self):
        'Trigger server callback'
        self.socketIO.define(Namespace)
        self.socketIO.emit('ack', PAYLOAD)
        self.socketIO.wait(0.1)
        self.assertEqual(self.socketIO.get_namespace().argsByEvent, {
            'ack_response': (PAYLOAD,),
            'ack_callback_response': (PAYLOAD,),
        })

    def test_namespaces(self):
        'Behave differently in different namespaces'
        mainNamespace = self.socketIO.define(Namespace)
        chatNamespace = self.socketIO.define(Namespace, '/chat')
        newsNamespace = self.socketIO.define(Namespace, '/news')
        newsNamespace.emit('emit_with_payload', PAYLOAD)
        self.socketIO.wait(0.1)
        self.assertEqual(mainNamespace.argsByEvent, {})
        self.assertEqual(chatNamespace.argsByEvent, {})
        self.assertEqual(newsNamespace.argsByEvent, {
            'emit_with_payload_response': (PAYLOAD,),
        })


class Namespace(BaseNamespace):

    def initialize(self):
        self.response = None
        self.argsByEvent = {}

    def on_message(self, data):
        self.response = data

    def on_event(self, event, *args):
        callback, args = find_callback(args)
        if callback:
            callback(*args)
        self.argsByEvent[event] = args
