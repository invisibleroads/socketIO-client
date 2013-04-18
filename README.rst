socketIO-client
===============
Here is a socket.io_ client library for Python.  You can use it to write test code for your socket.io_ server.


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
            self.emit('eee', {'fff': 'ggg'})

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
    chatNamespace = socketIO.define(ChatNamespace, '/chat')
    chatNamespace.emit('bbb')
    newsNamespace = socketIO.define(NewsNamespace, '/news')
    newsNamespace.emit('ccc')
    socketIO.wait()  # Loop until CTRL-C

Open secure websockets (HTTPS / WSS) behind a proxy. ::

    SocketIO('localhost', 8000, 
        secure=True,
        proxies={'http': 'http://proxy.example.com:8080'})


License
-------
This software is available under the MIT License.


Credits
-------
- `Guillermo Rauch`_ wrote the `socket.io specification`_.
- `Hiroki Ohtani`_ wrote websocket-client_.
- rod_ wrote a `prototype for a python client to a socket.io server`_ on StackOverflow.
- `Alexandre Bourget`_ wrote gevent-socketio_, which is a socket.io server written in python.
- `Paul Kienzle`_, `Zac Lee`_, `Josh VanderLinden`_, `Ian Fitzpatrick`_, `Lucas Klein`_ submitted code to expand support of the socket.io protocol.


.. _socket.io: http://socket.io

.. _Guillermo Rauch: https://github.com/guille
.. _socket.io specification: https://github.com/LearnBoost/socket.io-spec

.. _Hiroki Ohtani: https://github.com/liris
.. _websocket-client: https://github.com/liris/websocket-client

.. _rod: http://stackoverflow.com/users/370115/rod
.. _prototype for a python client to a socket.io server: http://stackoverflow.com/questions/6692908/formatting-messages-to-send-to-socket-io-node-js-server-from-python-client

.. _Alexandre Bourget: https://github.com/abourget
.. _gevent-socketio: https://github.com/abourget/gevent-socketio

.. _Paul Kienzle: https://github.com/pkienzle
.. _Zac Lee: https://github.com/zratic
.. _Josh VanderLinden: https://github.com/codekoala
.. _Ian Fitzpatrick: https://github.com/GraphEffect
.. _Lucas Klein: https://github.com/lukashed
