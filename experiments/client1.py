import json
import requests
import time


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


base_url = 'http://localhost:9000'
session = requests.Session()
# Establish engine.io connection
url = base_url + '/socket.io/'
response = session.get(url, params={
    'EIO': 3,
    'transport': 'polling',
    't': get_timestamp(),
})
print response.url


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


# Establish socket.io connection
session.get


# [REQUEST] /socket.io/?EIO=3&transport=polling&t=1416156610865-1&sid=OXdRaq1cUWs5v3TVAAAF
# Receive socket.io event


# Send socket.io event
# [REQUEST] /socket.io/?EIO=3&transport=polling&t=1416156610887-2&sid=OXdRaq1cUWs5v3TVAAAF


# Send socket.io ping
# [REQUEST] /socket.io/?EIO=3&transport=polling&t=1416156635868-4&sid=OXdRaq1cUWs5v3TVAAAF
# Receive socket.io pong
