import six
try:
    from logging import NullHandler
except ImportError:  # Python 2.6
    from logging import Handler

    class NullHandler(Handler):

        def emit(self, record):
            pass
try:
    from urllib import urlencode as format_query
except ImportError:
    from urllib.parse import urlencode as format_query  # noqa
try:
    from urlparse import urlparse as parse_url
except ImportError:
    from urllib.parse import urlparse as parse_url  # noqa
try:
    memoryview = memoryview
except NameError:
    memoryview = buffer


def get_character(x, index):
    return chr(get_byte(x, index))


def get_byte(x, index):
    return six.indexbytes(x, index)


def decode_string(x):
    return x.decode('utf-8')


def encode_string(x):
    return x.encode('utf-8')
