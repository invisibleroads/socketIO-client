import requests
from .exceptions import ConnectionError, TimeoutError


ENGINEIO_PROTOCOL = 3


class AbstractTransport(object):
    pass


class XHR_PollingTransport(AbstractTransport):

    # pass http session
    # pass session id (can be none)
    # pass timeout

    def send_packet(self, engineIO_packet_type, engineIO_packet_data):
        _get_response()

        assert ok

        response = self._http_session.post(self._url, params={
            'EIO': self._engineIO_protocol,
            'transport': 'polling',
            't': self._get_timestamp(),
            'sid': self._session_id,
        }, data=_encode_engineIO_content([
            (engineIO_packet_type, engineIO_packet_data),
        ]), headers={
            'content-type': 'application/octet-stream',
        })
        assert response.content == 'ok'

    def _recv_packet(self):
        response = _get_response(
            self._http_session.get,
            self._url,
            params={
                'EIO': self._engineIO_protocol,
                'transport': 'polling',
                't': self._get_timestamp(),
                'sid': self._session_id,
            },
            timeout=self._ping_timeout)
        for engineIO_packet in _decode_engineIO_content(response.content):
            yield engineIO_packet


def _get_response(request, *args, **kw):
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
