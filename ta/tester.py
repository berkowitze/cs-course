import importlib
import traceback
import sys
from test import *

def indented_string(string):
    indented = map(lambda line: '|-\t%s' % line, string.strip().split('\n'))
    return '\n'.join(indented)

class Tester:
    def __init__(self, func_name,
                 soln_filename='student_solution.py',
                 tests_filename='student_tests.py',
                 compiles=True):
        '''
        Tester class
        Inputs:
            - soln_filename  : filepath of the student's solution file
            - tests_filename : filepath of the student's test file
            - func_name      : name of the function being tested
            - compiles       : indicates if the student's code compiles.
                               only for recursive usage.
        '''

        module_name = soln_filename.strip('.py')
        try:
            module = importlib.import_module(module_name)
            self.s_func = getattr(module, func_name)
        except ImportError as e:
            error = 'Invalid code filename, or student raised ImportError.'
            error += ' Fix and rerun.'
            raise ImportError(error)
        except AttributeError as e:
            error = 'Function %s does not exist, or student raised AttributeError.'
            error += ' Fix and rerun.'
            print error % func_name
            sys.exit(0)
        except Exception as e:
            print 'Error running student code:'
            print indented_string(traceback.format_exc())
            print 'Student code does not compile. Fix and press enter to'
            print 'retry, or press <ctrl-c> to exit' % base
            try:
                raw_input()
            except KeyboardInterrupt:
                print '\nExiting...'
                sys.exit(0)

            self.__init__(soln_filename=soln_filename,
                          tests_filename=tests_filename,
                          func_name=func_name,
                          compiles=False)

        self.compiles  = compiles
        self.func_name = func_name

        if not self.compiles:
            print 'Student code does not compile.'
            # except Exception as e:
            #     print e
            #     raise Exception

    def test_exact(self, args, expect):
        ''' tests if the studen'ts function returns the correct result.
        Inputs :
            - args   : a tuple of the arguments to be passed to
                       the student's function
            - expect : the correct result
        Output :
            - 0 if the test passes
            - 1 if the test fails
            - 2 if the student's function fails
        Example:
            Student function:
                def alive_p(age):
                    return age >= 0 and age < 130

            tester = Tester('solution.py', 'tests.py', 'alive_p')
            tester.test_exact((30, ), True)
        Example output: 0
        '''
        call_name = self._args_to_string(args)
        try:
            result = self.s_func(*args)
            if result == expect:
                return 0
            else:
                base = 'Student code incorrectly returned %s, expected %s on %s'
                print base % (result, expect, call_name)
                return 1
        except Exception as e:
            print 'Student code incorrectly failed on %s:' % call_name
            print indented_string(traceback.format_exc())
            return 2


    def test_within(self, args, expect, tol):
        ''' tests if the student's function returns
            a correct numeric result, within some tolerance
        Inputs :
            - args   : a tuple of the arguments to be passed to
                       the student's function
            - expect : the correct result
            - tol    : the tolerance to check within
        Output :
            - 0 if the test passes
            - 1 if the student function returns an incorrect result
            - 2 if the student function fails
        '''
        call_name = self._args_to_string(args)
        try:
            result = self.s_func(*args)
            if abs(result - expect) < tol:
                return 0
            else:
                base = 'Student code returned %s, expected %s on %s'
                print base % (result, expect, call_name)
                return 1
        except Exception as e:
            print 'Student code incorrectly failed with input %s' % args
            print indented_string(traceback.format_exc())
            return 2

    def test_error(self, args, expected_error=None):
        ''' Tests if the student's code raises an error, with an option
            to ensure the error is a certain type.
        Inputs : 
            - args : a tuple of the arguments to be passed to the
                     student's function
            - expected_error : if None (default), any error will
                               result in a test pass. if a string,
                               the error raised must be that type
        Output :
            - 0 if test passes
            - 1 if an error is not raised by the student's code
            - 2 if an error is raised but it's the wrong type
        Example:
            Student Function:
                def str_to_numb(string):
                    return float(string)

            tester = Tester('solution.py', 'tests.py', 'str_to_numb')
            tester.test_error('hi', 'ValueError')

        Example Output: 0
        '''
        call_name = self._args_to_string(args)
        try:
            self.s_func(*args)
            print 'Student code did not fail as expected on %s' % call_name
            return 1
        except Exception as e:
            if expected_error is not None:
                error_name = type(e).__name__
                if error_name != expected_error:
                    base = 'Student code failed with %s instead of %s on %s'
                    print base % (error_name, expected_error, call_name)
                    return 2
                else:
                    return 0
            else:
                return 0

    def _args_to_string(self, args):
        if len(args) == 0:
            substring = '()'
        elif len(args) == 1:
            substring = '(%s)' % args[0]
        else:
            substring = str(args)

        return '%s%s' % (self.func_name, substring)

class TestAnd:
    def __init__

if __name__ == '__main__':
    tester = Tester('sqrt')
    assert tester.test_exact((4,), 2) == 0
    assert tester.test_exact((4,), 1) == 1
    assert tester.test_exact((-1,), 1) == 2

    assert tester.test_within((3.,), 1.73, 0.01) == 0
    assert tester.test_within((5.,), 10, 0.01) == 1
    assert tester.test_within((-1,), 5, 0.5) == 2

    assert tester.test_error((-1,), 'ValueError') == 0
    assert tester.test_error((-1, )) == 0
    assert tester.test_error((4,)) == 1
    assert tester.test_error((-1,), 'AttributeError') == 2
    print ''
    print 'tests.py runs as expected.'

