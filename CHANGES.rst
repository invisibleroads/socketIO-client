0.5.3
-----
- Exit the wait loop if the client wants to disconnect
- Set heartbeat_interval to be half of the heartbeat_timeout

0.5.2
-----
- Replaced secure=True with host='https://example.com'
- Fixed sending heartbeats thanks to Travis Odom

0.5.1
-----
- Added error handling in the event of websocket timeout
- Fixed sending acknowledgments in custom namespaces thanks to Travis Odom

0.5
---
- Rewrote library to use coroutines instead of threads to save memory
- Improved connection resilience
- Added support for xhr-polling thanks to Francis Bull
- Added support for jsonp-polling thanks to Bernard Pratz
- Added support for query params and cookies

0.4
---
- Added support for custom headers and proxies thanks to Rui and Sajal
- Added support for server-side callbacks thanks to Zac Lee
- Added low-level _SocketIO to remove cyclic references
- Merged Channel functionality into BaseNamespace thanks to Alexandre Bourget

0.3
---
- Added support for secure connections
- Added socketIO.wait()
- Improved exception handling in _RhythmicThread and _ListenerThread

0.2
---
- Added support for callbacks and channels thanks to Paul Kienzle
- Incorporated suggestions from Josh VanderLinden and Ian Fitzpatrick

0.1
---
- Wrapped code from StackOverflow_
- Added exception handling to destructor in case of connection failure

.. _StackOverflow: http://stackoverflow.com/questions/6692908/formatting-messages-to-send-to-socket-io-node-js-server-from-python-client
