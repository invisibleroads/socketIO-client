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

    def __str__(self):
        return "PACKET{type: " + str(self.type) + ", payload: " + str(self.payload) + "}";

    def encode_as_string(self, for_websocket = False):
        data = "";
        path = "";
        if self.type == PacketType.MESSAGE and not isinstance(self.payload, basestring):
            data = self.payload.encode_as_string();
            path = self.payload.path;
        else:
            data = self.payload;           

        code_length = len(str(self.type));
        data_length = len(data);
        length = code_length + data_length;

        encoded = "";
        if for_websocket:
            encoded = str(self.type) + str(data);
        else:
            encoded = str(length) + ":" + str(self.type) + str(data);
 
        return encoded;

class Message():
    def __init__(self, message_type, message, path = "", attachments = "", message_id = None):
        self.type = message_type;
        if isinstance(message, basestring):
            try:
                self.message = json.loads(message);
            except:
                self.message = message;
        else:
            self.message = message;

        self.path = path;
        self.attachments = attachments;
        self.id = message_id;

    def __str__(self):
        if self.id is not None:
            return "MESSAGE{" + \
                "id: " + str(self.id) + ", " + \
                "type: " + str(self.type) + ", " + \
                "message: " + str(self.message) + ", " + \
                "path: " + self.path + \
                "}";
        else:
            return "MESSAGE{" + \
                "type: " + str(self.type) + ", " + \
                "message: " + str(self.message) + ", " + \
                "path: " + self.path + \
                "}";

    def encode_as_json(self):
        """Encodes a Message to be sent to socket.io server.
        
        Assumes the message payload will be dumped as a json string.
        """
        data = json.dumps(self.message);
        if self.id is not None:
            data = str(self.id) + json.dumps(self.message);

        if self.path == "":
            return str(self.type) + data;
        return str(self.type) + self.path + "," + data;

    def encode_as_string(self):
        """Same as the encode_as_string method except it doesn't encode things as a JSON string"""
        data = self.message;
        if self.id is not None:
            data = str(self.id) + self.message;

        if self.path == "":
            return str(self.type) + data;
        return str(self.type) + self.path + "," + data;

def _is_integer(s):
    try:
        int(s);
    except ValueError:
        return False;
    return True;

def decode_message(payload):
    """ Decodes a message encoded via socket.io
    """

    _log.debug("[decode payload] %s" % repr(payload));

    i = 0;
    message_type = int(payload[i]);
    message = "";
    path = "";
    attachments = "";
    message_id = None;

    i += 1;

    if len(payload) > i:
        if message_type == MessageType.BINARY_EVENT or message_type == MessageType.BINARY_ACK:
            while (payload[i] != "-"):
                attachments += payload[i];
                i += 1;

    if len(payload) > i:
        # This is kind of odd, but it is how socket.io-parser works (see
        # https://github.com/Automattic/socket.io-parser/blob/master/index.js#L292
        # @0ae9a4f).
        if payload[i] == "/":
            if "," in payload:
                split_point = payload.index(",");
                path = payload[i:split_point];
                i += split_point;
            else:
                path = payload[i:];
                i += len(path);
    
    if len(payload) > i:
        # This is another oddity. According to the socket.io-parser we
        # need to loop over the next chars until we stop finding ints
        # to determine if there is a message id.
        message_id_str = "";
        while _is_integer(payload[i]):
            message_id_str += payload[i];
            i += 1;
        if message_id_str != "":
            message_id = int(message_id_str);

    if len(payload) > i:
        message = payload[i:];

    return Message(message_type, message, path, attachments, message_id);

def decode_response(response):
    """Decodes a response from requests lib.

    """
    # TODO(sean): Should we use the 'raw' stream instead?
    if isinstance(response, basestring):
        _log.debug("[decode response (string)] Response: %s" % str(response));
        packet = decode_packet_string(response);
        yield packet;
    else:
        content = response.content;
        total_length = len(content);
        processed = 0;
        while processed < total_length:
            _log.debug("[decode response] Content: %s" % str(content));
            (read, packet) = decode_packet(content);
            content = content[read:];
            processed += read;
            yield packet;
            

def decode_packet_string(packet):
    packet_type = int(packet[0]);
    payload = packet[1:];

    if packet_type == PacketType.MESSAGE:
        message = decode_message(payload);
        payload = message;

    return Packet(packet_type, payload);

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
            
        return offset + length - 1, Packet(packet_type, payload);
    else:
        import ipdb; ipdb.set_trace();
        pass;

def encode_packet_string(code, path, data):
    """Encodes packet to be sent to socket.io server.
    """

