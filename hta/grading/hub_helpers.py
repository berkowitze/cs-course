import csv
import json
import os
from os.path import join as pjoin
from collections import defaultdict

import yagmail

from hta_classes import locked_file
from hta_helpers import load_students

# WARNING:
# summary script currently assumes:
# drill 18 is not complete yet
# only gets drills 1-18
# canvas data in hta folder called canvas-grades-11-17.csv
# drill 14 was done through grading app

BASE_PATH = '/course/cs0111'
grade_dir = pjoin(BASE_PATH, 'hta', 'grades')
sum_path = pjoin(BASE_PATH, 'hta', 'summaries')
lab_base = pjoin(BASE_PATH, 'ta', 'grading', 'data', 'labs')
data_path = pjoin(BASE_PATH, 'ta', 'assignments.json')
drill_path = pjoin(BASE_PATH, 'hta/canvas-grades-11-17.csv')
lab_excp_path = pjoin(BASE_PATH, 'ta/grading/data/labs/exceptions.txt')
ta_group_path = pjoin(BASE_PATH, 'hta/groups/tas.txt')
with locked_file(data_path) as f:
    asgn_data = json.load(f)

asgns = []
for asgn in asgn_data['assignments']:
    if asgn_data['assignments'][asgn]['grading_completed']:
        asgns.append(asgn)


def get_full_grade_dict(students=None):
    if students is None:
        students = map(lambda s: s[0], load_students())

    data = {}
    for student in students:
        data[student] = get_student_grade_dict(student)

    return data


def get_student_grade_dict(login):
    full_grade = {}
    sdir = pjoin(grade_dir, login)
    if not os.path.exists(sdir):
        raise ValueError(f'Trying to get nonexistent grade_dict for {login}')

    for asgn in asgns:
        d = asgn.replace(' ', '').lower()
        individual_path = pjoin(sdir, d)
        if not os.path.isdir(individual_path):
            full_grade[asgn] = {'Grade': 'No handin'}
            continue

        fs = os.listdir(individual_path)
        if 'grade-override.json' in fs:
            p = pjoin(individual_path, 'grade-override.json')
        else:
            p = pjoin(individual_path, 'grade.json')

        if not os.path.exists(p):
            print(f'Nonexistent grade in {individual_path}, continuing...')

        with locked_file(p) as f:
            grade = json.load(f)

        full_grade[asgn] = grade

    return full_grade


def get_drill_data():
    drill_data = defaultdict(lambda: (set(), set()))  # (complete, incomplete)
    with open(drill_path) as f:
        lines = list(csv.reader(f))

    header = lines[0]
    for line in lines[1:]:
        login = line[3].replace('@brown.edu', '')
        for col in range(6, 23):
            drill = f"drill{header[col].split(' ')[2]}"
            if drill == 'drill18':
                continue

            if line[col] == '':
                drill_data[login][1].add(drill)
            else:
                float(line[col])
                drill_data[login][0].add(drill)

    return drill_data


def get_lab_data():
    lab_path = pjoin(lab_base, 'attendance.json')
    with locked_file(lab_path) as f:
        attendance_data = json.load(f)

    all_labs = set(attendance_data.keys())

    lab_data = defaultdict(set)
    for lab in attendance_data:
        for student in attendance_data[lab]:
            lab_data[student].add(lab)

    with locked_file(lab_excp_path) as f:
        lines = f.read().strip().split('\n')

    for line in lines:
        login, lab = line.split(' ')
        lab_data[login].add(lab)

    return lab_data, all_labs


def generate_grade_summaries(write=False, to_return=True):
    print('Gathering grading app grade info...')
    data = get_full_grade_dict()
    print('Gathering lab info...')
    lab_data, all_labs = get_lab_data()
    print('Gathering drill info...')
    drill_data = get_drill_data()
    print('Generating summaries...')
    summs = {}
    for student in data:
        S = f'Aggregated grade summary for {student}\n\n'
        student_data = data[student]
        for (k, v) in sorted(student_data.items()):
            if k == 'Drill 14':
                if v == {'Grade': 'Complete'}:
                    drill_data[student][0].add('drill14')
                else:
                    drill_data[student][1].add('drill14')

                continue
            S += f'{k}\n'
            mlen = max(map(len, v.keys())) + 1

            for (cat, grade) in sorted(v.items()):
                spaces = (mlen - len(cat))
                S += f"{' ' * 4}{cat}{' ' * spaces}: {grade}\n"

            S += '\n'

        slabs = lab_data[student]
        unattended = all_labs.difference(slabs)
        nlabs = max(map(len, lab_data.values()))
        lab_sum = f'{len(slabs)}/{nlabs} labs attended\n'
        if unattended:
            unattended_list = sorted(list(unattended),
                                     key=lambda s: int(s.replace('lab', '')))
            unattended_str = ', '.join(unattended_list)
            lab_sum += f'Labs not attended: {unattended_str}\n'

        S += lab_sum
        S += '\n'

        complete, incomplete = drill_data[student]
        tot = len(complete) + len(incomplete)
        drill_sum = f'{len(complete)}/{tot} drills completed\n'
        if incomplete:
            sorted_drills = sorted(list(incomplete),
                                   key=lambda s: int(s.replace('drill', '')))
            incomplete_str = ', '.join(sorted_drills)
            drill_sum += f'Drills not completed: {incomplete_str}\n'

        S += drill_sum

        summs[student] = S
        if write:
            fp = pjoin(sum_path, f'{student}.txt')
            with locked_file(fp, 'w') as f:
                f.write(S)

    if to_return:
        return summs


def generate_gradebook(path=None):
    if path is None:
        path = pjoin(BASE_PATH, 'hta', 'gradebook.tsv')

    if os.path.splitext(path)[1] != '.tsv':
        print('Warning: Output format is tsv, but writing to non-tsv file')

    data = get_full_grade_dict()
    categories = set()
    gradebook = defaultdict(lambda: {})
    for student in data.keys():
        s_data = data[student]
        for key in s_data.keys():
            cats = s_data[key].keys()
            for cat in cats:
                descr = f'{key} {cat}'
                categories.add(descr)
                gradebook[descr][student] = s_data[key][cat]

    students = sorted(data.keys())
    sorted_cats = sorted(categories)
    book = [['Student', *sorted_cats]]

    for student in students:
        summary = [student]
        for descr in sorted_cats:
            if student in gradebook[descr]:
                grade = gradebook[descr][student]
            else:
                grade = '(No data)'

            summary.append(grade)

        book.append(summary)

    S = ''
    for line in book:
        line_str = '\t'.join(line)
        S += f'{line_str}\n'

    with locked_file(path, 'w') as f:
        f.write(S)


def send_summaries(resummarize=None, override_email=None):
    if resummarize is None:
        print('Regenerate summaries? [y/n]')
        resp = input('> ').lower()
        if resp == 'y':
            resummarize = True
        elif resp == 'n':
            resummarize = False
        else:
            send_summaries()

    if resummarize:
        generate_grade_summaries(write=True)

    yag = yagmail.SMTP('csci0111@brown.edu')
    full_students = load_students()
    login_to_email = {line[0]: line[1] for line in full_students}
    students = list(map(lambda line: line[0], full_students))
    with locked_file(ta_group_path) as f:
        tas = list(map(str.strip, f.read().strip().split('\n')))

    for sum_file in os.listdir(sum_path):
        path = pjoin(sum_path, sum_file)
        login = os.path.splitext(sum_file)[0]
        print(f'{login!r}')
        if login not in students or login in tas:
            print(f'skipping login {login}')
            continue

        with open(path) as f:
            contents = f'<pre>{f.read()}</pre>'

        em = login_to_email[login]
        if override_email is None:
            send_to = em
        else:
            send_to = override_email

        print(f'Sending {login} summary to {send_to}')
        yag.send(to=send_to,
                 subject='Aggregated grade report',
                 contents=[contents])
