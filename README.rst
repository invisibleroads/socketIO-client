socketIO.client
===============
Here is a barebones `socket.io <http://socket.io>`_ client library for Python.

Thanks to `rod <http://stackoverflow.com/users/370115/rod>`_ for his `StackOverflow question and answer <http://stackoverflow.com/questions/6692908/formatting-messages-to-send-to-socket-io-node-js-server-from-python-client/>`_, on which this code is based.

Thanks also to `liris <https://github.com/liris>`_ for his `websocket-client <https://github.com/liris/websocket-client>`_ and to `guille <https://github.com/guille>`_ for the `socket.io specification <https://github.com/LearnBoost/socket.io-spec>`_.


Installation
------------
::

    # Prepare isolated environment
    ENV=$HOME/Projects/env
    virtualenv $ENV 
    mkdir $ENV/opt

    # Activate isolated environment
    source $ENV/bin/activate

    # Install package
    easy_install -U socketIO-client


Usage
-----
::

    ENV=$HOME/Projects/env
    source $ENV/bin/activate
    python

        from socketIO import SocketIO
        s = SocketIO('localhost', 8000)
        s.emit('news', {'hello': 'world'})


License
-------
This software is available under the MIT License.  Please see LICENSE.txt for the full license text.
