.. image:: https://travis-ci.org/invisibleroads/socketIO-client.svg?branch=master
    :target: https://travis-ci.org/invisibleroads/socketIO-client


socketIO-client
===============
Here is a `socket.io <http://socket.io>`_ client library for Python.  You can use it to write test code for your socket.io server.

Please note that this version implements `socket.io protocol 1.x <https://github.com/automattic/socket.io-protocol>`_, which is not backwards compatible.  If you want to communicate using `socket.io protocol 0.9 <https://github.com/learnboost/socket.io-spec>`_ (which is compatible with `gevent-socketio <https://github.com/abourget/gevent-socketio>`_), please use `socketIO-client 0.5.7.2 <https://pypi.python.org/pypi/socketIO-client/0.5.7.2>`_.


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

    cd $(python -c "import os, socketIO_client;\
        print(os.path.dirname(socketIO_client.__file__))")

    DEBUG=* node tests/serve.js  # Start socket.io server in terminal one
    DEBUG=* node tests/proxy.js  # Start proxy server in terminal two
    nosetests                    # Run tests in terminal three

For debugging information, run these commands first. ::

    import logging
    logging.getLogger('socketIO-client').setLevel(logging.DEBUG)
    logging.basicConfig()

Emit. ::

    from socketIO_client import SocketIO, LoggingNamespace

    with SocketIO('127.0.0.1', 8000, LoggingNamespace) as socketIO:
        socketIO.emit('aaa')
        socketIO.wait(seconds=1)

Emit with callback. ::

    from socketIO_client import SocketIO, LoggingNamespace

    def on_bbb_response(*args):
        print('on_bbb_response', args)

    with SocketIO('127.0.0.1', 8000, LoggingNamespace) as socketIO:
        socketIO.emit('bbb', {'xxx': 'yyy'}, on_bbb_response)
        socketIO.wait_for_callbacks(seconds=1)

Define events. ::

    from socketIO_client import SocketIO, LoggingNamespace

    def on_connect():
        print('connect')

    def on_disconnect():
        print('disconnect')

    def on_reconnect():
        print('reconnect')

    def on_aaa_response(*args):
        print('on_aaa_response', args)

    socketIO = SocketIO('127.0.0.1', 8000, LoggingNamespace)
    socketIO.on('connect', on_connect)
    socketIO.on('disconnect', on_disconnect)
    socketIO.on('reconnect', on_reconnect)

    # Listen
    socketIO.on('aaa_response', on_aaa_response)
    socketIO.emit('aaa')
    socketIO.emit('aaa')
    socketIO.wait(seconds=1)

    # Stop listening
    socketIO.off('aaa_response')
    socketIO.emit('aaa')
    socketIO.wait(seconds=1)

    # Listen only once
    socketIO.once('aaa_response', on_aaa_response)
    socketIO.emit('aaa')  # Activate aaa_response
    socketIO.emit('aaa')  # Ignore
    socketIO.wait(seconds=1)

Define events in a namespace. ::

    from socketIO_client import SocketIO, BaseNamespace

    class Namespace(BaseNamespace):

        def on_aaa_response(self, *args):
            print('on_aaa_response', args)
            self.emit('bbb')

    socketIO = SocketIO('127.0.0.1', 8000, Namespace)
    socketIO.emit('aaa')
    socketIO.wait(seconds=1)

Define standard events. ::

    from socketIO_client import SocketIO, BaseNamespace

    class Namespace(BaseNamespace):

        def on_connect(self):
            print('[Connected]')

        def on_reconnect(self):
            print('[Reconnected]')

        def on_disconnect(self):
            print('[Disconnected]')

    socketIO = SocketIO('127.0.0.1', 8000, Namespace)
    socketIO.wait(seconds=1)

Define different namespaces on a single socket. ::

    from socketIO_client import SocketIO, BaseNamespace

    class ChatNamespace(BaseNamespace):

        def on_aaa_response(self, *args):
            print('on_aaa_response', args)

    class NewsNamespace(BaseNamespace):

        def on_aaa_response(self, *args):
            print('on_aaa_response', args)

    socketIO = SocketIO('127.0.0.1', 8000)
    chat_namespace = socketIO.define(ChatNamespace, '/chat')
    news_namespace = socketIO.define(NewsNamespace, '/news')

    chat_namespace.emit('aaa')
    news_namespace.emit('aaa')
    socketIO.wait(seconds=1)

Connect via SSL (https://github.com/invisibleroads/socketIO-client/issues/54). ::

    from socketIO_client import SocketIO

    # Skip server certificate verification
    SocketIO('https://127.0.0.1', verify=False)
    # Verify the server certificate
    SocketIO('https://127.0.0.1', verify='server.crt')
    # Verify the server certificate and encrypt using client certificate
    socketIO = SocketIO('https://127.0.0.1', verify='server.crt', cert=(
        'client.crt', 'client.key'))

Specify params, headers, cookies, proxies thanks to the `requests <http://python-requests.org>`_ library. ::

    from socketIO_client import SocketIO
    from base64 import b64encode

    SocketIO(
        '127.0.0.1', 8000,
        params={'q': 'qqq'},
        headers={'Authorization': 'Basic ' + b64encode('username:password')},
        cookies={'a': 'aaa'},
        proxies={'https': 'https://proxy.example.com:8080'})

Wait forever. ::

    from socketIO_client import SocketIO

    socketIO = SocketIO('127.0.0.1', 8000)
    socketIO.wait()

Don't wait forever. ::

    from requests.exceptions import ConnectionError
    from socketIO_client import SocketIO

    try:
        socket = SocketIO('127.0.0.1', 8000, wait_for_connection=False)
        socket.wait()
    except ConnectionError:
        print('The server is down. Try again later.')


License
-------
This software is available under the MIT License.


Credits
-------
- `Guillermo Rauch <https://github.com/rauchg>`_ wrote the `socket.io specification <https://github.com/automattic/socket.io-protocol>`_.
- `Hiroki Ohtani <https://github.com/liris>`_ wrote `websocket-client <https://github.com/liris/websocket-client>`_.
- `Roderick Hodgson <https://github.com/roderickhodgson>`_ wrote a `prototype for a Python client to a socket.io server <http://stackoverflow.com/questions/6692908/formatting-messages-to-send-to-socket-io-node-js-server-from-python-client>`_.
- `Alexandre Bourget <https://github.com/abourget>`_ wrote `gevent-socketio <https://github.com/abourget/gevent-socketio>`_, which is a socket.io server written in Python.
- `Paul Kienzle <https://github.com/pkienzle>`_, `Zac Lee <https://github.com/zratic>`_, `Josh VanderLinden <https://github.com/codekoala>`_, `Ian Fitzpatrick <https://github.com/ifitzpatrick>`_, `Lucas Klein <https://github.com/lukasklein>`_, `Rui Chicoria <https://github.com/rchicoria>`_, `Travis Odom <https://github.com/burstaholic>`_, `Patrick Huber <https://github.com/stackmagic>`_, `Brad Campbell <https://github.com/bradjc>`_, `Daniel <https://github.com/dabidan>`_, `Sean Arietta <https://github.com/sarietta>`_, `Sacha Stafyniak <https://github.com/stafyniaksacha>`_ submitted code to expand support of the socket.io protocol.
- `Bernard Pratz <https://github.com/guyzmo>`_, `Francis Bull <https://github.com/franbull>`_ wrote prototypes to support xhr-polling and jsonp-polling.
- `Joe Palmer <https://github.com/softforge>`_ sponsored development.
- `Eric Chen <https://github.com/taiyangc>`_, `Denis Zinevich <https://github.com/dzinevich>`_, `Thiago Hersan <https://github.com/thiagohersan>`_, `Nayef Copty <https://github.com/nayefc>`_, `Jörgen Karlsson <https://github.com/jorgen-k>`_, `Branden Ghena <https://github.com/brghena>`_, `Tim Landscheidt <https://github.com/scfc>`_, `Matt Porritt <https://github.com/mattporritt>`_, `Matt Dainty <https://github.com/bodgit>`_, `Thomaz de Oliveira dos Reis <https://github.com/thor27>`_, `Felix König <https://github.com/Felk>`_, `George Wilson <https://github.com/wilsonge>`_, `Andreas Strikos <https://github.com/astrikos>`_, `Alessio Sergi <https://github.com/asergi>`_ `Claudio Yacarini <https://github.com/cyacarinic>`_, `Khairi Hafsham <https://github.com/khairihafsham>`_, `Robbie Clarken <https://github.com/RobbieClarken>`_ suggested ways to make the connection more robust.
- `Merlijn van Deen <https://github.com/valhallasw>`_, `Frederic Sureau <https://github.com/fredericsureau>`_, `Marcus Cobden <https://github.com/leth>`_, `Drew Hutchison <https://github.com/drewhutchison>`_, `wuurrd <https://github.com/wuurrd>`_, `Adam Kecer <https://github.com/amfg>`_, `Alex Monk <https://github.com/Krenair>`_, `Vishal P R <https://github.com/vishalwy>`_, `John Vandenberg <https://github.com/jayvdb>`_, `Thomas Grainger <https://github.com/graingert>`_, `Daniel Quinn <https://github.com/danielquinn>`_, `Adric Worley <https://github.com/AdricEpic>`_, `Adam Roses Wight <https://github.com/adamwight>`_, `Jan Včelák <https://github.com/fcelda>`_ proposed changes that make the library more friendly and practical for you!
