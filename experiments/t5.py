import callableweakref


class O(object):

    def __init__(self):
        self.p = P(self.f)

    def __del__(self):
        print '__del__()'

    def f(self):
        print 'f()'


class P(object):

    def __init__(self, parentMethod):
        self.parentMethod = callableweakref.ref(parentMethod)

    def show(self):
        print self.parentMethod

    def run(self):
        self.parentMethod()()


o = O()
o.p.show()
o.p.run()
