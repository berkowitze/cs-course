import os
import csv
import datetime

base = '/course/cs0111'
os.path.join(base, 'hta', 'grading', 'extensions.txt')

def increasing(lst):
    ''' returns true if the input list is increasing (non-decreasing)
    (all numbers larger or equal to than previous numbers) '''
    while lst[1:]:
        if lst[0] > lst[1]:
            return False
        lst.pop(0)

    return True

def login_gradepath_list():
    '''
    Returns 1) a list of student logins, 2) a list of the grade paths
    for each login (in same order)
    '''
    logins = map(lambda l: l[0], load_students())
    spath = os.path.join(base, 'hta', 'groups', 'students.txt')
    with open(spath) as f:
        logins = map(str.strip, f.read().strip().split('\n'))

    grade_paths = map(lambda f: os.path.join(base, f), logins)
    return logins, grade_paths

def load_students():
    ''' reads students from the hta/groups/students.csv file '''
    path = os.path.join(base, 'hta', 'groups', 'students.csv')
    with open(path) as f:
        reader = csv.reader(f)
        return list(reader)

def email_to_login(email):
    students = load_students()
    for student in students:
        if student[1] == email:
            return student[0]

    raise Exception('Student %s not found.' % email)

def login_to_email(login):
    students = load_students()
    for student in students:
        if student[0] == login:
            return student[1]

    raise Exception('Student %s not found.' % login)

def student_list():
    ''' gets a list of the student logins '''
    return map(lambda l: l[0], load_students())

def get_extensions_by_login(login):
    datetime.now

