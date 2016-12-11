0.7
---
- Fixed thread cleanup
- Fixed disconnect detection if defined directly thanks to Andreas Strikos
- Fixed support for unicode payloads

0.6
---
- Upgraded to socket.io protocol 1.x thanks to Sean Arietta and Joe Palmer
- Fixed support for Python 3
- Fixed SSL support
- Added locks to fix concurrency issues with polling transport
- Added SocketIO.off() and SocketIO.once()

0.5
---
- Added support for Python 3
- Added support for jsonp-polling thanks to Bernard Pratz
- Added support for xhr-polling thanks to Francis Bull
- Added support for query params and cookies
- Fixed sending acknowledgments in custom namespaces thanks to Travis Odom
- Rewrote library to use coroutines instead of threads to save memory

0.4
---
- Added support for custom headers and proxies thanks to Rui and Sajal
- Added support for server-side callbacks thanks to Zac Lee
- Merged Channel functionality into BaseNamespace thanks to Alexandre Bourget

0.3
---
- Added support for secure connections
- Added SocketIO.wait()
- Improved exception handling in _RhythmicThread and _ListenerThread

0.2
---
- Added support for callbacks and channels thanks to Paul Kienzle
- Incorporated suggestions from Josh VanderLinden and Ian Fitzpatrick

0.1
---
- Wrapped `code from StackOverflow <http://stackoverflow.com/questions/6692908/formatting-messages-to-send-to-socket-io-node-js-server-from-python-client>`_
- Added exception handling to destructor in case of connection failure
