def mean(lst):
    if len(lst) == 0:
        raise Exception('Cannot take mean of empty list.')
    S = 0
    for item in lst:
        S += item

    return S / float(len(lst))

def bad_mean(lst):
    if len(lst) == 0:
        raise Exception('Cannot take mean of empty list.')

    S = 0
    for item in lst:
        S += item
        return S / float(len(lst))

def map2(f, lst1, lst2):
    out = []
    for item1, item2 in zip(lst1, lst2):
        out.append(f(item1, item2))

    return out

def str_to_numb(string):
    return float(string)

def square(x):
    return x**2

def sqrt(x):
    if x < 0:
        raise ValueError('input to sqrt cannot be negative')
    else:
        return x**0.5