import os
import csv
import json

hw1_scores = [
    ['abdirahim_mohamed',9],
    ['abdullah_alshammari',0],
    ['ayenna_cagaanan',10],
    ['boyu_chen',9],
    ['chengxuan_he',8],
    ['david_fu',9],
    ['dingyue_zhang',10],
    ['haoyuan_ma',8],
    ['jee_won_park',9],
    ['jesus_contreras',10],
    ['keying_huang',10],
    ['chemtai_langat',10],
    ['mingyi_wang',9],
    ['ridha_alkhabaz',9],
    ['sara_ahmed_y_alrabiah',10],
    ['siyu_chen2',10],
    ['wanning_su',9],
    ['will_jaekle',10],
    ['william_ward1',9],
    ['xiaojun_lin',8],
    ['xinyan_he1',10]]

base = '/course/cs0050'
grades = {}
def add_score(login, score, category):
    if login not in grades:
        grades[login] = {}

    grades[login][category] = score

def extract_grades(file_path, categories):
    with open(file_path) as f:
        lines = map(str.strip, f.read().strip().split('\n'))
    
    cgrade = {}
    for line in lines:
        for category in categories:
            if line.startswith(category) and ' : ' in line:
                if category in cgrade:
                    raise Exception('uh oh %s %s' % (category, lines))
                cgrade[category] = line.split(' : ')[-1]
    return cgrade

# homework 1
for login, score in hw1_scores:
    add_score(login, score, 'homework1')

students_path = os.path.join(base, 'hta/handin/students')
students = os.walk(students_path).next()[1]
homeworks = ['homework2', 'homework3']
categories = [['Functionality', 'Explanations', 'Testing', 'Design/Style'],
              ['Functionality', 'Design & Style', 'Testing']]

for student in students:
    student_path = os.path.join(students_path, student)
    for cats, hw in zip(categories, homeworks):
        hw_path = os.path.join(student_path, hw)
        if not os.path.exists(hw_path):
            print 'no handin for %s %s' % (student, hw)
            has_handin = False
        else:
            has_handin = True
        
        if has_handin:
            files = []
            gen = os.walk(hw_path)
            while 'grade.txt' not in files:
                try:
                    dirname, folders, files = gen.next()
                except StopIteration:
                    print 'no grade for %s %s' % (student, hw)
                    if raw_input('Override? [y]\n> ').lower() == 'y':
                        has_grade = False
                        break
                    else:
                        raise
            if 'grade.txt' in files:
                has_grade = True
                grade_path = os.path.join(dirname, 'grade.txt')
                cgrades = extract_grades(grade_path, cats)
                for key in cgrades:
                    add_score(student, cgrades[key], '%s %s' % (hw, key))
            else:
                for key in cats:
                    add_score(student, 'NO GRADE', '%s %s' % (hw, key))
        else:
            for key in cats:
                add_score(student, 'No handin', '%s %s' % (hw, key))

for student in students:
    if 'homework1' not in grades[student]:
        grades[student]['homework1'] = 'No handin'
    
# homeworks 4 on
data_path = os.path.join(base, 'ta', 'assignments.json')
with open(data_path) as f:
    data = json.load(f)

asgns = data['assignments']
for asgn in asgns:
    # TODO get rid of this for A
    if asgn == 'Homework 2' or asgn == 'Homework 1' or asgn == 'Homework 3':
        continue

    if not asgns[asgn]['grading_completed']:
        continue

    mini_name = asgn.replace(' ', '').lower()
    grade_path = os.path.join(base, 'hta', 'grades')
    walker = os.walk(grade_path)
    _, students, _ = walker.next()
    for student in students:
        full_path = os.path.join(grade_path, student, mini_name, 'grade.json')
        if not os.path.exists(full_path):
            continue

        with open(full_path) as f:
            cgrade = json.load(f)

        for key in cgrade:
            grades[student]['%s %s' % (asgn, key)] = cgrade[key]

columns = []
for key in grades['william_ward1']:
    columns.append(key)

columns.sort()
rows = []
for student in grades:
    row = [student]
    for col in columns:
        if col not in grades[student]:
            print 'warning with %s, potentially invalid grade.txt' % student, col
            row.append('No handin')
        else:
            row.append(grades[student][col])
    rows.append(row)

columns.insert(0, 'Student')
assert len(columns) == len(rows[0])

coljoin = lambda r: '%s\n' % ('\t'.join(r))
with open('grade-summary.tsv', 'w') as f:
    f.truncate()
with open('grade-summary.tsv', 'a') as f:
    f.write(coljoin(columns))
    for row in rows:
        f.write(coljoin(map(str,row)))


    # print asgn, asgns[asgn]['grading_completed']


