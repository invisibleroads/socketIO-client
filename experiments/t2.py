import weakref


class O(object):

    def __init__(self):
        self.p = P(self)

    def __del__(self):
        print '__del__()'


class P(object):

    def __init__(self, parent):
        self.parent = weakref.ref(parent)


o = O()
