'Launch this server in another terminal window before running tests'
from socketio import socketio_manage
from socketio.namespace import BaseNamespace
from socketio.server import SocketIOServer


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
    socketIOServer = SocketIOServer(('0.0.0.0', 8000), Application())
    socketIOServer.serve_forever()
