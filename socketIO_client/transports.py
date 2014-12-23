import json
import logging
import parser
from parser import Message, MessageType, PacketType
import re
import requests
import six
import socket
import time
import websocket

from .exceptions import SocketIOError, ConnectionError, TimeoutError


TRANSPORTS = 'websocket', 'xhr-polling', 'jsonp-polling'
BOUNDARY = six.u('\ufffd')
TIMEOUT_IN_SECONDS = 300
_log = logging.getLogger(__name__)


class _AbstractTransport(object):

    def __init__(self):
        self._packet_id = 0
        self._callback_by_packet_id = {}
        self._wants_to_disconnect = False
        self._packets = []
        self._timeout = TIMEOUT_IN_SECONDS;

    def set_timeout(self, timeout):
        self._timeout = timeout;

    def disconnect(self, path=''):
        if not path:
            self._wants_to_disconnect = True
        if not self.connected:
            return
        if path:
            self.send_packet(PacketType.CLOSE, path)
        else:
            self.close()

    def connect(self, path):
        if path != "":
            _log.debug("Connecting to path: %s" % path);
            data = Message(MessageType.CONNECT, path).encode_as_string();
            self.send_packet(PacketType.MESSAGE, path, data);

            # Wait for response.
            responded = False;
            while not responded:
                for packet in self.recv_packet():
                    _log.debug("[connect wait] Waiting for confirmation");
                    if (packet.type == PacketType.MESSAGE
                        and packet.payload.type == MessageType.CONNECT
                        and packet.payload.path == path):
                        _log.debug("Connected to path: %s" % path);
                        responded = True;
        else:
            self.send_packet(PacketType.OPEN, path, data);

    def send_heartbeat(self):
        self.send_packet(PacketType.PING)

    def message(self, path, data, callback):
        if isinstance(data, basestring):
            code = 3
        else:
            code = 4
            data = json.dumps(data, ensure_ascii=False)
        self.send_packet(code, path, data, callback)

    def emit(self, path, event, args, callback):
        message = Message(MessageType.EVENT, [event, args], path);
        self.send_packet(PacketType.MESSAGE, path, message.encode_as_json(), callback)

    def ack(self, path, packet_id, *args):
        packet_id = packet_id.rstrip('+')
        data = '%s+%s' % (
            packet_id,
            json.dumps(args, ensure_ascii=False),
        ) if args else packet_id
        #self.send_packet(6, path, data)

    def noop(self, path=''):
        self.send_packet(PacketType.NOOP, path)

    def send_packet(self, code, path='', data='', callback=None):
        packet_text = parser.encode_packet_string(code, path, data);
        self.send(packet_text)
        _log.debug('[packet sent] %s', packet_text)

    def recv_packet(self):
        try:
            while self._packets:
                yield self._packets.pop(0)
        except IndexError:
            pass
        for packet in self.recv():
            yield packet

    def _enqueue_packet(self, packet):
        self._packets.append(packet)

    def set_ack_callback(self, callback):
        'Set callback to be called after server sends an acknowledgment'
        self._packet_id += 1
        self._callback_by_packet_id[str(self._packet_id)] = callback
        return '%s+' % self._packet_id

    def get_ack_callback(self, packet_id):
        'Get callback to be called after server sends an acknowledgment'
        callback = self._callback_by_packet_id[packet_id]
        del self._callback_by_packet_id[packet_id]
        return callback

    @property
    def has_ack_callback(self):
        return True if self._callback_by_packet_id else False


class WebsocketTransport(_AbstractTransport):

    def __init__(self, socketIO_session, is_secure, base_url, **kw):
        super(WebsocketTransport, self).__init__()

        self._url = '%s://%s/?EIO=%d&transport=websocket&sid=%s' % (
            'wss' if is_secure else 'ws',
            base_url, parser.ENGINE_PROTOCOL, socketIO_session.id)

        try:
            self._connection = websocket.create_connection(self._url)
        except socket.timeout as e:
            raise ConnectionError(e)
        except socket.error as e:
            raise ConnectionError(e)
        self._connection.settimeout(TIMEOUT_IN_SECONDS)

    @property
    def connected(self):
        return self._connection.connected

    def send_packet(self, code, path="", data='', callback=None):
        packet_text = Message(code, data).encode_as_string();
        self.send(packet_text)
        _log.debug('[packet sent] %s', packet_text)

    def send(self, packet_text):
        try:
            self._connection.send(packet_text)
        except websocket.WebSocketTimeoutException as e:
            message = 'timed out while sending %s (%s)' % (packet_text, e)
            _log.warn(message)
            raise TimeoutError(e)
        except socket.error as e:
            message = 'disconnected while sending %s (%s)' % (packet_text, e)
            _log.warn(message)
            raise ConnectionError(message)

    def recv(self):
        try:
            response = self._connection.recv();
            try:
                for packet in parser.decode_response(response):
                    _log.debug('[websocket packet received] %s', str(packet));
                    yield packet;
            except AttributeError:
                _log.warn('[packet error] %s', repr(response))
                return;
        except websocket.WebSocketTimeoutException as e:
            raise TimeoutError(e)
        except websocket.SSLError as e:
            if 'timed out' in e.message:
                raise TimeoutError(e)
            else:
                raise ConnectionError(e)
        except websocket.WebSocketConnectionClosedException as e:
            raise ConnectionError('connection closed (%s)' % e)
        except socket.error as e:
            raise ConnectionError(e)

    def close(self):
        self._connection.close()


class XHR_PollingTransport(_AbstractTransport):

    def __init__(self, socketIO_session, is_secure, base_url, **kw):
        super(XHR_PollingTransport, self).__init__()
        self._url = '%s://%s/?EIO=%d&transport=polling&sid=%s' % (
            'https' if is_secure else 'http',
            base_url, parser.ENGINE_PROTOCOL, socketIO_session.id)
        self._connected = True
        self._http_session = _prepare_http_session(kw)
        self._waiting = False;

    @property
    def connected(self):
        return self._connected

    @property
    def _params(self):
        return dict(t=int(time.time() * 1000))

    def send(self, packet_text):
        uri = self._url + "&" + '&'.join("%s=%s" % (k, v) for (k, v) in self._params.iteritems());
        response = None;
        try:
            response = requests.post(uri, data=packet_text);
        except requests.exceptions.Timeout as e:
            message = 'timed out while sending %s (%s)' % (packet_text, e)
            _log.warn(message)
            raise TimeoutError(e)
        except requests.exceptions.ConnectionError as e:
            message = 'disconnected while sending %s (%s)' % (packet_text, e)
            _log.warn(message)
            raise ConnectionError(message)
        except requests.exceptions.SSLError as e:
            raise ConnectionError('could not negotiate SSL (%s)' % e)
            status = response.status_code
            if 200 != status:
                raise ConnectionError('unexpected status code (%s)' % status)
        return response

    def recv(self):
        if self._waiting:
            return;

        self._waiting = True;
        response = _get_response(
            self._http_session.get,
            self._url,
            params = self._params,
            timeout = self._timeout)

        self._waiting = False;
        if response is None:
            return;

        for packet in parser.decode_response(response):
            yield packet;
        return

    def close(self):
        self.send_packet(41)
        self.send_packet(1)
        self._connected = False

def _yield_text_from_framed_data(framed_data, parse=lambda x: x):
    parts = [parse(x) for x in framed_data.split(BOUNDARY)]
    for text_length, text in zip(parts[1::2], parts[2::2]):
        if text_length != str(len(text)):
            warning = 'invalid declared length=%s for packet_text=%s' % (
                text_length, text)
            _log.warn('[packet error] %s', warning)
            continue
        yield text


def _get_response(request, *args, **kw):
    response = None;
    try:
        response = request(*args, **kw);
        response.close();
    except requests.exceptions.Timeout as e:
        raise TimeoutError(e)
    except requests.exceptions.ConnectionError as e:
        raise ConnectionError(e)
    except requests.exceptions.SSLError as e:
        raise ConnectionError('could not negotiate SSL (%s)' % e)
    status = response.status_code
    if 200 != status:
        raise ConnectionError('unexpected status code (%s)' % status)
    return response


def _prepare_http_session(kw):
    http_session = requests.Session()
    http_session.headers.update(kw.get('headers', {}))
    http_session.auth = kw.get('auth')
    http_session.proxies.update(kw.get('proxies', {}))
    http_session.hooks.update(kw.get('hooks', {}))
    http_session.params.update(kw.get('params', {}))
    http_session.verify = kw.get('verify')
    http_session.cert = kw.get('cert')
    http_session.cookies.update(kw.get('cookies', {}))
    return http_session
