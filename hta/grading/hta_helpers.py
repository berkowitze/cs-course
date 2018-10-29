import os
import csv
import datetime
import numpy as np

base = '/course/cs0111'

def increasing(lst):
    ''' returns true if the input list is increasing (non-decreasing)
    (all numbers larger or equal to than previous numbers) '''
    while lst[1:]:
        if lst[0] > lst[1]:
            return False
        lst.pop(0)

    return True

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

def latest_submission_path(base, login, assignment):
    sub_path = os.path.join(base, login, assignment)
    if not os.path.exists(sub_path):
        return None

    submissions = filter(lambda f: 'submission' in f,
                         os.listdir(sub_path))
    sub_numbs = map(lambda f: int(f.split('-')[0]), submissions)
    latest = submissions[np.argmax(sub_numbs)]
    return os.path.join(sub_path, latest)

