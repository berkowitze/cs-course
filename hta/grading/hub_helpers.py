import os
import json
from collections import defaultdict
from hta_helpers import load_students
from hta_classes import HTA_Assignment, locked_file

BASE_PATH = '/course/cs0111'
grade_dir = os.path.join(BASE_PATH, 'hta', 'grades')
sum_path = os.path.join(BASE_PATH, 'hta', 'summaries')

def get_full_grade_dict(students=None):
    if students is None:
        students = map(lambda s: s[0], load_students())

    data = {}
    for student in students:
        data[student] = get_student_grade_dict(student)

    return data

def get_student_grade_dict(login):
    full_grade = {}
    sdir = os.path.join(grade_dir, login)
    if not os.path.exists(sdir):
        raise ValueError('Trying to get nonexistent grade_dict for %s' % login)

    for d in os.listdir(sdir):
        individual_path = os.path.join(sdir, d)
        if not os.path.isdir(individual_path):
            continue

        fs = os.listdir(individual_path)
        if 'grade-override.json' in fs:
            p = os.path.join(individual_path, 'grade-override.json')
        else:
            p = os.path.join(individual_path, 'grade.json')

        if not os.path.exists(p):
            print('Nonexistent grade in %s, continuing...' % individual_path)
        
        with locked_file(p) as f:
            grade = json.load(f)

        full_grade[d] = grade

    return full_grade

def generate_grade_summaries(write=False, to_return=True):
    data = get_full_grade_dict()
    summs = {}
    for student in data:
        S = 'Aggregated grade summary for %s\n\n' % student
        student_data = data[student]
        for (k, v) in sorted(student_data.items()):
            S += '%s\n' % k
            for (cat, grade) in sorted(v.items()):
                S += '%s%s: %s\n' % (' ' * 4, cat, grade)

            S += '\n'

        summs[student] = S
        if write:
            fp = os.path.join(sum_path, '%s.txt' % student)
            with locked_file(fp, 'w') as f:
                f.write(S)

    if to_return:
        return summs

def generate_gradebook(path=None):
    if path is None:
        path = os.path.join(BASE_PATH, 'hta', 'gradebook.tsv')

    if os.path.splitext(path)[1] != '.tsv':
        print('Warning: Output format is tsv, but writing to non-tsv file')

    data = get_full_grade_dict()
    for student in data:
        s_data = data[student]


