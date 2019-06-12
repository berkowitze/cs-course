import csv
import json
import os
import shutil
from os.path import join as pjoin
from collections import defaultdict

import yagmail

from typing import Optional, List, Dict, Tuple, Set
from helpers import locked_file, CONFIG
from custom_types import Grade, AssignmentData
from hta_helpers import load_students

# WARNING:
# summary script currently assumes:
# drill 18 is not complete yet
# only gets drills 1-18
# canvas data in hta folder called canvas-grades-11-17.csv
# drill 14 was done through grading app

BASE_PATH = CONFIG.base_path
grade_dir = pjoin(BASE_PATH, 'hta', 'grades')
sum_path = pjoin(BASE_PATH, 'hta', 'summaries')
lab_base = pjoin(BASE_PATH, 'ta', 'grading', 'data', 'labs')
data_path = pjoin(BASE_PATH, 'ta', 'assignments.json')
drill_path = pjoin(BASE_PATH, 'hta/canvas-grades-11-17.csv')
lab_excp_path = pjoin(BASE_PATH, 'ta/grading/data/labs/exceptions.txt')
ta_group_path = pjoin(BASE_PATH, 'hta/groups/tas.txt')
with locked_file(data_path) as f:
    asgn_data: Dict[str, AssignmentData] = json.load(f)['assignments']

completed_asgn_names: List[str] = []
for asgn in asgn_data:
    if asgn_data[asgn]['grading_completed']:
        completed_asgn_names.append(asgn)


def get_full_grade_dict(students: Optional[List[str]] = None
                        ) -> Dict[str, Dict[str, Grade]]:
    """

    get a dictionary of student -> dictionary of grades

    :param students: students for whom to collect grade info. if None, data
                     for all students will be collected. defaults to None
    :type students: Optional[List[str]], optional
    :returns: dictionary of login -> dictionary of
              (assignment mini_name -> student's grade for that assignment)
              dictionary values
    :rtype: Dict[str, Dict[str, Grade]]

    """
    if students is None:
        logins = list(map(lambda s: s[0], load_students()))
    else:
        logins = students

    data = {}
    for login in logins:
        data[login] = get_student_grade_dict(login)

    return data


def get_student_grade_dict(login: str) -> Dict[str, Grade]:
    """

    given a login, collect grade information for that student

    :param login: CS login of student for whom to collect grade info
    :type login: str
    :returns: a dictionary of assignment mini_name -> grade for that assignment
    :rtype: Dict[str, Grade]
    :raises ValueError: no grades for this student

    """
    full_grade: Dict[str, Grade] = {}
    sdir = pjoin(grade_dir, login)
    if not os.path.exists(sdir):
        raise ValueError(f'Trying to get nonexistent grade_dict for {login}')

    for asgn in completed_asgn_names:
        d = asgn.replace(' ', '').lower()
        individual_path = pjoin(sdir, d)
        if not os.path.isdir(individual_path):
            full_grade[asgn] = {'Grade': 'No handin'}
            continue

        grade_path = pjoin(individual_path, 'grade.json')

        if not os.path.exists(grade_path):
            print(f'Nonexistent grade in {individual_path}, continuing...')
            continue

        with locked_file(grade_path) as f:
            grade: Grade = json.load(f)

        full_grade[asgn] = grade

    return full_grade


def get_drill_data() -> Dict[str, Tuple[Set[str], Set[str]]]:
    """

    collect drill information for this course

    :returns: dictionary of login -> (completed drills, uncompleted drills)
              2-tuples, the tuple is comprised of sets
    :rtype: Dict[str, Tuple[Set[str], Set[str]]]

    """
    drill_data: Dict[str, Tuple[Set[str], Set[str]]]
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


def get_lab_data() -> Tuple[Dict[str, Set[str]], Set[str]]:
    """

    collect lab information for this course

    :returns: dictionary of login -> attended labs set and a set of
              all the labs for the course
    :rtype: Tuple[Dict[str, Set[str]], Set[str]]

    """
    lab_data: Dict[str, Set[str]]
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


def generate_grade_summaries(write: bool = False) -> Dict[str, str]:
    """

    generate grade summaries for the course

    :param write: whether or not to write the summaries into files in
                  /hta/summaries, defaults to False
    :type write: bool, optional
    :returns: dictionary of login -> grade summary strings
    :rtype: Dict[str, str]
    """
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
            if isinstance(v, (int, str, float)):
                S += f'{" " * 4}Grade: {v}'
            else:
                cats = v.keys()
                for cat in v:
                    grade = v[cat]
                    spaces = (mlen - len(cat))
                    S += f"{' ' * 4}{cat}{' ' * spaces}: {grade}\n"

            S += '\n'

        slabs = lab_data[student]
        unattended = all_labs.difference(slabs)
        nlabs = len(all_labs)
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

    return summs


def generate_gradebook(path: Optional[str] = None) -> None:
    """

    generates gradebook for the course

    :param path: path to put gradebook in; puts in /hta/gradebook.tsv if None.
                defaults to None
    :type path: Optional[str], optional

    """
    if path is None:
        path = pjoin(BASE_PATH, 'hta', 'gradebook.tsv')

    if os.path.splitext(path)[1] != '.tsv':
        print('Warning: Output format is tsv, but writing to non-tsv file')

    data = get_full_grade_dict()
    categories = set()
    gradebook: Dict[str, dict] = defaultdict(lambda: {})
    for student in data.keys():
        s_data = data[student]
        for asgn in s_data.keys():
            grade = s_data[asgn]
            if isinstance(grade, (int, str, float)):
                gradebook[asgn][student] = grade
            else:
                cats = grade.keys()
                for cat in cats:
                    descr = f'{asgn} {cat}'
                    categories.add(descr)
                    gradebook[descr][student] = grade[cat]

    students = sorted(data.keys())
    sorted_cats = sorted(categories)
    book = [['Student', *sorted_cats]]

    for student in students:
        summary = [student]
        for descr in sorted_cats:
            if student in gradebook[descr]:
                book_grade = gradebook[descr][student]
            else:
                book_grade = '(No data)'

            summary.append(book_grade)

        book.append(summary)

    S = ''
    for line in book:
        line_str = '\t'.join(line)
        S += f'{line_str}\n'

    with locked_file(path, 'w') as f:
        f.write(S)


def send_summaries(resummarize: Optional[bool] = None) -> None:
    """

    send course grade summaries

    :param resummarize: whether or not to regenerate grade summaries, or None
                        to have program prompt whether or not to regenerate
    :type resummarize: Optional[bool], optional

    """
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

    yag = yagmail.SMTP(CONFIG.email_from)
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

        with locked_file(path) as f:
            contents = f'<pre>{f.read()}</pre>'

        em = login_to_email[login]
        to = CONFIG.test_mode_emails_to if CONFIG.test_mode else em

        print(f'Sending {login} summary to {to}')
        yag.send(to=to,
                 subject='Aggregated grade report',
                 contents=[contents])


def delete_subdirs(path: str) -> None:
    assert os.path.exists(path)
    for folder in os.listdir(path):
        if folder.startswith('.'):
            continue

        f_p = pjoin(path, folder)
        shutil.rmtree(f_p, ignore_errors=True)


def delete_subfiles(path: str) -> None:
    assert os.path.exists(path)
    for f in os.listdir(path):
        if f.startswith('.'):
            continue

        full_path = pjoin(path, f)
        if os.path.isfile(full_path):
            os.remove(full_path)
