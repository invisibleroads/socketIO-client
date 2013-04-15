'Launch this server in another terminal window before running tests'
try:
    from socketio import socketio_manage
    from socketio.namespace import BaseNamespace
    from socketio.server import SocketIOServer
except ImportError:
    from setuptools.command import easy_install
    easy_install.main(['-U', 'gevent-socketio'])
    print('\nPlease run the script again to launch the test server.')
    import sys; sys.exit(1)


class Namespace(BaseNamespace):

    def on_aaa(self, *args):
        self.emit('aaa_response', *args)


class Application(object):

    def __call__(self, environ, start_response):
        socketio_manage(environ, {
            '': Namespace,
            '/chat': Namespace,
            '/news': Namespace,
        })


if __name__ == '__main__':
    from socketIO_client.tests import PORT
    print 'Starting server at port %s' % PORT
    socketIOServer = SocketIOServer(('0.0.0.0', PORT), Application())
    socketIOServer.serve_forever()
