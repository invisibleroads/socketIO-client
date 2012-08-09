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

    socketIO = SocketIO('localhost', 8000)
    socketIO.emit('aaa', {'bbb': 'ccc'})

Emit with callback. ::

    from socketIO_client import SocketIO

    def on_response(arg1, arg2, arg3, arg4):
        print arg1, arg2, arg3, arg4

    socketIO = SocketIO('localhost', 8000)
    socketIO.emit('aaa', {'bbb': 'ccc'}, on_response)
    socketIO.wait()

Define events. ::

    from socketIO_client import SocketIO

    def on_ddd(arg1, arg2, arg3, arg4):
        print arg1, arg2, arg3, arg4

    socketIO = SocketIO('localhost', 8000)
    socketIO.on('ddd', on_ddd)

Define events in a namespace. ::

    from socketIO_client import SocketIO, BaseNamespace

    class Namespace(BaseNamespace):

        def on_ddd(self, arg1, arg2):
            self.socketIO.emit('eee', {'fff': arg1 + arg2})

    socketIO = SocketIO('localhost', 8000, Namespace)

Define standard events. ::

    from socketIO_client import SocketIO, BaseNamespace

    class Namespace(BaseNamespace):

        def on_connect(self, socketIO):
            print '[Connected]'

        def on_disconnect(self):
            print '[Disconnected]'

        def on_error(self, name, message):
            print '[Error] %s: %s' % (name, message)

        def on_message(self, id, message):
            print '[Message] %s: %s' % (id, message)

    socketIO = SocketIO('localhost', 8000, Namespace)

Define different behavior for different channels on a single socket. ::

    mainSocket = SocketIO('localhost', 8000, MainNamespace())
    chatSocket = mainSocket.connect('/chat', ChatNamespace())
    newsSocket = mainSocket.connect('/news', NewsNamespace())


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
