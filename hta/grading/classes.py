# written by Eli Berkowitz (eberkowi) 2018
import json
import csv
import os
import numpy as np
import random
import shutil
from textwrap import wrap, fill
import sys
from helpers import locked_file, require_resource
from datetime import datetime as dt

## READ BEFORE EDITING THIS FILE ##
# do not use the builtin `open` function; instead use the
# locked_file function (or the require_resource function)
# see the bottom of /ta/grading/helpers.py for an explanation
# of what these functions are; you should be able to safely use:
# with locked_file(filename, mode) as f:
#     ...
current_time = dt.now()
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

with locked_file(asgn_data_path) as f:
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


class User(object):
    def __init__(self, uname):
        ''' given a username, make a user instance.
        be careful about using this for authentication, as it is hard
        to be confident about the origin of uname within a python script. 
        the .ta and .hta attributes should only be used for browser
        rendering; routes that require ta/hta permission should use a
        hashed password authentication and session cookies '''
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
        except KeyError:
            base = 'No assignment key "%s" in assignments.json'
            raise KeyError(base % self.full_name)
        else:
            self.due_date = dt.strptime(self.json['due'], '%m/%d/%Y %I:%M%p')
            self.due = self.due_date < current_time
            self.started = self.json['grading_started']

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
        for qnumb, q in enumerate(self.json['questions']):
            question = Question(self, qnumb)
            question.load_handins()
            questions.append(question)

        self.questions = questions

    @is_started
    def get_question(self, ndx):
        ''' get a question by index, won't work if grading isn't started '''
        return self.questions[ndx]

    def __repr__(self):
        ''' representation of instance (i.e. for printing) '''
        return 'Assignment(name="%s")' % self.full_name

class Question(object):
    def __init__(self, parent_assignment, question_ndx):
        ''' makes a Question instance; must be given an Assignment
        instance and a question index (zero-indexed)
        Question(Assignment("Homework 4"), 0)
        '''

        # input type checking
        if not isinstance(parent_assignment, Assignment):
            raise TypeError('Question must be instantiated with an Assignment')

        if not isinstance(question_ndx, int):
            e = 'Question must be instantiated with a problem index (integer)'
            raise TypeError(e)

        try:
            cdata = parent_assignment.json['questions'][question_ndx]
        except IndexError: # no question with this index on this assignment
            base = '%s does not have problem indexed %s'
            raise ValueError(base % (parent_assignment, question_ndx))
        else: # this is a valid question, so continue
            self.json = cdata

        self.assignment = parent_assignment
        self.qnumb = question_ndx + 1
        
        self.grade_path = os.path.join(parent_assignment.grade_path,
                                       'q%s' % self.qnumb)
        self.rubric_filepath = os.path.join(parent_assignment.rubric_path,
                                            'q%s.json' % self.qnumb)
        self.log_filepath = os.path.join(parent_assignment.log_path,
                                         'q%s.csv' % self.qnumb)
        self.code_filename = self.json['filename']

    def load_handins(self):
        ''' set self.handins based on the questions' log file '''
        with locked_file(self.log_filepath) as f:
            reader = csv.reader(f)

            # reader.next() will get the first line; after next is used, when
            # looping over reader, it will start from the second line
            # look up generators if you need to modify this, or run
            # lines = list(csv.reader(f)) and you will get a full list
            try:
                header = reader.next()
            except StopIteration:
                base = '%s log file has no contents; must have a header'
                raise OSError(base % self.log_filepath)
            else: # no errors loading file, so load handins
                handins = []
                for line in reader:
                    handins.append(Handin(self, line))

            self.handins = handins
            self.handin_count = len(self.handins)

        # now set some boolean attributes
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

        self.grading_started = self.assignment.started
        self.has_incomplete = has_incomplete()
        self.has_flagged = has_flagged()
        # how many handins for this question have been completed
        self.completed_count = len([x for x in self.handins if x.complete])

    def ta_handins(self, user):
        ''' return all handins for the given user (User class) '''
        if not isinstance(user, User):
            raise TypeError('html_data user must be a User instance')

        return filter(lambda handin: handin.grader == user.uname,
                      self.handins)

    def html_data(self, user):
        ''' given a user, return a dictionary with the data that will be used
        to populate that TA's view of handins to grade '''
        if not isinstance(user, User):
            raise TypeError('html_data user must be a User instance')

        # refresh the handins to make sure outdated information isnt loaded
        # potentially unnecessary but I think it's a good idea just in case
        self.load_handins()
        
        user_handins = self.ta_handins(user) # get this users' handins to grade
        hdata = {
            # only get data for this TA, not for other TA's
            # todo rename these keys
            "handin_data": map(lambda h: h.get_rubric_data(), user_handins),
            "handins": len(self.handins),
            "completed": self.completed_count
        }
        return hdata

    @require_resource()
    def get_random_handin(self, user):
        ''' start grading a random handin '''

        if not isinstance(user, User):
            raise TypeError('html_data user must be a User instance')

        # refresh handins; this is definitely a good thing to do just
        # in case someone else has extracted in the meantime
        self.load_handins()

        ndxs = range(len(self.handins))
        gradeable = filter(lambda h: h.gradeable_by(user.uname), self.handins)
        if gradeable == []: # no gradeable handins for this TA
            return None
        else:
            # get random handin (so if someone unextracts they won't get
            # the same handin twice in a row)
            handin = random.choice(gradeable)
            handin.start_grading(ta=user.uname)
            return handin

    def get_handin_by_sid(self, anon_id, user):
        ''' given a anonymous identity (i.e. 23) and the user, return
        the handin if the user is the grader of that handin or the
        user is an HTA '''
        for handin in self.handins:
            if handin.id == anon_id:
                if not (handin.grader == user.uname or user.hta):
                    base = 'Handin only viewable by HTA or %s'
                    raise PermissionError(base % handin.grader)
                else:
                    return handin

        raise ValueError('No handin with id %s' % anon_id)

    def add_handin_to_log(self, id): # can somehow use Handin.write_line?
        ''' add a new handin to the question's log file '''
        with locked_file(self.log_filepath, 'a') as f:
            f.write('%s\n' % ','.join([str(id), '', '1', '1', '']))

        self.load_handins()

    def copy_rubric(self):
        ''' return the json rubric '''
        with locked_file(self.rubric_filepath) as f:
            return json.load(f)

    def rewrite_rubric(self, rubric, override):
        ''' given a new rubric and a second argument which must be the string
        'yes', overwrite the rubric for this assignment. should probably only
        be used by HTA's (TA's edit by hand) but there's no HTA_Question parent
        class (yet) so... '''
        if override.lower() != 'yes':
            raise ValueError('Attempting to rewrite rubric without override.')

        with locked_file(self.rubric_filepath, 'w') as f:
            json.dump(rubric, f, indent=2)
    
    @require_resource() # using this here is definitely important
    def add_comment(self, category, comment):
        ''' add a comment to the rubric AND all extracted students '''
        # if you're getting weird errors, this may be where they're from
        # (I'm relatively confident this method won't be a problem
        # though; do some printing if you think it is). alternative is
        # loading global comments from only the question rubric file and
        # not copying them into the students rubric file, but that's messy
        # for different reasons
        for handin in self.handins:
            if handin.extracted:
                handin.add_comment(category, comment)

        with locked_file(self.rubric_filepath) as f:
            rubric = json.load(f)

        comment_data = {'comment': comment, 'value': False}
        if category == 'General':
            rubric['_COMMENTS'].append(comment_data)
        else:
            try:
                rubric[category]['comments'].append(comment_data)
            except TypeError:
                print self
                raise

        with locked_file(self.rubric_filepath, 'w') as f:
            json.dump(rubric, f, indent=2)

    def __repr__(self):
        return 'Question(file=[%s])' % self.code_filename

class Handin(object):
    def __init__(self, question, line):
        try:
            self.id = int(line[0])
        except ValueError:
            base = '%s has invalid line %s (ID must be integer)'
            raise ValueError(base % (question, line))
        except IndexError:
            base = '%s has invalid line %s (must start with ID)'
            raise ValueError(base % (question, line))

        self.question = question
        self.line = line

        self.grade_path = os.path.join(question.grade_path,
                                       'student-%s.json' % self.id)
        self.handin_path = os.path.join(self.question.assignment.s_files_path,
                                        'student-%s' % self.id)
        self.update_attrs(line)

    def update_attrs(self, line):
        # status can be:
        # 1 <- either unextracted or in progress
        # 2 <- complete
        try:
            self.complete = int(self.line[2]) == 2
        except ValueError:
            raise ValueError('Invalid status in log %s' % question.log_filepath)

        # flagged can be:
        # 1 <- TA has not flagged handin
        # 2 <- TA has requested help
        try:
            self.flagged = int(self.line[3]) == 2
        except ValueError:
            raise('Invalid flag in log %s' % question.log_filepath)

        # TA in second column
        self.grader = self.line[1]
        # not extracted if no allocated TA
        self.extracted = (self.grader != '')

        e = 'extracted handin for student %s missing grade file'
        e += ' or incorrectly has grade file'
        assert self.extracted == os.path.exists(self.grade_path), e % self.id

    def get_rubric(self):
        ''' get the rubric for this handin only; must be extracted '''
        if os.path.exists(self.grade_path):
            with locked_file(self.grade_path) as f:
                return json.load(f)
        else:
            base = 'Attempting to get rubric of unextracted handin %s'
            raise ValueError(base % self)

    def get_rubric_data(self):
        ''' collect information about the student's grade rubric '''
        self.line = self.read_line()
        self.update_attrs(self.line)
        rdata = {}
        rdata['functionality'] = 3
        rdata['id'] = self.id
        rdata['flagged'] = self.flagged
        rdata['complete'] = self.complete
        rdata['rubric'] = self.get_rubric()
        rdata['filename'] = self.question.code_filename
        rdata['student-code'] = self.get_code()
        return rdata

    def get_code(self):
        ''' right now, this returns the code as raw text from the
        file the student submitted; this could be updated to be more
        complex (depending on filename, etc.), and would need to be
        updated in /ta/grading/static/main.js to handle those updates '''
        files = os.listdir(self.handin_path)
        filepath = os.path.join(self.handin_path, self.question.code_filename)
        if not os.path.exists(filepath):
            msg = 'No submission (or code issue). Check %s to make sure'
            return msg % self.handin_path
        else:
            # only ever reading this file, no need for lock
            with open(filepath) as f:
                code = f.read()

            return code

    def read_line(self):
        ''' read the handin's line from the question's logfile '''
        with locked_file(self.question.log_filepath, 'r') as f:
            for line in csv.reader(f):
                try:
                    if int(line[0]) == self.id:
                        return line
                except ValueError:
                    continue

    def write_line(self, ta=None, status=None, flagged=None, msg=None):
        ''' write the handin line to the question's log path. does not
        update anything if ta, status, flagged, or msg kwargs are not
        passed in '''
        cline = self.read_line()
        if ta is not None:
            cline[1] = ta
        if status is not None:
            cline[2] = status
        if flagged is not None:
            cline[3] = flagged
        if msg is not None:
            # get rid of commas so csv in isn't messed up
            cline[4] = msg.replace(',', '_')

        with locked_file(self.question.log_filepath) as f:
            lines = csv.reader(f)
            newlines = [lines.next()] # put header into list
            found = False
            for line in lines:
                if int(line[0]) == self.id:
                    found = True
                    newlines.append(cline)
                else:
                    newlines.append(line)

        if found:
            with locked_file(self.question.log_filepath, 'w') as f:
                writer = csv.writer(f)
                writer.writerows(newlines)
        else: # this is a new handin, so just append the new line
            with locked_file(self.question.log_filepath, 'a') as f:
                writer = csv.writer(f)
                writer.writerow(cline)

    def start_grading(self, ta):
        ''' given a TA username, start grading this handin '''
        self.write_line(ta=ta, status=1, flagged=1, msg='')
        shutil.copyfile(self.question.rubric_filepath, self.grade_path)
        self.grader = ta
        self.line = self.read_line()
        self.extracted = True

    def unextract(self):
        ''' unextract handin; gets rid of grade rubric '''
        self.write_line(ta='', status=1, flagged=1, msg='')
        os.remove(self.grade_path)
        self.grader = ''
        self.line = self.read_line()
        self.extracted = False

    def flag(self, msg=''):
        ''' flag a handin with an optional message '''
        if not isinstance(msg, (str, unicode)):
            raise TypeError('flag msg must be str, got %s' % msg)
        self.write_line(flagged='2', msg=msg)
        self.flagged = True

    def unflag(self):
        ''' unflag handin, reset flag message if there was one '''
        self.write_line(flagged='1', msg='')
        self.flagged = False

    def set_complete(self):
        ''' handin grading complete '''
        self.write_line(status='2')
        self.complete = True

    def write_grade(self, json_data):
        ''' write the grade rubric '''
        with locked_file(self.grade_path, 'w') as f:
            json.dump(json_data, f, indent=2)

    def save_data(self, data, new_comments, force_complete=False):
        rubric = self.get_rubric()
        def check_rubric_complete():
            ''' makes sure there's no empty data cells in the rubric '''
            for key in data:
                if data[key][0] is None or data[key][0] == 'None':
                    return False

            return True

        def update_comments(old_comments, new_comment_texts):
            ''' given the original comments (dict list) and a list of new
            comments to add, update the matching old_comments to the "value"
            key be True. (potential break point should be fine tho) '''
            final_comments = []
            for i, comment in enumerate(old_comments):
                if comment['comment'] in new_comment_texts:
                    new_comment_texts.remove(comment['comment'])
                    old_comments[i]['value'] = True
                else:
                    old_comments[i]['value'] = False

            # do i want to add the remaining idk instead of assertionerror
            assert new_comment_texts == [], \
                'c not empty (%s)' % new_comment_texts 

        # update general comments
        update_comments(rubric['_COMMENTS'], new_comments['General'])
        for key in new_comments:
            if key == 'General':
                continue
            else:
                update_comments(rubric[key]['comments'], new_comments[key])

        if force_complete and not check_rubric_complete():
            # attempting to finish grading but has empty rubric cells
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

    def gradeable_by(self, uname):
        ''' is this handin gradeable by input uname (str);
        checks if the student is blocklisted by the TA or if the 
        handin has already been extracted (False if so) '''
        return not (self.blocklisted_by(uname) or self.extracted)

    def blocklisted_by(self, ta):
        ''' returns True if the student is blocklisted by ta (str) '''
        student_id = self.id
        bl_path = self.question.assignment.blocklist_path
        with locked_file(bl_path) as f:
            lines = csv.reader(f)
        
            for line in lines:
                if line[0] == ta and int(line[1]) == student_id:
                    return True

        return False

    def add_comment(self, category, comment):
        ''' add comment to the handin's json grade rubric, with 
        value of False. must save with the comment in the list of
        comments selected under the dropdown to have the value be True '''
        assert self.extracted, 'cannot add comment to unextracted handin'
        with locked_file(self.grade_path) as f:
            rubric = json.load(f)

        comment_data = {'comment': comment, 'value': False}
        if category == 'General':
            rubric['_COMMENTS'].append(comment_data)
        else:
            rubric[category]['comments'].append(comment_data)
        with locked_file(self.grade_path, 'w') as f:
            json.dump(rubric, f, indent=2)

    def generate_grade_report(self):
        ''' return a report_str (all comments collected and formatted nicely)
        and a dictionary with one key per theme, values being the numeric score
        the student received in that category for this question only '''
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

        report_str = '%s\n' % self.question.code_filename
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
