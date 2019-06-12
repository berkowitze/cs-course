import yagmail
import os
import json
import subprocess
import sys
import logging
import urllib.parse

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
    ssid = json.load(f)['response-ssid']


class FormError(Exception):
    pass


def handle(row: List[str]) -> None:
    if len(row) < 7:
        raise FormError('Weird error? Len != 7/8')

    # Figure out the assignment that we are dealing with
    try:
        asgn = HTA_Assignment(row[2])
    except KeyError:
        raise FormError(f'No such assignment {row[2]}')

    # THIS IS NOT RELEVANT
    # if not asgn.emails_sent:
    #     # ignore the student
    #     raise FormError(f'Chill this assignment has not been graded yet')

    # Figure out the student
    try:
        student_login = asgn.id_to_login(int(row[6]))
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
        handin = real_question.get_handin_by_id(int(row[6]))
    except ValueError:
        raise FormError(f'No such handin for question {row[3]}')

    # figure out grader
    grader = handin.grader

    grade_updated = (row[4] == 'Yes')

    # Then you would go ahead and change the student's grade
    if grade_updated:
        asgn.generate_one_report(student_login, soft=False, overrides=True)
        asgn.send_emails(yag, [student_login])

    # Send another email with the instructor's response:
    email_to = f'{student_login}@cs.brown.edu'
    subject = f'Grade complaint response for {row[2]} question {row[3]}'
    asgn_link = urllib.parse.quote(asgn.full_name)
    filled_link = f'https://docs.google.com/forms/d/e/1FAIpQLSetfASPqeG_pc8Jw4CCYIgVpRblxJTIJ36sYPjE55fYHNnM2A/viewform?usp=pp_url&entry.1832652590={asgn_link}&entry.1252387205={row[3]}'
    body = f"""
    <ul>
        <li><strong>Assignment:</strong> {row[2]}</li>
        <li><strong>Question:</strong> {row[3]}</li>
        <li><strong>Instructor's response:</strong> {row[5]}</li>
    </ul>
    <p>Please use <a href='{filled_link}'>this Google Form</a> to respond to the instructor, if you so desire.</p>
    """.replace('\n', '')

    print(f'Sending grade complaint response to {email_to}')
    yag.send(email_to, subject, body)


print('Checking requests starting...')

rng = 'A1:H'
service = sheets_api()
spreadsheets = service.spreadsheets().values()
result = spreadsheets.get(spreadsheetId=ssid, range=rng).execute()
rows = result['values'][1:]
handle_column = "H"
for i, row in enumerate(rows):
    if not row:
        continue

    if len(row) > 7 and row[7]:
        continue

    print('Handling row: ' + str(row))

    handled = False
    try:
        handle(row)
        handled = True
    except FormError as e:
        body = f"""
        You submitted an invalid regrade response.

        Error message: {e.args[0]}

        <a href="mailto:cs0111headtas@lists.brown.edu">Email the htas</a>, or <a href="mailto:eliberkowitz@gmail.com">Eli</a> if you have any questions.
        """
        yag.send(row[1], 'Invalid regrade response', body)
        handled = True

    if handled:
        # update handled column on Gsheets
        resp = spreadsheets.update(spreadsheetId=ssid,
                                   range=f'{handle_column}{i+2}',
                                   valueInputOption='RAW',
                                   body={'values': [[True]]}).execute()


print('Checking requests complete.')
