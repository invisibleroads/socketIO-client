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

    + Make decision on websocket-client issue for #139
    + Merge #139 into 0.7.2

20161209-2330 - 20161210-0000: 30 minutes

    + Merge #125 into 0.5.7.2

20161210-0045 - 20161210-0115: 30 minutes

    + Merge #136 into 0.7.2

20161210-1100 - 20161210-1200: 1 hour

    + Merge #135 into 0.7.2

20161210-2200 - 20161210-2230: 30 minutes

I tried experimenting for a while with unicode events, where there are unicode characters in the event name, but it seems that Python 2 does not support unicode attributes.

# Tasks

    + Release 0.5.7.2
    + Release 0.7.2
    Release 0.8.0

    Add binary support
        https://github.com/invisibleroads/socketIO-client/pull/85
        https://github.com/invisibleroads/socketIO-client/issues/70
        https://github.com/invisibleroads/socketIO-client/issues/71
        https://github.com/invisibleroads/socketIO-client/issues/91
    Replace *args with args
        Investigate whether it is really true that callbacks can't take dictionaries
        https://github.com/invisibleroads/socketIO-client/pull/112
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
    Consider allowing milliseconds
        https://github.com/invisibleroads/socketIO-client/issues/106
    Consider using attrs instead of namedtuple
