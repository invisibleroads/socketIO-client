from .logs import LoggingMixin


class EngineIONamespace(LoggingMixin):
    'Define engine.io client behavior'

    def __init__(self, io):
        self._io = io
        self._callback_by_event = {}
        self._once_events = set()
        self._log_name = io._url
        self.initialize()

    def initialize(self):
        """Initialize custom variables here.
        You can override this method."""

    def on(self, event, callback):
        'Define a callback to handle an event emitted by the server'
        self._callback_by_event[event] = callback

    def once(self, event, callback):
        'Define a callback to handle the first event emitted by the server'
        self._once_events.add(event)
        self.on(event, callback)

    def off(self, event):
        'Remove an event handler'
        try:
            self._once_events.remove(event)
        except KeyError:
            pass
        self._callback_by_event.pop(event, None)

    def send(self, data):
        'Send a message'
        self._io.send(data)

    def on_open(self):
        """Called when client receives open packet from engine.io server.
        You can override this method."""

    def on_close(self):
        """Called when client receives close packet from engine.io server.
        You can override this method."""

    def on_ping(self, data):
        """Called when client receives ping packet from engine.io server.
        You can override this method."""

    def on_pong(self, data):
        """Called when client receives pong packet from engine.io server.
        You can override this method."""

    def on_message(self, data):
        """Called when client receives message packet from engine.io server.
        You can override this method."""

    def on_upgrade(self):
        """Called when client receives upgrade packet from engine.io server.
        You can override this method."""

    def on_noop(self):
        """Called when client receives noop packet from engine.io server.
        You can override this method."""

    def _find_packet_callback(self, event):
        # Check callbacks defined by on()
        try:
            callback = self._callback_by_event[event]
        except KeyError:
            pass
        else:
            if event in self._once_events:
                self.off(event)
            return callback
        # Check callbacks defined explicitly
        return getattr(self, 'on_' + event)


class SocketIONamespace(EngineIONamespace):
    'Define socket.io client behavior'

    def __init__(self, io, path):
        self.path = path
        super(SocketIONamespace, self).__init__(io)

    def connect(self):
        self._io.connect(self.path)

    def disconnect(self):
        self._io.disconnect(self.path)

    def emit(self, event, *args, **kw):
        self._io.emit(event, path=self.path, *args, **kw)

    def send(self, data='', callback=None):
        self._io.send(data, callback)

    def on_connect(self):
        """Called when client receives first connect packet from socket.io
        server. You can override this method."""

    def on_reconnect(self):
        """Called when client receives subsequent connect packet from
        socket.io server. You can override this method."""

    def on_disconnect(self):
        """Called when client receives disconnect packet from socket.io
        server. You can override this method."""

    def on_event(self, event, *args):
        """Called if there is no matching event handler.
        You can override this method.
        There are three ways to define an event handler:

        - Call socketIO.on()

            socketIO = SocketIO('localhost', 8000)
            socketIO.on('my_event', my_function)

        - Call namespace.on()

            namespace = socketIO.get_namespace()
            namespace.on('my_event', my_function)

        - Define namespace.on_xxx

            class Namespace(SocketIONamespace):

                def on_my_event(self, *args):
                    my_function(*args)

            socketIO.define(Namespace)"""

    def on_error(self, data):
        """Called when client receives error packet from socket.io server.
        You can override this method."""
        if data.lower() == 'invalid namespace':
            self._invalid = True

    def _find_packet_callback(self, event):
        # Interpret events
        if event == 'connect':
            if not hasattr(self, '_was_connected'):
                self._was_connected = True
            else:
                event = 'reconnect'
        # Check callbacks defined by on()
        try:
            callback = self._callback_by_event[event]
        except KeyError:
            pass
        else:
            if event in self._once_events:
                self.off(event)
            return callback
        # Check callbacks defined explicitly or use on_event()
        return getattr(
            self, 'on_' + event.replace(' ', '_'),
            lambda *args: self.on_event(event, *args))


class LoggingEngineIONamespace(EngineIONamespace):

    def on_open(self):
        self._debug('[engine.io open]')
        super(LoggingEngineIONamespace, self).on_open()

    def on_close(self):
        self._debug('[engine.io close]')
        super(LoggingEngineIONamespace, self).on_close()

    def on_ping(self, data):
        self._debug('[engine.io ping] %s', data)
        super(LoggingEngineIONamespace, self).on_ping(data)

    def on_pong(self, data):
        self._debug('[engine.io pong] %s', data)
        super(LoggingEngineIONamespace, self).on_pong(data)

    def on_message(self, data):
        self._debug('[engine.io message] %s', data)
        super(LoggingEngineIONamespace, self).on_message(data)

    def on_upgrade(self):
        self._debug('[engine.io upgrade]')
        super(LoggingEngineIONamespace, self).on_upgrade()

    def on_noop(self):
        self._debug('[engine.io noop]')
        super(LoggingEngineIONamespace, self).on_noop()

    def on_event(self, event, *args):
        callback, args = find_callback(args)
        arguments = [repr(_) for _ in args]
        if callback:
            arguments.append('callback(*args)')
        self._info('[engine.io event] %s(%s)', event, ', '.join(arguments))
        super(LoggingEngineIONamespace, self).on_event(event, *args)


class LoggingSocketIONamespace(SocketIONamespace, LoggingEngineIONamespace):

    def on_connect(self):
        self._debug(
            '%s[socket.io connect]', make_logging_prefix(self.path))
        super(LoggingSocketIONamespace, self).on_connect()

    def on_reconnect(self):
        self._debug(
            '%s[socket.io reconnect]', make_logging_prefix(self.path))
        super(LoggingSocketIONamespace, self).on_reconnect()

    def on_disconnect(self):
        self._debug(
            '%s[socket.io disconnect]', make_logging_prefix(self.path))
        super(LoggingSocketIONamespace, self).on_disconnect()

    def on_event(self, event, *args):
        callback, args = find_callback(args)
        arguments = [repr(_) for _ in args]
        if callback:
            arguments.append('callback(*args)')
        self._info(
            '%s[socket.io event] %s(%s)', make_logging_prefix(self.path),
            event, ', '.join(arguments))
        super(LoggingSocketIONamespace, self).on_event(event, *args)

    def on_error(self, data):
        self._warn(
            '%s[socket.io error] %s', make_logging_prefix(self.path), data)
        super(LoggingSocketIONamespace, self).on_error(data)


def find_callback(args, kw=None):
    'Return callback whether passed as a last argument or as a keyword'
    if args and callable(args[-1]):
        return args[-1], args[:-1]
    try:
        return kw['callback'], args
    except (KeyError, TypeError):
        return None, args


def make_logging_prefix(path):
    return path + ' ' if path else ''
