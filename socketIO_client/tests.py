import logging
import time
from unittest import TestCase

from . import SocketIO, LoggingNamespace, find_callback
from .transports import TIMEOUT_IN_SECONDS


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

    def on_response(self, *args):
        for arg in args:
            if isinstance(arg, dict):
                self.assertEqual(arg, PAYLOAD)
            else:
                self.assertEqual(arg, DATA)
        self.called_on_response = True

    def test_disconnect(self):
        'Disconnect'
        self.socketIO.define(LoggingNamespace)
        self.assertTrue(self.socketIO.connected)
        self.socketIO.disconnect()
        self.assertFalse(self.socketIO.connected)
        # Use context manager
        with SocketIO(HOST, PORT, Namespace) as self.socketIO:
            namespace = self.socketIO.get_namespace()
            self.assertFalse(namespace.called_on_disconnect)
            self.assertTrue(self.socketIO.connected)
        self.assertTrue(namespace.called_on_disconnect)
        self.assertFalse(self.socketIO.connected)

    def test_message(self):
        'Message'
        namespace = self.socketIO.define(Namespace)
        self.socketIO.message()
        self.socketIO.wait(self.wait_time_in_seconds)
        self.assertEqual(namespace.response, 'message_response')

    def test_message_with_data(self):
        'Message with data'
        namespace = self.socketIO.define(Namespace)
        self.socketIO.message(DATA)
        self.socketIO.wait(self.wait_time_in_seconds)
        self.assertEqual(namespace.response, DATA)

    def test_message_with_payload(self):
        'Message with payload'
        namespace = self.socketIO.define(Namespace)
        self.socketIO.message(PAYLOAD)
        self.socketIO.wait(self.wait_time_in_seconds)
        self.assertEqual(namespace.response, PAYLOAD)

    def test_message_with_callback(self):
        'Message with callback'
        self.socketIO.define(LoggingNamespace)
        self.socketIO.message(callback=self.on_response)
        self.socketIO.wait_for_callbacks(seconds=self.wait_time_in_seconds)
        self.assertTrue(self.called_on_response)

    def test_message_with_callback_with_data(self):
        'Message with callback with data'
        self.socketIO.define(LoggingNamespace)
        self.socketIO.message(DATA, self.on_response)
        self.socketIO.wait_for_callbacks(seconds=self.wait_time_in_seconds)
        self.assertTrue(self.called_on_response)

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
        self.socketIO.define(LoggingNamespace)
        self.socketIO.emit('emit_with_callback', self.on_response)
        self.socketIO.wait_for_callbacks(seconds=self.wait_time_in_seconds)
        self.assertTrue(self.called_on_response)

    def test_emit_with_callback_with_payload(self):
        'Emit with callback with payload'
        self.socketIO.define(LoggingNamespace)
        self.socketIO.emit(
            'emit_with_callback_with_payload', self.on_response)
        self.socketIO.wait_for_callbacks(seconds=self.wait_time_in_seconds)
        self.assertTrue(self.called_on_response)

    def test_emit_with_callback_with_multiple_payloads(self):
        'Emit with callback with multiple payloads'
        self.socketIO.define(LoggingNamespace)
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

    def test_ack(self):
        'Trigger server callback'
        namespace = self.socketIO.define(Namespace)
        self.socketIO.emit('ack', PAYLOAD)
        self.socketIO.wait(self.wait_time_in_seconds)
        self.assertEqual(namespace.args_by_event, {
            'ack_response': (PAYLOAD,),
            'ack_callback_response': (PAYLOAD,),
        })

    def test_wait_with_disconnect(self):
        'Exit loop when the client wants to disconnect'
        self.socketIO.define(Namespace)
        self.socketIO.emit('wait_with_disconnect')
        timeout_in_seconds = 5
        start_time = time.time()
        self.socketIO.wait(timeout_in_seconds)
        self.assertTrue(time.time() - start_time < timeout_in_seconds)

    def test_namespace_emit(self):
        'Behave differently in different namespaces'
        main_namespace = self.socketIO.define(Namespace)
        chat_namespace = self.socketIO.define(Namespace, '/chat')
        news_namespace = self.socketIO.define(Namespace, '/news')
        news_namespace.emit('emit_with_payload', PAYLOAD)
        self.socketIO.wait(self.wait_time_in_seconds)
        self.assertEqual(main_namespace.args_by_event, {})
        self.assertEqual(chat_namespace.args_by_event, {})
        self.assertEqual(news_namespace.args_by_event, {
            'emit_with_payload_response': (PAYLOAD,),
        })

    def test_namespace_ack(self):
        'Trigger server callback'
        chat_namespace = self.socketIO.define(Namespace, '/chat')
        chat_namespace.emit('ack', PAYLOAD)
        self.socketIO.wait(self.wait_time_in_seconds)
        self.assertEqual(chat_namespace.args_by_event, {
            'ack_response': (PAYLOAD,),
            'ack_callback_response': (PAYLOAD,),
        })


class Test_WebsocketTransport(TestCase, BaseMixin):

    def setUp(self):
        super(Test_WebsocketTransport, self).setUp()
        self.socketIO = SocketIO(HOST, PORT, transports=['websocket'])
        self.wait_time_in_seconds = 0.1


class Test_XHR_PollingTransport(TestCase, BaseMixin):

    def setUp(self):
        super(Test_XHR_PollingTransport, self).setUp()
        self.socketIO = SocketIO(HOST, PORT, transports=['xhr-polling'])
        self.wait_time_in_seconds = TIMEOUT_IN_SECONDS + 1


class Test_JSONP_PollingTransport(TestCase, BaseMixin):

    def setUp(self):
        super(Test_JSONP_PollingTransport, self).setUp()
        self.socketIO = SocketIO(HOST, PORT, transports=['jsonp-polling'])
        self.wait_time_in_seconds = TIMEOUT_IN_SECONDS + 1


class Namespace(LoggingNamespace):

    def initialize(self):
        self.response = None
        self.args_by_event = {}
        self.called_on_disconnect = False

    def on_disconnect(self):
        self.called_on_disconnect = True

    def on_message(self, data):
        self.response = data

    def on_event(self, event, *args):
        callback, args = find_callback(args)
        if callback:
            callback(*args)
        self.args_by_event[event] = args

    def on_wait_with_disconnect_response(self):
        self.disconnect()
