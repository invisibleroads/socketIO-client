import codecs
import json
import logging
import re
import requests
import six
import socket
import sys
import time
import websocket

from .exceptions import ConnectionError, TimeoutError
from .symmetries import _decode_safely, _get_text


if not hasattr(websocket, 'create_connection'):
    sys.exit("""Incompatible websocket implementation
- Please make sure that you have websocket-client installed
- Please remove other websocket implementations""")


TRANSPORTS = 'websocket', 'xhr-polling', 'jsonp-polling'
BOUNDARY = six.u('\ufffd')
TIMEOUT_IN_SECONDS = 3
_log = logging.getLogger(__name__)
escape_unicode = lambda x: codecs.getdecoder('unicode_escape')(x)[0]
try:
    unicode
except NameError:
    encode_unicode = lambda x: x
else:
    encode_unicode = lambda x: unicode(x).encode('utf-8')


class _AbstractTransport(object):

    def __init__(self):
        self._packet_id = 0
        self._callback_by_packet_id = {}
        self._wants_to_disconnect = False
        self._packets = []

    def _log(self, level, msg, *attrs):
        _log.log(level, '[%s] %s' % (self._url, msg), *[
            _decode_safely(x) for x in attrs])

    def disconnect(self, path=''):
        if not path:
            self._wants_to_disconnect = True
        if not self.connected:
            return
        if path:
            self.send_packet(0, path)
        else:
            self.close()

    def connect(self, path):
        self.send_packet(1, path)

    def send_heartbeat(self):
        self.send_packet(2)

    def message(self, path, data, callback):
        if isinstance(data, six.string_types):
            code = 3
        else:
            code = 4
            data = json.dumps(data, ensure_ascii=False)
        self.send_packet(code, path, data, callback)

    def emit(self, path, event, args, callback):
        data = json.dumps(dict(name=event, args=args), ensure_ascii=False)
        self.send_packet(5, path, data, callback)

    def ack(self, path, packet_id, *args):
        packet_id = packet_id.rstrip('+')
        data = '%s+%s' % (
            packet_id,
            json.dumps(args, ensure_ascii=False),
        ) if args else packet_id
        self.send_packet(6, path, data)

    def noop(self, path=''):
        self.send_packet(8, path)

    def send_packet(self, code, path='', data='', callback=None):
        packet_id = self.set_ack_callback(callback) if callback else ''
        packet_parts = str(code), packet_id, path, encode_unicode(data)
        packet_text = ':'.join(packet_parts)
        self.send(packet_text)
        self._log(logging.DEBUG, '[packet sent] %s', packet_text)

    def recv_packet(self, timeout=None):
        try:
            while self._packets:
                yield self._packets.pop(0)
        except IndexError:
            pass
        for packet_text in self.recv(timeout=timeout):
            self._log(logging.DEBUG, '[packet received] %s', packet_text)
            try:
                packet_parts = packet_text.split(':', 3)
            except AttributeError:
                self._log(logging.WARNING, '[packet error] %s', packet_text)
                continue
            code, packet_id, path, data = None, None, None, None
            packet_count = len(packet_parts)
            if 4 == packet_count:
                code, packet_id, path, data = packet_parts
            elif 3 == packet_count:
                code, packet_id, path = packet_parts
            elif 1 == packet_count:
                code = packet_parts[0]
            yield code, packet_id, path, data

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


class _WebsocketTransport(_AbstractTransport):

    def __init__(self, socketIO_session, is_secure, base_url, **kw):
        super(_WebsocketTransport, self).__init__()
        url = '%s://%s/websocket/%s' % (
            'wss' if is_secure else 'ws',
            base_url, socketIO_session.id)
        self._url = url
        http_session = _prepare_http_session(kw)
        req = http_session.prepare_request(requests.Request('GET', url))
        headers = ['%s: %s' % item for item in req.headers.items()]
        try:
            self._connection = websocket.create_connection(url, header=headers)
        except socket.timeout as e:
            raise ConnectionError(e)
        except socket.error as e:
            raise ConnectionError(e)
        self._connection.settimeout(TIMEOUT_IN_SECONDS)

    @property
    def connected(self):
        return self._connection.connected

    def send(self, packet_text):
        try:
            self._connection.send(packet_text)
        except websocket.WebSocketTimeoutException as e:
            message = 'timed out while sending %s (%s)' % (packet_text, e)
            self._log(logging.WARNING, message)
            raise TimeoutError(e)
        except socket.error as e:
            message = 'disconnected while sending %s (%s)' % (packet_text, e)
            self._log(logging.WARNING, message)
            raise ConnectionError(message)

    def recv(self, timeout=None):
        if timeout:
            self._connection.settimeout(timeout)
        try:
            yield self._connection.recv()
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


class _XHR_PollingTransport(_AbstractTransport):

    def __init__(self, socketIO_session, is_secure, base_url, **kw):
        super(_XHR_PollingTransport, self).__init__()
        self._url = '%s://%s/xhr-polling/%s' % (
            'https' if is_secure else 'http',
            base_url, socketIO_session.id)
        self._connected = True
        self._http_session = _prepare_http_session(kw)
        # Create connection
        for packet in self.recv_packet():
            self._enqueue_packet(packet)

    @property
    def connected(self):
        return self._connected

    @property
    def _params(self):
        return dict(t=int(time.time()))

    def send(self, packet_text):
        _get_response(
            self._http_session.post,
            self._url,
            params=self._params,
            data=packet_text,
            timeout=TIMEOUT_IN_SECONDS)

    def recv(self, timeout=None):
        response = _get_response(
            self._http_session.get,
            self._url,
            params=self._params,
            timeout=timeout or TIMEOUT_IN_SECONDS,
            stream=True)
        response_text = _get_text(response)
        if not response_text.startswith(BOUNDARY):
            yield response_text
            return
        for packet_text in _yield_text_from_framed_data(response_text):
            yield packet_text

    def close(self):
        _get_response(
            self._http_session.get,
            self._url,
            params=dict(list(self._params.items()) + [('disconnect', True)]))
        self._connected = False


class _JSONP_PollingTransport(_AbstractTransport):

    RESPONSE_PATTERN = re.compile(r'io.j\[(\d+)\]\("(.*)"\);')

    def __init__(self, socketIO_session, is_secure, base_url, **kw):
        super(_JSONP_PollingTransport, self).__init__()
        self._url = '%s://%s/jsonp-polling/%s' % (
            'https' if is_secure else 'http',
            base_url, socketIO_session.id)
        self._connected = True
        self._http_session = _prepare_http_session(kw)
        self._id = 0
        # Create connection
        for packet in self.recv_packet():
            self._enqueue_packet(packet)

    @property
    def connected(self):
        return self._connected

    @property
    def _params(self):
        return dict(t=int(time.time()), i=self._id)

    def send(self, packet_text):
        _get_response(
            self._http_session.post,
            self._url,
            params=self._params,
            data='d=%s' % requests.utils.quote(json.dumps(packet_text)),
            headers={'content-type': 'application/x-www-form-urlencoded'},
            timeout=TIMEOUT_IN_SECONDS)

    def recv(self, timeout=None):
        'Decode the JavaScript response so that we can parse it as JSON'
        response = _get_response(
            self._http_session.get,
            self._url,
            params=self._params,
            headers={'content-type': 'text/javascript; charset=UTF-8'},
            timeout=timeout or TIMEOUT_IN_SECONDS)
        response_text = _get_text(response)
        try:
            self._id, response_text = self.RESPONSE_PATTERN.match(
                response_text).groups()
        except AttributeError:
            self._log(logging.WARNING, '[packet error] %s', response_text)
            return
        if not response_text.startswith(BOUNDARY):
            yield escape_unicode(response_text)
            return
        for packet_text in _yield_text_from_framed_data(
                response_text, escape_unicode):
            yield packet_text

    def close(self):
        _get_response(
            self._http_session.get,
            self._url,
            params=dict(list(self._params.items()) + [('disconnect', True)]))
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
    try:
        response = request(*args, **kw)
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
