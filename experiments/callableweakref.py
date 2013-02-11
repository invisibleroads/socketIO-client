import types
import weakref


def ref(function):
    return CallableWeakReference(function)


class CallableWeakReference(object):

    def __init__(self, function):
        'Create a weak reference to a callable'
        try:
            if function.im_self:
                # We have a bound method or class method
                self._reference = weakref.ref(function.im_self)
            else:
                # We have an unbound method
                self._reference = None
            self._function = function.im_func
            self._class = function.im_class
        except AttributeError:
            try:
                function.func_code
                # We have a normal function or static method
                self._reference = None
                self._function = function
                self._class = None
            except AttributeError:
                function = function.__call__
                # We have a class masquerading as a function
                self._reference = weakref.ref(function.im_self)
                self._function = function.im_func
                self._class = function.im_class

    def __call__(self):
        if self.dead:
            return
        if self._reference:
            # We have a bound method
            return types.MethodType(self._function, self._reference(), self._class)
        elif self._class:
            return types.MethodType(self._function, None, self._class)
        else:
            return self._function

    @property
    def dead(self):
        if self._reference and not self._reference():
            # We have a bound method whose parent reference has died
            return True
        return False
