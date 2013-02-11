# Note 1: The expected behavior of weakref to an instance is that it should
# return None if no other strong references to the instance exist,
# signalling that the instance can be safely garbage collected.
#
# Note 2: The expected behavior of weakref to a method is that it should
# return None if no other strong references to the parent instance exist,
# signalling that the parent instance can be safely garbage collected.
#
# Note 3: The IPython interpreter stores its own references and will
# produce results different from those of the default Python interpreter.
import callableweakref
import weakref
import unittest


class TestCallableWeakRef(unittest.TestCase):

    def test_instanceDirectWeakref_dies_on_arrival(self):
        'Assert that weakref works as expected'
        instanceDirectWeakref = weakref.ref(Instance())
        assert instanceDirectWeakref() is None

    def test_instanceIndirectWeakref_dies_when_instance_dies(self):
        'Assert that weakref works as expected'
        instance = Instance()
        instanceIndirectWeakref = weakref.ref(instance)
        assert instanceIndirectWeakref() is instance
        del instance
        assert instanceIndirectWeakref() is None

    def test_boundMethodDirectWeakref_dies_on_arrival(self):
        'Assert that weakref does not work as expected'
        instance = Instance()
        boundMethodDirectWeakref = weakref.ref(instance.call)
        assert boundMethodDirectWeakref() is None  # Should be instance

    def test_boundMethodIndirectWeakref_lives_when_instance_dies(self):
        'Assert that weakref works as expected'
        instance = Instance()
        boundMethod = instance.call
        boundMethodIndirectWeakref = weakref.ref(boundMethod)
        assert boundMethodIndirectWeakref() is boundMethod
        del instance
        assert boundMethodIndirectWeakref() is boundMethod
        del boundMethod
        assert boundMethodIndirectWeakref() is None

    def test_unboundMethodDirectWeakref_dies_on_arrival(self):
        'Assert that weakref does not work as expected'
        unboundMethodDirectWeakref = weakref.ref(Instance.call)
        assert unboundMethodDirectWeakref() is None  # Should be Instance.call

    def test_unboundMethodIndirectWeakref_dies_when_unboundMethod_dies(self):
        'Assert that weakref works as expected'
        unboundMethod = Instance.call
        unboundMethodIndirectWeakref = weakref.ref(unboundMethod)
        assert unboundMethodIndirectWeakref() is unboundMethod
        del unboundMethod
        assert unboundMethodIndirectWeakref() is None

    def test_classFunctionDirectWeakref_dies_on_arrival(self):
        'Assert that weakref works as expected'
        classFunctionDirectWeakref = weakref.ref(Instance())
        assert classFunctionDirectWeakref() is None

    def test_classFunctionIndirectWeakref_dies_when_classFunction_dies(self):
        'Assert that weakref works as expected'
        classFunction = Instance()
        classFunctionIndirectWeakref = weakref.ref(classFunction)
        assert classFunctionIndirectWeakref() is classFunction
        del classFunction
        assert classFunctionIndirectWeakref() is None

    def test_normalFunctionDirectWeakref_dies_when_normal_function_dies(self):
        'Assert that weakref works as expected'
        call = lambda: None
        normalFunctionDirectWeakref = weakref.ref(call)
        assert normalFunctionDirectWeakref() is call
        del call
        assert normalFunctionDirectWeakref() is None

    def test_normalFunctionIndirectWeakref_dies_when_normal_function_dies(self):
        'Assert that weakref works as expected'
        call = lambda: None
        normalFunction = call
        normalFunctionIndirectWeakref = weakref.ref(normalFunction)
        assert normalFunctionIndirectWeakref() is normalFunction
        del normalFunction
        assert normalFunctionIndirectWeakref() is call
        del call
        assert normalFunctionIndirectWeakref() is None

    # Assert that CallableWeakref works as expected for callables

    def test_boundMethodDirectCallableWeakref_dies_when_instance_dies(self):
        instance = Instance()
        boundMethodDirectCallableWeakref = callableweakref.ref(instance.call)
        self.assertEqual(boundMethodDirectCallableWeakref(), instance.call)
        del instance
        assert boundMethodDirectCallableWeakref() is None

    def test_boundMethodIndirectCallableWeakref_dies_when_instance_dies(self):
        instance = Instance()
        boundMethod = instance.call
        boundMethodIndirectCallableWeakref = callableweakref.ref(boundMethod)
        self.assertEqual(boundMethodIndirectCallableWeakref(), boundMethod)
        del instance
        self.assertEqual(boundMethodIndirectCallableWeakref(), boundMethod)
        del boundMethod
        assert boundMethodIndirectCallableWeakref() is None

    def test_unboundMethodDirectCallableWeakref_lives_on_arrival(self):
        unboundMethodDirectCallableWeakref = callableweakref.ref(Instance.call)
        self.assertEqual(unboundMethodDirectCallableWeakref(), Instance.call)

    def test_unboundMethodIndirectCallableWeakref_lives_on_arrival(self):
        unboundMethod = Instance.call
        unboundMethodIndirectCallableWeakref = callableweakref.ref(unboundMethod)
        self.assertEqual(unboundMethodIndirectCallableWeakref(), unboundMethod)

    def test_classMethodIndirectCallableWeakref_lives_on_arrival(self):
        classMethod = Instance.call_classmethod
        classMethodIndirectCallableWeakref = callableweakref.ref(classMethod)
        self.assertEqual(classMethodIndirectCallableWeakref(), classMethod)

    def test_staticMethodIndirectCallableWeakref_lives_on_arrival(self):
        staticMethod = Instance.call_staticmethod
        staticMethodIndirectCallableWeakref = callableweakref.ref(staticMethod)
        self.assertEqual(staticMethodIndirectCallableWeakref(), staticMethod)

    def test_classFunctionDirectCallableWeakref_dies_on_arrival(self):
        classFunctionDirectCallableWeakref = callableweakref.ref(Instance())
        assert classFunctionDirectCallableWeakref() is None

    def test_classFunctionIndirectCallableWeakref_dies_when_classFunction_dies(self):
        classFunction = Instance()
        classFunctionIndirectCallableWeakref = callableweakref.ref(classFunction)
        self.assertEqual(classFunctionIndirectCallableWeakref(), classFunction.__call__)
        del classFunction
        assert classFunctionIndirectCallableWeakref() is None

    def test_normalFunctionDirectCallableWeakref_lives_on_arrival(self):
        call = lambda: None
        normalFunctionDirectCallableWeakref = callableweakref.ref(call)
        self.assertEqual(normalFunctionDirectCallableWeakref(), call)

    def test_normalFunctionIndirectCallableWeakref_lives_on_arrival(self):
        call = lambda: None
        normalFunction = call
        normalFunctionIndirectWeakref = callableweakref.ref(normalFunction)
        self.assertEqual(normalFunctionIndirectWeakref(), normalFunction)
        del normalFunction
        self.assertEqual(normalFunctionIndirectWeakref(), call)


class Instance(object):

    def __call__(self):
        pass

    def call(self):
        pass

    @classmethod
    def call_classmethod(Class):
        pass

    @staticmethod
    def call_staticmethod():
        pass
