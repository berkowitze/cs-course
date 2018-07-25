import json
import os
from hta_classes import get_full_asgn_list, asgn_data_path, BASE_PATH
import sys
import tabulate

def get_opt(prompt, options, first=True):
    ''' given a prompt (to display to the user), and a list of options,
    this will collect a valid index (0-indexed) from the options.
    if first=True, the options will be displayed to the user. '''
    if first:
        for i, opt in enumerate(options):
            print '%s. %s' % (i + 1, opt)

    choice = raw_input(prompt)
    try:
        numb_choice = int(choice) - 1
        if numb_choice in range(len(options)):
            return numb_choice
        else:
            print 'Invalid input...'
            return get_opt(prompt, options, first=False)
    except ValueError:
        print 'Enter a number...'
        return get_opt(prompt, options, first=False)

opt = get_opt('> ', ['Generate gradebook', 'Work with assignment'])
asgns = get_full_asgn_list()
if opt == 0:
    path = os.path.join(BASE_PATH, 'hta', 'gradebook.tsv')
    print 'gradebook will be saved as "%s".' % path
    print 'Press enter to continue, or enter custom path (absolute)'
    res = raw_input('> ')
    if res != '':
        dirname, fname = os.path.split(res)
        assert os.path.exists(dirname), \
            'directory %s does not exist' % dirname
        print fname
        if not fname.endswith('.tsv'):
            print 'Warning: gradebook should end with .tsv.'
            print 'Enter to continue or ctrl-c to cancel.'
            raw_input()

        path = res

    print 'Collecting grades for:'
    # i hope there's a better way to do this...
    students = os.listdir(os.path.join(BASE_PATH, 'hta', 'grades'))
    header = ['Student']
    for asgn in asgns:
        if asgn.grading_completed:
            cats = sorted(asgn.get_empty_grade().keys())
            string = '('
            for cat in cats:
                header.append('%s %s' % (asgn.full_name, cat))
                string += cat
                string += ', '


            string = string[:-2]
            string += ')'
            print '\t%s %s' % (asgn.full_name, string)


    rows = []
    for student in students:
        row = range(len(header))
        row[0] = student
        spath = os.path.join(BASE_PATH, 'hta', 'grades', student)
        for asgn in asgns:
            if not asgn.grading_completed:
                continue
            
            egrade = asgn.get_empty_grade()
            override_path = os.path.join(spath, asgn.mini_name,
                                         'grade-override.json')
            if os.path.exists(override_path):
                with open(override_path) as f:
                    student_grade = json.load(f)
            else:
                grade_path = os.path.join(spath, asgn.mini_name, 'grade.json')
                try:
                    with open(grade_path) as f:
                        student_grade = json.load(f)
                except IOError:
                    student_grade = {}
                    for key in egrade.keys():
                        student_grade[key] = "No handin"

            for key in egrade:
                colname = '%s %s' % (asgn.full_name, key)
                ndx = header.index(colname)
                try:
                    row[ndx] = student_grade[key]
                except:
                    print student_grade, key, asgn, student
                    raise

        rows.append(row)

    with open(path, 'a') as f:
        f.write('\t'.join(map(str, header)))
        for row in rows:
            f.write('\t'.join(map(str, row)))

    print 'Gradebook outputted to %s' % path
    sys.exit(0)

else:
    rows = []
    header = ["#", "Asgn", "Due", "Grading Started",
              "Grading Done", "Regrading Done"]
    maxlen = len(max(header)) + 3
    rows = []
    for i, Asgn in enumerate(asgns):
        row = [i + 1, Asgn.full_name, Asgn.due, Asgn.started,
               Asgn.grading_completed, False]
        row = map(str, row)
        rm = len(max(row)) + 3
        maxlen = rm if rm > maxlen else maxlen
        rows.append(row)

    print tabulate.tabulate(rows, header)
    print ''
    print 'Which assignment # would you like to work on?'
    ndx = get_opt('> ', range(1, len(asgns) + 1), False)
    asgn = asgns[ndx]
    if not asgn.started:
        print '%s grading unstarted. Start it?' % asgn.full_name
        if get_opt('> ', ['Yes', 'No']) == 0:
            if not asgn.due:
                s = 'Students can still hand in for this assignment.'
                print s + ' Continue anyway?'
                choice = get_opt('> ', ['Yes', 'No'])
                if choice != 0:
                    print 'Exiting...'
                    sys.exit(0)

            asgn.init_grading()
            print 'Grading started...'
        else:
            print 'Cancelling...'
    else:
        new_header = ["Problem", "# Handins", "# Graded", "# Flagged"]
        rows = []
        for question in asgn.questions:
            print question


    # raise NotImplementedError