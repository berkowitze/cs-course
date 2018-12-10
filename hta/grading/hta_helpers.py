import os
import csv
import datetime
from helpers import locked_file
from typing import List, Optional, Union
from numpy import argmax

base = '/course/cs0111'

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
    return [l[0] for l in load_students()]

def latest_submission_path(base, login, assignment):
    sub_path = os.path.join(base, login, assignment)
    if not os.path.exists(sub_path):
        return None

    submissions = [f for f in os.listdir(sub_path) if 'submission' in f]
    sub_numbs = [int(f.split('-')[0]) for f in submissions]
    latest = submissions[argmax(sub_numbs)]
    return os.path.join(sub_path, latest)

def line_read(filename: str, delim: Optional[str] = None) -> list:
    ''' read lines from a file. returns list of strings with whitespace
    right-stripped with delim=None, or list of lists of strings with
    whitespace stripped with delim=str
    '''
    with locked_file(filename) as f:
        raw: str = f.read()

    lines = [line.rstrip() for line in raw.strip().split('\n')]
    if delim is not None:
        return [line.split(delim) for line in lines]
    else:
        return lines



