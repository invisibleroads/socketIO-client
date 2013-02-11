class O(object):

    def __init__(self):
        self.p = P(self.f)

    def __del__(self):
        print '__del__()'

    def f(self):
        pass


class P(object):

    def __init__(self, parentMethod):
        self.parentMethod = parentMethod


o = O()
