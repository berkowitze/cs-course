import json
import os
import prompts
import subprocess
import sys
import tabulate
import yagmail
from typing import List

from hta_classes import (BASE_PATH, User, asgn_data_path, get_hta_asgn_list,
                         login_to_email, student_list, HTA_Assignment)
from hub_helpers import *

asgns: List[HTA_Assignment] = get_hta_asgn_list()


def send_grade_reports(asgn: HTA_Assignment, logins: List[str]) -> None:
    yag = yagmail.SMTP('csci0111@brown.edu')
    asgn.send_emails(yag, logins, override_send_to='eliberkowitz@gmail.com')


print('At any time, press ctrl-c to quit')
STATE = 0
while True:
    if STATE == 0:
        resp1 = prompts.opt_prompt(['Generate gradebook',
                                    'Generate and send grade summaries',
                                    'Work with assignment'
                                    ])
        if resp1 is None:
            break
        elif resp1 == 1:
            STATE = 1
        elif resp1 == 2:
            STATE = 2
        elif resp1 == 3:
            STATE = 3

    elif STATE == 1:
        path = pjoin(BASE_PATH, 'hta/gradebook.tsv')
        print(f'gradebook will be saved as "{path}".')
        print('Press enter to continue, or enter custom path (absolute and')
        print('with filename ending with .tsv)')
        resp2 = prompts.ez_prompt('> ')
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
        resp3 = prompts.opt_prompt(['Generate grade summaries',
                                    'Send grade summaries',
                                    'Go back'])

        if resp3 is None:
            break
        elif resp3 == 1:
            generate_grade_summaries(write=True, to_return=False)
            print(f'Summaries output in {sum_path}')
            continue
        elif resp3 == 2:
            send_summaries(resummarize=False, override_email='eliberkowitz@gmail.com')
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

        resp5 = prompts.table_prompt(rows, header)
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

        resp6 = prompts.opt_prompt(['Yes', 'No', 'Go back'])
        if resp6 is None:
            break
        elif resp6 == 3 or resp6 == 2:
            STATE = 3
            continue

        if not asgn.due:
            print('Students can still hand in for this assignment.')
            print('Continue anyway?')
            resp7 = (['Yes', 'No', 'Go back'])
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
        option = prompts.opt_prompt(['Reset Assignment Grading',
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
        resp8 = prompts.opt_prompt(['Confirm removal', 'Go Back'])
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
            resp9 = prompts.opt_prompt(['Yes', 'No/Go back'])
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
        resp11 = prompts.opt_prompt(['Send to individual student',
                                     'Send to all students'])
        if resp11 is None:
            break
        elif resp11 == 1:
            # send to one student
            login2 = prompts.ez_prompt('Enter student login: ')
            if login2 is None:
                break

            handins = asgn.get_handin_dict([login2])
            handin_list = handins[login2]

            if asgn.report_already_generated(login2):
                print(f'Grade report already generated for {login2}')
                print('Re-generate report or email existing report?')
                resp12 = prompts.opt_prompt(['Regenerate report',
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
        resp13 = prompts.ez_prompt('Press enter to continue')
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
        input('Press enter to continue')

    elif STATE == 11:
        # deanonymize assignment
        asgn.deanonymize()
        print('Assignment deanonymized')
        STATE = 5
        input('Press enter to continue')


print('\nExiting...')
