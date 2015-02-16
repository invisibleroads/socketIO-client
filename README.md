[![Build Status](https://travis-ci.org/invisibleroads/socketIO-client.svg?branch=master)](https://travis-ci.org/invisibleroads/socketIO-client)

socketIO-client
===============
Here is a [socket.io](http://socket.io) client library for Python.  You can use it to write test code for your socket.io server.


Installation
------------
Install the package in an isolated environment.

    VIRTUAL_ENV=$HOME/.virtualenv

    # Prepare isolated environment
    virtualenv $VIRTUAL_ENV

    # Activate isolated environment
    source $VIRTUAL_ENV/bin/activate

    # Install package
    pip install -U socketIO-client


Usage
-----
Activate isolated environment.

    VIRTUAL_ENV=$HOME/.virtualenv
    source $VIRTUAL_ENV/bin/activate

Launch your socket.io server.

    node serve-tests.js

For debugging information, run these commands first.

    import logging
    logging.basicConfig(level=logging.DEBUG)

Emit.

    from socketIO_client import SocketIO, LoggingNamespace

    with SocketIO('localhost', 8000, LoggingNamespace) as socketIO:
        socketIO.emit('aaa')
        socketIO.wait(seconds=1)

Emit with callback.

    from socketIO_client import SocketIO, LoggingNamespace

    def on_bbb_response(*args):
        print 'on_bbb_response', args

    with SocketIO('localhost', 8000, LoggingNamespace) as socketIO:
        socketIO.emit('bbb', {'xxx': 'yyy'}, on_bbb_response)
        socketIO.wait_for_callbacks(seconds=1)

Define events.

    from socketIO_client import SocketIO, LoggingNamespace

    def on_aaa_response(*args):
        print 'on_aaa_response', args

    socketIO = SocketIO('localhost', 8000, LoggingNamespace)
    socketIO.on('aaa_response', on_aaa_response)
    socketIO.emit('aaa')
    socketIO.wait(seconds=1)

Define events in a namespace.

    from socketIO_client import SocketIO, BaseNamespace

    class Namespace(BaseNamespace):

        def on_aaa_response(self, *args):
            print 'on_aaa_response', args
            self.emit('bbb')

    socketIO = SocketIO('localhost', 8000, Namespace)
    socketIO.emit('aaa')
    socketIO.wait(seconds=1)

Define standard events.

    from socketIO_client import SocketIO, BaseNamespace

    class Namespace(BaseNamespace):

        def on_connect(self):
            print '[Connected]'

    socketIO = SocketIO('localhost', 8000, Namespace)
    socketIO.wait(seconds=1)

Define different namespaces on a single socket.

    from socketIO_client import SocketIO, BaseNamespace

    class ChatNamespace(BaseNamespace):

        def on_aaa_response(self, *args):
            print 'on_aaa_response', args

    class NewsNamespace(BaseNamespace):

        def on_aaa_response(self, *args):
            print 'on_aaa_response', args

    socketIO = SocketIO('localhost', 8000)
    chat_namespace = socketIO.define(ChatNamespace, '/chat')
    news_namespace = socketIO.define(NewsNamespace, '/news')

    chat_namespace.emit('aaa')
    news_namespace.emit('aaa')
    socketIO.wait(seconds=1)

Connect via SSL.

    from socketIO_client import SocketIO

    SocketIO('https://localhost', verify=False)

Specify params, headers, cookies, proxies thanks to the [requests](http://python-requests.org) library.

    from socketIO_client import SocketIO
    from base64 import b64encode

    SocketIO('localhost', 8000,
        params={'q': 'qqq'},
        headers={'Authorization': 'Basic ' + b64encode('username:password')},
        cookies={'a': 'aaa'},
        proxies={'https': 'https://proxy.example.com:8080'})

Wait forever.

    from socketIO_client import SocketIO

    socketIO = SocketIO('localhost')
    socketIO.wait()


License
-------
This software is available under the MIT License.


Credits
-------
- [Guillermo Rauch](https://github.com/rauchg) wrote the [socket.io specification](https://github.com/LearnBoost/socket.io-spec).
- [Hiroki Ohtani](https://github.com/liris) wrote [websocket-client](https://github.com/liris/websocket-client).
- [rod](http://stackoverflow.com/users/370115/rod) wrote a [prototype for a Python client to a socket.io server](http://stackoverflow.com/questions/6692908/formatting-messages-to-send-to-socket-io-node-js-server-from-python-client) on StackOverflow.
- [Alexandre Bourget](https://github.com/abourget) wrote [gevent-socketio](https://github.com/abourget/gevent-socketio), which is a socket.io server written in Python.
- [Paul Kienzle](https://github.com/pkienzle), [Zac Lee](https://github.com/zratic), [Josh VanderLinden](https://github.com/codekoala), [Ian Fitzpatrick](https://github.com/ifitzpatrick), [Lucas Klein](https://github.com/lukasklein), [Rui Chicoria](https://github.com/rchicoria), [Travis Odom](https://github.com/burstaholic), [Patrick Huber](https://github.com/stackmagic), [Brad Campbell](https://github.com/bradjc), [Daniel](https://github.com/dabidan), [Sean Arietta](https://github.com/sarietta) submitted code to expand support of the socket.io protocol.
- [Bernard Pratz](https://github.com/guyzmo), [Francis Bull](https://github.com/franbull) wrote prototypes to support xhr-polling and jsonp-polling.
- [Eric Chen](https://github.com/taiyangc), [Denis Zinevich](https://github.com/dzinevich), [Thiago Hersan](https://github.com/thiagohersan), [Nayef Copty](https://github.com/nayefc), [Jörgen Karlsson](https://github.com/jorgen-k), [Branden Ghena](https://github.com/brghena) suggested ways to make the connection more robust.
- [Merlijn van Deen](https://github.com/valhallasw), [Frederic Sureau](https://github.com/fredericsureau), [Marcus Cobden](https://github.com/leth), [Drew Hutchison](https://github.com/drewhutchison), [wuurrd](https://github.com/wuurrd), [Adam Kecer](https://github.com/amfg), [Alex Monk](https://github.com/Krenair), [Vishal P R](https://github.com/vishalwy), [John Vandenberg](https://github.com/jayvdb), [Thomas Grainger](https://github.com/graingert) proposed changes that make the library more friendly and practical for you!
