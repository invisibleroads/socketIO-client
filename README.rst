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
    pip install -U socketIO-client


Usage
-----
Activate isolated environment. ::

    VIRTUAL_ENV=$HOME/.virtualenv
    source $VIRTUAL_ENV/bin/activate

Emit. ::

    from socketIO_client import SocketIO

    with SocketIO('localhost', 8000) as socketIO:
        socketIO.emit('aaa')
        socketIO.wait(seconds=1)

Emit with callback. ::

    from socketIO_client import SocketIO

    def on_bbb_response(*args):
        print 'on_bbb_response', args

    with SocketIO('localhost', 8000) as socketIO:
        socketIO.emit('bbb', {'xxx': 'yyy'}, on_bbb_response)
        socketIO.wait_for_callbacks(seconds=1)

Define events. ::

    from socketIO_client import SocketIO

    def on_aaa_response(*args):
        print 'on_aaa_response', args

    socketIO = SocketIO('localhost', 8000)
    socketIO.on('aaa_response', on_aaa_response)
    socketIO.emit('aaa')
    socketIO.wait(seconds=1)

Define events in a namespace. ::

    from socketIO_client import SocketIO, BaseNamespace

    class Namespace(BaseNamespace):

        def on_aaa_response(self, *args):
            print 'on_aaa_response', args
            self.emit('bbb')

    socketIO = SocketIO('localhost', 8000, Namespace)
    socketIO.emit('aaa')
    socketIO.wait(seconds=1)

Define standard events. ::

    from socketIO_client import SocketIO, BaseNamespace

    class Namespace(BaseNamespace):

        def on_connect(self):
            print '[Connected]'

    socketIO = SocketIO('localhost', 8000, Namespace)
    socketIO.wait(seconds=1)

Define different namespaces on a single socket. ::

    from socketIO_client import SocketIO, BaseNamespace

    class ChatNamespace(BaseNamespace):

        def on_aaa_response(self, *args):
            print 'on_aaa_response', args

    class NewsNamespace(BaseNamespace):

        def on_aaa_response(self, *args):
            print 'on_aaa_response', args

    socketIO = SocketIO('localhost', 8000)
    chatNamespace = socketIO.define(ChatNamespace, '/chat')
    newsNamespace = socketIO.define(NewsNamespace, '/news')

    chatNamespace.emit('aaa')
    newsNamespace.emit('aaa')
    socketIO.wait(seconds=1)

Open secure websockets (HTTPS / WSS) behind a proxy. ::

    from socketIO_client import SocketIO

    SocketIO('localhost', 8000, 
        secure=True,
        proxies={'https': 'https://proxy.example.com:8080'})

Specify params, headers and cookies thanks to the `requests`_ library. ::

    from socketIO_client import SocketIO
    from base64 import b64encode

    SocketIO('localhost', 8000, 
        params={'q': 'qqq'},
        headers={'Authorization': 'Basic ' + b64encode('username:password')},
        cookies={'a': 'aaa'})


License
-------
This software is available under the MIT License.


Credits
-------
- `Guillermo Rauch`_ wrote the `socket.io specification`_.
- `Hiroki Ohtani`_ wrote websocket-client_.
- rod_ wrote a `prototype for a Python client to a socket.io server`_ on StackOverflow.
- `Alexandre Bourget`_ wrote gevent-socketio_, which is a socket.io server written in Python.
- `Paul Kienzle`_, `Zac Lee`_, `Josh VanderLinden`_, `Ian Fitzpatrick`_, `Lucas Klein`_, `Rui Chicoria`_ submitted code to expand support of the socket.io protocol.
- `Bernard Pratz`_ and `Francis Bull`_ wrote prototypes to support xhr-polling and jsonp-polling.
- `Eric Chen`_, `Denis Zinevich`_, `Thiago Hersan`_ suggested ways to make the connection more robust.
  

.. _socket.io: http://socket.io
.. _requests: http://python-requests.org

.. _Guillermo Rauch: https://github.com/guille
.. _socket.io specification: https://github.com/LearnBoost/socket.io-spec

.. _Hiroki Ohtani: https://github.com/liris
.. _websocket-client: https://github.com/liris/websocket-client

.. _rod: http://stackoverflow.com/users/370115/rod
.. _prototype for a Python client to a socket.io server: http://stackoverflow.com/questions/6692908/formatting-messages-to-send-to-socket-io-node-js-server-from-python-client

.. _Alexandre Bourget: https://github.com/abourget
.. _gevent-socketio: https://github.com/abourget/gevent-socketio

.. _Bernard Pratz: https://github.com/guyzmo
.. _Francis Bull: https://github.com/franbull
.. _Paul Kienzle: https://github.com/pkienzle
.. _Zac Lee: https://github.com/zratic
.. _Josh VanderLinden: https://github.com/codekoala
.. _Ian Fitzpatrick: https://github.com/GraphEffect
.. _Lucas Klein: https://github.com/lukashed
.. _Rui Chicoria: https://github.com/rchicoria

.. _Eric Chen: https://github.com/taiyangc
.. _Denis Zinevich: https://github.com/dzinevich 
.. _Thiago Hersan: https://github.com/thiagohersan
