'Launch this server in another terminal window before running tests'
import sys
try:
    from socketio import socketio_manage
    from socketio.namespace import BaseNamespace
    from socketio.server import SocketIOServer
except ImportError:
    from setuptools.command import easy_install
    easy_install.main(['-U', 'gevent-socketio'])
    print('\nPlease run the script again to launch the test server.')
    sys.exit(1)


class Namespace(BaseNamespace):

    def on_aaa(self, *args):
        self.socket.send_packet(dict(
            type='event',
            name='ddd',
            args=args,
            endpoint=self.ns_name))


class Application(object):

    def __call__(self, environ, start_response):
        socketio_manage(environ, {
            '': Namespace,
            '/chat': Namespace,
            '/news': Namespace,
        })


if __name__ == '__main__':
    port = 8000
    print 'Starting server at port %s' % port
    socketIOServer = SocketIOServer(('0.0.0.0', port), Application())
    socketIOServer.serve_forever()
