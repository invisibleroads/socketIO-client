'Launch this server in another terminal window before running tests'
try:
    from socketio import socketio_manage
    from socketio.namespace import BaseNamespace
    from socketio.server import SocketIOServer
except ImportError:
    import sys
    from setuptools.command import easy_install
    easy_install.main(['-U', 'gevent-socketio'])
    print('\nPlease run the script again to launch the test server.')
    sys.exit(1)


class Namespace(BaseNamespace):

    def on_aaa(self, *args):
        self.emit('aaa_response', *args)

    def on_bbb(self, *args):
        def callback(*args):
            self.emit('callback_response', *args)
        self.emit('bbb_response', *args, callback=callback)


class App(object):

    def __call__(self, environ, start_response):
        socketio_manage(environ, {
            '': Namespace,
            '/chat': Namespace,
            '/news': Namespace,
        })


if __name__ == '__main__':
    from socketIO_client.tests import PORT
    print 'Starting server at port %s' % PORT
    try:
        server = SocketIOServer(('0.0.0.0', PORT), App())
        server.serve_forever()
    except KeyboardInterrupt:
        pass
