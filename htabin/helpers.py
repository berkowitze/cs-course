import os
from filelock import Timeout, FileLock
from contextlib import contextmanager

@contextmanager
def locked_file(filename, mode='r', hta=False):
    ''' this will ensure no file is opened across different processes '''
    # todo: should probably make write mode threaded, not sure how to easily
    # though. so if the program halts while a file is open in write mode,
    # the contents of the file won't be removed. one option is havng user
    # pass in a function that does the work if they are using 'w' mode, but
    # that's a hassle. will implement if it becomes an issue (.snapshots until
    # then if necessary)
    if not (mode == 'r' or mode == 'a' or mode == 'w'):
        base = 'Can only open locked file in r, w, or a mode (just in case)'
        raise ValueError(base)

    lock_path = filename + '.lock'
    lock = FileLock(lock_path, timeout=5) # throw error after 5 seconds
    with lock, open(filename, mode) as f:
        yield f

        # after file is closed, attempt to remove the .lock
        # file; the file is only clutter, it won't have an impact
        # on anything, so don't try too hard.
        try:
            os.unlink(lock_path)
        except NameError:
            raise
        except:
            pass
