import json
import os
import subprocess
import shutil
import sys
import tabulate
import yagmail
from typing import List

from datetime import datetime
from textwrap import dedent

from prompts import ez_prompt, opt_prompt, table_prompt, toggle_prompt
from hta_classes import (BASE_PATH, User, asgn_data_path, get_hta_asgn_list,
                         login_to_email, student_list, HTA_Assignment,
                         json_edit)
from hub_helpers import *
from helpers import red

asgns: List[HTA_Assignment] = get_hta_asgn_list()


def send_grade_reports(asgn: HTA_Assignment, logins: List[str]) -> None:
    yag = yagmail.SMTP('csci0111@brown.edu')
    asgn.send_emails(yag, logins, override_send_to='eliberkowitz@gmail.com')


print('At any time, press ctrl-c to quit')
STATE = 0
while True:
    if STATE == 0:
        resp1 = opt_prompt(['Generate gradebook',
                            'Generate and send grade summaries',
                            'Work with assignment',
                            'Course options (backups, etc.)'
                            ])
        if resp1 is None:
            break
        elif resp1 == 1:
            STATE = 1
        elif resp1 == 2:
            STATE = 2
        elif resp1 == 3:
            STATE = 3
        elif resp1 == 4:
            STATE = 12

    elif STATE == 1:
        path = pjoin(BASE_PATH, 'hta/gradebook.tsv')
        print(f'gradebook will be saved as "{path}".')
        print('Press enter to continue, or enter custom path (absolute and')
        print('with filename ending with .tsv)')
        resp2 = ez_prompt('> ')
        if resp2 is None:
            break
        elif resp2:
            dirname, fname = os.path.split(resp2)
            if not os.path.exists(dirname) or not fname.endswith('.tsv'):
                continue

            gradebook_path = resp2

        else:
            gradebook_path = path

        generate_gradebook(gradebook_path)
        print(f'Gradebook generated in "{gradebook_path}"')
        STATE = 0

    elif STATE == 2:
        # generate grade summaries
        resp3 = opt_prompt(['Generate grade summaries',
                            'Send grade summaries',
                            'Go back'])

        if resp3 is None:
            break
        elif resp3 == 1:
            generate_grade_summaries(write=True)
            print(f'Summaries output in {sum_path}')
            continue
        elif resp3 == 2:
            send_summaries(resummarize=False)
        elif resp3 == 3:
            STATE = 0

    elif STATE == 3:
        # assignment chooser
        print('Which assignment would you like to work on?')
        rows: List[List[str]] = []
        header = ["Asgn", "Due", "Grading Started",
                  "Grading Done"]

        rows = []
        for asgn in asgns:
            row = [asgn.full_name, str(asgn.due), str(asgn.started),
                   str(asgn.grading_completed)]
            rows.append(row)

        resp5 = table_prompt(rows, header)
        if resp5 is None:
            break
        asgn = asgns[resp5 - 1]
        if asgn.started:
            asgn.load()
            STATE = 5
        else:
            STATE = 4

    elif STATE == 4:
        # starting assignment grading
        print(f'{asgn.full_name} grading unstarted. Start it?')

        resp6 = opt_prompt(['Yes', 'No', 'Go back'])
        if resp6 is None:
            break
        elif resp6 == 3 or resp6 == 2:
            STATE = 3
            continue

        if not asgn.due:
            print('Students can still hand in for this assignment.')
            print('Continue anyway?')
            resp7 = opt_prompt(['Yes', 'No', 'Go back'])
            if resp7 is None:
                break
            elif resp7 == 3 or resp7 == 2:
                STATE = 3
                continue

        try:
            asgn.init_grading()
        except Exception:
            asgn.reset_grading(True)
            print('Error starting assignment (grading reset)')
            print('Error message:')
            raise
        else:
            asgn.load()
            STATE = 5

    elif STATE == 5:
        # assignment modifier
        print('')
        if not asgn.started:
            print('Got assignment modifier state with unstarted assignment...')
            STATE = 3
            continue

        print(asgn)
        asgn_header = ["Filename", "# Handins", "# Graded", "# Flagged"]
        rows = asgn.table_summary()
        print(tabulate.tabulate(rows, asgn_header))
        print('')

        print('What would you like to do?')
        option = opt_prompt(['Reset Assignment Grading',
                             'Generate Grade Reports',
                             'Email Grade Report(s)',
                             'View flagged handins',
                             'Add handin',
                             'Deanonymize (for regrading)',
                             'Go back'])
        if option is None:
            break
        elif option == 1:  # reset assignment grading
            STATE = 6
        elif option == 2:  # generate grade reports
            STATE = 7
        elif option == 3:  # email grade reports
            STATE = 8
        elif option == 4:  # view flagged handins
            STATE = 9
        elif option == 5:  # add handin
            STATE = 10
        elif option == 6:  # deanonymize assignment
            STATE = 11
        elif option == 7:
            STATE = 3

    elif STATE == 6:
        # resetting assignment grading
        print('Resetting the assignment will delete any grades given.')
        resp8 = opt_prompt(['Confirm removal', 'Go Back'])
        if resp8 is None:
            break
        elif resp8 == 2:
            STATE = 3
            continue
        else:
            asgn.reset_grading(True)
            STATE = 3

    elif STATE == 7:
        # generating grade reports
        if asgn.emails_sent:
            print('Emails have already been sent. Regenerate reports?')
            resp9 = opt_prompt(['Yes', 'No/Go back'])
            if resp9 is None:
                break
            elif resp9 == 2:
                STATE = 5
                continue
            else:
                overrides = True
        else:
            overrides = False

        print('Generating grade reports...')
        logins = student_list()
        handins = asgn.get_handin_dict(logins)
        for student in handins:
            asgn._generate_report(handins[student], login=student,
                                  soft=False, overrides=overrides)

        print('Grade reports generated.')
        STATE = 5

    elif STATE == 8:
        # emailing grade reports
        resp11 = opt_prompt(['Send to individual student',
                             'Send to all students'])
        if resp11 is None:
            break
        elif resp11 == 1:
            # send to one student
            login2 = ez_prompt('Enter student login: ')
            if login2 is None:
                break

            handins = asgn.get_handin_dict([login2])
            handin_list = handins[login2]

            if asgn.report_already_generated(login2):
                print(f'Grade report already generated for {login2}')
                print('Re-generate report or email existing report?')
                resp12 = opt_prompt(['Regenerate report',
                                     'Send existing report'])
                if resp12 is None:
                    break
                elif resp12 == 1:
                    asgn._generate_report(handin_list,
                                          login=login2,
                                          soft=False,
                                          overrides=True)
                    print('Report regenerated')

            to_send = [login2]

        else:
            # send reports to all students
            # TODO : change to those who handed in? careful for group projects
            to_send = student_list()
            print('After sending reports, deanonymize assignment if needed.')

        send_grade_reports(asgn, to_send)
        STATE = 5

    elif STATE == 9:
        # view flagged handins
        flag_header = ['Anon ID', 'Login', 'Grader',
                       'Flag Reason', 'Code Path']
        for q in asgn.questions:
            print(q)
            full_data = []
            for h in q.handins:
                if h.flagged:
                    data = [h.id, asgn.id_to_login(h.id),
                            h.grader, h.flag_reason, h.filepath]

                    full_data.append(data)

            table = tabulate.tabulate(full_data, flag_header)
            lines = table.split('\n')
            indented = ['  ' + l for l in lines]
            print('\n'.join(indented))

        print('')
        print(f'To unflag, go to {asgn.log_path}')
        resp13 = ez_prompt('Press enter to continue')
        if resp13 is None:
            break

        STATE = 5

    elif STATE == 10:
        # add new handin
        login = input('Enter student login: ')
        if login is None:
            break

        asgn.add_new_handin(login)
        print(f'Handin for {login} added')
        STATE = 5
        input('Press enter to continue or ctrl-c to quit')

    elif STATE == 11:
        # deanonymize assignment
        asgn.deanonymize()
        print('Assignment deanonymized')
        STATE = 5
        input('Press enter to continue or ctrl-c to quit')

    elif STATE == 12:
        # course options
        resp14 = opt_prompt([
            'Backup grading and handin data',
            'Restore grading and handin data (backup made beforehand)',
            'Clear grading and handin data (backup made beforehand)',
            'Delete old backups',
            'Go back'
            ])
        if resp14 is None:
            break
        elif resp14 == 1:
            print('Enter a custom name for the backup or leave blank ')
            print('to use a datetime-based name')
            fn = ez_prompt('> ',
                           checker=lambda s: not s or s.endswith('.zip'),
                           fail_check_msg='Must enter a .zip filename')
            if fn is None:
                break

            make_backup = pjoin(BASE_PATH, 'htabin/cs111-data-backup')
            print('Creating backup...')
            subprocess.call([make_backup, fn])
            print('')

        elif resp14 == 2:
            restore_backup = pjoin(BASE_PATH, 'htabin/cs111-restore-backup')
            subprocess.call(restore_backup)

        elif resp14 == 3:
            STATE = 14

        elif resp14 == 4:
            STATE = 13

        elif resp14 == 5:
            STATE = 0

    elif STATE == 13:
        # removing old backups
        backup_path = pjoin(BASE_PATH, 'hta/data_backups')
        files = [f for f in os.listdir(backup_path) if f.endswith('.zip')]
        to_remove: Set[str] = set()
        date_data: List[Tuple[str, datetime]] = []
        for f in files:
            try:
                dt = datetime.strptime(f, '%Y-%m-%d_%H-%M-%S.zip')
                date_data.append((f, dt))
            except ValueError:
                continue

        mx_dat = max(date_data, key=lambda dat: dat[1])

        # set of date-named files that are not the latest backup
        to_remove = {dat[0] for dat in date_data if dat is not mx_dat}

        print('Red backups will be removed, white ones kept.')
        print('Enter numbers to toggle removal.')
        print('Enter nothing to complete removal.')
        removed = toggle_prompt(files, to_remove)
        if removed is None:
            break

        for remove in removed:
            path = pjoin(backup_path, remove)
            os.remove(path)
            print(f'{path} removed...')

        print('All done.')
        print('')
        STATE = 12

    elif STATE == 14:
        # clearing data
        print(dedent(red("""
        This should only be used for starting a new semester.
        The following steps will occur:
        0. **Test files, rubrics, and assignments.json **will be kept**
           (other than some booleans in assignment.json switching)**
        1. All assignment grading will be reset
        2. All grade files will be removed (including summaries)
        3. All student handin files will be removed
        4. All group data will be cleared
        5. All lab data will be removed
        6. All blocklist data will be removed
        8. All extension data will be removed

        You should be able to restore all this data using the restore
        option in cs111-asgn-hub.

        Do not ctrl-c once starting; if you want to cancel, restore
        a backup instead. If this script fails, restore the backup then debug.

        Type CONFIRM to confirm clearing this data.
        """)))
        resp16 = ez_prompt('> ')
        if resp16 is None:
            break
        elif resp16 != 'CONFIRM':
            STATE = 12
            continue

        print('Creating backup...')
        make_backup = pjoin(BASE_PATH, 'htabin/cs111-data-backup')
        subprocess.call(make_backup)
        print('')

        for assignment in get_hta_asgn_list():
            if not assignment.started:
                continue

            assignment.load()
            assignment.reset_grading(True, quiet=True)

        project_path = pjoin(BASE_PATH, 'ta/grading/data/projects')
        delete_subfiles(project_path)
        print('Assignment grading reset.')

        grade_path = pjoin(BASE_PATH, 'hta/grades')
        delete_subdirs(grade_path)
        summ_path = pjoin(BASE_PATH, 'hta/summaries')
        delete_subfiles(summ_path)
        ta_grade_path = pjoin(BASE_PATH, 'ta/grading/grades')
        delete_subdirs(ta_grade_path)
        print('Grades removed.')

        handin_path = pjoin(BASE_PATH, 'hta/handin/students')
        delete_subdirs(handin_path)
        print('Handin data removed.')

        group_path = pjoin(BASE_PATH, 'ta/groups')
        delete_subfiles(group_path)
        print('Group data removed.')

        lab_path = pjoin(BASE_PATH, 'ta/grading/data/labs')
        try:
            with json_edit(pjoin(lab_path, 'roster.json')) as data:
                data.clear()
        except OSError:
            pass

        try:
            with json_edit(pjoin(lab_path, 'attendance.json')) as data:
                data.clear()
        except OSError:
            pass

        print('Lab data removed.')

        with json_edit(pjoin(BASE_PATH, 'ta/t-s-blocklist.json')) as data:
            data.clear()

        with json_edit(pjoin(BASE_PATH, 'hta/s-t-blocklist.json')) as data:
            data.clear()

        print('Blocklist data removed.')

        ext_path = pjoin(BASE_PATH, 'hta/grading/extensions.txt')
        print('Extensions not cleared (need to update extension format)')
        print('Clearing complete.')
        print('')
        STATE = 12


print('\nExiting...')
