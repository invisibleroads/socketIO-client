# Will the destructor of a class be called if its two children have cyclic
# references to each other?  Yes.


class Parent(object):

    def __init__(self):
        self.child = Child()

    def __del__(self):
        print 'Parent.__del__()'


class Child(object):

    def __init__(self):
        self.grandChild = GrandChild(self)

    def __del__(self):
        print 'Child.__del__()'


class GrandChild(object):

    def __init__(self, parent):
        self.parent = parent

    def __del__(self):
        print 'GrandChild.__del__()'


parent = Parent()
