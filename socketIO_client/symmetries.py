from six import indexbytes


try:
    from ssl import SSLError
except ImportError:
    class SSLError(Exception):
        pass


try:
    memoryview = memoryview
except NameError:
    memoryview = buffer


def get_byte(x, index):
    return indexbytes(x, index)


def get_character(x, index):
    return chr(get_byte(x, index))


def decode_string(x):
    return x.decode('utf-8')


def encode_string(x):
    return x.encode('utf-8')
