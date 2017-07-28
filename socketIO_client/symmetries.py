try:
    from urllib.parse import urlparse as _parse_url
except ImportError:
    from urlparse import urlparse as _parse_url


def _decode_utf8(x):
    return x.decode('utf-8') if hasattr(x, 'decode') else x


try:
    unicode
except NameError:
    def _encode_utf8(x):
        return x
else:
    def _encode_utf8(x):
        return unicode(x).encode('utf-8')


def _get_text(response):
    try:
        return response.text     # requests 2.7.0
    except AttributeError:
        return response.content  # requests 0.8.2
