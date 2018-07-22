import os
import sys
from hta_classes import HTA_Assignment
print 'currently only works for cs50 "Homework 4"' 
run_mode = raw_input('1. View grades\n2. Generate grades\n> ')
if run_mode == '1':
    soft = True
    desc = 'viewing'
elif run_mode == '2':
    desc = 'generating'
    soft = False
else:
    print 'invalid input (put 1 or 2)'
    sys.exit(0)

base = '/course/cs0050'
grade_base = os.path.join(base, 'ta/grading/data/grades')
anon_base  = os.path.join(base, 'hta/grading/anonymization')
asgn_name = raw_input("Which assignment are you %s grades for?\n> " % desc)
asgn = HTA_Assignment(asgn_name)
if not soft and asgn.reports_generated:
    print 'Reports for this assignment were already generated.'
    if raw_input('Continue anyway? [y/n]\n> ').lower() != 'y':
        print 'Quitting...'
        sys.exit(0)

asgn.load_questions()
handin_dict = {}
for q in asgn.logs:# TODO rename logs to questions, make sure it's ordered
    for handin in q.handins:
        student = asgn.id_to_login(handin.id)
        if not handin.complete:
            warning = 'handin for student(%s, %s) not complete. quitting.'
            sys.exit(0)
        if student in handin_dict:
            handin_dict[student]['problems'].append(handin)
        else:
            handin_dict[student] = {}
            handin_dict[student]['id'] = handin.id
            handin_dict[student]['problems'] = [handin]

# print handin_dict
results = []
for key in handin_dict:
    if soft:
        res = asgn.generate_report(handin_dict[key], key, soft=soft)
        results.append(res)
    else:
        asgn.generate_report(handin_dict[key], key, soft=soft)

if soft:
    summary = {}
    for _, grades, _ in results:
        for key in grades:
            if key not in summary:
                summary[key] = {}
            
            if grades[key] not in summary[key].keys():
                summary[key][grades[key]] = 0

            summary[key][grades[key]] += 1

    from pprint import pprint

    pprint(results)
    print '\nSUMMARY:'
    for key in summary:
        print '%s: %s' % (key, summary[key])
