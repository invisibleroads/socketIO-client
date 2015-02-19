import requests
from .exceptions import ConnectionError, TimeoutError


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
