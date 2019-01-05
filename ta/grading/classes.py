# written by Eli Berkowitz (eberkowi) 2018
# TODO: formalize docstring format

import json
import os
import random
import shutil
import subprocess
from datetime import datetime as dt
from typing import Any, Callable, Dict, List, Optional, Tuple

from course_customization import full_asgn_name_to_dirname, \
    get_handin_report_str
from custom_types import HTMLData, Log, LogItem, Rubric
from helpers import locked_file, require_resource, \
    rubric_check, update_comments

# READ BEFORE EDITING THIS FILE #
# do not use the builtin `open` function; instead use the
# locked_file function (or the require_resource function)
# see the bottom of /ta/grading/helpers.py for an explanation
# of what these functions are; you should be able to safely use:
# with locked_file(filename, mode) as f:
#     ...
current_time = dt.now()
BASE_PATH = '/course/cs0111'
DATA_PATH = os.path.join(BASE_PATH, 'ta', 'grading', 'data')
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
assert os.path.exists(asgn_data_path), 'No data file "{asgn_data_path}"'

with locked_file(asgn_data_path) as f:
    asgn_data = json.load(f)


# function that checks if an assignment has been started
# func is the function the wrapper will be wrapped around
def is_started(func: Callable) -> Callable:
    """decorator to ensure grading has started before calling methods
    to prevent weird errors/behavior
    anything with this decorator has no docstring, so you will
    need to read the source code in classes.py 
    
    Args:
        func (Callable): Function to wrap
    """
    def magic(asgn, *args, **kwargs):
        if not asgn.started:
            e = (
                 f'attempting to call method on unstarted '
                 f'assignment {asgn.full_name}'
                )
            raise Exception(e)
        else:
            """ run as normal if grading has started """
            is_started.__doc__ = f.__doc__
            return func(asgn, *args, **kwargs)

    return magic


class User:

    """User class to give an interface to the user and their permissions
    
    Attributes:
        uname (str): The user's login
        hta (bool): Whether or not the user is an HTA
        ta (bool): Whether or not the user is a TA
    """
    
    def __init__(self, uname: str) -> None:
        """
        
        Args:
            uname (str): CS login of user
        """
        with locked_file(ta_path) as t, locked_file(hta_path) as h:
            tas = t.read().strip().split('\n')
            htas = h.read().strip().split('\n')

        self.uname = uname
        self.ta = uname in tas
        self.hta = uname in htas

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
    """
    Assignment class
    Provides interface with logs, grades, and rubrics, files, etc.
    
    Attributes:
        proj_dir (Optional[str]): If group_asgn is False, None. If group_asgn
            is True, the name of the common directory to use (for
            multi-assignment projects). For example, "project3"
    
    Discouraged Attributes:
        _json (dict): the JSON data for the assignment loaded 
            from assignments.json
    
    Private Attributes:
        __login_to_id_map (Dict[str, int]): a map from login to anonymous ID
            for this assignment
        __id_to_login_map (Dict[int, str]): a map from anonymous ID to login
            for this assignment
    
    Deleted Attributes:
        full_name (str): Full name of assignment (i.e. "Homework 2")
        mini_name (str): Directory name of assignment (i.e. "homework2")
        due_date (datetime): Datetime of the assignment's due date
        due (bool): Whether or not the assignment deadline has passed
        started (bool): Whether or not grading has started for this assignment
        group_asgn (bool): Whether or not the assignment is a group assignment
            (i.e. True for projects)
        anonymous (bool): True if the assignment is being graded anonymously
        log_path (str): Directory path for log files
        rubric_path (str): Directory path for rubric files
        grade_path (str): Directory path for grade files
        files_path (str): Directory path where students' handins will be copied
        test_path (str): JSON path where anonymization information for this
            assignment will be stored.
        blocklist_path (str): JSON parth where blocklist information for this
            assignment will be stored
    """
    def __init__(self, key: str, full_load: bool = False) -> None:
        """Create a new assignment based on the key from /ta/assignments.json
        
        Args:
            key (str): Key of assignment to load (i.e. 'Homework 4')
            full_load (bool, optional): whether or not to fully load the
                assignment and all its Questions
        
        Raises:
            ValueError: You cannot fully load unstarted assignments
        """
        self.full_name: str = key
        self.mini_name: str = full_asgn_name_to_dirname(self.full_name)

        self._json: dict = asgn_data['assignments'][self.full_name]

        self.due_date: dt = dt.strptime(self._json['due'], '%m/%d/%Y %I:%M%p')
        self.due: bool = self.due_date < current_time
        self.started: bool = self._json['grading_started']

        self.group_asgn: bool = self._json['group_asgn']
        self.proj_dir: Optional[str]
        if self.group_asgn:
            group_dir = self._json['group_dir']
            self.proj_dir = os.path.join(proj_base_path, group_dir + '.json')
        else:
            self.proj_dir = None

        self.anonymous: bool = self._json['anonymous']
        self.log_path: str = os.path.join(log_base_path, self.mini_name)
        self.rubric_path: str = os.path.join(rubric_base_path, self.mini_name)
        self.grade_path: str = os.path.join(grade_base_path, self.mini_name)
        self.files_path: str = os.path.join(s_files_base_path, self.mini_name)
        self.test_path: str = os.path.join(test_base_path, self.mini_name)
        self.anon_path: str = os.path.join(anon_base_path,
                                           f'{self.mini_name}.json')
        self.blocklist_path: str = os.path.join(blocklist_path,
                                                f'{self.mini_name}.json')
        self.bracket_path: str = os.path.join(rubric_base_path,
                                              self.mini_name,
                                              'bracket.json')

        if self.started and full_load:
            self.load()
        elif not self.started and full_load:
            e = f'Attempting to fully load unstarted assignment {self}'
            raise ValueError(e)

    @is_started
    def load(self):
        """Loads the assignment (checks all paths are proper and 
        loads all assignment questions)
        """
        # checking that assignment has correct paths
        n = self.full_name
        assert os.path.exists(self.log_path), \
            f'started assignment f"{n}" with no log directory'
        assert os.path.exists(self.rubric_path), \
            f'started assignment f"{n}" with no rubric directory'
        assert os.path.exists(self.grade_path), \
            f'started assignment f"{n}" with no grade directory'
        assert os.path.exists(self.blocklist_path), \
            f'started assignment f"{n}" with no blocklist file'
        assert os.path.exists(self.files_path), \
            f'started assignment f"{n}" with no student code directory'

        if not self.anonymous:
            with locked_file(self.anon_path) as f:
                data: Dict[str, int] = json.load(f)

            self.__login_to_id_map: Dict[str, int] = data
            self.__id_to_login_map: Dict[int, str] = {data[k]: k for k in data}

        self.__load_questions()

    @is_started
    def __load_questions(self) -> None:
        """load all log files, creating Question instances stored into
        self.questions.  
        """
        questions = []
        for qnumb, q in enumerate(self._json['questions']):
            question = Question(self, qnumb)
            questions.append(question)

        self.questions: List[Question] = questions

    def check_rubric(self) -> bool:
        """Checks if assignment's rubric is valid
        
        Returns:
            bool: checks if rubric is valid, using rubric_check helper 
        """
        try:
            rubric_check(self.rubric_path)
        except AssertionError as e:
            print(f'Invalid rubric, with error {e}')
            return False
        else:
            return True

    @is_started
    def get_question(self, ndx: int) -> 'Question':
        """get a question by index (0 indexed) 
        
        Args:
            ndx (int): Index of question (0 index)
        
        Returns:
            Question: Question corresponding to that index
        
        Raises:
            IndexError: No such question
        """
        try:
            return self.questions[ndx]
        except IndexError:
            e = (
                 f'Trying to get qn {ndx} from assignment with '
                 f'{len(self.questions)} qns'
                )
            raise IndexError(e)
    
    @is_started
    def login_to_id(self, login: str) -> int:
        """Get anonymous ID of student by login
        
        Args:
            login (str): Student CS login
        
        Returns:
            int: Anonymous ID for student by login
        
        Raises:
            ValueError: Student has no anonymous ID for this assignment
        """
        if self.anonymous:
            raise ValueError('Cannot get login on anonymous assignment')

        #  first try using cached info
        if login in self.__login_to_id_map:
            return self.__login_to_id_map[login]

        #  next try reloading anonymization information
        with locked_file(self.anon_path) as f:
            data: Dict[str, int] = json.load(f)

        try:
            self.__login_to_id_map[login] = data[login]
            self.__id_to_login_map[data[login]] = login
            return data[login]
        except KeyError:
            #  then fail
            raise ValueError(f'login {login} does not exist in map for {self}')
    
    @is_started
    def id_to_login(self, ident: int) -> str:
        """convert anonymous id to login for this assignment
        
        Args:
            ident (int): Anonymous ID of student to look for
        
        Returns:
            str: CS login of student with ident anon id for this assignment
        
        Raises:
            ValueError: No student with ident anon id for this assignment
        """
        if self.anonymous:
            raise ValueError('Cannot get login on anonymous assignment')

        #  first try using cached info
        if ident in self.__id_to_login_map:
            return self.__id_to_login_map[ident]

        #  next try reloading anonymization information
        with locked_file(self.anon_path) as f:
            data: Dict[str, int] = json.load(f)

        for login in data:
            if data[login] == ident:
                self.__id_to_login_map[ident] = login
                self.__login_to_id_map[login] = ident
                return login

        #  then fail
        raise ValueError(f'id {ident} does not exist in map for {self}')

    def __repr__(self) -> str:
        """ representation of instance (i.e. for printing) """
        return f'Assignment(name="{self.full_name}")'


class Question:

    """Class for questions (Assignments are made up of a list of questions)
    
    Attributes:
        assignment (Assignment): assignment this question is from
        code_filename (str): string of the filename of this question
            (i.e. maze.arr)
        completed_count (int): number of handins graded
        flagged_count (int): number of handins flagged for review
        grade_path (str): path that grades of this question will be stored in
        grading_started (bool): whether or not grading has started (TODO: remove?)
        handin_count (int): total number of handins for this question
        handins (List[Handin]): list of handins for this question
        has_flagged (bool): whether or not there are flagged
            handins for this question
        has_incomplete (bool): whether or not there are incomplete handins for
            this question
        log_filepath (str): filepath for the log file for this question
        _qnumb (int): question number
        rubric_filepath (str): filepath for the base rubric for this question
        test_path (str): base filepath for the testsuite for this question

    Discouraged Attributes:
        _json (dict): JSON for this question from /ta/assignments.json
    """
    
    def __init__(self, parent_assignment: Assignment, q_ndx: int) -> None:
        """ makes a Question instance; must be given an Assignment
        instance and a question index (zero-indexed)
        Question(Assignment("Homework 4"), 0)
        highly recommend against direct instantiation (let Assignment class
        do it)
        TODO: make Question nested class of Assignment? would allow for
              HTA_Question and HTA_Handin classes which could be helpful
        """
        try:
            cdata = parent_assignment._json['questions'][q_ndx]
        except IndexError:  # no question with this index on this assignment
            base = (
                    f'{parent_assignment} does not have problem '
                    f'indexed {q_ndx}'
                   )
            raise ValueError(base)

        else:  # this is a valid question, so continue
            self._json = cdata

        self.assignment = parent_assignment
        self._qnumb = qn = q_ndx + 1        
        self.grade_path = os.path.join(parent_assignment.grade_path, f'q{qn}')
        self.rubric_filepath = os.path.join(parent_assignment.rubric_path,
                                            f'q{qn}.json')
        self.log_filepath = os.path.join(parent_assignment.log_path,
                                         f'q{qn}.json')

        self.code_filename = self._json['filename']
        test_filename = f'q{qn}.{self._json["test-ext"]}'
        self.test_path = os.path.join(parent_assignment.test_path,
                                      test_filename)

        self.load_handins()

    @require_resource('/course/cs0111/handin-loading-lock.lock')
    def load_handins(self) -> None:
        """set self.handins based on the questions log file 
        """
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

    def ta_handins(self, user: User) -> List['Handin']:
        """return all handins for the given user
        
        Args:
            user (User): user for whom to find handins
        
        Returns:
            List['Handin']: handins that user is grading
        """
        return [h for h in self.handins if h.grader == user.uname or h.grader == 'eberkowi']

    def html_data(self, user: User) -> HTMLData:
        """given a user, return a dictionary with the data that will be used
        to populate that TA's view of already extracted handins to grade 
        
        Args:
            user (User): user for whom to get html data
        
        Returns:
            HTMLData: the data required by the web app to allow the TA
            to grade handins for this question
        """

        # refresh the handins to make sure outdated information isnt loaded
        # potentially unnecessary but I think it's a good idea just in case
        self.load_handins()

        user_handins = self.ta_handins(user)  # get this users' handins to grade

        unextracted_logins: Optional[List[str]] = None
        if not self.assignment.anonymous:
            unextracted_logins = []
            for h in self.handins:
                if not (h.extracted or h.blocklisted_by(user.uname)):
                    unextracted_logins.append(self.assignment.id_to_login(h.id))

        hdata: HTMLData = {
            'ta_handins':         [h.get_rubric_data() for h in user_handins],
            'handin_count':       len(self.handins),
            'complete_count':     self.completed_count,
            'anonymous':          self.assignment.anonymous,
            'unextracted_logins': unextracted_logins
        }

        return hdata

    @require_resource()
    def get_random_handin(self, user: User) -> Optional['Handin']:
        """Get a random handin gradeable by the user
        
        Args:
            user (User): user for whom to get a handin
        
        Returns:
            Optional['Handin']: None if there are no more gradeable handins
            for this question and user, or a randomly selected Handin otherwise
        
        No Longer Raises:
            TypeError: invalid input type (must be User class)
        """

        # refresh handins, in case someone else has extracted in the meantime
        self.load_handins()

        gradeable = [h for h in self.handins if h.gradeable_by(user.uname)]
        if not gradeable:  # no gradeable handins for this TA
            return None
        else:
            return random.choice(gradeable)

    def get_handin_by_id(self, anon_id: int) -> 'Handin':
        """
        inputs:
            - anon_id: anonymous identifier of student for this assignment
        output:
            the Handin of the relevant student for this question
        """
        for handin in self.handins:
            if handin.id == anon_id:
                return handin

        raise ValueError(f'No handin with id {anon_id}')

    def add_handin_to_log(self, ident: int) -> None:
        """
        description: add a new handin to the question's log file
        inputs:
            - ident: anonymous identifier of the new handin
        """
        with locked_file(self.log_filepath) as f:
            data = json.load(f)
        
        new_data: LogItem = {'id': ident, 'flag_reason': None,
                             'complete': False, 'grader': None}
        data.append(new_data)
        with locked_file(self.log_filepath, 'w') as f:
            json.dump(data, f, indent=2, sort_keys=True)

        self.load_handins()  # ugh idk concurrency is annoying

    def copy_rubric(self) -> dict:
        """ return the json rubric """
        with locked_file(self.rubric_filepath) as f:
            return json.load(f)

    def rewrite_rubric(self, rubric, override):
        """ given a new rubric and a second argument which must be the string
        'yes', overwrite the rubric for this assignment. should probably only
        be used by HTA's (TA's edit by hand) but there's no HTA_Question parent
        class (yet) so... """
        if override.lower() != 'yes':
            raise ValueError('Attempting to rewrite rubric without override.')

        with locked_file(self.rubric_filepath, 'w') as f:
            json.dump(rubric, f, indent=2, sort_keys=True)
    
    @require_resource()  # using this here is definitely important
    def add_ungiven_comment(self, category: Optional[str], comment: str):
        """ add a comment to the rubric & all extracted students """
        def add_comment(path):
            """ helper to take in a path and add the global comment to
            the rubric in that file """
            with locked_file(path) as f:
                rubric = json.load(f)

            if category is None:
                rubric['comments']['un_given'].append(comment)
            else:
                comments = rubric['rubric'][category]['comments']
                comments['un_given'].append(comment)

            with locked_file(path, 'w') as f:
                json.dump(rubric, f, indent=2, sort_keys=True)

        add_comment(self.rubric_filepath)  # add to main rubric

        for handin in self.handins:        # add to all extracted handins
            if handin.extracted:
                add_comment(handin.grade_path)

    def __repr__(self):
        return f'Question(file=[{self.code_filename}])'


class Handin:
    def __init__(self, question: Question, ident: int, complete: bool,
                 grader: Optional[str], flag_reason: Optional[str]) -> None:
        self.question: Question = question
        self.id: int = ident
        self.complete: bool = complete
        self.extracted: bool = (grader is not None)
        self.grader: Optional[str] = grader
        self.flagged: bool = flag_reason is not None
        self.flag_reason: Optional[str] = flag_reason
        self.student_name: str = 'Not loaded'

        self.grade_path = os.path.join(question.grade_path,
                                       f'student-{self.id}.json')
        self.handin_path = os.path.join(self.question.assignment.files_path,
                                        f'student-{self.id}')
        self.filepath = os.path.join(self.handin_path,
                                     self.question.code_filename)
        if not self.question.assignment.anonymous:
            self.login = self.question.assignment.id_to_login(self.id)

    def raw_data(self):
        """ read the handin's data from the question's logfile """
        with locked_file(self.question.log_filepath, 'r') as f:
            data = json.load(f)

        for handin in data:
            if handin['id'] == self.id:
                return handin

    def get_rubric(self) -> Rubric:
        """ get the rubric for this handin only; must be extracted """
        if os.path.exists(self.grade_path):
            with locked_file(self.grade_path) as f:
                d = json.load(f)
                return d
        else:
            base = f'Attempting to get rubric of unextracted handin {self}'
            raise ValueError(base)

    def get_rubric_data(self) -> Dict[str, Any]:
        """ collect information about the student's grade rubric """
        rdata: Dict[str, Any] = {'id': self.id}
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
        rdata['sfile-link'] = self.handin_path
        return rdata

    def get_code(self) -> str:
        """ right now, this returns the code as raw text from the
        file the student submitted; this could be updated to be more
        complex (depending on filename, etc.), and would need to be
        updated in /ta/grading/static/main.js to handle those updates """
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
        """ update the log file for this handin
        kwargs:
            - grader : login str of the handin grader
            - flag_reason : str explaining why the handin is flagged
            - complete : boolean whether or not handin is complete
        """
        with locked_file(self.question.log_filepath) as f:
            data: Log = json.load(f)

        found = False
        for handin in data:
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
            raise ValueError(f'write_line: handin {self} not in log')

        with locked_file(self.question.log_filepath, 'w') as f:
            json.dump(data, f, indent=2, sort_keys=True)

    @require_resource('/course/cs0111/ta/question_extract_resource')
    def start_grading(self, ta: str) -> None:
        """ given a TA username, start grading this handin """
        assert not self.extracted, 'cannot start grading on extracted handin'
        self.write_line(grader=ta, flag_reason=None, complete=False)
        shutil.copyfile(self.question.rubric_filepath, self.grade_path)
        self.grader = ta
        self.extracted = True

    @require_resource()
    def unextract(self) -> None:
        """ unextract handin; gets rid of grade rubric """
        self.write_line(grader=None, extracted=False, flag_reason=None)
        os.remove(self.grade_path)
        self.grader = None
        self.extracted = False
        self.complete = False

    def flag(self, msg: str = '') -> None:
        """ flag a handin with an optional message """
        if not isinstance(msg, str):
            raise TypeError(f'flag msg must be str, got {msg}')

        self.write_line(flag_reason=msg)
        self.flagged = True

    def unflag(self) -> None:
        """ unflag handin, reset flag message if there was one """
        self.write_line(flag_reason=None)
        self.flagged = False

    def set_complete(self) -> None:
        """ handin grading complete """
        self.write_line(complete=True)
        self.complete = True

    def write_grade(self, json_data: Rubric) -> None:
        """ write the grade rubric """
        with locked_file(self.grade_path, 'w') as f:
            json.dump(json_data, f, indent=2, sort_keys=True)

    def save_data(self,
                  data: Dict[str, Dict[str, Optional[int]]],
                  new_comments: Tuple[List[str], Dict[str, List[str]]],
                  force_complete: bool = False) -> bool:
        def check_rubric_complete() -> bool:
            """ check if rubric is complete (any unfilled rubric options) """
            for key in data:
                if any(map(lambda descr: data[key][descr] is None, data[key])):
                    return False

            return True

        rubric: Rubric = self.get_rubric()
        rub_complete = check_rubric_complete()

        # update comments irregardless of whether rubric is complete
        update_comments(rubric['comments'], new_comments[0])
        for cat in new_comments[1]:
            update_comments(rubric['rubric'][cat]['comments'],
                            new_comments[1][cat])
        
        if force_complete and not rub_complete:
            # attempting to finish grading but has empty rubric cells
            return False

        for cat in data:
            for descr in data[cat]:
                val = data[cat][descr]
                for ri in rubric['rubric'][cat]['rubric_items']:
                    if ri['descr'] == descr:
                        ri['selected'] = val
                        break

        self.write_grade(rubric)
        return True
    
    def gradeable_by(self, uname: str) -> bool:
        """ is this handin gradeable by input uname (str);
        checks if the student is blocklisted by the TA or if the 
        handin has already been extracted (False if so) """
        return not (self.blocklisted_by(uname) or self.extracted)

    def blocklisted_by(self, ta: str) -> bool:
        """ returns True if the student is blocklisted by ta (str) """
        bl_path = self.question.assignment.blocklist_path
        with locked_file(bl_path) as f:
            data = json.load(f)

        return ta in data and self.id in data[ta]

    def generate_report_str(self, rubric: Optional[Rubric] = None) -> str:
        """ return a report string for this handin (this question only)
        will format so that no lines are over 74 characters, indentation
        is all pretty, etc. uses rubric if provided, otherwise loads
        the handins' rubric """
        if rubric is None:
            rubric = self.get_rubric()

        if self.grader is None:
            e = f'Trying to generate report of handin with no grader {self}'
            raise ValueError(e)

        return get_handin_report_str(rubric, self.grader, self.question)

    def generate_grade_report(self) -> Tuple[str, Dict[str, int]]:
        """ return a report_str (all comments collected and formatted nicely)
        and a dictionary with one key per theme, values being the numeric score
        the student received in that category for this question only 
        NOTE: no grades can below a 0; as such, any negative grades will
        be rounded up to 0 """
        rubric: Rubric = self.get_rubric()
        report_str = self.generate_report_str(rubric)
        grade = {}
        for key in rubric['rubric']:
            # set grade for this category
            grade[key] = 0
            for rubric_item in rubric['rubric'][key]['rubric_items']:
                sel_ndx = rubric_item['selected']
                if sel_ndx is None:
                    e = (
                         f'Invalid generate_grade_report call on '
                         f'{self}'
                        )
                    raise ValueError(e)

                grade[key] += rubric_item['items'][sel_ndx]['point_val']

        for key in grade:
            if grade[key] < 0:
                grade[key] = 0

        return report_str, grade

    def run_test(self) -> str:
        test_type = self.question._json['test-ext']
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
                lines.insert(0, f'import file("{relpath}") as SC\n')

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

        base += f', grader={self.grader})' if self.extracted else ')'
        return base


def started_asgns() -> List[Assignment]:
    """
    Returns list of started assignments (unloaded)
    """
    assignments = []
    for key in asgn_data['assignments']:
        asgn = Assignment(key)
        if asgn.started:
            assignments.append(asgn)

    return assignments


def all_asgns() -> List[Assignment]:
    """
    Returns list of all assignments (unloaded)
    """
    assignments = []
    for key in asgn_data['assignments']:
        asgn = Assignment(key)
        assignments.append(asgn)

    return assignments
