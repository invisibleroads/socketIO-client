import json
import requests
import time


# def unwrap_payload
# def decode_payload(payload)
def get_packets(content):
    packets = []
    index = 0
    content_length = len(content)
    while index < content_length:
        index, packet_length = read_packet_length(content, index)
        index, packet = read_packet(content, index, packet_length)
        packet_type = int(packet[0])
        packet_payload = packet[1:]
        packets.append((packet_type, packet_payload))
    return packets


def read_packet_length(content, index):
    while ord(content[index]) != 0:
        index += 1
    index += 1
    packet_length_string = ''
    while ord(content[index]) != 255:
        packet_length_string += str(ord(content[index]))
        index += 1
    return index, int(packet_length_string)


def read_packet(content, index, packet_length):
    while ord(content[index]) == 255:
        index += 1
    packet = content[index:index + packet_length]
    return index + packet_length, packet


request_counter = 0


def get_timestamp():
    global request_counter
    timestamp = '%s-%s' % (int(time.time() * 1000), request_counter)
    request_counter += 1
    return timestamp


print '*** Connect'
base_url = 'http://localhost:9000'
session = requests.Session()
print session.cookies.items()
url = base_url + '/socket.io/'
response = session.get(url, params={
    'EIO': 3,
    'transport': 'polling',
    't': get_timestamp(),
})
print response.url
print session.cookies.items()
packets = get_packets(response.content)
for packet_type, packet in packets:
    print packet_type, packet
packet_type, packet = packets[0]
packet_json = json.loads(packet)
print packet_json
print packet_json['pingInterval']
print packet_json['pingTimeout']
print packet_json['sid']
assert packet_type == 0


""
base_url = 'http://localhost:9000'
url = base_url + '/socket.io/'
response = session.get(url, params={
    'EIO': 3,
    'transport': 'polling',
    't': get_timestamp(),
    'sid': packet_json['sid'],
})
print response.url
print session.cookies.items()
packets = get_packets(response.content)
for packet_type, packet in packets:
    print 'engineIO_packet_type = %s' % packet_type
    print 'socketIO_packet_type = %s' % packet[0]
    print 'packet = %s' % packet[1:]
# from IPython import embed; embed()


# def wrap_payload
def encode_payload(packs):
    parts = []
    for packet_type, packet in packs:
        content = str(packet_type) + str(packet)
        parts.append(make_header(content) + content)
    return ''.join(parts)


def make_header(content):
    length_string = str(len(content))
    print length_string
    header_digits = [0]
    for index in xrange(len(length_string)):
        header_digits.append(ord(length_string[index]) - 48)
    header_digits.append(255)
    return ''.join(chr(x) for x in header_digits)


# print '***'
# base_url = 'http://localhost:9000'
# url = base_url + '/socket.io/'
# response = session.get(url, params={
    # 'EIO': 3,
    # 'transport': 'polling',
    # 't': get_timestamp(),
    # 'sid': packet_json['sid'],
# })
# print response.url
# print response.content
# packets = get_packets(response.content)
# for packet_type, packet in packets:
    # print packet_type, packet


print '*** Send event'
packets = [
    (4, '2["my other event",{"my":"data"}]'),
]
payload = encode_payload(packets)
print payload
base_url = 'http://localhost:9000'
url = base_url + '/socket.io/'
print session.cookies.items()
response = session.post(url, params={
    'EIO': 3,
    'transport': 'polling',
    't': get_timestamp(),
    'sid': packet_json['sid'],
}, data=payload)
print response.url
print response.content

from time import sleep
sleep(10)


print '*** Send event'
packets = [
    (4, '2["my other event",{"my":"data"}]'),
]
payload = encode_payload(packets)
print payload
base_url = 'http://localhost:9000'
url = base_url + '/socket.io/'
print session.cookies.items()
response = session.post(url, params={
    'EIO': 3,
    'transport': 'polling',
    't': get_timestamp(),
    'sid': packet_json['sid'],
}, data=payload)
print response.url
print response.content


"""
print '*** Send ping'
packets = [
    (2, ''),
]
payload = encode_payload(packets)
print payload
base_url = 'http://localhost:9000'
url = base_url + '/socket.io/'
response = session.post(url, params={
    'EIO': 3,
    'transport': 'polling',
    't': get_timestamp(),
    'sid': packet_json['sid'],
}, data=payload)
print response.url
print response.content
# packets = get_packets(response.content)
# for packet_type, packet in packets:
    # print packet_type, packet


print '*** Send ping'
packets = [
    (2, ''),
]
payload = encode_payload(packets)
print payload
base_url = 'http://localhost:9000'
url = base_url + '/socket.io/'
response = session.post(url, params={
    'EIO': 3,
    'transport': 'polling',
    't': get_timestamp(),
    'sid': packet_json['sid'],
}, data=payload)
print response.url
print response.content
"""
