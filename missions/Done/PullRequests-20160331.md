# Vision
Ensure that Python scripts can communicate with a Socket.IO server.

# Mission
Address pull requests.

# Owner
Roy Hyunjin Han

# Context
It is important to demonstrate discipline in maintaining an open source project.

# Timeframe
20160331-1245 - 20160417-1245: 17 days estimated

20160331-1245 - 20160715-1700: 107 days actual

# Objectives
1. + Make sure that the library works as promised.
2. + Address pull requests.

# Log

20160331-1300 - 20160331-1500

Make sure that the library works as promised.

I think that if I allocate a few hours each day, then I should be able to get this done on schedule.

    + Clone repository
    + Download socket.io
    + Work through chat application example
    + Start a new branch

We'll just check whether all unit tests pass. We should also change our tests to use pytest.

    + Check that library works with both versions of socket.io

        + Test that socket.io-0.9.14 works with socketIO-client-0.5.6

            cd ~/Projects/socketIO-client-0.5.6
            python setup.py develop
            pip install -I -U nose
            npm install socket.io@0.9.14
            node serve-tests
            ~/.virtualenvs/crosscompute/bin/nosetests

        + Test that socket.io-1.4.5 works with socketIO-client-0.6.5

            cd ~/Projects/socketIO-client-0.6.5
            python setup.py develop
            pip install -I -U nose
            npm install socket.io yargs
            node socketIO_client/tests/serve.js
            ~/.virtualenvs/crosscompute/bin/nosetests

Well, I'm pleasantly surprised. Both tests still pass!

    _ Write an experiment to detect version of socket.io on server
        + Option 1 is to try to connect with both and avoid the one that fails. But that is naive.
            + Connect socketIO-client-0.5.6 to socket.io-1.4.5 and see what happens (it just hangs)
            + Connect socketIO-client-0.6.5 to socket.io-0.9.14 and see what happens (warning: connection refused)
        _ Option 2 is to have more precision by testing certain connection points.

Let's try "Connect socketIO-client-0.6.5 to socket.io-0.9.14" again.

    WARNING:root:localhost:9000/socket.io [waiting for connection] HTTPConnectionPool(host='localhost', port=9000): Max retries exceeded with url: /socket.io/?EIO=3&transport=polling&t=1459452848797-0 (Caused by NewConnectionError('<requests.packages.urllib3.connection.HTTPConnection object at 0x7f361b4a1590>: Failed to establish a new connection: [Errno 111] Connection refused',))

After thinking about it some more, I think supporting both protocols in the same library will be needlessly complicated. We will keep the existing structure of having different versions for different protocols.

20160331-2010 - 20160331-2030

    + Add documentation for server SSL certification verification
    + Add documentation for client SSL certification encryption

20160331-2030 - 20160331-2130

    + Work through one pull request

20160403-1100 - 20160403-1200: 1 hour estimated

20160403-1100 - 20160403-1400: 3 hours actual

    + Work through one pull request

20160625-1815 - 20160625-1845: 30 minutes

I am noticing some thread-related errors.

For example, here is an error that appears

	Exception in thread Thread-1 (most likely raised during interpreter shutdown):
	Traceback (most recent call last):
	File "/usr/lib64/python2.7/threading.py", line 804, in __bootstrap_inner
	File "/home/rhh/.virtualenvs/crosscompute/lib/python2.7/site-packages/socketIO_client/heartbeats.py", line 34, in run
	File "/usr/lib64/python2.7/threading.py", line 617, in wait
	File "/usr/lib64/python2.7/threading.py", line 367, in wait
	<type 'exceptions.ValueError'>: list.remove(x): x not in list
	Unhandled exception in thread started by
	sys.excepthook is missing
	lost sys.stderr

I am looking at line 367 of threading.py but it looks like the exception should have been ignored.

	try:
		self.__waiters.remove(waiter)
	except ValueError:
		pass

I think the ValueError is coming from somewhere else.

    - https://github.com/segmentio/analytics-python/issues/69
    - http://stackoverflow.com/questions/9532264/how-to-use-multiple-threads

For now, let's just wait for the heartbeat thread to join.

	self._heartbeat_thread.join()

If the exception appears again, then we'll use atexit.register(self._heartbeat_thread.join()).

20160714-2053

The issue is that packet_text has utf-8 but we need a bytestring and six.b only encodes using latin-1.

    Option 1: Encode packet_text into a bytestring using utf-8, but then we won't be working with unicode.
    Option 2: Leave packet_text alone and handle it differently based on whether it is unicode or a bytestring.

20160715-1315

After thinking about it a bit, I think the second approach is more robust, because we'll just leave the packet data as it is mostly and just handle it verbatim. The first option can be vulnerable to cases where the packet type might be wrong?

20160715-1700

If I ever do revisit binary support, I should try to generate a log of the binary protocol using Chrome Developer Tools. There were some notes about XHR2 vs base64.

    - https://github.com/socketio/engine.io-protocol
    - https://github.com/socketio/socket.io-protocol

The feus4177 repository has a working solution for binary support, but I didn't completely understand how it worked and I felt uncomfortable about merging something without full understanding.

I also wanted to address unicode support and the decision was to keep everything as an encoded bytestring and only decode for non-binary events. I tried the approach of leaving the packet alone and just handling unicode or bytestring on a case by case basis, but it proved too messy.

Perhaps when my life becomes less complex, I'll revisit both binary and unicode support. But for now, I have too many things in my head and my capacity for extra complexity is becoming rather limited.
