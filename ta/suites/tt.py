from tester import make_test

@make_test('This is a test!')
def f(x):
    try:
        int(x)
        return False
    except ValueError:
        return True


