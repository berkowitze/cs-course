import os
from filelock import Timeout, FileLock
from contextlib import contextmanager

@contextmanager
def locked_file(filename, mode='r', hta=False):
    """ this will ensure no file is opened across different processes
    Note: minimize code in the with block; as little time as possible should
    be spent with the file locked. if possible, the with block should contain
    a single read or write operation and no more (parse outside).
    
    usage:
    with locked_file(filename, mode) as f:
        f.read()
        ...
        # OR
        f.write(...)
    """
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
