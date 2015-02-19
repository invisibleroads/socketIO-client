import logging
from unittest import TestCase

from .. import SocketIO, LoggingSocketIONamespace, find_callback


HOST = 'localhost'
PORT = 8000
logging.basicConfig(level=logging.DEBUG)


class BaseMixin(object):

    def test_emit(self):
        'Emit'
        namespace = self.socketIO.define(Namespace)
        self.socketIO.emit('emit')
        self.socketIO.wait(self.wait_time_in_seconds)
        self.assertEqual(namespace.args_by_event, {
            'emit_response': (),
        })


class Test_XHR_PollingTransport(TestCase, BaseMixin):

    def setUp(self):
        super(Test_XHR_PollingTransport, self).setUp()
        self.socketIO = SocketIO(HOST, PORT, transports=['xhr-polling'])
        self.wait_time_in_seconds = 1


class Namespace(LoggingSocketIONamespace):

    def initialize(self):
        self.args_by_event = {}

    def on_event(self, event, *args):
        print 'xxx *** xxx'
        callback, args = find_callback(args)
        if callback:
            callback(*args)
        self.args_by_event[event] = args
