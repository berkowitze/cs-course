import datetime as dt
import io
import json
import os
import subprocess
import sys
import traceback
import yagmail
import zipfile
from apiclient.discovery import build
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapi import sheets_api
from googleapiclient.http import HttpError, MediaIoBaseDownload
from googlefile import GoogleFile
from handin_helpers import make_span
from helpers import BASE_PATH, check_assignments, locked_file, CONFIG

HCONFIG = CONFIG.handin

os.umask(0o007)  # set file permissions

data_file = os.path.join(BASE_PATH, 'ta/assignments.json')
with locked_file(data_file) as f:
    data = json.load(f)

check_assignments(data)

log_path = HCONFIG.log_path
add_sub_path = os.path.join(BASE_PATH, 'hta/grading/add-student-submission')
proj_base = os.path.join(BASE_PATH, 'ta/grading/data/projects')

# minutes after deadline students can submit without penalty
# applies to both extended handins and normal handins
SOFT_CUTOFF = 5

# students can submit up to one day after deadline
# and still be graded
# does not apply to extended handins
HARD_CUTOFF = (19 * 60) + SOFT_CUTOFF

sc = dt.timedelta(0, SOFT_CUTOFF * 60)  # soft cutoff
hc = dt.timedelta(0, HARD_CUTOFF * 60)  # hard cutoff


class Question:
    def __init__(self, question, row):
        self.downloaded: bool = False
        self.q_data: dict = question
        col = self.q_data['col']
        ind = col_str_to_num(col) - 1
        self.link: Optional[str]
        self.link = row[ind] if ind < len(row) and row[ind] != '' else None
        self.completed: bool = (self.link is not None)
        self.fname: str = self.q_data['filename']

    def get_gfile(self):
        # extensions which a snippet can be extracted from
        valid_exts = ['.txt', '.py', '.arr', '.tex', '.java']
        ident = url_to_gid(self.link)  # google file id
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
                print((e % (login, actual_ext, self.fname)))
                with locked_file('filename_error_template.html', 'r') as f:
                    self.warning = f.read().format(exp_ext=expect_ext,
                                                   sub_ext=actual_ext)
            else:
                self.warning = ''

            self.gf.download(fpath)

        self.file_path = fpath
        self.downloaded = True

    def get_snippet(self):
        lines_per_file = 5  # how many lines to print per snippet
        if not self.downloaded:
            e = (
                 f'File {self.fname} must be downloaded before '
                 f'generating snippet'
                 )
            raise ValueError(e)

        if not self.completed:
            return make_span("Not submitted.", "red"), ''
        elif not self.make_snippet:
            first_cell = make_span(f'Submitted.{self.warning}', 'green')
            return first_cell, 'Snippet Unavailable'
        else:
            with locked_file(self.file_path) as dl_f:
                try:
                    lines = dl_f.read().strip().split('\n')
                except UnicodeDecodeError:
                    return 'Submitted', 'Snippet Unavailable'
                if lines == [] or lines == ['']:
                    first_cell = make_span(f'Empty file.{self.warning}',
                                           'orange')
                    return first_cell, ''

                if len(lines) > lines_per_file:
                    snippet = lines[0:lines_per_file]
                    snippet.append('...')
                elif len(lines) == lines_per_file:
                    snippet = lines
                else:
                    snippet = lines[0:len(lines)]

            snippet = '<br>'.join(line.strip() for line in snippet)
            first_cell = make_span(f'Submitted.{self.warning}', 'green')
            return first_cell


class Response:
    def __init__(self, row, ident):
        # submission time
        self.sub_time = datetime.strptime(row[0], '%m/%d/%Y %H:%M:%S')
        self.sub_timestr = self.sub_time.strftime('%m/%d/%y %I:%M:%S%p')
        # submission email (must be Brown account)
        self.email = row[col_str_to_num(HCONFIG.student_email_col) - 1]
        # submission login
        self.login = email_to_login(self.email)

        self.asgn_name = row[col_str_to_num(HCONFIG.assignment_name_col) - 1]
        self.dir_name = self.asgn_name.replace(' ', '').lower()
        self.ident = ident
        self.row = row
        self.confirmed = self.ident in confirmed_responses(log_path)
        self.asgn = data['assignments'][self.asgn_name]
        if not self.confirmed and self.asgn['partner_data'] is not None:
            self.set_partner_data(row)

        self.due = datetime.strptime(self.asgn['due'], '%m/%d/%Y %I:%M%p')

    def set_partner_data(self, row):
        ''' given a row, sets project partner data for this student
        (puts into project_name.json file) '''
        if self.asgn['partner_data'] is None:
            e = 'Cannot call set_partner_data on non-partner-data assignment'
            raise ValueError(e)

        rndx = col_str_to_num(self.asgn['partner_data'])
        partner_data = row[rndx - 1].split(', ')
        if self.login not in partner_data:
            partner_data.append(self.login)

        proj_path = os.path.join(proj_base, self.asgn['group_dir'] + '.json')
        if not os.path.exists(proj_path):
            with locked_file(proj_path, 'w') as f:
                json.dump([], f, indent=2, sort_keys=True)

        with locked_file(proj_path) as f:
            groups = json.load(f)

        # checking this is a valid group
        in_file = False
        for group in groups:
            if set(group) == set(partner_data):
                in_file = True
                continue

            for student in partner_data:
                if student in group:
                    e = f'Student {student} signed up for multiple groups.'
                    e += ' Needs fixing (in /ta/grading/data/projects)'
                    print(e)

        if len(partner_data) != 2:
            print(f'Group {partner_data} with != 2 members')

        if not in_file:
            groups.append(partner_data)
            with locked_file(proj_path, 'w') as f:
                json.dump(groups, f, indent=2, sort_keys=True)

    def set_status(self):
        ''' set status attributes of instance:
               - self.email_late : should confirmation email
                        say the submission was late
               - self.gradeable  : should the handin be graded
                        (will send rejection email, not be downloaded)
               - self.actual_late : will the assignment be deducted
                        for being submitted late
               - self.ext_applied : was an extension applied to the
                        handin
        '''
        # if submitted more than a minute late
        # just say "late" in email, dont mark late
        if self.sub_time > self.due + dt.timedelta(0, 60):
            email_late = True
        else:
            email_late = False

        gradeable = True
        ext_applied = False
        if self.sub_time > self.due + sc:
            # ^ submitted after soft cutoff
            ext = self.load_ext()
            if ext and (self.sub_time < (ext.date + sc)):
                # ^has extension and submitted before ext. deadline
                ext_applied = True
                actual_late = False
            elif self.sub_time > self.due + hc:
                # ^submitted after hard cutoff, no ext
                gradeable = False
                actual_late = True
            else:
                # ^submitted between hard and soft cutoffs, no ext
                actual_late = True
        else:
            # not late
            actual_late = False

        self.email_late = email_late
        self.gradeable = gradeable
        self.actual_late = actual_late
        self.ext_applied = ext_applied

    def load_ext(self):  # TODO : remove
        exts = load_extensions()

        def relevant_ext(e):
            return e.student == self.login and e.asgn == self.dir_name

        s_a_exts = list(filter(relevant_ext, exts))
        if s_a_exts:
            # get furthest-reaching extension
            return max(s_a_exts, key=lambda e: e.date)
        else:
            return None

    def download(self):
        if self.confirmed:
            raise ValueError('Response already downloaded & confirmed.')

        self.qs = []
        for i in range(len(self.asgn['questions'])):
            question = Question(self.asgn['questions'][i], self.row)
            question.get_gfile()
            self.qs.append(question)

        self.set_status()
        if self.gradeable:
            self.create_directory()
            self.gfiles = [q.gf for q in self.qs]
            self.download_files()
            self.downloaded = True

    def confirm(self):
        with locked_file('confirmation_template.html') as f:
            html = f.read().strip()

        row_template = ('<tr><td>{cell_1}</td>'
                        '<td>{cell_2}</td>'
                        '<td><pre>{cell_3}</pre></td></tr>')
        table = ''
        for q in self.qs:
            row = row_template
            a, b = q.get_snippet()
            table += row.format(cell_1=q.fname, cell_2=a, cell_3=b)

        if self.email_late and not self.ext_applied:
            msg = (f'<p>{make_span("Note: Submission was late.", "red")} '
                   f'If you have an extension and are seeing this, '
                   f'email the HTAs.</p>')
        elif self.email_late and self.ext_applied:
            msg = make_span('Note: Extension Applied', 'green')
        else:
            msg = ''
        html = html.format(name=self.login,
                           sub_time=self.sub_timestr,
                           msg=msg,
                           asgn_name=self.asgn_name,
                           tab_conts=table)

        yag = yagmail.SMTP(CONFIG.email_from)
        subject = f'Confirmation of {self.asgn_name} submission'
        if self.email_late:
            subject += ' (late)'

        zip_path = self.get_zip()
        if self.asgn['grading_started']:
            subprocess.check_output([add_sub_path, self.asgn_name, self.login])
            c = 'Student %s submitted %s after grading had started.\nTo grade,'
            c += ' run cs111-grade and extract the handin. Let an HTA know when'
            c += ' you are done so the report can be sent.'
            c = c % (self.login, self.asgn_name)
            yag.send(to=CONFIG.hta_email,
                     subject='Submission after grading started',
                     contents=f'<pre>{c}</pre>')

        to = CONFIG.test_mode_emails_to if CONFIG.test_mode else self.email
        yag.send(to=to,
                 subject=subject,
                 contents=[html, zip_path])
        os.remove(zip_path)

    def reject(self):
        with locked_file('reject_template.html') as f:
            html = f.read().strip()

        html = html.format(name=self.login,
                           sub_time=self.sub_timestr,
                           asgn_name=self.asgn_name)
        yag = yagmail.SMTP(CONFIG.email_from)
        subject = f'Rejection of {self.asgn_name} submission'
        to = CONFIG.test_mode_emails_to if CONFIG.test_mode else self.email
        yag.send(to=to, subject=subject, contents=[html])

    def add_to_log(self):
        with locked_file(log_path, 'a') as f:
            f.write(f'{self.ident}\n')

    def create_directory(self):
        # todo: use get_latest_sub_path from grading helpers
        base = HCONFIG.handin_path
        login_path = os.path.join(base, self.login)
        if not os.path.exists(login_path):
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
                except ValueError:
                    print(
                          f'Student {self.login} directory contains '
                          f'invalid directory {submission}'
                         )
                    continue

            fold_name = '%s-submission' % str(last_sub + 1)

        self.full_path = os.path.join(full_base_path, fold_name)
        if self.actual_late:
            self.full_path += '-late'

        if self.gradeable:
            os.mkdir(self.full_path)

    def download_files(self):
        for q in self.qs:
            q.download(self.full_path, self.login)

    def get_zip(self):
        # /course/cs0111/hta/tmpzips TODO
        zipf = zipfile.ZipFile('submission.zip', 'w')
        for q in self.qs:
            if q.completed:
                zipf.write(q.file_path, arcname=q.fname)

        zipf.close()
        return zipf.filename

    def __repr__(self):
        return f'Response(asgn={self.asgn_name}, email={self.email})'


def fetch_submissions():
    yag = yagmail.SMTP(CONFIG.email_from)
    ss_id = HCONFIG.spreadsheet_id
    rng = HCONFIG.get_range()

    service = sheets_api()
    spreadsheets = service.spreadsheets().values()
    result = spreadsheets.get(spreadsheetId=ss_id, range=rng).execute()

    try:
        vals = result['values']
    except KeyError as e:
        raise ValueError('Handin spreadsheet is empty') from e
    responses = []
    for i in range(len(vals)):
        try:
            responses.append(Response(vals[i], i))
        except ValueError as e:
            if 'not found' in str(e):
                responses.append(None)
            else:
                raise

    for response in responses:
        if response is not None and not response.confirmed:
            response.download()

            if response.gradeable:
                response.confirm()
            else:
                response.reject()

            response.add_to_log()
            response.done = True

    return responses


def try_fetch():
    try:
        fetch_submissions()
        success = True
    except HttpError as e:
        tb = str(traceback.format_exc())
        estr = str(e)
        cstr = str(e.content)
        success = False
    except Exception as e:
        tb = str(traceback.format_exc())
        estr = str(e)
        cstr = ''
        success = False

    if not success:
        yag = yagmail.SMTP(CONFIG.email_from)
        yag.send(to=CONFIG.email_errors_to,
                 subject='SUBMISSION ERROR',
                 contents='<pre>%s\n%s\n%s</pre>' % (tb, estr, cstr))
        sys.exit(1)


if __name__ == '__main__':
    try_fetch()
