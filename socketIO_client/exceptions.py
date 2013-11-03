class SocketIOError(Exception):
    pass


class SocketIOConnectionError(SocketIOError):
    pass


class _TimeoutError(Exception):
    pass


class _PacketError(SocketIOError):
    pass
