class A(object):

    def __init__(self):
        self.b = B(self)

    def __del__(self):
        print '__del__()'


class B(object):

    def __init__(self, a):
        self.a = a


a = A()
