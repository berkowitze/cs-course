import datetime as dt
import io
import json
import os
import subprocess
import sys
import traceback
import yagmail
import zipfile
from contextlib import contextmanager
from typing import Optional, List
from datetime import datetime, timedelta

from apiclient.discovery import build
from datetime import datetime
from enum import Enum, auto
from google.oauth2.credentials import Credentials
from googleapi import sheets_api
from googleapiclient.http import HttpError, MediaIoBaseDownload
from googlefile import GoogleFile
from handin_helpers import (Extension, load_extensions, confirmed_responses,
                            make_span, email_to_login, url_to_gid)
from helpers import (BASE_PATH, CONFIG, check_assignments,
                     locked_file, col_str_to_num)
from hta_helpers import latest_submission_path
from jinja2 import Environment, FileSystemLoader

template_path = os.path.join(BASE_PATH, 'hta/handin')
jinja_env = Environment(loader=FileSystemLoader(template_path))
jinja_env.trim_blocks = True
jinja_env.lstrip_blocks = True


class HState(Enum):
    on_time = auto()  # on time
    first_deadline_buffer = auto()  # after first deadline, but in buffer time
    kinda_late = auto()  # between first and second deadline
    kinda_late_buffer = auto()  # after second deadline, but in buffer time
    kinda_late_exp_ext = auto()  # between extension & 2nd + buffer deadline
    late = auto()  # late with no extension
    late_with_ext = auto()  # in any non-on-time period, but with an extension
    late_exp_ext = auto()  # has extension but submitted after it expired


on_time_stats = [HState.on_time, HState.first_deadline_buffer,
                 HState.late_with_ext]
kinda_late_stats = [HState.kinda_late, HState.kinda_late_buffer,
                    HState.kinda_late_exp_ext]
late_stats = [HState.late, HState.late_exp_ext]
HCONFIG = CONFIG.handin
extensions = load_extensions()

os.umask(0o007)  # set file permissions

data_file = os.path.join(BASE_PATH, 'ta/assignments.json')
with locked_file(data_file) as f:
    data = json.load(f)

check_assignments(data)

log_path = HCONFIG.get_sub_log(CONFIG.test_mode)
add_sub_path = os.path.join(BASE_PATH, 'hta/grading/add-student-submission')
proj_base = os.path.join(BASE_PATH, 'ta/grading/data/projects')


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
            return first_cell, snippet


class Response:
    def __init__(self, row: List[str], ident: int) -> None:
        self.confirmed = ident in confirmed_responses(log_path)
        if self.confirmed:
            return

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
        self.asgn = data['assignments'][self.asgn_name]

        dt_fmt = '%m/%d/%Y %I:%M%p'
        self.due = datetime.strptime(self.asgn['due'], dt_fmt)
        self.late_due = datetime.strptime(self.asgn['late_due'], dt_fmt)

    def get_status(self) -> HState:
        sub_time = self.sub_time
        due = self.due
        late_due = self.late_due
        late_buffer = timedelta(minutes=HCONFIG.handin_late_buffer)

        student_ext = self.load_ext()
        if student_ext is not None and student_ext.date < due:
            #  extension given to pre-deadline time, might as well have no
            #  extension.
            print(f'Useless extension for {self.login}')
            student_ext = None

        if student_ext is None:
            if sub_time <= due:
                return HState.on_time
            elif sub_time <= due + late_buffer:
                if HCONFIG.warn_students_in_buffer:
                    return HState.first_deadline_buffer
                else:
                    return HState.on_time
            elif sub_time <= late_due:
                return HState.kinda_late
            elif sub_time <= late_due + late_buffer:
                if HCONFIG.warn_students_in_buffer:
                    return HState.kinda_late_buffer
                else:
                    return HState.kinda_late
            else:
                return HState.late
        else:
            ext_until = student_ext.date
            if ext_until <= late_due + late_buffer:
                #  didn't get extension until late deadline
                if sub_time <= ext_until + late_buffer:
                    return HState.on_time
                elif sub_time <= late_due + late_buffer:
                    return HState.kinda_late_exp_ext
                else:
                    return HState.late_exp_ext
            else:
                if sub_time <= ext_until + late_buffer:
                    return HState.late_with_ext
                else:
                    return HState.late_exp_ext

    def process(self):
        if self.confirmed:
            raise ValueError('Attempting to process confirmed Response')

        if self.asgn['group_data'] is not None:
            self.__set_partner_data()

        status = self.get_status()

        on_time = (status in on_time_stats)
        kinda_late = (status in kinda_late_stats)
        late = (status in late_stats)

        if kinda_late:
            self.__download(True)
        elif on_time:
            self.__download(False)
        elif late:
            pass  # do not download late submissions

        if status == HState.on_time:
            self.__confirm_email(late=False, warn=False)
        elif status == HState.first_deadline_buffer:
            self.__confirm_email(late=False, warn=True)
        elif status == HState.kinda_late:
            self.__confirm_email(late=True, warn=False)
        elif status == HState.kinda_late_buffer:
            self.__confirm_email(late=True, warn=True)
        elif status == HState.kinda_late_exp_ext:
            self.__confirm_email(late=True, warn=False, ext_expired=True)
        elif status == HState.late_with_ext:
            self.__confirm_email(late=False, warn=False, ext_applied=True)
        elif status == HState.late:
            self.__reject_email(ext_expired=False)
        elif status == HState.late_exp_ext:
            self.__reject_email(ext_expired=True)
        else:
            raise ValueError('Got non HState status')

        self._add_to_log()
        self.confirmed = True

    def __download(self, late: bool) -> None:
        if self.confirmed:
            raise ValueError('Response already confirmed.')

        self.qs: List[Question] = []
        for i in range(len(self.asgn['questions'])):
            question = Question(self.asgn['questions'][i], self.row)
            question.get_gfile()
            self.qs.append(question)

        download_to = self.__create_directory(late)
        self.gfiles = [q.gf for q in self.qs]
        self._download_files(download_to)
        self.downloaded = True

    def __create_directory(self, late: bool) -> str:
        base = HCONFIG.handin_path
        last_sub = latest_submission_path(base, self.login, self.dir_name)
        full_base = os.path.join(base, self.login, self.dir_name)
        if last_sub is None:
            os.makedirs(full_base, exist_ok=True)
            fold_name = '1-submission'
        else:
            last_numb = int(os.path.split(last_sub)[1].split('-')[0])
            sub_numb = last_numb + 1
            fold_name = f'{sub_numb}-submission'

        full_path = os.path.join(full_base, fold_name)
        if late:
            full_path += '-late'

        os.mkdir(full_path)

        return full_path

    def _download_files(self, download_to: str) -> None:
        for q in self.qs:
            q.download(download_to, self.login)

    def __confirm_email(self, *, late: bool, warn: bool,
                        ext_applied: bool = False, ext_expired: bool = False
                        ) -> None:
        assert not (ext_applied and ext_expired), \
            f'called __confirm_email with invalid extension {self.login}'

        template = jinja_env.get_template('confirmation_template.html')

        msgs = []
        if late:
            late_msg = 'Submission is late. Deduction will be applied.'
            msgs.append(make_span(late_msg, 'red'))

        if warn and not late:
            warn_msg = 'Submission is late.'
            msgs.append(make_span(warn_msg, 'orange'))

        if warn and late:
            late_warn = ('Submission is past late deadline, but '
                         'is close enough to still be graded.'
                         )
            msgs.append(make_span(warn_msg, 'orange'))

        if ext_applied:
            ext = self.load_ext()
            assert ext is not None, 'applying extension when extension is None'
            ext_msg = (
                       f'Extension applied. You have until '
                       f'{ext.date} to resubmit.'
                       )
            msgs.append(make_span(ext_msg, 'green'))

        if ext_expired:
            msgs.append(make_span('Submission after extension', 'orange'))

        content = template.render(qs=self.qs,
                                  name=self.login,
                                  asgn_name=self.asgn_name,
                                  msgs=msgs)

        yag = yagmail.SMTP(CONFIG.email_from)
        subject = f'Confirmation of {self.asgn_name} submission'
        if late:
            subject += ' (late)'

        if self.asgn['grading_started']:
            subprocess.check_output([add_sub_path, self.asgn_name, self.login])
            c = (
                 f'Student {self.login} submitted {self.asgn_name!r} after '
                 f'grading had started.\nTo grade,'
                 f'run cs111-grade and extract the handin. Let an HTA know '
                 f'when you are done so the report can be sent.'
                 )
            yag.send(to=CONFIG.hta_email,
                     subject='Submission after grading started',
                     contents=f'<pre>{c}</pre>')

        to = CONFIG.test_mode_emails_to if CONFIG.test_mode else self.email
        print(f"CONFIRM: SENDING EMAIL TO {to}")
        with self.get_zip() as zip_path:
            pass
            # yag.send(to=to,
            #          subject=subject,
            #          contents=[html, zip_path])

    def __reject_email(self, *, ext_expired: bool):
        template = jinja_env.get_template('reject_template.html')
        content = template.render(name=self.login,
                                  sub_time=self.sub_timestr,
                                  asgn_name=self.asgn_name)
        yag = yagmail.SMTP(CONFIG.email_from)
        subject = f'Rejection of {self.asgn_name} submission'
        to = CONFIG.test_mode_emails_to if CONFIG.test_mode else self.email
        print(f'REJECT: SENDING EMAIL TO {to}')
        # yag.send(to=to, subject=subject, contents=[html])

    def load_ext(self) -> Optional[Extension]:  # TODO : remove [why?]
        def relevant(e):
            return e.student == self.login and e.asgn == self.dir_name

        s_a_exts = [ext for ext in extensions if relevant(ext)]
        if s_a_exts:
            # get furthest-reaching extension
            return max(s_a_exts, key=lambda e: e.date)
        else:
            return None

    def __set_partner_data(self):
        ''' sets project partner data for this student
        (puts into project_name.json file) '''
        gdata = self.asgn['group_data']
        if gdata is None or gdata['partner_col'] is None:
            raise ValueError('Cannot call set_partner_data on assignment '
                             'with no partner column')

        rndx = col_str_to_num(gdata['partner_col'])
        partner_data = set(self.row[rndx - 1].split(', '))
        partner_data.add(self.login)

        proj_path = os.path.join(proj_base, f'{gdata["multi_part_name"]}.json')
        if not os.path.exists(proj_path):
            with locked_file(proj_path, 'w') as f:
                json.dump([], f, indent=2, sort_keys=True)

        with locked_file(proj_path) as f:
            groups = json.load(f)

        # checking this is a valid group
        in_file = False
        for group in groups:
            if set(group) == partner_data:
                # this group has already submitted something
                in_file = True
                # but keep checking to make sure no students in this group are
                # in another group
                continue

            for student in partner_data:
                if student in group:
                    e = f'Student {student} signed up for multiple groups.'
                    e += ' Needs fixing (in /ta/grading/data/projects)'
                    print(e)

        if len(partner_data) != 2:
            print(f'Group {partner_data} with != 2 members')

        if not in_file:
            groups.append(list(partner_data))
            with locked_file(proj_path, 'w') as f:
                json.dump(groups, f, indent=2, sort_keys=True)

    def _add_to_log(self) -> None:
        with locked_file(log_path, 'a') as f:
            f.write(f'{self.ident}\n')

    @contextmanager
    def get_zip(self):
        zip_path = os.path.join(BASE_PATH, 'hta/tmpzips/submission.zip')
        zipf = zipfile.ZipFile(zip_path, 'w')
        for q in self.qs:
            if q.completed:
                zipf.write(q.file_path, arcname=q.fname)

        zipf.close()
        try:
            yield zip_path
        finally:
            os.remove(zip_path)

    def __repr__(self):
        return f'Response(asgn={self.asgn_name}, email={self.email})'


def fetch_submissions() -> List[Response]:
    yag = yagmail.SMTP(CONFIG.email_from)

    ss_id = HCONFIG.get_ssid(CONFIG.test_mode)
    rng = HCONFIG.get_range(CONFIG.test_mode)

    service = sheets_api()
    spreadsheets = service.spreadsheets().values()
    result = spreadsheets.get(spreadsheetId=ss_id, range=rng).execute()

    try:
        vals = result['values']
    except KeyError as e:
        raise ValueError('Handin spreadsheet is empty') from e

    responses = []
    for i, row in enumerate(vals):
        resp = Response(row, i)
        if not resp.confirmed:
            responses.append(resp)
            resp.process()

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
    fetch_submissions()
