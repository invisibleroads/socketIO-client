socketIO-client
===============
Here is a socket.io_ client library for Python.  You can use it to write test code for your socket.io_ server.

Thanks to rod_ for the `StackOverflow question and answer`__ on which this code is based.

Thanks to liris_ for websocket-client_ and to guille_ for the `socket.io specification`_.

Thanks to `Paul Kienzle`_, `Josh VanderLinden`_, `Ian Fitzpatrick`_ for submitting code to expand support of the socket.io protocol.


Installation
------------
::

    VIRTUAL_ENV=$HOME/.virtualenv

    # Prepare isolated environment
    virtualenv $VIRTUAL_ENV

    # Activate isolated environment
    source $VIRTUAL_ENV/bin/activate

    # Install package
    easy_install -U socketIO-client


Usage
-----
Activate isolated environment. ::

    VIRTUAL_ENV=$HOME/.virtualenv
    source $VIRTUAL_ENV/bin/activate

Emit. ::

    from socketIO_client import SocketIO
    with SocketIO('localhost', 8000) as socketIO:
        socketIO.emit('aaa')
        socketIO.wait(1)  # Wait a second

Emit with callback. ::

    from socketIO_client import SocketIO

    def on_response(*args):
        print args

    with SocketIO('localhost', 8000) as socketIO:
        socketIO.emit('aaa', {'bbb': 'ccc'}, on_response)
        socketIO.wait(seconds=1, forCallbacks=True)  # Wait for callback

Define events. ::

    from socketIO_client import SocketIO

    def on_ddd(*args):
        print args

    socketIO = SocketIO('localhost', 8000)
    socketIO.on('ddd', on_ddd)
    socketIO.wait()  # Loop until CTRL-C

Define events in a namespace. ::

    from socketIO_client import SocketIO, BaseNamespace

    class Namespace(BaseNamespace):

        def on_ddd(self, *args):
            self.socketIO.emit('eee', {'fff': 'ggg'})

    socketIO = SocketIO('localhost', 8000)
    socketIO.define(Namespace)
    socketIO.wait()  # Loop until CTRL-C

Define standard events. ::

    from socketIO_client import SocketIO, BaseNamespace

    class Namespace(BaseNamespace):

        def on_connect(self):
            print '[Connected]'

        def on_disconnect(self):
            print '[Disconnected]'

        def on_error(self, reason, advice):
            print '[Error] %s' % advice

        def on_message(self, messageData):
            print '[Message] %s' % messageData

    socketIO = SocketIO('localhost', 8000)
    socketIO.define(Namespace)
    socketIO.wait()  # Loop until CTRL-C

Define different namespaces on a single socket. ::

    from socketIO_client import SocketIO, BaseNamespace

    class MainNamespace(BaseNamespace):

        def on_aaa(self, *args):
            print 'aaa', args

    class ChatNamespace(BaseNamespace):

        def on_bbb(self, *args):
            print 'bbb', args

    class NewsNamespace(BaseNamespace):

        def on_ccc(self, *args):
            print 'ccc', args

    socketIO = SocketIO('localhost', 8000)
    socketIO.define(MainNamespace)
    chatSocket = socketIO.define(ChatNamespace, '/chat')
    chatSocket.emit('bbb')
    newsSocket = socketIO.define(NewsNamespace, '/news')
    newsSocket.emit('ccc')
    socketIO.wait()  # Loop until CTRL-C

Open secure websockets (HTTPS / WSS) behind a proxy. ::

    SocketIO('localhost', 8000, 
        secure=True,
        proxies={'http': 'http://proxy.example.com:8080'})


License
-------
This software is available under the MIT License.


.. _socket.io: http://socket.io
.. _rod: http://stackoverflow.com/users/370115/rod
.. _StackOverflowQA: http://stackoverflow.com/questions/6692908/formatting-messages-to-send-to-socket-io-node-js-server-from-python-client
__ StackOverflowQA_
.. _liris: https://github.com/liris
.. _websocket-client: https://github.com/liris/websocket-client
.. _guille: https://github.com/guille
.. _socket.io specification: https://github.com/LearnBoost/socket.io-spec
.. _Paul Kienzle: https://github.com/pkienzle
.. _Josh VanderLinden: https://github.com/codekoala
.. _Ian Fitzpatrick: https://github.com/GraphEffect
