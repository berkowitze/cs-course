import json
import zipfile
import traceback
import io
import os
import yagmail
from google.oauth2.credentials import Credentials
from apiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googlefile import GoogleFile
from googleapi import sheets_api
import datetime
from datetime import datetime as dt
from helpers import *

# TODO :
# - change confirmation email to be from brown email/brown cs email
# - need to figure out yagmail with different accnt

data_file = '/course/cs0050/ta/assignments.json'
data = load_data(data_file)
log_path = os.path.join(data['handin_log_path'])

class Question:
    def __init__(self, question, row):
        self.downloaded = False
        self.q_data = question
        col = self.q_data['col']
        ind = col_str_to_num(col) - 1

        self.link = row[ind] if ind < len(row) and row[ind] != '' else None
        self.completed = self.link != None
        self.fname = self.q_data['filename']

    def get_gfile(self):
        # extensions which a snippet can be extracted from
        valid_exts = ['.txt', '.py', '.arr', '.tex']
        ident = url_to_gid(self.link) # google file id
        self.gf = None if ident is None else GoogleFile(ident)
        if self.completed:
            # make a snippet during confirmation if the student
            # uploaded a valid file & its a "raw text" file
            self.make_snippet = os.path.splitext(self.gf.name)[1] in valid_exts
        else:
            self.make_snippet = False

    def download(self, base_path, login):
        fpath = os.path.join(base_path, self.fname)
        if self.gf is None:
            # no submission
            self.downloaded = True
            return
        else:
            expect_ext = os.path.splitext(self.fname)[1]
            actual_ext = os.path.splitext(self.gf.name)[1]
            # student uploaded incorrect filetype (name irrelevant)
            if expect_ext != actual_ext:
                if expect_ext == '.zip':
                    # this is a hack to make things not break
                    # but it will make other things break. FIX IT.
                    fpath += actual_ext 
                    self.fname += actual_ext

                e = 'Student %s uploaded a %s file, expected %s'
                print e % (login, actual_ext, self.fname)
                with open('filename_error_template.html', 'r') as f:
                    self.warning = f.read().format(exp_ext=expect_ext,
                                                   sub_ext=actual_ext)
            else:
                self.warning = ''

            self.gf.download(fpath)

        self.file_path = fpath
        self.downloaded = True

    def get_snippet(self):
        lines_per_file = 5 # how many lines to print per snippet
        if not self.downloaded:
            e = 'File %s must be downloaded before generating snippet'
            raise Exception(e % self.fname)

        if not self.completed:
            return '<span style="color: red">Not submitted.</span>', ''
        elif not self.make_snippet:
            first_cell =  '<span style="color: green">Submitted.%s</span>'
            return first_cell % self.warning, \
                   'Snippet Unavailable'
        else:
            with open(self.file_path, 'r') as dl_f:
                lines = dl_f.readlines()
                if lines == [] or lines == ['']:
                    first_cell = '<span style="color: orange">Empty file.%s</span>'
                    return first_cell % self.warning, ''

                if len(lines) > lines_per_file:
                    snippet = lines[0:lines_per_file]
                    snippet.append('...')
                elif len(lines) == lines_per_file:
                    snippet = lines
                else:
                    snippet = lines[0:len(lines)]
            
            snippet = '<br>'.join(map(lambda line: line.strip(), snippet))
            first_cell = '<span style="color: green">Submitted.%s</span>'
            return first_cell % self.warning, snippet

class Response:
    def __init__(self, row, ident):
        # submission time
        self.sub_time  = dt.strptime(row[0], '%m/%d/%Y %H:%M:%S')
        self.sub_timestr = self.sub_time.strftime('%m/%d/%y %I:%M:%S%p')
        # submission email (must be Brown account)
        self.email = row[col_str_to_num(data['email_col']) - 1]
        # submission login
        self.login = email_to_login(self.email)
        self.asgn_name = row[col_str_to_num(data['submit_col']) - 1]
        self.dir_name  = self.asgn_name.replace(' ', '').lower()
        self.ident     = ident
        self.row       = row
        self.confirmed = self.ident in confirmed_responses(log_path)

    def download(self):
        if self.confirmed:
            raise 'Response has already been downloaded & confirmed.'

        self.asgn      = data['assignments'][self.asgn_name.lower()]
        self.due       = dt.strptime(self.asgn['due'], '%m/%d/%Y %I:%M%p')
        self.qs = []
        for i in range(len(self.asgn['questions'])):
            question = Question(self.asgn['questions'][i], self.row)
            question.get_gfile()
            self.qs.append(question)

        self.create_directory()
        self.gfiles = map(lambda q: q.gf, self.qs)
        self.download_files()
        self.downloaded = True

    def confirm(self):
        html = open('confirmation_template.html').read().strip()
        row_template = '<tr><td>{cell_1}</td><td>{cell_2}</td><td>{cell_3}</td></tr>'
        table = ''
        for q in self.qs:
            row = row_template
            a, b = q.get_snippet()
            table += row.format(cell_1=q.fname, cell_2=a, cell_3=b)

        if self.email_late:
            msg = '<p><span style="color: red">Note: Submission was late.</span>'
            msg += ' If you have an extension, disregard this message.</span>'
        else:
            msg = ''
        html = html.format(name=self.login,
                           sub_time=self.sub_timestr,
                           msg=msg,
                           asgn_name=self.asgn_name,
                           tab_conts=table)

        yag = yagmail.SMTP(data['email_from'])
        subject  = 'Confirmation of %s submission' % self.asgn_name
        if self.email_late:
            subject += ' (late)'

        zip_path = self.get_zip()
        if self.asgn['grading_completed']:
            c = 'Student %s submitted %s after grading had started.'
            yag.send(to=data['email_errors_to'],
                     subject='Submission after grading started',
                     contents=c % (self.login, self.asgn_name))
        # print map(lambda q: q.q_data, self.qs)
        yag.send(to=self.email,
                 subject=subject,
                 contents=[html, zip_path])
        os.remove(zip_path)

    def add_to_log(self):
        with open(log_path, 'a') as f:
            f.write('%s\n' % self.ident)
            f.flush()

    def create_directory(self):
        base = data['base_path'] #change to /course/cs0111/hta/...
        login_path = os.path.join(base, self.login)
        if not os.path.exists(login_path):
            print 'Directory for %s did not exist, creating...' % self.login
            os.mkdir(login_path)

        full_base_path = os.path.join(base, self.login, self.dir_name)
        if not os.path.exists(full_base_path):
            os.mkdir(full_base_path)

        submissions = list(os.walk(full_base_path))[0][1]
        if not submissions:
            fold_name = '1-submission'
        else:
            last_sub = 0
            for submission in submissions:
                try:
                    sub_numb = int(submission.split('-')[0])
                    if sub_numb > last_sub:
                        last_sub = sub_numb
                except:
                    e = 'Student %s directory contains invalid directory %s'
                    print e % (self.login, submission)
                    continue

            fold_name = '%s-submission' % str(last_sub + 1)

        # if submitted more than a minute late
        # just say "late" in email, dont mark late
        if self.sub_time > self.due + datetime.timedelta(0, 60):
            self.email_late = True
        else:
            self.email_late = False
        # if submitted more than 5 minutes after deadline...
        if self.sub_time > self.due + datetime.timedelta(0, 5*60):
            fold_name += '-late'
            self.actual_late = True
        else:
            self.actual_late = False

        self.full_path = os.path.join(full_base_path, fold_name)
        os.mkdir(self.full_path)

    def download_files(self):
        for q in self.qs:
            q.download(self.full_path, self.login)

    def get_zip(self):
        zipf = zipfile.ZipFile('submission.zip', 'w') # /course/cs0111/hta/tmpzips
        for q in self.qs:
            if q.completed:
                zipf.write(q.file_path, arcname=q.fname)

        zipf.close()
        return zipf.filename

def fetch_submissions():
    yag = yagmail.SMTP(data['email_from'])
    ss_id = data['sheet_id']
    rng = '%s!%s%s:%s' % (data['sheet_name'], data['start_col'],
                          data['start_row'], data['end_col'])
    service = sheets_api()

    spreadsheets = service.spreadsheets().values()
    result = spreadsheets.get(spreadsheetId=ss_id, range=rng).execute()

    vals = result['values']
    responses = []
    for i in range(len(vals)):
        responses.append(Response(vals[i], i))

    confirms = 0
    for response in responses:
        if not response.confirmed:
            confirms += 1
            try:
                response.download()
            except:
                tb = traceback.format_exc()
                content = 'Error in response downloading, student %s row %s\n%s'
                content = content % (response.login, response.ident+2, tb)
                yag.send(to=data['email_errors_to'],
                         subject='SUBMISSION ERROR',
                         contents=content)
                raise
            try:
                response.confirm()
            except:
                tb = traceback.format_exc()
                raise
            try:
                response.add_to_log()
                response.done = True
            except:
                raise

def try_fetch():
    try:
        fetch_submissions()
    except Exception as e:
        tb = traceback.format_exc()
        yag = yagmail.SMTP(data['email_from'])
        yag.send(to=data['email_errors_to'],
                 subject='SUBMISSION ERROR',
                 contents=str(tb) + str(e))

if __name__ == '__main__':
    try_fetch()
