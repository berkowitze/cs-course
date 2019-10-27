import yagmail
import os
import urllib.parse
import json
import sys
import logging

from os.path import join as pjoin
from typing import List
from helpers import locked_file, CONFIG, BASE_PATH, gen_email
from googleapi import sheets_api
from hta_classes import HTA_Assignment
from handin_helpers import email_to_login

regrade_log = os.path.join(BASE_PATH, 'hta/grading/regrading/regrade_log.json')

# quiet mode just overwrites print function, it's terrible but it works
# and logging is annoying
if len(sys.argv) > 1 and (sys.argv[1] == '--quiet' or sys.argv[1] == '-q'):
    def print(*args, **kwargs):
        pass

os.umask(0o007)  # set file permissions
yag = yagmail.SMTP(CONFIG.email_from)

settings_path = pjoin(BASE_PATH, 'hta/grading/regrading/settings.json')
with locked_file(settings_path) as f:
    settings = json.load(f)

ssid = settings['request-ssid']
instruction_link = settings['regrade-instructions']


class FormError(Exception):
    pass


def handle(row: List[str]) -> None:
    # figure out who the student is
    student_email = row[1]
    try:
        login = email_to_login(student_email)
    except ValueError:
        # send error to student
        subject, body = gen_email('regrade_request_email_not_found',
                                  email_vars={
                                      "to_student": True,
                                      "student_email": student_email,
                                      "hta_email": CONFIG.hta_email,
                                      "hta_descriptor": CONFIG.hta_descriptor
                                  })
        yag.send(student_email, subject, body)

        # send error to HTAs
        subject, body = gen_email('regrade_request_email_not_found',
                                  email_vars={
                                      "to_student": False,
                                      "student_email": student_email,
                                      "hta_email": CONFIG.hta_email,
                                      "hta_descriptor": CONFIG.hta_descriptor
                                  })
        yag.send(CONFIG.hta_email, subject, body)

        # stop handling this row
        return

    asgn_name = row[2]
    try:
        asgn = HTA_Assignment(asgn_name)
    except KeyError:
        raise FormError(f'No assignment with name {asgn_name!r} was found.')

    if not asgn.emails_sent:
        raise FormError(f'Assignment {asgn.full_name!r} is not graded yet')

    try:
        student_ID = asgn.login_to_id(login)
    except ValueError:
        err = (
                f'No submission found for {asgn.full_name!r} for student with'
                f' email {asgn_name!r} login {login!r}'
              )
        raise FormError(err)

    # figure out the question/assignment
    indicated_question = int(row[3])
    try:
        real_question = asgn.questions[indicated_question - 1]
    except IndexError:
        err = (
               f'Invalid question number (questions range from 1'
               f' to {len(asgn.questions)} for {asgn.full_name})'
              )
        raise FormError(err)

    # figure out the handin based on the question
    try:
        handin = real_question.get_handin_by_id(student_ID)
    except ValueError:
        err = (
                f'No submission found for student {student_ID} '
                f'{asgn.full_name} question {indicated_question}.'
              )
        raise FormError(err)

    # figure out grader
    grader = handin.grader
    asgn_link = urllib.parse.quote(asgn.full_name)
    link_template = settings['response-form-filled-link']
    filled_link = link_template.format(assignment_name=asgn_link,
                                       indicated_question=indicated_question,
                                       student_ID=student_ID)

    # Tis when assignment has not been graded yet? Weird
    if grader is not None:
        # generate and send email to grader
        email_to = f'{grader}@cs.brown.edu'
        complaint = row[4].replace('\n', '<br/>')

        subject, body = gen_email('regrade_request',
                                  subject_vars={
                                      'asgn_name': asgn_name,
                                      'qn': row[3]
                                  },
                                  email_vars={
                                      "asgn_name": asgn_name,
                                      "indicated_question": indicated_question,
                                      "student_ID": student_ID,
                                      "complaint": complaint,
                                      "filled_link": filled_link,
                                      "instruction_link": instruction_link
                                  })
        print(f'\tSending grade change request to {email_to}')
        yag.send(email_to, subject, body)
        msg_data = {
            'from': login,
            'to': grader,
            'message': complaint
        }
        with json_edit(regrade_log) as data:
            if asgn.full_name not in data:
                data[asgn.full_name] = {}

            if real_question.qname not in data[asgn.full_name]:
                data[asgn.full_name][real_question.qname] = {}

            qlog = data[asgn.full_name][real_question.qname]
            if login not in qlog:
                qlog[login] = []

            qlog[login].append(msg_data)
    else:
        subject, body = gen_email('regrade_request_no_grader')
        yag.send(student_email, subject, body)

        subject, body = gen_email('regrade_request_no_grader_hta',
                                  email_vars={
                                      'student_ID': student_ID,
                                      'asgn_name': asgn.full_name,
                                      'qn': indicated_question
                                  })
        yag.send(CONFIG.hta_email, subject, body)


print('Checking requests starting...')

rng = 'A2:F'  # starting at 2 to remove header
service = sheets_api()
spreadsheets = service.spreadsheets().values()
result = spreadsheets.get(spreadsheetId=ssid, range=rng).execute()
rows = result['values']
handle_column = 'F'
for i, row in enumerate(rows):
    if not row:
        continue

    if len(row) > 5 and row[5] == 'TRUE':
        continue

    print(f'Handling row {i + 2} with timestamp {row[0]} and email {row[1]}')

    handled = False
    try:
        handle(row)
        handled = True
    except FormError as e:
        subject, body = gen_email('regrade_request_form_error',
                                  email_vars={
                                      'error': e.args[0],
                                      'hta_email': CONFIG.hta_email,
                                      'hta_descriptor': CONFIG.hta_descriptor
                                  })
        yag.send(row[1], subject, body)
        handled = True

    if handled:
        # After successfully handling, update handled on Gsheets
        cell = f'{handle_column}{i+2}'
        try:
            spreadsheets.update(spreadsheetId=ssid,
                                range=cell,
                                valueInputOption='RAW',
                                body={'values': [[True]]}).execute()
        except Exception as e:
            ss_url = f'https://docs.google.com/spreadsheets/d/{ssid}'
            err = (
                    'BAD - HANDLE IMMMEDIATELY - Regrade request was '
                    'successfully processed but there was an error when '
                    'setting the handled column to TRUE in the Google Sheet.'
                    f'Manually set the value of cell {cell} to TRUE in this'
                    f'spreadsheet: {ss_url}. Also, forward this email to '
                    f'Eli at eliberkowitz@gmail.com.'
                    )
            raise ValueError(err) from e
    else:
        print(f'Potential error processing row {row}')


print('Checking requests complete.')
