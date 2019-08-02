import yagmail
import os
import urllib.parse
import json
import sys
import logging

from os.path import join as pjoin
from typing import List
from helpers import locked_file, CONFIG, BASE_PATH
from googleapi import sheets_api
from hta_classes import HTA_Assignment
from handin_helpers import email_to_login

# quiet mode just overwrites print function, it's terrible but it works
# and logging is annoying
if len(sys.argv) > 1 and (sys.argv[1] == '--quiet' or sys.argv[1] == '-q'):
    def print(*args, **kwargs):
        pass

os.umask(0o007)  # set file permissions
yag = yagmail.SMTP(CONFIG.email_from)

data_file = pjoin(BASE_PATH, 'ta/assignments.json')
with locked_file(data_file) as f:
    data = json.load(f)

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
        subject = 'Error processing grade complaint'
        body = (
          f'<p>There was an error processing your grade complaint request.</p>'
          f'<p>There was no account associated with the email '
          f'{student_email}.</p>'
          f'<p>If you believe this is an error, please '
          f'<a href="mailto:{CONFIG.hta_email}">email the HTAs</a>.'
        ).replace('\n', '')
        yag.send(student_email, subject, body)
        hta_head = '<p>POTENTIAL ERROR PROCESSING GRADE CHANGE REQUEST:</p>'
        yag.send(CONFIG.hta_email, subject, hta_head + body)
        return

    try:
        asgn = HTA_Assignment(row[2])
    except KeyError:
        raise FormError(f'No assignment with name {row[2]!r} was found.')

    if not asgn.emails_sent:
        raise FormError(f'Assignment {asgn.full_name!r} is not graded yet')

    try:
        student_ID = asgn.login_to_id(login)
    except ValueError:
        err = (
                f'No submission found for {asgn.full_name!r} for student with'
                f' email {row[2]!r} login {login!r}'
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
        subject = f'Grade complaint for {row[2]} question {row[3]}'
        complaint = row[4].replace('\n', '<br/>')
        body = f"""
        <ul>
            <li><strong>Assignment:</strong> {row[2]}</li>
            <li><strong>Question:</strong> {row[3]}</li>
            <li><strong>Anonymous ID:</strong> {student_ID}</li>
            <li><strong>Complaint content:</strong><br/>{complaint}</li>
        </ul>
        <p>Please use <a href='{filled_link}'>this Google Form</a> to respond
        to this grade complaint.</p>
        <p>Please refer to <a href='{instruction_link}'>these Regrade
        Instructions</a> for more details on how to handle grade requests.</p>
        """.replace('\n', '')

        print(f'\tSending grade change request to {email_to}')
        yag.send(email_to, subject, body)
    else:
        err_subject = 'Error processing grade complaint'
        err_body = (
                     'We could not find a grader for your handin. This is '
                     'likely an issue on our side; the HTAs have also been '
                     'notified of the issue and will let you know when '
                     'it is resolved.'
                    )
        yag.send(student_email, err_subject, err_body)

        hta_err_body = f"""Potential error with regrade request system.
        A grader was not found for student {student_ID} who requested a
        regrade on {asgn.full_name} question {indicated_question}."""
        yag.send(CONFIG.hta_email, err_subject, hta_err_body)


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
        body = f"""
        You submitted an invalid regrade request.

        Error message: {e.args[0]}

        <a href="mailto:{CONFIG.hta_email}">Email {CONFIG.hta_name}</a> if
        you have any questions or believe this is an error.
        """
        yag.send(row[1], 'Invalid regrade request', body)
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
                    'BAD HANDLE IMMMEDIATELY: Regrade request was '
                    'successfully processed but there was an error when '
                    'setting the handled column to TRUE in the Google Sheet.'
                    f'Manually set the value of cell {cell} to TRUE in this'
                    f'spreadsheet: {ss_url}. Also, forward this email to '
                    f'Eli at eliberkowitz@gmail.com.'
                    )
            raise ValueError(err) from e


print('Checking requests complete.')
