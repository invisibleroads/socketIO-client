# Vision
Ensure that Python scripts can communicate with a Socket.IO server.

# Mission
Address pull requests.

# Owner
Roy Hyunjin Han

# Context
Some of our systems now rely on this package.

# Timeframe
20161209-2100 - 20161223-2100: 2 weeks estimated

# Objectives
1. Review pull requests.
2. Review issues.
3. Release version.

# Log

20161209-2130 - 20161209-2230: 1 hour

    Make decision on websocket-client issue

# Tasks

    Add binary support
        https://github.com/invisibleroads/socketIO-client/pull/85
        https://github.com/invisibleroads/socketIO-client/issues/70
        https://github.com/invisibleroads/socketIO-client/issues/71
        https://github.com/invisibleroads/socketIO-client/issues/91
    Move logging into a separate namespace
        https://github.com/invisibleroads/socketIO-client/pull/105
    Use six.u for unicode encoding
        https://github.com/invisibleroads/socketIO-client/pull/109
    Replace *args with args
        Investigate whether it is really true that callbacks can't take dictionaries
        https://github.com/invisibleroads/socketIO-client/pull/112
    Check unicode issues
        https://github.com/invisibleroads/socketIO-client/issues/81
    Check python3 support for socketIO-client 0.5.6
        https://github.com/invisibleroads/socketIO-client/issues/83
    Check why connected=True after termination
        https://github.com/invisibleroads/socketIO-client/issues/80
        https://github.com/invisibleroads/socketIO-client/issues/98
    Consider catching heartbeat thread exception
        https://github.com/invisibleroads/socketIO-client/issues/100
    Check disconnection issues
        https://github.com/invisibleroads/socketIO-client/issues/107
        https://github.com/invisibleroads/socketIO-client/issues/111
    Check why transports are not being set
        https://github.com/invisibleroads/socketIO-client/issues/102
    Look at 404 not found error
        https://github.com/invisibleroads/socketIO-client/issues/101
    Check whether it works on Windows 8
        https://github.com/invisibleroads/socketIO-client/issues/97
    Add debian packaging support
        https://github.com/invisibleroads/socketIO-client/pull/89
        https://github.com/invisibleroads/socketIO-client/pull/113
    Consider allowing milliseconds
        https://github.com/invisibleroads/socketIO-client/issues/106
    Update setup.py for consistency
        Replace nose with pytest
    Consider using attrs instead of namedtuple
