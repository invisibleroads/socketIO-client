import six
try:
    from urllib.parse import urlparse as parse_url
except ImportError:
    from urlparse import urlparse as parse_url


def get_byte(x, index):
    return six.indexbytes(x, index)


def get_character(x, index):
    return chr(six.indexbytes(x, index))


def encode_string(x):
    return x.encode('utf-8')


def decode_string(x):
    return x.decode('utf-8')
