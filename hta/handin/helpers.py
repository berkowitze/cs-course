from datetime import datetime
import json
import os
from filelock import Timeout, FileLock
from contextlib import contextmanager

BASE_PATH = '/course/cs0111'
extension_path = os.path.join(BASE_PATH, 'hta/grading/extensions.txt')

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

def col_num_to_str(n):
    ''' convert a column number to the letter corresponding to that
    column in a spreadsheet
    example : col_num_to_str(4) outputs "D" '''
    string = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        string = chr(65 + remainder) + string
    return string

def col_str_to_num(col):
    ''' convert a spreadsheet column letter to the number, starting from 1,
    corresponding to that column
    example: col_str_to_num("C") outputs 3 '''
    import string
    num = 0
    for c in col:
        if c in string.ascii_letters:
            num = num * 26 + (ord(c.upper()) - ord('A')) + 1
    return num

def url_to_gid(url):
    ''' take a drive.google.com URL and extract the ID '''
    import urllib.parse
    if url == '' or url == None:
        return None
    try:
        o = urllib.parse.urlparse(url)
        return urllib.parse.parse_qs(o.query)['id'][0]
    except Exception as e:
        print('Check columns in assignments.json')
        raise Exception('Invalid link in url_to_gid')

def load_students():
    path = os.path.join(BASE_PATH, 'ta', 'groups', 'students.csv')
    students = []
    with locked_file(path, 'r') as f:
        lines = map(str.strip, f.read().strip().split('\n'))
        for line in lines:
            row      = line.split(',')
            if len(row) != 3:
                e = 'row %s in students.txt invalid, lines=%s'
                raise IndexError(e % (row, lines))
            username = row[0]
            email    = row[1]
            students.append((email, username))

    students.append(('csci0111@brown.edu', 'csci0111', 'HTA Account'))

    return students

def load_data(path):
    with locked_file(path) as f:
        data = json.load(f)

    for key in list(data['assignments'].keys()):
        data['assignments'][key.lower()] = data['assignments'].pop(key)

    return data

def email_to_login(email):
    students = load_students()
    for student in students:
        if student[0] == email:
            return student[1]

    raise ValueError('Student %s not found.' % email)

def login_to_email(login):
    students = load_students()
    for student in students:
        if student[1] == login:
            return student[0]

    raise ValueError('Student %s not found.' % login)

def confirmed_responses(filename='submission_log.txt'):
    with locked_file(filename, 'r') as f:
        lines = f.read().strip().split('\n')
        if not lines or lines == ['']:
            return []
        else:
            return list(map(int, lines))

def timestamp_to_datetime(timestamp):
    ''' given a timestamp from a Google Form submission sheet, turn it
    into a datetime object and return the datetime '''
    return datetime.strptime(timestamp, '%m/%d/%Y %H:%M:%S')

class Extension:
    def __init__(self, student, asgn, date):
        self.student = student
        self.asgn    = asgn
        self.date    = date

    def __repr__(self):
        return 'Extension(%s, %s)' % (self.student, self.asgn)

def load_extensions():
    with locked_file(extension_path) as f:
        lines = f.read().strip().split('\n')[1:]
    
    exts = []
    for line in lines:
        parts = list(map(str.strip, line.split(' ')))
        user = parts[0]
        asgn = parts[1]
        date = datetime.strptime(parts[2], '%m/%d/%Y-%I:%M%p')
        exts.append(Extension(user, asgn, date))

    return exts
