import six
try:
    from urllib.parse import urlparse as parse_url
except ImportError:
    from urlparse import urlparse as parse_url


def get_byte(x, index):
    return six.indexbytes(x, index)


def get_character(x, index):
    return chr(six.indexbytes(x, index))


def get_unicode(x):
    return x.decode('utf-8')
