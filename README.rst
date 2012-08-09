socketIO-client
===============
Here is a socket.io_ client library for Python.

.. _socket.io: http://socket.io

Thanks to rod_ for the `StackOverflow question and answer`__ on which this code is based.

.. _rod: http://stackoverflow.com/users/370115/rod
.. _StackOverflowQA: http://stackoverflow.com/questions/6692908/formatting-messages-to-send-to-socket-io-node-js-server-from-python-client
__ StackOverflowQA_

Thanks to liris_ for websocket-client_ and to guille_ for the `socket.io specification`_.

.. _liris: https://github.com/liris
.. _websocket-client: https://github.com/liris/websocket-client
.. _guille: https://github.com/guille
.. _socket.io specification: https://github.com/LearnBoost/socket.io-spec

Thanks to `Paul Kienzle`_, `Josh VanderLinden`_, `Ian Fitzpatrick`_ for submitting code to expand support of the socket.io protocol.

.. _Paul Kienzle: https://github.com/pkienzle
.. _Josh VanderLinden: https://github.com/codekoala
.. _Ian Fitzpatrick: https://github.com/GraphEffect


Installation
------------
::

    VIRTUAL_ENV=$HOME/.virtualenv

    # Prepare isolated environment
    virtualenv $VIRTUAL_ENV

    # Activate isolated environment
    source $VIRTUAL_ENV/bin/activate

    # Install package
    easy_install -U socketIOClient


Usage
-----
Activate isolated environment.

.. code-block:: bash

    VIRTUAL_ENV=$HOME/.virtualenv
    source $VIRTUAL_ENV/bin/activate

Emit.

.. code-block:: python

    from socketIOClient import SocketIO

    socketIO = SocketIO('localhost', 8000)
    socketIO.emit('aaa', {'bbb': 'ccc'})

Emit with callback.

.. code-block:: python

    from socketIOClient import SocketIO

    def on_response(arg1, arg2, arg3, arg4):
        print arg1, arg2, arg3, arg4

    socketIO = SocketIO('localhost', 8000)
    socketIO.emit('aaa', {'bbb': 'ccc'}, on_response)
    socketIO.wait()

Define events.

.. code-block:: python

    from socketIOClient import SocketIO

    def on_ddd(arg1, arg2, arg3, arg4):
        print arg1, arg2, arg3, arg4

    socketIO = SocketIO('localhost', 8000)
    socketIO.on('ddd', on_ddd)

Define events in a namespace.

.. code-block:: python

    from socketIOClient import SocketIO, BaseNamespace

    class Namespace(BaseNamespace):

        def on_ddd(self, arg1, arg2):
            self.socketIO.emit('eee', {'fff': arg1 + arg2})

    socketIO = SocketIO('localhost', 8000, Namespace)

Define standard events.

.. code-block:: python

    from socketIOClient import SocketIO, BaseNamespace

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

Define different behavior for different channels on a single socket.

.. code-block:: python

    mainSocket = SocketIO('localhost', 8000, MainNamespace())
    chatSocket = mainSocket.connect('/chat', ChatNamespace())
    newsSocket = mainSocket.connect('/news', NewsNamespace())


License
-------
This software is available under the MIT License.
