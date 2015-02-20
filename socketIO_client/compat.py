import six


def get_byte(x, index):
    return six.indexbytes(x, index)


def get_character(x, index):
    return chr(six.indexbytes(x, index))


def get_unicode(x):
    return x.decode('utf-8')
