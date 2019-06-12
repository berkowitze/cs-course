import yagmail
import os
import urllib.parse
import json
import subprocess
import sys
import logging

from os.path import join as pjoin
from typing import List
from helpers import locked_file, CONFIG, BASE_PATH
from googleapi import sheets_api
from hta_classes import HTA_Assignment

if len(sys.argv) > 1 and (sys.argv[1] == '--quiet' or sys.argv[1] == '-q'):
    def print(*args, **kwargs):
        pass

os.umask(0o007)  # set file permissions
yag = yagmail.SMTP(CONFIG.email_from)

data_file = pjoin(BASE_PATH, 'ta/assignments.json')
with locked_file(data_file) as f:
    data = json.load(f)

settings = pjoin(BASE_PATH, 'hta/grading/regrading/settings.json')
with locked_file(settings) as f:
    ssid = json.load(f)['request-ssid']


instruction_link = 'https://docs.google.com/document/d/1xWOYBp_9_GIg3ON_z2zFUfE8RBGoPLi7ZBQgmplTuqQ/edit'


class FormError(Exception):
    pass


def handle(row: List[str]) -> None:
    # figure out who the student is
    em_to_login_cmd = pjoin(BASE_PATH, 'tabin/email-to-login')
    student_login = subprocess.check_output([em_to_login_cmd, row[1]], text=True).strip()
    if not student_login:
        # TODO : send this student an email?
        print('bye')
        return

    try:
        asgn = HTA_Assignment(row[2])
    except KeyError:
        raise FormError(f'No such assignment {row[2]}')

    if not asgn.emails_sent:
        # ignore the student
        raise FormError(f'Chill this assignment has not been graded yet')

    try:
        student_ID = asgn.login_to_id(student_login)
    except ValueError:
        raise FormError(f'No such handin {row[2]}')

    # figure out the question/assignment
    indicated_question = row[3]
    try:
        real_question = asgn.questions[int(indicated_question) - 1]
    except IndexError:
        raise FormError(f'No such question {row[3]}')

    # figure out the handin based on the question
    try:
        handin = real_question.get_handin_by_id(student_ID)
    except ValueError:
        raise FormError(f'No such handin for question {row[3]}')

    # figure out grader
    grader = handin.grader
    asgn_lnk = urllib.parse.quote(asgn.full_name)
    filled_link = f'https://docs.google.com/forms/d/e/1FAIpQLSe3eNapyqLg74xMy_O4TBxebwgT4aZ0Kl50JYtWhdNzHnYonw/viewform?usp=pp_url&entry.2102360043={asgn_lnk}&entry.1573848516={row[3]}&entry.660184789={student_ID}'
    # Tis when assignment has not been graded yet? Weird
    if grader is not None:
        # generate and send email to grader
        email_to = f'{grader}@cs.brown.edu'
        subject = f'Grade complaint for {row[2]} question {row[3]}'
        body = f"""
        <ul>
            <li><strong>Assignment:</strong> {row[2]}</li>
            <li><strong>Question:</strong> {row[3]}</li>
            <li><strong>Anonymous ID:</strong> {student_ID}</li>
            <li><strong>Complaint content:</strong> {row[4]}</li>
        </ul>
        <p>Please use <a href='{filled_link}'>this Google Form</a> to respond to this grade request.</p>
        <p>Please refer to <a href='{instruction_link}'>these Regrade Instructions</a> for more details on how to handle grade requests.</p>
        """.replace('\n', '')

        print(f'Sending grade change request to {email_to}')
        yag.send(email_to, subject, body)
    else:
        # Ignore? Or email the student? Meh
        print('hi')
        pass


print('Checking requests starting...')

rng = 'A1:F'
service = sheets_api()
spreadsheets = service.spreadsheets().values()
result = spreadsheets.get(spreadsheetId=ssid, range=rng).execute()
rows = result['values'][1:]
handle_column = "F"
for i, row in enumerate(rows):
    if not row:
        continue

    if len(row) > 5 and row[5]:
        continue

    print('Handling row: ' + str(row))

    handled = False
    try:
        handle(row)
        handled = True
    except FormError as e:
        body = f"""
        You submitted an invalid regrade request.

        Error message: {e.args[0]}

        <a href="mailto:cs0111headtas@lists.brown.edu">Email the htas</a> if you have any questions.
        """
        yag.send(row[1], 'Invalid regrade request', body)
        handled = True
        # After successfully handling, update handled on Gsheets
    if handled:
        resp = spreadsheets.update(spreadsheetId=ssid,
                                   range=f'{handle_column}{i+2}',
                                   valueInputOption='RAW',
                                   body={'values': [[True]]}).execute()


print('Checking requests complete.')
