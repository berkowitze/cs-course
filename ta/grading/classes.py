# written by Eli Berkowitz (eberkowi) 2018
import json
import csv
import os
import random
import grp
import shutil
import sys
import subprocess
from textwrap import wrap, fill
from typing import List, Tuple, Callable, Optional, Any, Union, Dict, NewType
from datetime import datetime as dt
from helpers import locked_file, require_resource, bracket_check, rubric_check
from custom_types import Rubric, RubricCategory, RubricItem, \
                         RubricOption, Comments

# TODO : improve rubric format so this is more specific
Rubric = NewType('Rubric', dict)

## READ BEFORE EDITING THIS FILE ##
# do not use the builtin `open` function; instead use the
# locked_file function (or the require_resource function)
# see the bottom of /ta/grading/helpers.py for an explanation
# of what these functions are; you should be able to safely use:
# with locked_file(filename, mode) as f:
#     ...
current_time = dt.now()
BASE_PATH = '/course/cs0111'
DATA_PATH = os.path.join(BASE_PATH, 'ta', 'grading', 'data')
GLOB_COMMENTS     = os.path.join(DATA_PATH, 'global-comments.json')
proj_base_path    = os.path.join(DATA_PATH, 'projects')
asgn_data_path    = os.path.join(BASE_PATH, 'ta', 'assignments.json')
ta_path           = os.path.join(BASE_PATH, 'ta/groups', 'tas.txt')
hta_path          = os.path.join(BASE_PATH, 'ta/groups', 'htas.txt')
student_path      = os.path.join(BASE_PATH, 'ta/groups', 'students.txt')
log_base_path     = os.path.join(DATA_PATH, 'logs')
test_base_path    = os.path.join(DATA_PATH, 'tests')
rubric_base_path  = os.path.join(DATA_PATH, 'rubrics')
grade_base_path   = os.path.join(DATA_PATH, 'grades')
s_files_base_path = os.path.join(DATA_PATH, 'sfiles')
anon_base_path    = os.path.join(DATA_PATH, 'anonymization')
blocklist_path    = os.path.join(DATA_PATH, 'blocklists')
if not os.path.exists(asgn_data_path):
    raise OSError('No data file "{asgn_data_path}"')

with locked_file(asgn_data_path) as f:
    data = json.load(f)

def insert_global_comments(write_to: str) -> None:
    with locked_file(write_to) as f:
        to = json.load(f)

    with locked_file(GLOB_COMMENTS) as f:
        library = json.load(f)

    for key in library:
        if key in to:
            for comment in library[key]:
                to[key]['comments'].append({'comment': comment, 'value': False})
    
    with locked_file(write_to, 'w') as f:
        json.dump(to, f, indent=2, sort_keys=True)

# function that checks if an assignment has been started
# f is the function the wrapper will be wrapped around
def is_started(f: Callable) -> Callable:
    ''' decorator to ensure grading has started before calling methods
        to prevent weird errors/behavior
        anything with this decorator has no docstring, so you will
        need to read the source code in classes.py '''
    def magic(*args, **kwargs):
        ''' use local scope to get access to self '''
        asgn = args[0]
        if not asgn.started:
            e = (
                 f'attempting to call method on unstarted '
                 f'assignment {asgn.full_name}'
                )
            raise Exception(e)
        else:
            ''' run as normal if grading has started '''
            is_started.__doc__ = f.__doc__
            return f(*args, **kwargs)

    return magic


class User(object):
    def __init__(self, uname: str) -> None:
        ''' given a username, make a user instance.
        be careful about using this for authentication, as it is hard
        to be confident about the origin of uname within a python script. 
        the .ta and .hta attributes should only be used for browser
        rendering; routes that require ta/hta permission should use a
        hashed password authentication and session cookies '''
        self.uname = uname
        with locked_file(ta_path) as t, locked_file(hta_path) as h:
            tas = t.read().strip().split('\n')
            htas = h.read().strip().split('\n')

        self.ta  = self.uname in tas
        self.hta = self.uname in htas

    def __repr__(self) -> str:
        if self.hta and self.ta:
            f = 'HTA-and-TA'
        elif self.hta:
            f = 'HTA'
        elif self.ta:
            f = 'TA'
        else:
            f = 'No-Permission-User'

        return f'<{f}({self.uname})>'


class Assignment:
    '''
    Assignment class
    Provides interface with logs, grades, and rubrics, files, etc.
    Takes in a key like "Homework 4" which must match a key in the
    /course/course/ta/assignments.json file.
    '''
    def __init__(self, key: str) -> None:
        # ex "Homework 2"
        self.full_name = key

        # ex "homework2"; lowercase, no spaces; used for folders files etc
        self.mini_name = key.strip().lower().replace(' ', '')

        # gives due date, questions, expected filenames, etc.
        try:
            self.json = data['assignments'][self.full_name]
        except KeyError:
            base = f'No assignment key "{self.full_name}" in assignments.json'
            raise KeyError(base)

        self.due_date = dt.strptime(self.json['due'], '%m/%d/%Y %I:%M%p')
        self.due = self.due_date < current_time # may be unnecessary
        try:
            self.started = self.json['grading_started']
        except KeyError:
            raise KeyError(f'{self.full_name} should have grading_started key')
        
        try:
            self.group_asgn = self.json['group_asgn']
        except KeyError:
            raise KeyError(f'{self.full_name} should have group_asgn key')

        if self.group_asgn:
            group_dir = self.json['group_dir']
            self.proj_dir = os.path.join(proj_base_path, group_dir + '.json')
        try:
            self.anonymous = self.json['anonymous']
            jpath = f'{self.mini_name}.json'
            self.anon_path = os.path.join(anon_base_path, jpath)
        except KeyError:
            raise KeyError(f'{self.full_name} should have anonymous key')

        # directory with all grading logs
        self.log_path = os.path.join(log_base_path, self.mini_name)

        # directory with all rubrics
        self.rubric_path = os.path.join(rubric_base_path, self.mini_name)

        # directory where grades are stored (raw rubrics)
        self.grade_path = os.path.join(grade_base_path, self.mini_name)
        
        # directory where all student files are stored
        self.s_files_path = os.path.join(s_files_base_path, self.mini_name)

        # directory where tests are stored
        self.test_path = os.path.join(test_base_path, self.mini_name)
        
        # file with blocklist mapping
        self.blocklist_path = os.path.join(blocklist_path,
                                           f'{self.mini_name}.json')

        # do not load questions, just return skeleton assignment
        if not self.started: 
            return None
        
        # started assignments must have certain paths
        key = f'"{key}"'
        assert os.path.exists(self.log_path), \
            f'started assignment {key} with no log directory'

        assert os.path.exists(self.rubric_path), \
            f'started assignment {key} with no rubric directory'

        assert os.path.exists(self.grade_path), \
            f'started assignment {key} with no grade directory'

        assert os.path.exists(self.blocklist_path), \
            f'started assignment {key} with no blocklist file'

        assert os.path.exists(self.s_files_path), \
            f'started assignment {key} with no student code directory'

        self.load_questions()  # TODO : make this only happen if desired

    def check_rubric(self) -> bool:
        passed, msg = rubric_check(self.rubric_path)
        if not passed:
            print(f'{self.mini_name} has invalid rubric:\n\t{msg}')
            return False
        else:
            return True

    @is_started
    def load_questions(self) -> None:
        ''' load all log files, creating Question instances stored into
            self.questions '''
        questions = []
        for qnumb, q in enumerate(self.json['questions']):
            question = Question(self, qnumb)
            question.load_handins()
            questions.append(question)

        self.questions = questions

    @is_started
    def get_question(self, ndx: int) -> Question:
        ''' get a question by index, won't work if grading isn't started '''
        return self.questions[ndx]
    
    @is_started
    def login_to_id(self, login: str) -> int:
        # TODO : make this faster (use cached file). it's used a lot.
        if self.anonymous:
            raise ValueError('Cannot get login on anonymous assignment')

        with locked_file(self.anon_path) as f:
            data = json.load(f)

        try:
            return data[login]
        except KeyError:
            raise ValueError(f'login {login} does not exist in map for {self}')
    
    @is_started
    def id_to_login(self, ident: int) -> str:
        # TODO : make this faster (use cached file). it's used a lot.
        if self.anonymous:
            raise ValueError('Cannot get login on anonymous assignment')
        
        with locked_file(self.anon_path) as f:
            data = json.load(f)

        for k in data:
            if data[k] == ident:
                return str(k)

        raise ValueError(f'id {ident} does not exist in map for {self}')

    def __repr__(self) -> str:
        ''' representation of instance (i.e. for printing) '''
        return f'Assignment(name="{self.full_name}")'

class Question:
    def __init__(self, parent_assignment: Assignment, q_ndx: int) -> None:
        ''' makes a Question instance; must be given an Assignment
        instance and a question index (zero-indexed)
        Question(Assignment("Homework 4"), 0)
        '''
        # input type checking
        if not isinstance(parent_assignment, Assignment):
            raise TypeError('Question must be instantiated with an Assignment')

        if not isinstance(q_ndx, int):
            e = 'Question must be instantiated with a problem index (integer)'
            raise TypeError(e)

        try:
            cdata = parent_assignment.json['questions'][q_ndx]
        except IndexError: # no question with this index on this assignment
            base = (
                    f'{parent_assignment} does not have problem '
                    f'indexed {q_ndx}'
                   )
            raise ValueError(base)

        else:  # this is a valid question, so continue
            self.json = cdata

        self.assignment = parent_assignment
        self.qnumb = qn = q_ndx + 1
        
        self.grade_path = os.path.join(parent_assignment.grade_path, f'q{qn}')
        self.rubric_filepath = os.path.join(parent_assignment.rubric_path,
                                            f'q{qn}.json')
        self.log_filepath = os.path.join(parent_assignment.log_path,
                                         f'q{qn}.json')

        self.code_filename = self.json['filename']
        test_filename = f'q{qn}.{self.json["text-ext"]}'
        self.test_path = os.path.join(parent_assignment.test_path,
                                      test_filename)

    @require_resource('/course/cs0111/handin-loading-lock.lock')
    def load_handins(self) -> None:
        ''' set self.handins based on the questions' log file '''
        with locked_file(self.log_filepath) as f:
            data = json.load(f)
        
        handins = []
        for raw_handin in data:
            handins.append(Handin(self, raw_handin.pop('id'), **raw_handin))

        self.handins = handins
        self.handin_count = len(self.handins)

        # now set some boolean attributes
        def has_incomplete() -> bool:
            for handin in self.handins:
                if not handin.complete:
                    return True

            return False

        def has_flagged() -> bool:
            for handin in self.handins:
                if handin.flagged:
                    return True

            return False

        self.grading_started = self.assignment.started
        self.has_incomplete = has_incomplete()
        self.has_flagged = has_flagged()

        # how many handins for this question have been completed
        self.completed_count = len([x for x in self.handins if x.complete])
        self.flagged_count = len([x for x in self.handins if x.flagged])

    def ta_handins(self, user: User) -> List[Handin]:
        ''' return all handins for the given user (User class) '''
        if not isinstance(user, User):
            raise TypeError('html_data user must be a User instance')

        return [h for h in self.handins if h.grader == user.uname]

    def html_data(self, user: User) -> Dict[str, Union[List, int, bool]]:
        ''' given a user, return a dictionary with the data that will be used
        to populate that TA's view of already extracted handins to grade '''
        if not isinstance(user, User):
            raise TypeError('html_data user must be a User instance')

        # refresh the handins to make sure outdated information isnt loaded
        # potentially unnecessary but I think it's a good idea just in case
        self.load_handins()
        
        user_handins = self.ta_handins(user) # get this users' handins to grade
        hdata = {
            # only get data for this TA, not for other TA's
            # todo rename these keys
            "handin_data": [h.get_rubric_data() for h in user_handins],
            "handins": len(self.handins),
            "completed": self.completed_count,
            "anonymous": self.assignment.anonymous
        }
        if not self.assignment.anonymous:
            ss = []
            for h in self.handins:
                if not (h.extracted or h.blocklisted_by(user.uname)):
                    ss.append(self.assignment.id_to_login(h.id))

            hdata['students'] = ss

        return hdata

    @require_resource()
    def get_random_handin(self, user: User) -> Optional[Handin]:
        ''' start grading a random handin, or return None if there aren't
        any left to grade '''

        if not isinstance(user, User):
            raise TypeError('html_data user must be a User instance')

        # refresh handins; this is definitely a good thing to do just
        # in case someone else has extracted in the meantime
        self.load_handins()

        ndxs = list(range(len(self.handins)))
        gradeable = [h for h in self.handins if h.gradeable_by(user.uname)]
        if gradeable == []: # no gradeable handins for this TA
            return None
        else:
            # get random handin (so if someone unextracts they won't get
            # the same handin twice in a row)
            handin = random.choice(gradeable)
            handin.start_grading(ta=user.uname)
            return handin

    @require_resource()
    def start_ident_handin(self,
                           anon_id: int,
                           user: User) -> Union[str, Handin]:
        # TODO : Fix this output union to be Optional[Handin]
        self.load_handins()

        handin = self.get_handin_by_sid(anon_id, user)
        if not handin.gradeable_by(user.uname):
            return "student blacklisted"

        if handin.extracted:
            return "already extracted"

        handin.start_grading(ta=user.uname)
        return handin

    def get_handin_by_sid(self, anon_id: int, user: User) -> Handin:
        ''' given a anonymous identity (i.e. 23) and the user, return
        the handin if the user is the grader of that handin or the
        user is an HTA '''
        for handin in self.handins:
            if int(handin.id) == int(anon_id):
                if (user.hta or
                      handin.grader == user.uname or
                      (not self.assignment.anonymous)):
                    return handin
                else:
                    base = (
                            f'Handin on anonymous assignment only viewable '
                            f'by HTA or {handin.grader}'
                           )
                    raise IOError(base)

        raise ValueError(f'No handin with id {anon_id}')

    def add_handin_to_log(self, id: int) -> None:
        ''' add a new handin to the question's log file '''
        # TODO : standardize id param names
        with locked_file(self.log_filepath) as f:
            data = json.load(f)
        
        new_data = {'id': id, 'flag_reason': None,
                    'complete': False, 'grader': None}
        data.append(new_data)
        with locked_file(self.log_filepath, 'w') as f:
            json.dump(data, f, indent=2, sort_keys=True)

        self.load_handins()  # ugh idk concurrency is annoying

    def copy_rubric(self) -> dict:
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
            json.dump(rubric, f, indent=2, sort_keys=True)
    
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
                print(self)
                raise

        with locked_file(self.rubric_filepath, 'w') as f:
            json.dump(rubric, f, indent=2, sort_keys=True)

    def __repr__(self):
        return f'Question(file=[{self.code_filename}])'

class Handin:
    def __init__(self, question, id, complete, grader, flag_reason):
        self.question = question
        self.id       = id
        self.complete = complete
        self.extracted = (grader is not None)
        self.grader   = grader
        self.flagged  = flag_reason is not None
        self.flag_reason = flag_reason

        self.grade_path = os.path.join(question.grade_path,
                                       f'student-{self.id}.json')
        self.handin_path = os.path.join(self.question.assignment.s_files_path,
                                        f'student-{self.id}')
        self.filepath = os.path.join(self.handin_path,
                                     self.question.code_filename)
        if not self.question.assignment.anonymous:
            self.login = self.question.assignment.id_to_login(self.id)

    def raw_data(self):
        ''' read the handin's data from the question's logfile '''
        with locked_file(self.question.log_filepath, 'r') as f:
            data = json.load(f)

        for handin in data:
            if handin['id'] == self.id:
                return handin

    def get_rubric(self) -> Rubric:
        ''' get the rubric for this handin only; must be extracted '''
        if os.path.exists(self.grade_path):
            with locked_file(self.grade_path) as f:
                d = json.load(f)
                return d
        else:
            base = f'Attempting to get rubric of unextracted handin {self}'
            raise ValueError(base)

    def get_rubric_data(self) -> Dict[str, Any]:
        ''' collect information about the student's grade rubric '''
        rdata: Dict[str, Any] = {}
        rdata['functionality'] = 3
        rdata['id'] = self.id
        asgn = self.question.assignment
        if not asgn.anonymous:
            try:
                self.student_name = asgn.id_to_login(self.id)
            except ValueError:
                self.student_name = 'Not found'

            rdata['student-name'] = self.student_name
        else:
            rdata['student-name'] = None

        rdata['flagged'] = self.flagged
        rdata['complete'] = self.complete
        rdata['rubric'] = self.get_rubric()
        rdata['filename'] = self.question.code_filename
        rdata['student-code'] = self.get_code()
        rdata['sfile-link'] = self.handin_path
        return rdata

    def get_code(self) -> str:
        ''' right now, this returns the code as raw text from the
        file the student submitted; this could be updated to be more
        complex (depending on filename, etc.), and would need to be
        updated in /ta/grading/static/main.js to handle those updates '''
        filepath = os.path.join(self.handin_path, self.question.code_filename)
        if not os.path.exists(filepath):
            return (
                    f'No submission (or code issue). '
                    f'Check {self.handin_path} to make sure'
                   )
        elif os.path.splitext(filepath)[1] == '.zip':
            msg = 'Submission is a zip file; open in file viewer'
            return msg
        else:
            # only ever reading this file, no need for lock
            with open(filepath) as f:
                code = f.read()
            
            try:
                json.dumps(code)
            except UnicodeDecodeError:
                code = 'Students code could not be decoded. Look at'
                code += ' original handin & contact an HTA'

            return code


    def write_line(self, **kwargs) -> None:
        ''' update the log file for this handin
        kwargs:
            - grader : login str of the handin grader
            - flag_reason : str explaining why the handin is flagged
            - complete : boolean whether or not handin is complete
        '''
        with locked_file(self.question.log_filepath) as f:
            data = json.load(f)
           
        for handin in data:
            found = False
            if handin['id'] == self.id:
                found = True
                if 'grader' in kwargs:
                    handin['grader'] = kwargs['grader']

                if 'flag_reason' in kwargs:
                    handin['flag_reason'] = kwargs['flag_reason']

                if 'complete' in kwargs:
                    handin['complete'] = kwargs['complete']
                
                break

        if not found:
            raise ValueError('write_line inexistent handin not in log')
        
        with locked_file(self.question.log_filepath, 'w') as f:
            json.dump(data, f, indent=2, sort_keys=True)

    @require_resource('/course/cs0111/ta/question_extract_resource')
    def start_grading(self, ta: str) -> None:
        ''' given a TA username, start grading this handin '''
        assert not self.extracted, 'cannot start grading on extracted handin'
        self.write_line(grader=ta, flag_reason=None, complete=False)
        shutil.copyfile(self.question.rubric_filepath, self.grade_path)
        insert_global_comments(self.grade_path)
        self.grader = ta
        self.extracted = True

    @require_resource()
    def unextract(self) -> None:
        ''' unextract handin; gets rid of grade rubric '''
        self.write_line(grader=None, extracted=False, flag_reason=None)
        os.remove(self.grade_path)
        self.grader = None
        self.extracted = False
        self.complete = False

    def flag(self, msg: str = '') -> None:
        ''' flag a handin with an optional message '''
        if not isinstance(msg, str):
            raise TypeError(f'flag msg must be str, got {msg}')

        self.write_line(flag_reason=msg)
        self.flagged = True

    def unflag(self) -> None:
        ''' unflag handin, reset flag message if there was one '''
        self.write_line(flag_reason=None)
        self.flagged = False

    def set_complete(self) -> None:
        ''' handin grading complete '''
        self.write_line(complete=True)
        self.complete = True

    def write_grade(self, json_data: Rubric) -> None:
        ''' write the grade rubric '''
        with locked_file(self.grade_path, 'w') as f:
            json.dump(json_data, f, indent=2, sort_keys=True)

    def save_data(self, data: dict, new_comments: dict,
                  force_complete: bool = False) -> bool:
        rubric = self.get_rubric()
        def check_rubric_complete() -> bool:
            ''' makes sure there's no empty data cells in the rubric '''
            for key in data:
                if data[key][0] is None or data[key][0] == 'None':
                    return False

            return True

        def update_comments(old_comments: List[dict],
                           new_comment_texts: List[str]) -> None:
            ''' given the original comments (dict list) and a list of new
            comments to add, update the matching old_comments to the "value"
            key be True. (potential break point should be fine tho) '''
            print(old_comments, new_comment_texts)
            for i, comment in enumerate(old_comments):
                if comment['comment'] in new_comment_texts:
                    new_comment_texts.remove(comment['comment'])
                    old_comments[i]['value'] = True
                else:
                    old_comments[i]['value'] = False

            # do i want to add the remaining idk instead of assertionerror
            assert new_comment_texts == [], \
                f'c not empty ({new_comment_texts})'

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

    def add_comment(self, category: str, comment: str) -> None:
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
            json.dump(rubric, f, indent=2, sort_keys=True)

    def gradeable_by(self, uname: str) -> bool:
        ''' is this handin gradeable by input uname (str);
        checks if the student is blocklisted by the TA or if the 
        handin has already been extracted (False if so) '''
        return not (self.blocklisted_by(uname) or self.extracted)

    def blocklisted_by(self, ta: str) -> bool:
        ''' returns True if the student is blocklisted by ta (str) '''
        student_id = self.id
        bl_path = self.question.assignment.blocklist_path
        with locked_file(bl_path) as f:
            data = json.load(f)

        return ta in data and int(self.id) in data[ta]

    def generate_report_str(self, rubric: Optional[Rubric] = None) -> str:
        ''' return a report string for this handin (this question only)
        will format so that no lines are over 74 characters, indentation
        is all pretty, etc. uses rubric if provided, otherwise loads
        the handins' rubric '''
        def get_comments(comments):
            ''' helper that gets the comment text from comments that
            were assigned to this student's handin '''
            return [c['comment'] for c in comments if c['value']]

        if rubric is None:
            rubric = self.get_rubric()

        comments = {}
        for key in rubric:
            if key == '_COMMENTS':
                comments['GENERAL'] = get_comments(rubric['_COMMENTS'])
            else:
                comments[key] = get_comments(rubric[key]['comments'])

        report_str = f'{self.question.code_filename}\n'
        pre_string = '  '  # each problem is nested by pre_string in email
        for key in comments:
            # if GENERAL comments or if there are no comments for that section,
            # do nothing...
            if key == 'GENERAL' or comments[key] == []:
                continue

            report_str += f'{pre_string}{key}:\n'
            # have longest comment at the top
            for comment in sorted(comments[key], key=lambda s: -len(s)):
                comment = comment.replace(f'{key}: ', '')
                comment_lines = fill(comment, 74,
                                     initial_indent=(pre_string * 2 + '- '),
                                     subsequent_indent=(pre_string * 3))
                report_str += f'{comment_lines}\n\n'

        for comment in sorted(comments['GENERAL'], key=lambda s: -len(s)):
            comment_lines = fill(comment, 74,
                                 initial_indent=(pre_string + '- '))
            report_str += f'{comment_lines}\n\n'
        
        report_str += f'Grader: {self.grader} ({self.grader}@cs.brown.edu)'
        report_str += f'\n\n{"-" * 74}\n'
        return report_str

    def generate_grade_report(self) -> Tuple[str, Dict[str, int]]:
        ''' return a report_str (all comments collected and formatted nicely)
        and a dictionary with one key per theme, values being the numeric score
        the student received in that category for this question only 
        NOTE: no grades can below a 0; as such, any negative grades will
        be rounded up to 0'''
        rubric = self.get_rubric()
        report_str = self.generate_report_str(rubric)
        grade = {}
        for key in rubric:
            if key == '_COMMENTS':
                continue

            # set grade for this category
            grade[key] = 0
            for rubric_item in rubric[key]['rubric_items']:
                try:
                    ndx = rubric_item['options'].index(rubric_item['value'])
                except KeyError:
                    print('PROBABLY REPEATED ITEM NAME: LOOKING AT ')
                    print(key)
                    print(rubric_item)
                    print((list(rubric[key].keys())))
                    raise
                except ValueError:
                    raise ValueError('Generating grade from incomplete rubric')
                grade[key] += rubric_item['point-val'][ndx]

        for key in grade:
            if grade[key] < 0:
                grade[key] = 0

        return report_str, grade

    def run_test(self) -> str:
        test_type = self.question.json['test-ext']
        if test_type == 'arr':
            return self.pyret_test()
        elif test_type == 'py':
            return self.python_test()
        else:
            return 'Invalid test extension (contact HTA)'

    def python_test(self) -> str:
        test_filepath = self.question.test_path
        cmd = [os.path.join(BASE_PATH, 'tabin', 'python-test'),
               test_filepath, self.filepath]
        return subprocess.check_output(cmd)
        

    def pyret_test(self) -> str:
        filepath = os.path.join(self.handin_path, self.question.code_filename)
        if not os.path.exists(filepath):
            return 'No handin or missing handin'
        
        test_dir = os.path.join(self.handin_path, 'TA_TESTS')
        if not os.path.exists(test_dir):
            os.mkdir(test_dir)

        if not os.path.exists(self.question.test_path):
            return 'No test file for this question: contact HTA'

        test_filepath = os.path.join(test_dir,
                                     os.path.split(self.question.test_path)[1])
        if not os.path.exists(test_filepath):
            shutil.copyfile(self.question.test_path, test_filepath)

            with locked_file(test_filepath, 'r') as f:
                lines = f.readlines()
                relpath = os.path.relpath(filepath, test_dir)
                lines.insert(0, 'import file("{relpath}") as SC\n')

            with locked_file(test_filepath, 'w') as f:
                f.writelines(lines)
        
        cmd = [os.path.join(BASE_PATH, 'tabin', 'pyret-test'),
               filepath, test_filepath, test_dir]

        return subprocess.check_output(cmd)


    def __repr__(self) -> str:
        if self.question.assignment.anonymous:
            base = (
                    f'Handin(id={self.id}, extracted={self.extracted}, '
                    f'complete={self.complete}'
                   )
        else:
            base = (
                    f'Handin(id={self.id}, login={self.login}, '
                    f'extracted={self.extracted}, complete={self.complete}'
                   )

        if self.extracted:
            base += f', grader={self.grader})'
        else:
            base += ')'

        return base

def started_asgns() -> List[Assignment]:
    assignments: List[Assignment] = []
    for key in data['assignments']:
        asgn = Assignment(key)
        if asgn.started:
            assignments.append(asgn)

    return assignments


