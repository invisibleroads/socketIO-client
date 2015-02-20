import logging
from unittest import TestCase

from .. import SocketIO, LoggingSocketIONamespace, find_callback


HOST = 'localhost'
PORT = 8000
DATA = 'xxx'
PAYLOAD = {'xxx': 'yyy'}
logging.basicConfig(level=logging.DEBUG)


class BaseMixin(object):

    def setUp(self):
        self.called_on_response = False

    def tearDown(self):
        del self.socketIO

    def test_emit(self):
        'Emit'
        namespace = self.socketIO.define(Namespace)
        self.socketIO.emit('emit')
        self.socketIO.wait(self.wait_time_in_seconds)
        self.assertEqual(namespace.args_by_event, {
            'emit_response': (),
        })

    def test_emit_with_payload(self):
        'Emit with payload'
        namespace = self.socketIO.define(Namespace)
        self.socketIO.emit('emit_with_payload', PAYLOAD)
        self.socketIO.wait(self.wait_time_in_seconds)
        self.assertEqual(namespace.args_by_event, {
            'emit_with_payload_response': (PAYLOAD,),
        })

    def test_emit_with_multiple_payloads(self):
        'Emit with multiple payloads'
        namespace = self.socketIO.define(Namespace)
        self.socketIO.emit('emit_with_multiple_payloads', PAYLOAD, PAYLOAD)
        self.socketIO.wait(self.wait_time_in_seconds)
        self.assertEqual(namespace.args_by_event, {
            'emit_with_multiple_payloads_response': (PAYLOAD, PAYLOAD),
        })

    def test_emit_with_callback(self):
        'Emit with callback'
        self.socketIO.define(LoggingSocketIONamespace)
        self.socketIO.emit('emit_with_callback', self.on_response)
        self.socketIO.wait_for_callbacks(seconds=self.wait_time_in_seconds)
        self.assertTrue(self.called_on_response)

    def test_emit_with_callback_with_payload(self):
        'Emit with callback with payload'
        self.socketIO.define(LoggingSocketIONamespace)
        self.socketIO.emit(
            'emit_with_callback_with_payload', self.on_response)
        self.socketIO.wait_for_callbacks(seconds=self.wait_time_in_seconds)
        self.assertTrue(self.called_on_response)

    def test_emit_with_callback_with_multiple_payloads(self):
        'Emit with callback with multiple payloads'
        self.socketIO.define(LoggingSocketIONamespace)
        self.socketIO.emit(
            'emit_with_callback_with_multiple_payloads', self.on_response)
        self.socketIO.wait_for_callbacks(seconds=self.wait_time_in_seconds)
        self.assertTrue(self.called_on_response)

    def test_emit_with_event(self):
        'Emit to trigger an event'
        self.socketIO.on('emit_with_event_response', self.on_response)
        self.socketIO.emit('emit_with_event', PAYLOAD)
        self.socketIO.wait(self.wait_time_in_seconds)
        self.assertTrue(self.called_on_response)

    def test_send(self):
        'Send'
        namespace = self.socketIO.define(Namespace)
        self.socketIO.send()
        self.socketIO.wait(self.wait_time_in_seconds)
        self.assertEqual(namespace.response, 'message_response')

    def test_send_with_data(self):
        'Send with data'
        namespace = self.socketIO.define(Namespace)
        self.socketIO.send(DATA)
        self.socketIO.wait(self.wait_time_in_seconds)
        self.assertEqual(namespace.response, DATA)

    def on_response(self, *args):
        for arg in args:
            if isinstance(arg, dict):
                self.assertEqual(arg, PAYLOAD)
            else:
                self.assertEqual(arg, DATA)
        self.called_on_response = True


# class Test_WebsocketTransport(TestCase, BaseMixin):

    # def setUp(self):
        # super(Test_WebsocketTransport, self).setUp()
        # self.socketIO = SocketIO(HOST, PORT, transports=['websocket'])
        # self.wait_time_in_seconds = 0.1


class Test_XHR_PollingTransport(TestCase, BaseMixin):

    def setUp(self):
        super(Test_XHR_PollingTransport, self).setUp()
        self.socketIO = SocketIO(HOST, PORT, transports=['xhr-polling'])
        self.wait_time_in_seconds = 1


class Namespace(LoggingSocketIONamespace):

    def initialize(self):
        self.called_on_disconnect = False
        self.args_by_event = {}
        self.response = None

    def on_disconnect(self):
        self.called_on_disconnect = True

    def on_wait_with_disconnect_response(self):
        self.disconnect()

    def on_event(self, event, *args):
        callback, args = find_callback(args)
        if callback:
            callback(*args)
        self.args_by_event[event] = args

    def on_message(self, data):
        self.response = data
