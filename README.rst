.. image:: https://travis-ci.org/invisibleroads/socketIO-client.svg?branch=0.6.1
    :target: https://travis-ci.org/invisibleroads/socketIO-client


socketIO-client
===============
Here is a `socket.io <http://socket.io>`_ client library for Python.  You can use it to write test code for your socket.io server.


Installation
------------
Install the package in an isolated environment. ::

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

Launch your socket.io server. ::

    # Get package folder
    PACKAGE_FOLDER=`python -c "import os, socketIO_client; print(os.path.dirname(socketIO_client.__file__))"`
    # Start socket.io server
    DEBUG=* node $PACKAGE_FOLDER/tests/serve.js
    # Start proxy server in a separate terminal on the same machine
    DEBUG=* node $PACKAGE_FOLDER/tests/proxy.js

For debugging information, run these commands first. ::

    import logging
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.basicConfig(level=logging.DEBUG)

Emit. ::

    from socketIO_client import SocketIO, LoggingNamespace

    with SocketIO('localhost', 8000, LoggingNamespace) as socketIO:
        socketIO.emit('aaa')
        socketIO.wait(seconds=1)

Emit with callback. ::

    from socketIO_client import SocketIO, LoggingNamespace

    def on_bbb_response(*args):
        print('on_bbb_response', args)

    with SocketIO('localhost', 8000, LoggingNamespace) as socketIO:
        socketIO.emit('bbb', {'xxx': 'yyy'}, on_bbb_response)
        socketIO.wait_for_callbacks(seconds=1)

Define events. ::

    from socketIO_client import SocketIO, LoggingNamespace

    def on_aaa_response(*args):
        print('on_aaa_response', args)

    socketIO = SocketIO('localhost', 8000, LoggingNamespace)
    socketIO.on('aaa_response', on_aaa_response)
    socketIO.emit('aaa')
    socketIO.wait(seconds=1)

Define events in a namespace. ::

    from socketIO_client import SocketIO, BaseNamespace

    class Namespace(BaseNamespace):

        def on_aaa_response(self, *args):
            print('on_aaa_response', args)
            self.emit('bbb')

    socketIO = SocketIO('localhost', 8000, Namespace)
    socketIO.emit('aaa')
    socketIO.wait(seconds=1)

Define standard events. ::

    from socketIO_client import SocketIO, BaseNamespace

    class Namespace(BaseNamespace):

        def on_connect(self):
            print('[Connected]')

    socketIO = SocketIO('localhost', 8000, Namespace)
    socketIO.wait(seconds=1)

Define different namespaces on a single socket. ::

    from socketIO_client import SocketIO, BaseNamespace

    class ChatNamespace(BaseNamespace):

        def on_aaa_response(self, *args):
            print('on_aaa_response', args)

    class NewsNamespace(BaseNamespace):

        def on_aaa_response(self, *args):
            print('on_aaa_response', args)

    socketIO = SocketIO('localhost', 8000)
    chat_namespace = socketIO.define(ChatNamespace, '/chat')
    news_namespace = socketIO.define(NewsNamespace, '/news')

    chat_namespace.emit('aaa')
    news_namespace.emit('aaa')
    socketIO.wait(seconds=1)

Connect via SSL. ::

    from socketIO_client import SocketIO

    SocketIO('https://localhost', verify=False)

Specify params, headers, cookies, proxies thanks to the `requests <http://python-requests.org>`_ library. ::

    from socketIO_client import SocketIO
    from base64 import b64encode

    SocketIO('localhost', 8000,
        params={'q': 'qqq'},
        headers={'Authorization': 'Basic ' + b64encode('username:password')},
        cookies={'a': 'aaa'},
        proxies={'https': 'https://proxy.example.com:8080'})

Wait forever. ::

    from socketIO_client import SocketIO

    socketIO = SocketIO('localhost', 8000)
    socketIO.wait()


License
-------
This software is available under the MIT License.


Credits
-------
- `Guillermo Rauch <https://github.com/rauchg>`_ wrote the `socket.io specification <https://github.com/LearnBoost/socket.io-spec>`_.
- `Hiroki Ohtani <https://github.com/liris>`_ wrote `websocket-client <https://github.com/liris/websocket-client>`_.
- `rod <http://stackoverflow.com/users/370115/rod>`_ wrote a `prototype for a Python client to a socket.io server <http://stackoverflow.com/questions/6692908/formatting-messages-to-send-to-socket-io-node-js-server-from-python-client>`_.
- `Alexandre Bourget <https://github.com/abourget>`_ wrote `gevent-socketio <https://github.com/abourget/gevent-socketio>`_, which is a socket.io server written in Python.
- `Paul Kienzle <https://github.com/pkienzle>`_, `Zac Lee <https://github.com/zratic>`_, `Josh VanderLinden <https://github.com/codekoala>`_, `Ian Fitzpatrick <https://github.com/ifitzpatrick>`_, `Lucas Klein <https://github.com/lukasklein>`_, `Rui Chicoria <https://github.com/rchicoria>`_, `Travis Odom <https://github.com/burstaholic>`_, `Patrick Huber <https://github.com/stackmagic>`_, `Brad Campbell <https://github.com/bradjc>`_, `Daniel <https://github.com/dabidan>`_, `Sean Arietta <https://github.com/sarietta>`_ submitted code to expand support of the socket.io protocol.
- `Bernard Pratz <https://github.com/guyzmo>`_, `Francis Bull <https://github.com/franbull>`_ wrote prototypes to support xhr-polling and jsonp-polling.
- `Eric Chen <https://github.com/taiyangc>`_, `Denis Zinevich <https://github.com/dzinevich>`_, `Thiago Hersan <https://github.com/thiagohersan>`_, `Nayef Copty <https://github.com/nayefc>`_, `Jörgen Karlsson <https://github.com/jorgen-k>`_, `Branden Ghena <https://github.com/brghena>`_ suggested ways to make the connection more robust.
- `Merlijn van Deen <https://github.com/valhallasw>`_, `Frederic Sureau <https://github.com/fredericsureau>`_, `Marcus Cobden <https://github.com/leth>`_, `Drew Hutchison <https://github.com/drewhutchison>`_, `wuurrd <https://github.com/wuurrd>`_, `Adam Kecer <https://github.com/amfg>`_, `Alex Monk <https://github.com/Krenair>`_, `Vishal P R <https://github.com/vishalwy>`_, `John Vandenberg <https://github.com/jayvdb>`_, `Thomas Grainger <https://github.com/graingert>`_ proposed changes that make the library more friendly and practical for you!
