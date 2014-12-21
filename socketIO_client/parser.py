import logging
import json

_log = logging.getLogger(__name__)

""" Decodes a response from requests lib.
"""
def decode_response(response):
    # TODO(sean): Should we use the 'raw' stream instead?
    raw_bytes = response.content;
    packet_type = "string" if ord(raw_bytes[0]) == 0 else "binary";
    _log.debug("Packet type: %s" % packet_type);

    if packet_type is "string":
        length_bytes = [];
        offset = 1;
        while ord(raw_bytes[offset]) is not 255:
            length_bytes.append(ord(raw_bytes[offset]));
            offset += 1;
        offset += 1;

        length = 0;
        base = 1;
        for digit in reversed(length_bytes):
            length += (int(digit) * base);
            base *= 10;
        _log.debug("Packet length: %d" % length);

        message_type = raw_bytes[offset];
        offset += 1;

        message = {"type": message_type, "payload": json.loads(raw_bytes[offset:offset + length - 1])};
        _log.debug("Message: %s" % repr(message));
        return message;
    else:
        pass;

    return "";

def decode_packet(packet):
    pass;
