# !!! Get pong
# !!! Change print statements into logging statements


import json
import requests
import time


__version__ = '0.5.4'
TRANSPORTS = []


class EngineIO(object):

    _engine_io_protocol = 3
    _request_index = 0

    def __init__(
            self, host, port=None,
            resource='engine.io'):
        self._url = 'http://%s:%s/%s/' % (host, port, resource)
        self._session = requests.Session()

        response = self._session.get(self._url, params={
            'EIO': self._engine_io_protocol,
            'transport': 'polling',
            't': self._get_timestamp(),
        })
        packs = _decode_content(response.content)
        packet_type, packet = packs[0]
        assert packet_type == 0
        packet_json = json.loads(packet)
        print packet_json
        # packet_json['pingInterval']
        # packet_json['pingTimeout']
        # packet_json['upgrades']
        self._session_id = packet_json['sid']

        response = self._session.get(self._url, params={
            'EIO': self._engine_io_protocol,
            'transport': 'polling',
            't': self._get_timestamp(),
            'sid': self._session_id,
        })
        packs = _decode_content(response.content)
        for packet_type, packet in packs:
            print 'engineIO_packet_type = %s' % packet_type
            print 'socketIO_packet_type = %s' % packet[0]
            print 'packet = %s' % packet[1:]

    def _get_timestamp(self):
        timestamp = '%s-%s' % (int(time.time() * 1000), self._request_index)
        self._request_index += 1
        return timestamp

    def _message(self, packet):
        packet_type = 4
        response = self._session.post(self._url, params={
            'EIO': self._engine_io_protocol,
            'transport': 'polling',
            't': self._get_timestamp(),
            'sid': self._session_id,
        }, data=_encode_content([(packet_type, packet)]), headers={
            'content-type': 'application/octet-stream',
        })
        packs = _decode_content(response.content)
        for packet_type, packet in packs:
            print 'engineIO_packet_type = %s' % packet_type
            print 'socketIO_packet_type = %s' % packet[0]
            print 'packet = %s' % packet[1:]

    def _ping(self):
        packet_type = 2
        packet = ''
        response = self._session.post(self._url, params={
            'EIO': self._engine_io_protocol,
            'transport': 'polling',
            't': self._get_timestamp(),
            'sid': self._session_id,
        }, data=_encode_content([(packet_type, packet)]), headers={
            'content-type': 'application/octet-stream',
        })
        packs = _decode_content(response.content)
        for packet_type, packet in packs:
            print 'engineIO_packet_type = %s' % packet_type
            print 'socketIO_packet_type = %s' % packet[0]
            print 'packet = %s' % packet[1:]


class SocketIO(EngineIO):

    def __init__(
            self, host, port=None, Namespace=None,
            wait_for_connection=True, transports=TRANSPORTS,
            resource='socket.io', **kw):
        super(SocketIO, self).__init__(host, port, resource)

    def define(self):
        pass

    def wait(self):
        pass

    def emit(self, event, *args, **kw):
        packet_type = 2
        packet = json.dumps([event])
        self._message(str(packet_type) + packet)

    def on(self, event, callback):
        pass


class BaseNamespace(object):
    pass


class LoggingNamespace(BaseNamespace):
    pass


def _decode_content(content):
    print content
    packs = []
    index = 0
    content_length = len(content)
    while index < content_length:
        try:
            index, packet_length = _read_packet_length(content, index)
        except IndexError:
            break
        index, packet = _read_packet(content, index, packet_length)
        packet_type = int(packet[0])
        packet_payload = packet[1:]
        packs.append((packet_type, packet_payload))
    return packs


def _encode_content(packs):
    parts = []
    for packet_type, packet_payload in packs:
        packet = str(packet_type) + str(packet_payload)
        parts.append(_make_packet_header(packet) + packet)
    return ''.join(parts)


def _read_packet_length(content, index):
    while ord(content[index]) != 0:
        index += 1
    index += 1
    packet_length_string = ''
    while ord(content[index]) != 255:
        packet_length_string += str(ord(content[index]))
        index += 1
    return index, int(packet_length_string)


def _read_packet(content, index, packet_length):
    while ord(content[index]) == 255:
        index += 1
    packet = content[index:index + packet_length]
    return index + packet_length, packet


def _make_packet_header(packet):
    length_string = str(len(packet))
    header_digits = [0]
    for index in xrange(len(length_string)):
        header_digits.append(ord(length_string[index]) - 48)
    header_digits.append(255)
    return ''.join(chr(x) for x in header_digits)


def find_callback(args, kw=None):
    pass
