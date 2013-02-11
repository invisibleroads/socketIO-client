import weakref


class O(object):

    def __init__(self):
        self.p = P(self.f)

    def __del__(self):
        print '__del__()'

    def f(self):
        pass


class P(object):

    def __init__(self, parentMethod):
        self.parentMethod = weakref.ref(parentMethod)

    def show(self):
        print self.parentMethod


o = O()
o.p.show()  # Dead on arrival
