# written by Eli Berkowitz (eberkowi) 2018
import json
import csv
import os
import numpy as np
import random
import shutil
from functools import wraps
from textwrap import wrap, fill
import sys
from filelock import Timeout, FileLock
from contextlib import contextmanager

# do NOT use the builtin open function; instead use the
# LockedFile function defined below.
# https://github.com/benediktschmitt/py-filelock/issues/34

@contextmanager
def LockedFile(filename, mode='r'):
        lock = FileLock(filename + ".lock")
        with lock, open(filename, mode) as f:
            yield f


BASE_PATH = '/course/cs0050'
DATA_PATH = os.path.join(BASE_PATH, 'ta', 'grading', 'data')
asgn_data_path    = os.path.join(BASE_PATH, 'ta', 'assignments.json')
ta_path           = os.path.join(BASE_PATH, 'ta', 'tas.txt')
hta_path          = os.path.join(BASE_PATH, 'ta', 'htas.txt')
log_base_path     = os.path.join(DATA_PATH, 'logs')
rubric_base_path  = os.path.join(DATA_PATH, 'rubrics')
grade_base_path   = os.path.join(DATA_PATH, 'grades')
s_files_base_path = os.path.join(DATA_PATH, 'sfiles')
blocklist_path    = os.path.join(DATA_PATH, 'blocklists')
if not os.path.exists(asgn_data_path):
    raise OSError('No data file "%s"' % asgn_data_path)

with LockedFile(asgn_data_path) as f:
    data = json.load(f)

def started_asgns():
    assignments = []
    for key in data['assignments'].keys():
        asgn = Assignment(key)
        if asgn.started:
            assignments.append(asgn)

    return assignments

# function that checks if an assignment has been started
# f is the function the wrapper will be wrapped around
def is_started(f):
    ''' decorator to ensure grading has started before calling methods
        to prevent weird errors/behavior
        anything with this decorator has no docstring, so you will
        need to read the source code in classes.py '''
    def magic(*args, **kwargs):
        ''' use local scope to get access to self '''
        asgn = args[0]
        if not asgn.started:
            e = 'attempting to call method on unstarted assignment %s'
            raise Exception(e % asgn.full_name)
        else:
            ''' run as normal if grading has started '''
            is_started.__doc__ = f.__doc__  # todo probably can delete
            return f(*args, **kwargs)

    return magic


class User:
    def __init__(self, uname):
        self.uname = uname
        tas = np.loadtxt(ta_path, dtype=str)
        htas = np.loadtxt(hta_path, dtype=str)
        self.ta  = self.uname in tas
        self.hta = self.uname in htas

    def __repr__(self):
        string = '<%s(%s)>'
        if self.hta and self.ta:
            f = 'HTA-and-TA'
        elif self.hta:
            f = 'HTA'
        elif self.ta:
            f = 'TA'
        else:
            f = 'No-Permission-User'

        return string % (f, self.uname)


class Assignment(object):
    '''
    Assignment class
    Provides interface with logs, grades, and rubrics, files, etc.
    Takes in a key like "Homework 4" which must match a key in the
    /course/course/ta/assignments.json file.
    '''
    def __init__(self, key):
        # ex "Homework 2"
        self.full_name = key

        # ex "homework2"; lowercase, no spaces
        self.mini_name = key.strip().lower().replace(' ', '')

        # gives due date, questions, expected filenames, etc.
        try:
            self.json = data['assignments'][self.full_name]
            self.started = self.json['grading_started']
        except KeyError:
            base = 'No assignment key "%s" in assignments.json'
            raise KeyError(base % self.full_name)

        # directory with all grading logs
        self.log_path = os.path.join(log_base_path, self.mini_name)

        # directory with all rubrics
        self.rubric_path = os.path.join(rubric_base_path, self.mini_name)

        # directory where grades will be stored
        self.grade_path = os.path.join(grade_base_path, self.mini_name)

        self.s_files_path = os.path.join(s_files_base_path, self.mini_name)

        self.blocklist_path = os.path.join(blocklist_path,
                                           '%s.csv' % self.mini_name)

        if not self.started:
            return

        assert os.path.exists(self.log_path), \
            'started assignment %s with no log directory' % key

        assert os.path.exists(self.rubric_path), \
            'started assignment %s with no rubric directory' % key

        assert os.path.exists(self.grade_path), \
            'started assignment %s with no grade directory' % key

        self.load_questions()

    @is_started
    def load_questions(self):
        ''' load all log files, creating Question instances stored into
            self.questions '''
        questions = []
        for i, q in enumerate(self.json['questions']):
            qlog_path = self.qnumb_to_log_path(i + 1)
            qrub_path = self.qnumb_to_rubric_path(i + 1)
            qgrade_path = self.qnumb_to_grade_path(i + 1)
            question = Question(log_path=qlog_path,
                                rubric_path=qrub_path,
                                grades_path=qgrade_path,
                                parent_asgn=self,
                                filename=q['filename'])
            
            questions.append(question)

        self.questions = questions

    def qnumb_to_log_path(self, qnumb):
        ''' given the question number, get the log path for that question '''
        return os.path.join(self.log_path, 'q%s.csv' % qnumb)
    
    def qnumb_to_rubric_path(self, qnumb):
        ''' given the question number, get the rubric path
            for that question '''
        return os.path.join(self.rubric_path, 'q%s.json' % qnumb)

    def qnumb_to_grade_path(self, qnumb):
        ''' given the question number, get the grade path for that question '''
        return os.path.join(self.grade_path, 'q%s' % qnumb)

    @is_started
    def get_question(self, ndx):
        ''' get a question by index, won't work if grading isn't started '''
        return self.questions[ndx]

    def __repr__(self):
        ''' representation of instance (i.e. for printing) '''
        return 'Assignment(name=%s)' % self.full_name

class Question:
    def __init__(self, log_path, rubric_path,
                 grades_path, parent_asgn, filename):
        self.log_path = log_path
        self.rubric_path = rubric_path
        self.parent = parent_asgn
        self.filename = filename
        self.grade_path = os.path.join(parent_asgn.grade_path, grades_path)
        self.load_handins()
        self.set_status()

    def load_handins(self):
        ''' set self.handins based on the questions' log file '''
        with LockedFile(self.log_path) as f:
            lines = list(csv.reader(f))[1:]

        # if a TA has extracted a homework, grading has started
        # (perhaps slightly arbitrary but easy)
        # yeah improve this TODO
        if lines == []:
            self.grading_started = False
            self.handins = []
            return
        else:
            self.grading_started = True

        # load handins
        handins = []
        for line in lines:
            handin = Handin(line, self)
            handins.append(handin)

        self.handins = handins

    def ta_handins(self, user):
        ''' return all handins for the given user (User class) '''
        return filter(lambda handin: handin.grader == user.uname, self.handins)

    def html_data(self, user):
        user_handins = self.ta_handins(user)
        # refresh the handins to make sure outdated information isnt loaded
        # may be unnecessary, not sure though
        self.load_handins()
        data = {
            "handin_data": map(lambda h: h.get_rubric_data(), user_handins),
            "handins": len(self.handins),
            "completed": self.completed_count
        }
        return data

    def get_random_handin(self, user):
        ''' start grading a random handin '''
        # refresh handins
        self.load_handins()
        # shuffle 'em up in case someone unextracts so they don't get
        # the same person twice, being careful not to mutate self.handins
        temp_handins = self.handins[:] # can i delete this todo
        ndxs = range(len(self.handins))
        random.shuffle(ndxs)
        for ndx in ndxs:
            handin = self.handins[ndx]
            if not handin.extracted and not handin.blocklisted_by(user):
                handin.start_grading(ta=user.uname)
                return handin

        return None

    def get_handin_by_sid(self, sid, user):
        for handin in self.handins:
            if handin.id == sid and handin.grader == user.uname:
                return handin

        raise Exception('No handin with id %s' % sid)

    def add_handin(self, id):
        with LockedFile(self.log_path, 'a') as f:
            f.write('%s\n' % ','.join([str(id), '', '1', '1', '']))

    def copy_rubric(self):
        ''' return the json rubric '''
        with LockedFile(self.rubric_path) as f:
            return json.load(f)

    def rewrite_rubric(self, rubric, override):
        if override.lower() != 'yes':
            raise 'Attempting to rewrite rubric without override.'

        with LockedFile(self.rubric_path, 'w') as f:
            json.dump(rubric, f, indent=2)

    def add_comment(self, category, comment):
        for handin in self.handins:
            if handin.extracted:
                handin.add_comment(category, comment)

        # todo combine this with add_comment method of Handin class
        with LockedFile(self.rubric_path) as f:
            rubric = json.load(f)

        comment_data = {'comment': comment, 'value': False}
        if category == 'General':
            rubric['_COMMENTS'].append(comment_data)
        else:
            rubric[category]['comments'].append(comment_data)

        with LockedFile(self.rubric_path, 'w') as f:
            json.dump(rubric, f, indent=2)

    def set_status(self):
        def has_incomplete():
            for handin in self.handins:
                if not handin.complete:
                    return True

            return False

        def has_flagged():
            for handin in self.handins:
                if handin.flagged:
                    return True

            return False

        self.has_incomplete = has_incomplete()
        self.has_flagged = has_flagged()
        # how many handins for this question have been completed
        self.completed_count = len([x for x in self.handins if x.complete])

    def __repr__(self):
        return 'Question(file=[%s])' % self.filename

class Handin:
    def __init__(self, line, question):
        try:
            self.id = int(line[0])
        except ValueError:
            print 'Invalid ID in log %s' % question.log_path
            raise

        self.question = question
        self.handin_dir = os.path.join(self.question.parent.s_files_path,
                                       'student-%s' % self.id)
        self.line = line
        # status can be:
        # 1 <- either unextracted or in progress
        # 2 <- complete
        try:
            self.complete = int(self.line[2]) == 2
        except ValueError:
            print 'Invalid status in log %s' % question.log_path
            raise

        # flagged can be:
        # 1 <- TA has not flagged handin
        # 2 <- TA has requested help
        try:
            self.flagged = int(self.line[3]) == 2
        except ValueError:
            print 'Invalid flagged in log %s' % question.log_path

        # TA in second column
        self.grader = self.line[1]
        # not extracted if no allocated TA
        self.extracted = (self.grader != '')
        self.grade_path = os.path.join(question.grade_path,
                                       'student-%s.json' % self.id)
        e = 'extracted handin for student %s missing grade file'
        e += ' or incorrectly has grade file'
        assert self.extracted == os.path.exists(self.grade_path), e % self.id

    def get_rubric(self):
        if os.path.exists(self.grade_path):
            with LockedFile(self.grade_path) as f:
                return json.load(f)
        else:
            raise Exception('this is wrong i think')
            return self.question.copy_rubric()

    def get_rubric_data(self):
        data = {}
        data['functionality'] = 3
        data['id'] = self.id
        data['flagged'] = self.flagged
        data['complete'] = self.complete
        data['rubric'] = self.get_rubric()
        data['filename'] = self.question.filename
        data['student-code'] = self.get_code()
        return data

    def get_code(self):
        files = os.listdir(self.handin_dir)
        filepath = os.path.join(self.handin_dir, self.question.filename)
        if not os.path.exists(filepath):
            msg = 'No submission (or code issue). Check %s to make sure'
            return msg % self.handin_dir
        else:
            with LockedFile(filepath) as f:
                code = f.read()

            return code

    def write_line(self, ta=None, status=None, flagged=None, msg=None):
        cline = self.read_line()
        if ta is not None:
            cline[1] = ta
        if status is not None:
            cline[2] = status
        if flagged is not None:
            cline[3] = flagged
        if msg is not None:
            # get rid of commas so reading csv in future isn't messed up 
            # (todo this necessary?)
            cline[4] = msg.replace(',', '_')

        with LockedFile(self.question.log_path) as f:  # TODO fix
            lines = list(csv.reader(f))
            newlines = []
            found = False
            for i, line in enumerate(lines):
                try:
                    if int(line[0]) == self.id:
                        found = True
                        newlines.append(cline)
                    else:
                        newlines.append(line)
                except ValueError:
                    # header row
                    newlines.append(line)
                    continue

            if not found:
                # this is a new handin
                newlines.append(cline)

        with LockedFile(self.question.log_path, 'w') as f:
            writer = csv.writer(f)
            writer.writerows(newlines)

    def start_grading(self, ta, writefile=True):
        self.write_line(ta=ta, status=1, flagged=1, msg='')
        shutil.copyfile(self.question.rubric_path, self.grade_path)
        self.grader = ta
        self.line = self.read_line()
        self.extracted = True

    def unextract(self):
        self.write_line(ta='', status=1, flagged=1, msg='')
        os.remove(self.grade_path)
        self.grader = ''
        self.line = self.read_line()
        self.extracted = False

    def read_line(self):
        with LockedFile(self.question.log_path, 'r') as f:
            for line in csv.reader(f):
                try:
                    if int(line[0]) == self.id:
                        return line
                except ValueError:
                    continue

    def flag(self, msg=''):
        self.write_line(flagged='2', msg=msg)
        self.flagged = True

    def unflag(self, msg=''):
        self.write_line(flagged='1', msg='')
        self.flagged = False

    def complete(self):
        self.write_line(status='2')

    def write_grade(self, json_data):
        with LockedFile(self.grade_path, 'w') as f:
            json.dump(json_data, f, indent=2)

    def save_data(self, data, new_comments, force_complete=False):
        rubric = self.get_rubric()
        def check_data():
            for key in data:
                if data[key][0] is None or data[key][0] == 'None':
                    return False

            return True

        def update_comments(old_comments, new_comment_texts):
            old_names = map(lambda c: c['comment'], old_comments)
            final_comments = []
            for i, comment in enumerate(old_comments):
                if comment['comment'] in new_comment_texts:
                    new_comment_texts.remove(comment['comment'])
                    old_comments[i]['value'] = True
                else:
                    old_comments[i]['value'] = False

            assert new_comment_texts == [], \
                'c not empty (%s)' % new_comment_texts

        update_comments(rubric['_COMMENTS'], new_comments['General'])
        for key in new_comments:
            if key == 'General':
                continue
            else:
                update_comments(rubric[key]['comments'], new_comments[key])

        if force_complete and not check_data():
            return False

        for description in data:
            value = data[description][0]
            category = data[description][1]
            for rubric_item in rubric[category]['rubric_items']:
                if description == rubric_item['name']:
                    rubric_item['value'] = value
                else:
                    continue

        self.write_grade(rubric)
        return True

    def completed(self):
        self.write_line(status='2')

    def blocklisted_by(self, ta_user):
        ta = ta_user.uname
        student_id = self.id
        bl_path = self.question.parent.blocklist_path
        with LockedFile(bl_path) as f:
            lines = list(csv.reader(f))
        
        for line in lines:
            if line[0] == ta and int(line[1]) == student_id:
                return True

        return False

    def add_comment(self, category, comment):
        assert self.extracted, 'cannot add comment to unextracted handin'
        with LockedFile(self.grade_path) as f:
            rubric = json.load(f)

        print 'GP: %s' % self.grade_path

        comment_data = {'comment': comment, 'value': False}
        if category == 'General':
            rubric['_COMMENTS'].append(comment_data)
        else:
            print category, rubric[category]
            rubric[category]['comments'].append(comment_data)
        with LockedFile(self.grade_path, 'w') as f:
            json.dump(rubric, f, indent=2)

    def generate_grade_report(self):
        def get_comments(comments):
            ''' simple helper that gets the comment text from comments that
            were assigned to this student's handin '''
            return map(lambda c: c['comment'],
                       filter(lambda c: c['value'], comments))

        rubric = self.get_rubric()
        grade = {}
        comments = {}
        for key in rubric:
            if key == '_COMMENTS':
                comments['GENERAL'] = get_comments(rubric['_COMMENTS'])
            else:
                comments[key] = get_comments(rubric[key]['comments'])

                # set grade for this category
                grade[key] = 0
                for rubric_item in rubric[key]['rubric_items']:
                    ndx = rubric_item['options'].index(rubric_item['value'])
                    grade[key] += rubric_item['point-val'][ndx]

        report_str = '%s\n' % self.question.filename
        pre_string = '  '  # each problem is nested by pre_string in email
        for key in comments:
            # if GENERAL comments or if there are no comments for that section,
            # do nothing...
            if key == 'GENERAL' or comments[key] == []:
                continue

            report_str += '%s%s:\n' % (pre_string, key)
            # have longest comment at the top
            for comment in sorted(comments[key], key=lambda s: -len(s)):
                comment = comment.replace('%s: ' % key, '')
                comment_lines = fill('%s' % comment, 74,
                                     initial_indent=(pre_string * 2 + '- '),
                                     subsequent_indent=(pre_string * 3))
                report_str += '%s\n\n' % comment_lines

        for comment in comments['GENERAL']:
            comment_lines = fill(comment, 74,
                                 initial_indent=(pre_string + '- '))
            report_str += '%s\n\n' % comment_lines

        report_str += '%s\n' % ('-' * 74)
        return report_str, grade

    def __repr__(self):
        base = 'Handin(id=%s, extracted=%s, completed=%s)'
        return base % (self.id, self.extracted, self.complete)
