import requests
import six
import ssl
import threading
import time
from six.moves.urllib.parse import urlencode as format_query
from six.moves.urllib.parse import urlparse as parse_url
from socket import error as SocketError
try:
    from websocket import (
        WebSocketConnectionClosedException, WebSocketTimeoutException,
        create_connection)
except ImportError:
    exit("""\
An incompatible websocket library is conflicting with the one we need.
You can remove the incompatible library and install the correct one
by running the following commands:

yes | pip uninstall websocket websocket-client
pip install -U websocket-client""")

from .exceptions import ConnectionError, TimeoutError
from .parsers import (
    encode_engineIO_content, decode_engineIO_content,
    format_packet_text, parse_packet_text)
from .symmetries import SSLError, memoryview


ENGINEIO_PROTOCOL = 3
TRANSPORTS = 'xhr-polling', 'websocket'


class AbstractTransport(object):

    def __init__(self, http_session, is_secure, url, engineIO_session=None):
        self.http_session = http_session
        self.is_secure = is_secure
        self.url = url
        self.engineIO_session = engineIO_session

    def recv_packet(self):
        pass

    def send_packet(self, engineIO_packet_type, engineIO_packet_data=''):
        pass

    def set_timeout(self, seconds=None):
        pass


class XHR_PollingTransport(AbstractTransport):

    def __init__(self, http_session, is_secure, url, engineIO_session=None):
        super(XHR_PollingTransport, self).__init__(
            http_session, is_secure, url, engineIO_session)
        self._params = {
            'EIO': ENGINEIO_PROTOCOL, 'transport': 'polling'}
        if engineIO_session:
            self._request_index = 1
            self._kw_get = dict(
                timeout=engineIO_session.ping_timeout)
            self._kw_post = dict(
                timeout=engineIO_session.ping_timeout,
                headers={'content-type': 'application/octet-stream'})
            self._params['sid'] = engineIO_session.id
        else:
            self._request_index = 0
            self._kw_get = {}
            self._kw_post = {}
        http_scheme = 'https' if is_secure else 'http'
        self._http_url = '%s://%s/' % (http_scheme, url)
        self._request_index_lock = threading.Lock()
        self._send_packet_lock = threading.Lock()

    def recv_packet(self):
        params = dict(self._params)
        params['t'] = self._get_timestamp()
        response = get_response(
            self.http_session.get,
            self._http_url,
            params=params,
            **self._kw_get)
        for engineIO_packet in decode_engineIO_content(response.content):
            engineIO_packet_type, engineIO_packet_data = engineIO_packet
            yield engineIO_packet_type, engineIO_packet_data

    def send_packet(self, engineIO_packet_type, engineIO_packet_data=''):
        with self._send_packet_lock:
            params = dict(self._params)
            params['t'] = self._get_timestamp()
            data = encode_engineIO_content([
                (engineIO_packet_type, engineIO_packet_data),
            ])
            get_response(
                self.http_session.post,
                self._http_url,
                params=params,
                data=memoryview(data),
                **self._kw_post)

    def _get_timestamp(self):
        with self._request_index_lock:
            timestamp = '%s-%s' % (
                int(time.time() * 1000), self._request_index)
            self._request_index += 1
        return timestamp


class WebsocketTransport(AbstractTransport):

    def __init__(self, http_session, is_secure, url, engineIO_session=None):
        super(WebsocketTransport, self).__init__(
            http_session, is_secure, url, engineIO_session)
        params = dict(http_session.params, **{
            'EIO': ENGINEIO_PROTOCOL, 'transport': 'websocket'})
        request = http_session.prepare_request(requests.Request('GET', url))
        kw = {'header': ['%s: %s' % x for x in request.headers.items()]}
        if engineIO_session:
            params['sid'] = engineIO_session.id
            kw['timeout'] = self._timeout = engineIO_session.ping_timeout
        ws_url = '%s://%s/?%s' % (
            'wss' if is_secure else 'ws', url, format_query(params))
        http_scheme = 'https' if is_secure else 'http'
        if http_scheme in http_session.proxies:  # Use the correct proxy
            proxy_url_pack = parse_url(http_session.proxies[http_scheme])
            kw['http_proxy_host'] = proxy_url_pack.hostname
            kw['http_proxy_port'] = proxy_url_pack.port
            if proxy_url_pack.username:
                kw['http_proxy_auth'] = (
                    proxy_url_pack.username, proxy_url_pack.password)
        if http_session.verify:
            if http_session.cert:  # Specify certificate path on disk
                if isinstance(http_session.cert, six.string_types):
                    kw['ca_certs'] = http_session.cert
                else:
                    kw['ca_certs'] = http_session.cert[0]
        else:  # Do not verify the SSL certificate
            kw['sslopt'] = {'cert_reqs': ssl.CERT_NONE}
        try:
            self._connection = create_connection(ws_url, **kw)
        except Exception as e:
            raise ConnectionError(e)

    def recv_packet(self):
        try:
            packet_text = self._connection.recv()
        except WebSocketTimeoutException as e:
            raise TimeoutError('recv timed out (%s)' % e)
        except SSLError as e:
            raise ConnectionError('recv disconnected by SSL (%s)' % e)
        except WebSocketConnectionClosedException as e:
            raise ConnectionError('recv disconnected (%s)' % e)
        except SocketError as e:
            raise ConnectionError('recv disconnected (%s)' % e)
        if not isinstance(packet_text, six.binary_type):
            packet_text = packet_text.encode('utf-8')
        engineIO_packet_type, engineIO_packet_data = parse_packet_text(
            packet_text)
        yield engineIO_packet_type, engineIO_packet_data

    def send_packet(self, engineIO_packet_type, engineIO_packet_data=''):
        packet = format_packet_text(engineIO_packet_type, engineIO_packet_data)
        try:
            self._connection.send(packet)
        except WebSocketTimeoutException as e:
            raise TimeoutError('send timed out (%s)' % e)
        except (SocketError, WebSocketConnectionClosedException) as e:
            raise ConnectionError('send disconnected (%s)' % e)

    def set_timeout(self, seconds=None):
        self._connection.settimeout(seconds or self._timeout)


def get_response(request, *args, **kw):
    try:
        response = request(*args, stream=True, **kw)
    except requests.exceptions.Timeout as e:
        raise TimeoutError(e)
    except requests.exceptions.ConnectionError as e:
        raise ConnectionError(e)
    except requests.exceptions.SSLError as e:
        raise ConnectionError('could not negotiate SSL (%s)' % e)
    status_code = response.status_code
    if 200 != status_code:
        raise ConnectionError('unexpected status code (%s %s)' % (
            status_code, response.text))
    return response


def prepare_http_session(kw):
    http_session = requests.Session()
    http_session.headers.update(kw.get('headers', {}))
    http_session.auth = kw.get('auth')
    http_session.proxies.update(kw.get('proxies', {}))
    http_session.hooks.update(kw.get('hooks', {}))
    http_session.params.update(kw.get('params', {}))
    http_session.verify = kw.get('verify', True)
    http_session.cert = _get_cert(kw)
    http_session.cookies.update(kw.get('cookies', {}))
    return http_session


def _get_cert(kw):
    # Reduce (None, None) to None
    cert = kw.get('cert')
    if hasattr(cert, '__iter__') and cert[0] is None:
        cert = None
    return cert
