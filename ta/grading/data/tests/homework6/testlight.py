# a function for simulating tests. The first argument
# is a string with a descriptive name. The second and
# third arguments are the computed and expected expressions

red = lambda s: s
# following line doesn't work on windows
# red = lambda s: '\033[91m%s\033[0m' % s 

def test(descr : str, v1, v2):
  if v1 != v2:
    print("Test '%s' %s." % (descr, red('failed')))
    print('\tActual result: %s' % v1)
    print('\tExpected result: %s' % v2)
  else:
    print("Test '%s' passed" % descr)

# v_func needs to be a function that takes no arguments and
# runs the expression you want to test
def testValueError(descr : str, v_func):
  try:
    v_func()
    print("Test '%s' %s (did not raise error)" % (descr, red('failed')))
  except Exception as e:
    print("Test '%s' passed (correctly raised error '%s')" % (descr, e.args[0]))

# ----------- EXAMPLE OF USE -------------------

## A simple function that raises an error when given 5 as input --
## this is just here to show how to write tests that raise errors
#def error_five(x : int):
#  if x == 5:
#    raise ValueError("got 5")
#  else:
#    return x

# a test that should raise an error
#testValueError("try 5", lambda: error_five(5))

# a test that will not raise an error, so the report will show the test failed
#testValueError("try 4", lambda: error_five(4))

# if a test should not raise an error, use the existing test function
#test("try 4 expect to run", 4, 4)
