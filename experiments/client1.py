import requests


def get_packets(content):
    packets = []
    index = 0
    content_length = len(content)
    while index < content_length:
        index, packet_length = read_packet_length(content, index)
        index, packet = read_packet(content, index, packet_length)
        packets.append((packet[0], packet[1:]))
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


base_url = 'http://localhost:9000'
session = requests.Session()
# Establish engine.io connection
response = session.get(
    base_url + '/socket.io/?EIO=3&transport=polling&t=1416156610842-0')
packets = get_packets(response.content)
for packet_type, packet in packets:
    print packet_type, packet
packet_type, packet = packets[0]
import json
packet_json = json.loads(packet)
print packet_json
print packet_json['pingInterval']
print packet_json['pingTimeout']
print packet_json['sid']
# Establish socket.io connection
# Receive socket.io event
# Send socket.io event
# Send socket.io ping
# Receive socket.io pong
