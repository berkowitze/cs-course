from filelock import Timeout, FileLock
from contextlib import contextmanager
from functools import wraps
import os

BASE_PATH = '/course/cs0050'
default_resource_path = os.path.join(BASE_PATH, 'resource-lock.lock')

@contextmanager
def locked_file(filename, mode='r'):
    ''' this will ensure no file is opened across different processes '''
    lock = FileLock(filename + ".lock")
    with lock, open(filename, mode) as f:
        yield f

def require_resource(resource=default_resource_path):
    ''' use require_resource as a decorator when writing a function that you
    don't want to be run simultaneously; for example, if you don't want to run
    extract_handin at the same time on two different TA's computers
    you'd do something like:

    @require_resource()
    def extract_handin(...):
        ...

    see example at end of file (/ta/grading/helpers.py)
    '''
    def decorator(f):
        @wraps(f)
        def magic(*args, **kwargs):
            ''' run the wrapped functions while a lock is acquired '''
            with FileLock(resource):
                return f(*args, **kwargs)

        return magic

    return decorator

if __name__ == '__main__':
    fp = os.path.join(BASE_PATH, 'ta', 'assignments.json')
    ## example of file locking; run helpers.py in two separate shells
    #  and observe the behavior
    # def single_file():
    #     print 'Beginning execution of single_file'
    #     with locked_file(fp) as f:
    #         print 'Beginning to do things with lock acquired'
    #         # raw_input simulating an expensive program being run
    #         raw_input('Press enter to continue...')

    #     print 'Lock has been released.'

    # single_file()
    ## end of first example

    ## example of resource locking; uncomment & run helpers.py in two
    #  different shells and observe the behavior

    import time
    @require_resource(fp + '.lock')
    def resource(x):
        print 'Resource lock acquired. Running resource(%s)' % x
        # raw input simulating long execution of resource function
        raw_input('Press enter to continue')
        print 'Resource lock released'

    resource(time.time())

