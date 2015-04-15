import logging
import time
from unittest import TestCase

from .. import SocketIO, LoggingNamespace, find_callback


HOST = 'localhost'
PORT = 9000
DATA = 'xxx'
PAYLOAD = {'xxx': 'yyy'}
logging.basicConfig(level=logging.DEBUG)


class BaseMixin(object):

    def setUp(self):
        super(BaseMixin, self).setUp()
        self.called_on_response = False
        self.wait_time_in_seconds = 1

    def tearDown(self):
        super(BaseMixin, self).tearDown()
        self.socketIO.disconnect()

    def test_disconnect(self):
        'Disconnect'
        namespace = self.socketIO.define(Namespace)
        self.assertTrue(self.socketIO.connected)
        self.assertFalse(namespace.called_on_disconnect)
        self.socketIO.disconnect()
        self.assertTrue(namespace.called_on_disconnect)
        self.assertFalse(self.socketIO.connected)

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
        self.socketIO.emit('emit_with_callback', self.on_response)
        self.socketIO.wait_for_callbacks(seconds=self.wait_time_in_seconds)
        self.assertTrue(self.called_on_response)

    def test_emit_with_callback_with_payload(self):
        'Emit with callback with payload'
        self.socketIO.emit(
            'emit_with_callback_with_payload', self.on_response)
        self.socketIO.wait_for_callbacks(seconds=self.wait_time_in_seconds)
        self.assertTrue(self.called_on_response)

    def test_emit_with_callback_with_multiple_payloads(self):
        'Emit with callback with multiple payloads'
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

    def test_ack(self):
        'Respond to a server callback request'
        namespace = self.socketIO.define(Namespace)
        self.socketIO.emit('trigger_server_expects_callback', PAYLOAD)
        self.socketIO.wait(self.wait_time_in_seconds)
        self.assertEqual(namespace.args_by_event, {
            'server_expects_callback': (PAYLOAD,),
            'server_received_callback': (PAYLOAD,),
        })

    def test_wait_with_disconnect(self):
        'Exit loop when the client wants to disconnect'
        self.socketIO.define(Namespace)
        self.socketIO.disconnect()
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
        'Respond to a server callback request within a namespace'
        chat_namespace = self.socketIO.define(Namespace, '/chat')
        chat_namespace.emit('trigger_server_expects_callback', PAYLOAD)
        self.socketIO.wait(self.wait_time_in_seconds)
        self.assertEqual(chat_namespace.args_by_event, {
            'server_expects_callback': (PAYLOAD,),
            'server_received_callback': (PAYLOAD,),
        })

    def on_response(self, *args):
        for arg in args:
            if isinstance(arg, dict):
                self.assertEqual(arg, PAYLOAD)
            else:
                self.assertEqual(arg, DATA)
        self.called_on_response = True


class Test_XHR_PollingTransport(BaseMixin, TestCase):

    def setUp(self):
        super(Test_XHR_PollingTransport, self).setUp()
        self.socketIO = SocketIO(HOST, PORT, LoggingNamespace, transports=[
            'xhr-polling'], verify=False)
        self.assertEqual(self.socketIO.transport_name, 'xhr-polling')


class Test_WebsocketTransport(BaseMixin, TestCase):

    def setUp(self):
        super(Test_WebsocketTransport, self).setUp()
        self.socketIO = SocketIO(HOST, PORT, LoggingNamespace, transports=[
            'xhr-polling', 'websocket'], verify=False)
        self.assertEqual(self.socketIO.transport_name, 'websocket')


class Namespace(LoggingNamespace):

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
