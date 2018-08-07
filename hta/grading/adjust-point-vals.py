import json
import os
from hta_classes import HTA_Assignment, Handin
print('This needs to be built in to the assignment hub')
def get_choice(prompt, choices):
    ''' get a numeric choice, valid choices are integers
    in the choices input '''
    try:
        choice = int(raw_input(prompt))
        if choice not in choices:
            print 'Invalid choice...'
            return get_choice(prompt, choices)
        else:
            return choice

    except ValueError:
        print 'Input must be an integer...'
        return get_choice(prompt, choices)

base = '/course/cs0111'
grade_base = os.path.join(base, 'ta/grading/data/grades')
#asgn_name = raw_input("Which assignment are you generating grades for?\n> ")
asgn_name = 'Homework 4' # TODO fix this
asgn = HTA_Assignment(asgn_name)
asgn.load_questions()

print 'Which question are you updating the JSON for?'
for i, q in enumerate(asgn.logs):
    print '%s. %s' % (i + 1, q)

choice = get_choice('> ', range(1, len(asgn.logs) + 1))
question = asgn.logs[choice - 1]

print 'Which category are you adjusting?'
rubric = question.copy_rubric()
for i, c in enumerate(rubric.keys()):
    print '%s. %s' % (i + 1, c)

choice = get_choice('> ', range(1, len(rubric.keys()) + 1))
category = rubric.keys()[choice - 1]

sub_rubric = rubric[category]
print 'Which rubric item are you changing?'
for i, item in enumerate(sub_rubric):
    print '%s. %s' % (i + 1, item['name'])

choice = get_choice('> ', range(1, len(sub_rubric) + 1))
item = sub_rubric[choice - 1]

print 'Current list is %s' % item['point-val']
print 'Enter list of new point values with following format: #, #, #, ...'
while True:
    new_list = raw_input('> ')
    try:
        x = map(float, new_list.split(', '))
        break
    except:
        print 'Invalid input format'

print "Updating..."
rubric[category][choice - 1]['point-val'] = x
question.rewrite_rubric(rubric, 'YES')

for handin in question.handins:
    if handin.extracted:
        grade = handin.get_rubric()
        c_cat = grade[category]
        found = False
        for c_ndx, c_item in enumerate(c_cat):
            if c_item['name'] == item['name']:
                found = True
                break

        assert found
        assert c_item['name'] == item['name']
        grade[category][c_ndx]['point-val'] = x
        handin.write_grade(grade)
    else:
        if os.path.exists(handin.grade_path):
            raise Exception('this might be ok but check!')

print 'Update complete.'
