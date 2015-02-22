import json
from collections import namedtuple

from .symmetries import (
    decode_string, encode_string, get_byte, get_character, parse_url)


EngineIOSession = namedtuple('EngineIOSession', [
    'id', 'ping_interval', 'ping_timeout', 'transport_upgrades'])
SocketIOData = namedtuple('SocketIOData', ['path', 'ack_id', 'args'])


def parse_host(host, port, resource):
    if not host.startswith('http'):
        host = 'http://' + host
    url_pack = parse_url(host)
    is_secure = url_pack.scheme == 'https'
    port = port or url_pack.port or (443 if is_secure else 80)
    url = '%s:%d%s/%s' % (url_pack.hostname, port, url_pack.path, resource)
    return is_secure, url


def parse_engineIO_session(engineIO_packet_data):
    d = json.loads(decode_string(engineIO_packet_data))
    return EngineIOSession(
        id=d['sid'],
        ping_interval=d['pingInterval'] / float(1000),
        ping_timeout=d['pingTimeout'] / float(1000),
        transport_upgrades=d['upgrades'])


def encode_engineIO_content(engineIO_packets):
    parts = []
    for packet_type, packet_data in engineIO_packets:
        packet_string = str(packet_type) + encode_string(packet_data)
        parts.append(_make_packet_header(packet_string) + packet_string)
    return ''.join(parts)


def decode_engineIO_content(content):
    content_index = 0
    content_length = len(content)
    while content_index < content_length:
        try:
            content_index, packet_length = _read_packet_length(
                content, content_index)
        except IndexError:
            break
        content_index, packet_string = _read_packet_string(
            content, content_index, packet_length)
        engineIO_packet_type = int(get_character(packet_string, 0))
        engineIO_packet_data = packet_string[1:]
        yield engineIO_packet_type, engineIO_packet_data


def parse_socketIO_data(data):
    data = decode_string(data)
    if data.startswith('/'):
        try:
            path, data = data.split(',', 1)
        except ValueError:
            path = data
            data = ''
    else:
        path = ''
    try:
        ack_id_string, data = data.split('[', 1)
        data = '[' + data
        ack_id = int(ack_id_string)
    except (ValueError, IndexError):
        ack_id = None
    try:
        args = json.loads(data)
    except ValueError:
        args = []
    return SocketIOData(path=path, ack_id=ack_id, args=args)


def format_socketIO_data(path=None, ack_id=None, args=None):
    socketIO_packet_data = json.dumps(args) if args else ''
    if ack_id is not None:
        socketIO_packet_data = str(ack_id) + socketIO_packet_data
    if path:
        socketIO_packet_data = path + ',' + socketIO_packet_data
    return socketIO_packet_data


def _make_packet_header(packet_string):
    length_string = str(len(packet_string))
    header_digits = [0]
    for i in range(len(length_string)):
        header_digits.append(ord(length_string[i]) - 48)
    header_digits.append(255)
    return ''.join(chr(x) for x in header_digits)


def _read_packet_length(content, content_index):
    while get_byte(content, content_index) != 0:
        content_index += 1
    content_index += 1
    packet_length_string = ''
    byte = get_byte(content, content_index)
    while byte != 255:
        packet_length_string += str(byte)
        content_index += 1
        byte = get_byte(content, content_index)
    return content_index, int(packet_length_string)


def _read_packet_string(content, content_index, packet_length):
    while get_byte(content, content_index) == 255:
        content_index += 1
    packet_string = content[content_index:content_index + packet_length]
    return content_index + packet_length, packet_string
