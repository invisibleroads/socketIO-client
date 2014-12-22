import json
import requests
import time


class EngineIO(object):

    _path = 'engine.io'
    _engine_io_protocol = 3
    _request_index = 0

    def __init__(self, host, port):
        url = 'http://%s:%s/%s/' % (host, port, self._path)
        session = requests.Session()
        response = session.get(url, params={
            'EIO': self._engine_io_protocol,
            'transport': 'polling',
            't': self._get_timestamp(),
        })
        packs = _decode_content(response.content)
        packet_type, packet = packs[0]
        assert packet_type == 0
        packet_json = json.loads(packet)
        print(packet_json)
        response = session.get(url, params={
            'EIO': self._engine_io_protocol,
            'transport': 'polling',
            't': self._get_timestamp(),
            'sid': packet_json['sid'],
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


class SocketIO(EngineIO):

    _path = 'socket.io'
    _socket_io_protocol = 4

    def __init__(self, host, port):
        super(SocketIO, self).__init__(host, port)

    def on(self, event, callback):
        pass


def _decode_content(content):
    packs = []
    index = 0
    content_length = len(content)
    while index < content_length:
        index, packet_length = _read_packet_length(content, index)
        index, packet = _read_packet(content, index, packet_length)
        packet_type = int(packet[0])
        packet_payload = packet[1:]
        packs.append((packet_type, packet_payload))
    return packs


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
