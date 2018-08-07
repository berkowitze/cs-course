__author__  = 'Eli Berkowitz'
__email__   = 'eliberkowitz@gmail.com' # email with any questions

import json
from filelock import Timeout, FileLock
from contextlib import contextmanager
from functools import wraps
import os
from threading import Thread

BASE_PATH = '/course/cs0050'
default_resource_path = os.path.join(BASE_PATH, 'resource-lock.lock')
@contextmanager
def locked_file(filename, mode='r'):
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

def rubric_check(path):
    ''' given a path to a rubric JSON file
        /course/.../ta/grading/data/rubrics/.../q1.json
    determines whether or not the rubric is valid. Returns False if it's not
    a valid error, along with an informative string informing as to why
    it's invalid, and True if it is valid (with a useless string placeholder)
    '''
    if not os.path.exists(path):
        return False, 'Rubric %s does not exist' % path
    if not os.path.splitext(path)[1] == '.json':
        return False, 'Rubric %s needs to be a JSON file' % path
    try:
        with open(path) as f:
            data = json.load(f)
    except ValueError:
        return False, 'Rubric JSON is invalid (does not load)'
    
    if not '_COMMENTS' in data.keys():
        return False, 'Rubric needs a _COMMENTS key'
    if not isinstance(data['_COMMENTS'], list):
        return False, 'Rubric _COMMENTS must be list'
    for item in data['_COMMENTS']:
        if not isinstance(item, dict):
            return False, 'Rubric _COMMENTS has non-dict item %s' % item
        if 'comment' not in item.keys():
            return False, 'Comment %s does not have \'comment\' key' % item
        if 'value' not in item.keys():
            return False, 'Comment %s does not have \'value\' key' % item
        if not isinstance(item['value'], bool):
            v = 'Rubric general comment %s \'value\' key must be boolean'
            return False, v % item
    for key in data.keys():
        if key == '_COMMENTS':
            continue
        if not isinstance(data[key], dict):
            return False, 'Rubric key %s must be a dict' % key
        if 'comments' not in data[key]:
            return False, 'Rubric key %s must have \'comments\' key' % key
        if 'rubric_items' not in data[key]:
            return False, 'Rubric key %s must have \'rubric_items\' key' % key
        for item in data[key]['comments']:
            if not isinstance(item, dict):
                return False, 'Rubric key %s comments must be dicts' % key
            if 'comment' not in item.keys():
                v = 'Rubric key %s comment %s must have comment key'
                return False, v % (key, item)
            if 'value' not in item.keys():
                v = 'Rubric key %s comment %s must have value key'
                return False, v % (key, item)
            if not isinstance(item['value'], bool):
                v = 'Rubric key %s comment %s \'value\' key must be boolean'
                return False, v % (key, item)
        if not isinstance(data[key]['rubric_items'], list):
            return False, 'Rubric key %s rubric_items must be list' % key
        for item in data[key]['rubric_items']:
            if not isinstance(item, dict):
                v = 'Rubric key %s item %s must be a dict'
                return False, v % (key, item)
            expected = ['default', 'name', 'options', 'point-val']
            if sorted(item.keys()) != expected:
                v = 'Rubric key %s item %s must have %s keys'
                return False, v % (key, item, expected)
            if (not isinstance(item['default'], (str, unicode)) and
                    item['default'] is not None):
                v = 'Rubric key %s item %s default key must be a string'
                return False, v % (key, item)
            if not isinstance(item['name'], (str, unicode)):
                v = 'Rubric key %s item %s name key must be a string'
                return False, v % (key, item)
            if not isinstance(item['options'], list):
                v = 'Rubric key %s item %s options key must be a list'
                return False, v % (key, item)
            if not isinstance(item['point-val'], list):
                v = 'Rubric key %s item %s point-val key must be a list'
                return False, v % (key, item)
            if len(item['point-val']) != len(item['options']):
                v = 'Rubric key %s item %s options and point-val list must'
                v += ' be the same length'
                return False, v % (key, item)
            for v in item['point-val']:
                if not isinstance(v, (int, float)):
                    e = 'Rubric key %s item %s: all point-vals must be numbers'
                    return False, e % (key, item)
            for v in item['options']:
                if not isinstance(v, (str, unicode)):
                    e = 'Rubric key %s item %s: all options must be strings'
                    return False, e % (key, item)
    
    return True, 'No errors'

def bracket_check(path):
    if not os.path.exists(path):
        return False, 'Bracket %s does not exist' % path
    if not os.path.splitext(path)[1] == '.json':
        return False, 'Bracket %s needs to be a JSON file' % path
    try:
        with open(path) as f:
            data = json.load(f)
    except ValueError:
        return False, 'Bracket JSON is invalid (does not load)'
    for key in data.keys():
        if not isinstance(data[key], list):
            return False, 'Bracket key %s must be a list' % key
    good_len = len(data[data.keys()[0]])
    for key in data:
        if len(data[key]) != good_len:
            return False, 'All brackets must be the same length'
        for val in data[key]:
            if not isinstance(val, (int, float)):
                return False, 'Bracket %s has non-number value %s' % (key, val)

    return True, 'Valid bracket'
        
        
if __name__ == '__main__':
    import sys
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

    
