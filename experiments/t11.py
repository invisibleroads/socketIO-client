class A(object):

    def __init__(self):
        self.c = Common()
        self.b = B(self.c)

    def __del__(self):
        print '__del__()'


class B(object):

    def __init__(self, c):
        self.c = c


class Common(object):
    pass


a = A()
