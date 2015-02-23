import requests
import time

from .exceptions import ConnectionError, TimeoutError
from .parsers import decode_engineIO_content, encode_engineIO_content


ENGINEIO_PROTOCOL = 3
TRANSPORTS = 'websocket', 'xhr-polling'


class AbstractTransport(object):

    def __init__(self, http_session, is_secure, url, engineIO_session=None):
        self.http_session = http_session
        self.is_secure = is_secure
        self.url = url
        self.engineIO_session = engineIO_session

    def recv_packet(self):
        pass

    def send_packet(self, engineIO_packet_type, engineIO_packet_data):
        pass


class XHR_PollingTransport(AbstractTransport):

    def __init__(self, http_session, is_secure, url, engineIO_session=None):
        super(XHR_PollingTransport, self).__init__(
            http_session, is_secure, url, engineIO_session)
        self.http_url = '%s://%s/' % ('https' if is_secure else 'http', url)
        self.params = {
            'EIO': ENGINEIO_PROTOCOL,
            'transport': 'polling',
        }
        if engineIO_session:
            self.request_index = 1
            self.kw_get = dict(timeout=engineIO_session.ping_timeout)
            self.kw_post = dict(headers={
                'content-type': 'application/octet-stream',
            })
            self.params['sid'] = engineIO_session.id
        else:
            self.request_index = 0
            self.kw_get = {}
            self.kw_post = {}

    def recv_packet(self):
        params = dict(self.params)
        params['t'] = self._get_timestamp()
        response = get_response(
            self.http_session.get,
            self.http_url,
            params=params,
            **self.kw_get)
        for engineIO_packet in decode_engineIO_content(response.content):
            yield engineIO_packet

    def send_packet(self, engineIO_packet_type, engineIO_packet_data):
        params = dict(self.params)
        params['t'] = self._get_timestamp()
        response = get_response(
            self.http_session.post,
            self.http_url,
            params=params,
            data=encode_engineIO_content([
                (engineIO_packet_type, engineIO_packet_data),
            ]),
            **self.kw_post)
        assert response.content == 'ok'

    def _get_timestamp(self):
        timestamp = '%s-%s' % (int(time.time() * 1000), self.request_index)
        self.request_index += 1
        return timestamp


def get_response(request, *args, **kw):
    try:
        response = request(*args, **kw)
    except requests.exceptions.Timeout as e:
        raise TimeoutError(e)
    except requests.exceptions.ConnectionError as e:
        raise ConnectionError(e)
    except requests.exceptions.SSLError as e:
        raise ConnectionError('could not negotiate SSL (%s)' % e)
    status_code = response.status_code
    if 200 != status_code:
        raise ConnectionError('unexpected status code (%s)' % status_code)
    return response


def prepare_http_session(kw):
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
