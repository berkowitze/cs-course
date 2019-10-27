import yagmail
import os
import json
import sys
import logging
import urllib.parse

from os.path import join as pjoin
from typing import List
from helpers import locked_file, CONFIG, BASE_PATH, gen_email
from googleapi import sheets_api
from hta_classes import HTA_Assignment

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

ssid = settings['response-ssid']


class FormError(Exception):
    pass


def handle(row: List[str]) -> None:
    # Figure out the assignment that we are dealing with
    try:
        asgn = HTA_Assignment(row[2])
    except KeyError:
        raise FormError(f'No such assignment {row[2]!r}')

    # Figure out the student
    try:
        sid = int(row[4])
        student_login = asgn.id_to_login(sid)
    except ValueError:
        raise FormError(f'No student with anonymous id {row[4]}')

    # figure out the question/assignment
    indicated_question = int(row[3])
    try:
        real_question = asgn.questions[indicated_question - 1]
    except IndexError:
        err = (
                f'No such question {row[3]} (questions range from 1 '
                f'to {len(asgn.questions)} for {asgn.full_name})'
              )
        raise FormError(err)

    # figure out the handin based on the question
    try:
        handin = real_question.get_handin_by_id(sid)
    except ValueError:
        raise FormError(f'No such handin for question {row[3]} id {row[4]}')

    # figure out grader
    grader = handin.grader

    grade_updated = (row[5] == 'Yes')

    # Then change the student's grade
    if grade_updated:
        asgn.generate_one_report(student_login, write_files=True)
        asgn.send_emails(yag, [student_login])

    # Send another email with the instructor's response:
    # TODO: use login_to_email for this
    email_to = f'{student_login}@cs.brown.edu'
    asgn_link = urllib.parse.quote(asgn.full_name)
    link_template = settings['request-form-filled-link']
    filled_link = link_template.format(assignment_name=asgn_link,
                                       indicated_question=indicated_question)
    response = row[6].replace('\n', '<br/>')

    subject, body = gen_email('regrade_response',
                              subject_vars={
                                'asgn': row[2],
                                'qn': row[3]
                              },
                              email_vars={
                                'asgn': row[2],
                                'qn': row[3],
                                'grade_updated': grade_updated,
                                'response': response,
                                'hta_email': CONFIG.hta_email,
                                'filled_link': filled_link,
                                'hta_descriptor': CONFIG.hta_descriptor
                              })
    print(f'Sending grade complaint response to {email_to}')
    yag.send(email_to, subject, body)

    msg_data = {
        'from': grader,
        'to': student_login,
        'message': response,
        'grade_updated': grade_updated
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


print('Checking responses starting...')

rng = 'A1:H'
service = sheets_api()
spreadsheets = service.spreadsheets().values()
result = spreadsheets.get(spreadsheetId=ssid, range=rng).execute()
rows = result['values'][1:]
handle_column = "H"
for i, row in enumerate(rows):
    if not row:  # empty row
        continue

    if len(row) > 7 and row[7] == 'TRUE':
        continue

    print(f'Handling row {i + 2} with timestamp {row[0]} and email {row[1]}')

    handled = False
    try:
        handle(row)
        handled = True
    except FormError as e:
        subject, body = gen_email('regrade_response_form_error',
                                  email_vars={
                                    'error': e.args[0],
                                    'hta_email': CONFIG.hta_email,
                                    'hta_descriptor': CONFIG.hta_descriptor
                                  })
        yag.send(row[1], subject, body)
        handled = True

    if handled:
        # update handled column on Gsheets
        cell = f'{handle_column}{i+2}'
        try:
            resp = spreadsheets.update(spreadsheetId=ssid,
                                       range=cell,
                                       valueInputOption='RAW',
                                       body={'values': [[True]]}).execute()
        except Exception as e:
            ss_url = f'https://docs.google.com/spreadsheets/d/{ssid}'
            err = (
                     'BAD HANDLE IMMMEDIATELY: Regrade request was '
                     'successfully processed but there was an error when '
                     'setting the handled column to TRUE in the Google Sheet.'
                    f'Manually set the value of cell {cell} to TRUE in this'
                    f'spreadsheet: {ss_url}. Also, forward this email to '
                     'Eli at eliberkowitz@gmail.com'
                    )
            raise ValueError(err) from e
    else:
        print(f'Possible error handling response row {row}')


print('Checking responses complete.')
