def green(s):
    return '\033[32m%s\033[0m' % s

def yellow(s):
    return '\033[33m%s\033[0m' % s

def red(s):
    return '\033[31m%s\033[0m' % s

def run_test(name, success, error, fail=None):
    def testwrapper(f):
        def inner(*args, **kwargs):
            try:
                res = f(*args, **kwargs)
            except Exception as e:
                print '%s: %s (%s)' % (name, red("Raised Error"), str(e))
                return {name: error}

            if not (res is True or res is False):
                raise ValueError('Function must return boolean')

            if f(*args, **kwargs):
                print '%s: %s' % (name, green("Passed"))
                return {name: success}
            else:
                print '%s: %s' % (name, yellow("Failed"))
                return {name: fail}

        return inner

    return testwrapper

@run_test('Test 1', 'All tests passed', 'Error raised')
def f(x):
    a = []
    student_function()
    return a == [1,2,3]

f(3)
f(4)
f('h')
