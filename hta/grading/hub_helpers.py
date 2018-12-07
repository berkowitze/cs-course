import os
import json
import csv
import yagmail
from collections import defaultdict
from hta_helpers import load_students
from hta_classes import HTA_Assignment, locked_file

# WARNING:
# summary script currently assumes:
# drill 18 is not complete yet
# only gets drills 1-18
# canvas data in hta folder called canvas-grades-11-17.csv
# drill 14 was done through grading app

BASE_PATH = '/course/cs0111'
grade_dir = os.path.join(BASE_PATH, 'hta', 'grades')
sum_path = os.path.join(BASE_PATH, 'hta', 'summaries')
lab_base = os.path.join(BASE_PATH, 'ta', 'grading', 'data', 'labs')
data_path = os.path.join(BASE_PATH, 'ta', 'assignments.json')
drill_path = os.path.join(BASE_PATH, 'hta/canvas-grades-11-17.csv')
lab_excp_path = os.path.join(BASE_PATH, 'ta/grading/data/labs/exceptions.txt')
ta_group_path = os.path.join(BASE_PATH, 'hta/groups/tas.txt')
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
    sdir = os.path.join(grade_dir, login)
    if not os.path.exists(sdir):
        raise ValueError('Trying to get nonexistent grade_dict for %s' % login)
    
    for asgn in asgns:
        d = asgn.replace(' ', '').lower()
        individual_path = os.path.join(sdir, d)
        if not os.path.isdir(individual_path):
            full_grade[asgn] = {'Grade': 'No handin'}
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

        full_grade[asgn] = grade

    return full_grade

def get_drill_data():
    email_to_user = lambda u: u.replace('@brown.edu', '')
    descr_to_drill = lambda d: d.split(' ')[2]
    drill_data = defaultdict(lambda: (set(), set())) # (complete, incomplete)
    with open(drill_path) as f:
        lines = list(csv.reader(f))
    
    header = lines[0]
    for line in lines[1:]:
        login = email_to_user(line[3])
        for col in range(6, 23):
            drill = 'drill%s' % descr_to_drill(header[col])
            if drill == 'drill18':
                continue

            if line[col] == '':
                drill_data[login][1].add(drill)
            else:
                float(line[col])
                drill_data[login][0].add(drill)

    return drill_data
 

def get_lab_data():
    lab_data = defaultdict(lambda: set())
    all_labs = set()
    f_system = os.walk(lab_base)
    root, folds, _ = next(f_system)
    for lab_dirname in folds:
        lab_fold = os.path.join(root, lab_dirname)
        all_labs.add(lab_dirname)
        for f in os.listdir(lab_fold):
            if 'checkoff' not in f:
                continue

            fp = os.path.join(lab_fold, f)
            with open(fp) as fo:
                students = map(str.strip, fo.read().strip().split('\n'))
                for student in students:
                    lab_data[student].add(lab_dirname)
    
    with locked_file(lab_excp_path) as f:
        lines = map(str.strip, f.read().strip().split('\n'))

    for line in lines:
        line = line.split(' ')
        login = line[0]
        lab   = line[1]
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
        S = 'Aggregated grade summary for %s\n\n' % student
        student_data = data[student]
        for (k, v) in sorted(student_data.items()):
            if k == 'Drill 14':
                if v == {'Grade': 'Complete'}:
                    drill_data[student][0].add('drill14')
                else:
                    drill_data[student][1].add('drill14')

                continue
            S += '%s\n' % k
            mlen = max(map(len, v.keys())) + 1

            for (cat, grade) in sorted(v.items()):
                spaces = (mlen - len(cat))
                S += '%s%s%s: %s\n' % (' ' * 4, cat,  ' ' * spaces,  grade)

            S += '\n'
        
        slabs = lab_data[student]
        unattended = all_labs.difference(slabs)
        nlabs = max(map(len, lab_data.values()))
        lab_sum = '%s/%s labs attended\n' % (len(slabs), nlabs)
        if unattended:
            sorter = lambda s: int(s.replace('lab', ''))
            un_tup = str(tuple(sorted(list(unattended), key=sorter)))
            lab_sum += 'Labs not attended: %s\n' % un_tup

        S += lab_sum
        S += '\n'

        complete, incomplete = drill_data[student]
        tot = len(complete) + len(incomplete)
        drill_sum = '%s/%s drills completed\n' % (len(complete), tot)
        if incomplete:
            sorter = lambda s: int(s.replace('drill', ''))
            un_tup = str(tuple(sorted(list(incomplete), key=sorter)))
            drill_sum += 'Drills not completed: %s\n' % un_tup

        S += drill_sum

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
    categories = set()
    gradebook = defaultdict(lambda: {})
    for student in data.keys():
        s_data = data[student]
        for key in s_data.keys():
            cats = s_data[key].keys()
            for cat in cats:
                descr = '%s %s' % (key, cat)
                categories.add(descr)
                gradebook[descr][student] = s_data[key][cat]
    
    students = sorted(data.keys())
    col1 = sorted(data.keys())
    sorted_cats = sorted(categories)
    final_book_unt = [sorted_cats]
    book = [['Student']]
    book[0].extend(sorted_cats)
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
        S += '%s\n' % line_str

    with locked_file(path, 'w') as f:
        f.write(S)

def send_summaries(resummarize=None):
    if resummarize is None:
        print('Regenerate summaries? [y/n]')
        resp = raw_input('> ').lower()
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
    login_to_email = dict((line[0], line[1]) for line in full_students)
    students = map(lambda line: line[0], full_students)
    with locked_file(ta_group_path) as f:
        tas = map(str.strip, f.read().strip().split('\n'))

    for sum_file in os.listdir(sum_path):
        path = os.path.join(sum_path, sum_file)
        login = os.path.splitext(sum_file)[0]
        if login not in students or login in tas:
            print('skipping login %s' % login)
            continue

        with open(path) as f:
            contents = '<pre>%s</pre>' % f.read()
        
        em = login_to_email[login]
        print('Sending to %s' % em)
        yag.send(to=em, subject='Aggregated grade report', contents=[contents])


