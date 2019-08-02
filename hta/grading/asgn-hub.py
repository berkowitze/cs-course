import json
import os
import subprocess
import shutil
import sys
import tabulate
import yagmail
from typing import List
from enum import Enum, unique, auto

from datetime import datetime
from textwrap import dedent

from prompts import (ez_prompt, opt_prompt, table_prompt,
                     toggle_prompt, yn_prompt)
from hta_classes import (BASE_PATH, User, get_hta_asgn_list,
                         login_to_email, student_list, HTA_Assignment,
                         json_edit, CONFIG)
from hub_helpers import *
from helpers import red, moss_langs


asgns: List[HTA_Assignment] = get_hta_asgn_list()

backup_exec = pjoin(BASE_PATH, 'htabin/cs50-data-backup')
restore_backup = pjoin(BASE_PATH, 'htabin/cs50-restore-backup')


@unique
class State(Enum):
    home = auto()
    gradebook = auto()
    summaries = auto()
    asgn_home = auto()
    start_grading = auto()
    modify_asgn = auto()
    reset_asgn = auto()
    run_MOSS = auto()
    generate_reports = auto()
    email_reports = auto()
    view_flagged_handins = auto()
    add_handin = auto()
    deanonymize = auto()
    course_home = auto()
    remove_backups = auto()
    clear_data = auto()


def send_grade_reports(asgn: HTA_Assignment, logins: List[str]) -> None:
    yag = yagmail.SMTP(CONFIG.email_from)
    asgn.send_emails(yag, logins)


print('At any time, press ctrl-c to quit')
STATE: State = State.home
while True:
    if STATE == State.home:
        resp1 = opt_prompt(['Generate gradebook',
                            'Generate and send grade summaries',
                            'Work with assignment',
                            'Course options (backups, etc.)'
                            ])
        if resp1 is None:
            break
        elif resp1 == 1:
            STATE = State.gradebook
        elif resp1 == 2:
            STATE = State.summaries
        elif resp1 == 3:
            STATE = State.asgn_home
        elif resp1 == 4:
            STATE = State.course_home

    elif STATE == State.gradebook:
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
        input('Press enter to coninue')
        STATE = State.home

    elif STATE == State.summaries:
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
            STATE = State.home

    elif STATE == State.asgn_home:
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
            try:
                asgn.load()
            except Exception as e:
                print(f'Loading assignment {asgn.full_name} '
                      f'failed with message {e.args[0]}')
                print('Reset the grading for this assignment?')
                if yn_prompt():
                    asgn.reset_grading(True)
                    continue
                else:
                    STATE = State.asgn_home

            STATE = State.modify_asgn
        else:
            STATE = State.start_grading

    elif STATE == State.start_grading:
        print(f'{asgn.full_name} grading unstarted. Start it?')

        resp6 = opt_prompt(['Yes', 'No', 'Go back', 'Reset Grading'])
        if resp6 is None:
            break
        elif resp6 == 3 or resp6 == 2:
            STATE = State.asgn_home
            continue
        elif resp6 == 4:
		#try:
            asgn.reset_grading(True)
	    #except Exception:
		    # pass
            STATE = State.asgn_home
            continue

        if not asgn.due:
            print('Students can still hand in for this assignment.')
            print('Continue anyway?')
            resp7 = opt_prompt(['Yes', 'No', 'Go back'])
            if resp7 is None:
                break
            elif resp7 == 3 or resp7 == 2:
                STATE = State.asgn_home
                continue
	
        try:
            asgn._check_startable()
        except OSError as e:
            print("Some error with the json file. Please read error message.")
            print(e.strerror)
            raise

        try:
            asgn.init_grading()
        except Exception:
            asgn.reset_grading(True)
            print('Error starting assignment (grading reset)')
            print('Error message:')
            raise
        else:
            asgn.load()
            STATE = State.modify_asgn

    elif STATE == State.modify_asgn:
        print('')
        if not asgn.started:
            print('Got assignment modifier state with unstarted assignment...')
            STATE = State.asgn_home
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
                             'Run MOSS',
                             'Go back'])
        if option is None:
            break
        elif option == 1:
            STATE = State.reset_asgn
        elif option == 2:
            STATE = State.generate_reports
        elif option == 3:
            STATE = State.email_reports
        elif option == 4:
            STATE = State.view_flagged_handins
        elif option == 5:
            STATE = State.add_handin
        elif option == 6:
            STATE = State.deanonymize
        elif option == 7:
            STATE = State.run_MOSS
        elif option == 8:
            STATE = State.asgn_home

    elif STATE == State.reset_asgn:
        print('Resetting the assignment will delete any grades given.')
        resp8 = opt_prompt(['Confirm removal', 'Go Back'])
        if resp8 is None:
            break
        elif resp8 == 2:
            STATE = State.asgn_home
            continue
        else:
            asgn.reset_grading(True)
            STATE = State.asgn_home

    elif STATE == State.generate_reports:
        if asgn.emails_sent:
            print('Emails have already been sent. Regenerate reports?')
            resp9 = opt_prompt(['Yes', 'No/Go back'])
            if resp9 is None:
                break
            elif resp9 == 2:
                STATE = State.modify_asgn
                continue
            else:
                overrides = True
        else:
            overrides = False

        print('Generating grade reports...')
        logins = student_list()
        handins = asgn.get_handin_dict(logins)
        for student in handins:
            asgn._generate_report(handins[student],
                                  login=student,
                                  write_files=True)

        print('Grade reports generated.')
        STATE = State.modify_asgn

    elif STATE == State.email_reports:
        resp11 = opt_prompt(['Send to individual student',
                             'Send to all students'])
        # whether or not to update assignments.json with emails_sent: True
        mark_sent = False 
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
                                          write_files=True)
                    print('Report regenerated')

            to_send = [login2]

        else:
            # send reports to all students
            # TODO : change to those who handed in? careful for group projects
            to_send = student_list()
            mark_sent = True
            print('After sending reports, deanonymize assignment if needed.')

        send_grade_reports(asgn, to_send)
        if mark_sent:
            asgn.set_emails_sent()

        STATE = State.modify_asgn

    elif STATE == State.view_flagged_handins:
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

        STATE = State.modify_asgn

    elif STATE == State.add_handin:
        login = input('Enter student login: ')
        if login is None:
            break

        asgn.add_new_handin(login)
        print(f'Handin for {login} added')
        STATE = State.modify_asgn
        input('Press enter to continue or ctrl-c to quit')

    elif STATE == State.deanonymize:
        asgn.deanonymize()
        print('Assignment deanonymized')
        STATE = State.modify_asgn
        input('Press enter to continue or ctrl-c to quit')

    elif STATE == State.run_MOSS:
        print('Enter the language to be used by MOSS')
        valid_langs = list(moss_langs)
        valid_langs.append('NO LANGUAGE')
        resp15 = opt_prompt(valid_langs)
        if resp15 is None:
            break

        lang_choice = valid_langs[resp15 - 1]
        lang = lang_choice if lang_choice != "NO LANGUAGE" else None
        print('Enter file extension to filter by (i.e. py) or ')
        print('leave blank to upload all files')
        ext_choice = ez_prompt('> ')
        if ext_choice is None:
            break

        ext = ext_choice if ext_choice else None

        asgn.moss(moss_lang=lang, extension=ext)

        input('Press enter to continue')
        STATE = State.modify_asgn

    elif STATE == State.course_home:
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

            print('Creating backup...')
            subprocess.call([backup_exec, fn])
            print('')

        elif resp14 == 2:
            subprocess.call(restore_backup)

        elif resp14 == 3:
            STATE = State.clear_data

        elif resp14 == 4:
            STATE = State.remove_backups

        elif resp14 == 5:
            STATE = State.home

    elif STATE == State.remove_backups:
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

        try:
            mx_dat = max(date_data, key=lambda dat: dat[1])
        except ValueError:
            print('No backups to remove!')
            state = STATE.course_home
            continue

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
        STATE = State.course_home

    elif STATE == State.clear_data:
        # clearing data
        print(dedent(red("""
        This should only be used for starting a new semester.
        The following steps will occur:
        0. **Test files, rubrics, assignments.json, and config.py
           **will be kept** (other than some booleans in assignment.json
           switching).
        1. All assignment grading will be reset.
        2. All grade files will be removed (including summaries).
        3. All student handin files will be removed.
        4. All group data will be cleared.
        5. All lab data will be removed.
        6. All blocklist data will be removed.
        8. All extension data will be removed.

        You should be able to restore all this data using the restore
        option in cs-asgn-hub.

        Do not ctrl-c once starting; if you want to cancel, restore
        a backup instead. If this script fails, restore the backup then debug.

        Type CONFIRM to confirm clearing this data.
        """)))
        resp16 = ez_prompt('> ')
        if resp16 is None:
            break
        elif resp16 != 'CONFIRM':
            STATE = State.course_home
            continue

        print('Creating backup...')
        subprocess.call(backup_exec)
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
        STATE = State.course_home


print('\nExiting...')
