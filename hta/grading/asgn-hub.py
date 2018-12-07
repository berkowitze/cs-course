import cProfile, pstats, StringIO
# pr = cProfile.Profile()
# pr.enable()
import json
import os
from hta_classes import get_full_asgn_list, asgn_data_path, \
                        BASE_PATH, student_list, User, login_to_email
import sys
import tabulate
import yagmail
import subprocess

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

def send_asgn_emails(asgn, handins):
    ''' this needs to be cleaned up for project groups
    (send to groups that handed in only, including partners) '''
    # this is convoluted logic but it's so that I can see
    # what kind of issues come up; will make it better
    # during semester (maybe)
    yag = yagmail.SMTP('csci0111@brown.edu')
    for student in handins.keys():
        if student == 'csci0111':
            continue

        asgn.send_email(student, login_to_email(student), yag)

    asgn.set_emails_sent()
    return
    tosend = asgn.login_handin_list[:] # make copy of login list
    for student in handins.keys():
        hpath = os.path.join(BASE_PATH, 'hta/handin/students',
                             student, asgn.mini_name)
        if not os.path.exists(hpath): # if no submission for hw...
            print 'no submission for %s, not sending email' % student
            continue

        try:
            tosend.remove(student)
            em = login_to_email(student)
            asgn.send_email(student, em, yag)
        except ValueError:
            print '%s has handin but no grade. Not sending email.' % student
            continue

    if tosend:
        print 'Graded students that will not receive email:'
        print '\t%s' % tosend
        print 'This is likely because they are not in student list.'

    asgn.set_emails_sent()

def send_grade_report(asgn, login):
    yag = yagmail.SMTP('csci0111@brown.edu')
    asgn.send_email(login, login_to_email(login), yag)

def get_student_labcount(student):
    count = 0
    p = '/course/cs0111/ta/grading/data/labs'
    f_system = os.walk(p)
    root, folds, _ = next(f_system)
    for lab_fold in folds:
        lab_fold = os.path.join(root, lab_fold)
        labc = False
        for f in os.listdir(lab_fold):
            if 'checkoff' not in f:
                continue
            fp = os.path.join(lab_fold, f)
            with open(fp) as fo:
                students = map(str.strip, fo.read().strip().split('\n'))
                if student in students:
                    labc = True
                    break

        if labc:
            count += 1

    return count

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
    # there is! todo
    students = os.listdir(os.path.join(BASE_PATH, 'hta', 'grades'))
    tas = subprocess.check_output(['/course/cs0111/htabin/better-members', 'cs-0111ta']).strip()
    tas = tas.split(' ')
    students = [student for student in students if student not in tas]
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

    header.append('Labs attended')
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
        
        row.append(get_student_labcount(student))
        rows.append(row)

    with open(path, 'w') as f:
        f.truncate()

    with open(path, 'a') as f:
        f.write('\t'.join(map(str, header)) + '\n')
        for row in rows:
            f.write('\t'.join(map(str, row)) + '\n')

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
    x = (80 - len(asgn.full_name) - 2) / 2
    print ''
    print ('-' * x) + ' ' + asgn.full_name + ' ' + ('-' * x)
    print ''
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
            try:
                asgn.init_grading()
            except:
                asgn.reset_grading(True)
                print 'Error starting assignment:'
                raise
            print 'Grading started...'
        else:
            print 'Cancelling...'
    else:
        new_header = ["Problem #", "# Handins", "# Graded", "# Flagged"]
        opts = []
        rows = []
        for question in asgn.questions:
            row = ['%s (%s)' % (question.qnumb, question.code_filename),
                   question.handin_count,
                   question.completed_count,
                   question.flagged_count]

            rows.append(row)

        print tabulate.tabulate(rows, new_header)
        print ''

        print 'What would you like to do?'
        opt = get_opt('> ', ['Reset Assignment Grading',
                             'Generate [and email] Grade Reports',
                             'Email Grade Report(s)',
                             'View flagged handins',
                             'Add handin',
                             'Deanonymize (for regrading)'])
        if opt == 0:
            print 'Resetting the assignment will delete any grades given.'
            if raw_input('Confirm [y/n]: ').lower() != 'y':
                print 'Exiting...'
                sys.exit(0)

            asgn.reset_grading(True)

        elif opt == 1:
            if asgn.emails_sent:
                print 'Emails have already been sent. Generate override reports? [y/n]'
                if raw_input('> ').lower() != 'y':
                    print 'Exiting...'
                    sys.exit(0)

            import getpass
            username = getpass.getuser()
            user = User(username)
            print 'Generating grade reports...'
            logins = student_list()

            handins = asgn.get_handin_dict(logins, user)
            for student in handins.keys():
                asgn.generate_report(handins[student],
                                     student_id=student,
                                     soft=False,
                                     overrides=asgn.emails_sent)
            print 'Assignments generated.\n'
            print 'Send report emails? [yes/n]'
            if raw_input('> ').lower() != 'yes':
                print 'Exiting... Run cs111-asgn-hub again to send emails.'
                sys.exit(0)
            else:
                send_asgn_emails(asgn, handins)

        elif opt == 2:
            import getpass
            username = getpass.getuser()
            user = User(username)
            r = get_opt('> ',
                        ['Send to individual student (by login)',
                         'Send to individual student (by anon id)',
                         'Send to all students'])
            if r == 0 or r == 1:
                if r == 0:
                    l = raw_input('Enter student login: ')
                elif r == 1:
                    i = raw_input('Enter anonymous id: ')
                    l = asgn.id_to_login(i)
                else:
                    raise Exception('whut')
                handins = asgn.get_handin_dict([l], user)
                handin_list = handins[l]
                
                if asgn.report_already_generated(l):
                    print 'A grade report has already been generated for this student.'
                    print 'Re-generate report or email existing report?'
                    s = get_opt('> ', ['Regenerate report', 'Send existing report'])
                    if s == 0:
                        asgn.generate_report(handin_list,
                                     student_id=l,
                                     soft=False,
                                     overrides=True)
                    
                else:
                    asgn.generate_report(handin_list,
                                     student_id=l,
                                     soft=False,
                                     overrides=True)

                send_grade_report(asgn, l)

            else:
                logins = student_list()
                handins = asgn.get_handin_dict(logins, user)
                send_asgn_emails(asgn, handins)

        elif opt == 3:
            header = ['Anon ID', 'Login', 'Grader', 'Flag Reason']
            for q in asgn.questions:
                print q
                full_data = []
                for h in q.handins:
                    if h.flagged:
                        data = [h.id, asgn.id_to_login(h.id),
                                h.grader, h.flag_reason]

                        full_data.append(data)

                table = tabulate.tabulate(full_data, header)
                lines = table.split('\n')
                indented = map(lambda l: '  ' + l, lines)
                print '\n'.join(indented)

            print ''
            print 'To unflag, go to %s' % asgn.log_path


        elif opt == 4:
            login = raw_input('Enter student login: ')
            asgn.add_new_handin(login)

        elif opt == 5:
            asgn.deanonymize()
            print 'Assignment deanonymized'
