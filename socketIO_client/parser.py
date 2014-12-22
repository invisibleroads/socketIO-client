from enum import Enum
import logging
import json

_log = logging.getLogger(__name__)

ENGINE_PROTOCOL = 3;

class PacketType(Enum):
    OPEN = 0;
    CLOSE = 1;
    PING = 2;
    PONG = 3;
    MESSAGE = 4;
    UPGRADE = 5;
    NOOP = 6;

class MessageType(Enum):
    CONNECT = 0;
    DISCONNECT = 1;
    EVENT = 2;
    ACK = 3;
    ERROR = 4;
    BINARY_EVENT = 5;
    BINARY_ACK = 6;

class Packet():
    def __init__(self, packet_type, payload):
        self.type = packet_type;
        self.payload = payload;

class Message():
    def __init__(self, message_type, message, path = ""):
        self.type = message_type;
        if isinstance(message, basestring):
            try:
                self.message = json.loads(message);
            except:
                self.message = message;
        else:
            self.message = message;

        self.path = path;

    def encode_as_json(self):
        """Encodes a Message to be sent to socket.io server.
        
        Assumes the message payload will be dumped as a json string.
        """
        if self.path == "":
            return str(self.type) + json.dumps(self.message);
        return str(self.type) + self.path + "," + json.dumps(self.message);

    def encode_as_string(self):
        """Same as the encode_as_string method except it doesn't encode things as a JSON string"""
        if self.path == "":
            return str(self.type) + self.message;
        return str(self.type) + self.path + "," + self.message;

def decode_message(payload):
    """ Decodes a message encoded via socket.io
    """

    message_type = int(payload[0]);
    message = payload[1:];

    return Message(message_type, message);

def decode_response(response):
    """Decodes a response from requests lib.

    """
    # TODO(sean): Should we use the 'raw' stream instead?
    return decode_packet(response.content);

def decode_packet(packet):
    """Decodes a packet sent via engine.io.

    If the packet is a message, this method assumes the message was
    encoded by socket.io and will parse it as such.

    """

    packet_format = "string" if ord(packet[0]) == 0 else "binary";
    _log.debug("Packet type: %s" % packet_format);

    if packet_format is "string":
        length_bytes = [];
        offset = 1;
        while ord(packet[offset]) is not 255:
            length_bytes.append(ord(packet[offset]));
            offset += 1;
        offset += 1;

        length = 0;
        base = 1;
        for digit in reversed(length_bytes):
            length += (int(digit) * base);
            base *= 10;
        _log.debug("Packet length: %d" % length);

        packet_type = int(packet[offset]);
        offset += 1;

        payload = packet[offset:offset + length - 1];
        _log.debug("Payload: %s" % repr(payload));

        if packet_type is PacketType.MESSAGE:
            message = decode_message(payload);
            payload = message;

        return Packet(packet_type, payload);
    else:
        pass;

    return "";

    pass;

def encode_packet_string(code, path, data):
    """Encodes packet to be sent to socket.io server.
    """

    code_length = len(str(code));
    data_length = len(data);
    length = code_length + data_length;

    return str(length) + ":" + str(code) + str(data);
