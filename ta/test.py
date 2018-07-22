import types
from abc import ABCMeta, abstractmethod
import traceback

all_tests = []
class Test:
    __metaclass__ = ABCMeta
    tests = []
    def __init__(self, func, inputs, expected):
        if not isinstance(func, (types.FunctionType, types.BuiltinFunctionType)):
            # func keyword argument is not a valid function
            base = '%s test: func kwarg must be a function'
            raise TypeError(base % self.name)

        # if one argument input, convert it to a tuple
        # do not convert lists to tuples using tuple([...])
        if not isinstance(inputs, tuple):
            inputs = inputs,
        
        # format the test description string
        if len(inputs) == 0:
            inp_str = '()'
        elif len(inputs) == 1:
            inp_str = '(%s)' % inputs[0]
        else:
            inp_str = str(inputs)

        self.description = '%s%s' % (func.func_name, inp_str)
        self.func = func
        self.inps = inputs
        self.expected = expected

        if func.func_code.co_argcount != len(inputs):
            # input arg count doesn't match the expected argument count
            base = 'Invalid test %s: invalid number of arguments.'
            self.passed = False
            print base % self.description
            return
        
        self.passed = self.test()

        if not self.passed:
            base = 'Test %s failed. Actual result: %s, expected result: %s'
            print base % (self.description, self.result, self.expected)

        self.tests.append(self)
        print self.tests

    @abstractmethod
    def test(self):
        pass


class Expect(Test):
    name = 'Expect'
    def __init__(self, *args):
        '''
        Inputs :
                - func     : a function, i.e. "map"
                - inputs   : a tuple with the ordered inputs to test with func
                - expected : the expected result
        Example :
            def f(x):
                return x**2

            Expect(f, 3, 9)
            Expect(lambda x: x**2, -1, 1)
        '''
        super(Expect, self).__init__(*args)

    def test(self):
        try:
            self.result = self.func(*self.inps)
        except:
            print traceback.format_exc()
            self.result = 'CODE FAILURE'

        return self.result == self.expected

class Within(Test):
    ''' func, inputs, expected, tolerance=
        Inputs :
                - func      : a function, i.e. "map"
                - inputs    : a tuple with the ordered inputs to test with func
                - expected  : the expected result
                - tolerance : the range to check that the function
                              result is within
        Example :
            def f(x):
                return x/3.0

            Within(f, 10, 3.333, tolerance=0.01)
        '''
    name = 'Within'
    def __init__(self, *args, **kwargs):
        # check that the correct number of arguments is provided
        if len(args) > 3:
            raise TypeError('Within test was provided too many arguments')
        elif len(args) < 3:
            raise TypeError('Within test was provided too few arguments')

        # make sure tolerance keyword argument is provided
        if 'tolerance' not in kwargs:
            base = 'Invalid test %s: Must provide tolerance kwarg.'
            raise TypeError(base % self.description)
        elif not isinstance(kwargs['tolerance'], (int, float)):
            base = 'Invalid test %s: Tolerance must be a number.'
            raise TypeError(base % self.description)
        else:
            self.tolerance = kwargs['tolerance']

        super(Within, self).__init__(*args)

    def test(self):
        try:
            self.result = self.func(*self.inps)
        except:
            print traceback.format_exc()
            self.result = 'CODE FAILURE'
        return abs(self.result - self.expected) < self.tolerance

class Error(Test):
    name = 'Error'
    def __init__(self, *args):
        '''
        Inputs :
                - func      : a function, i.e. "map"
                - inputs    : a tuple with the ordered inputs to test with func
                - expected  : a string that is the expected error raised
                              for instance, if you raise Exception('error'),
                              expected should be 'error'.
        Example :
        def sqrt(x):
            if x < 0:
                raise Exception('sqrt takes non-negative inputs')
            else:
                return x**0.5

        Error(sqrt, -1, 'sqrt takes non-negative inputs')
        '''
        # ensures correct number of arguments entered
        if len(args) > 3:
            raise TypeError('Error test was provided too many arguments.')
        elif len(args) < 3:
            raise TypeError('Error test was provided too few arguments.')

        super(Error, self).__init__(*args)
        # make sure the `expected` argument is a string for proper error
        # handling
        if not isinstance(self.expected, str):
            base = 'Error test: expected keyword argument must be a string'
            raise TypeError(base)

    def test(self):
        try:
            self.result = self.func(*self.inps)
            return False
        except Exception as e:
            self.result = e.args[0]
            return self.result == self.expected

