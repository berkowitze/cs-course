# written by Eli Berkowitz (eberkowi) 2018

import json
import os
import random
import shutil
import subprocess
from datetime import datetime as dt
from functools import wraps
from os.path import join as pjoin
from os.path import exists as pexists
from typing import Any, Callable, Dict, List, Optional, Tuple

from course_customization import full_asgn_name_to_dirname, \
    get_handin_report_str, get_empty_raw_grade, determine_grade
from custom_types import (HTMLData, Log, LogItem, Rubric,
                          AssignmentJson, AssignmentData)
from helpers import (loaded_rubric_check, locked_file, json_edit,
                     require_resource, update_comments, rubric_check,
                     remove_duplicates, moss_langs, CONFIG, lang_dict)

# READ BEFORE EDITING THIS FILE #
# do not use the builtin `open` function; instead use the
# locked_file function (or the require_resource function)
# see the bottom of /ta/grading/helpers.py for an explanation
# of what these functions are; you should be able to safely use:
# with locked_file(filename, mode) as f:
#     ...

BASE_PATH = CONFIG.base_path
DATA_PATH = pjoin(BASE_PATH, 'ta/grading/data')
proj_base_path = pjoin(DATA_PATH, 'projects')
asgn_data_path = pjoin(BASE_PATH, 'ta/assignments.json')
ta_path = pjoin(BASE_PATH, 'ta/groups/tas.txt')
hta_path = pjoin(BASE_PATH, 'ta/groups/htas.txt')
student_path = pjoin(BASE_PATH, 'ta/groups/students.txt')
log_base_path = pjoin(DATA_PATH, 'logs')
test_base_path = pjoin(DATA_PATH, 'tests')
rubric_base_path = pjoin(DATA_PATH, 'rubrics')
grade_base_path = pjoin(DATA_PATH, 'grades')
s_files_base_path = pjoin(DATA_PATH, 'sfiles')
anon_base_path = pjoin(DATA_PATH, 'anonymization')
blocklist_path = pjoin(DATA_PATH, 'blocklists')
rubric_schema_path = pjoin(BASE_PATH, 'ta/grading/rubric_schema.json')
assert pexists(asgn_data_path), f'No data file "{asgn_data_path}"'

with locked_file(asgn_data_path) as f:
    asgn_data: AssignmentJson = json.load(f)


# function that checks if an assignment has been started
# func is the function the wrapper will be wrapped around
def is_started(func: Callable) -> Callable:
    """

    decorator that checks if assignment has been started before
    calling the appropriate method

    :param func: method for Assignments (should take in assignment as first
                 argument)
    :return: decorated method

    """
    @wraps(func)
    def magic(asgn: 'Assignment', *args, **kwargs):
        if not asgn.started:
            e = (
                 f'attempting to call method on unstarted '
                 f'assignment {asgn.full_name}'
                )
            raise ValueError(e)
        else:
            # run as normal if grading has started
            return func(asgn, *args, **kwargs)

    return magic


def is_extracted(func: Callable) -> Callable:
    """

    Ensures a handin is extracted (to be used as a decorator)
    raises ValueError if method called on unextracted handin

    :param func: any Handin method
    :type func: Callable
    :returns: decorated method that checks if handin is extracted
    :rtype: Callable
    :raises ValueError: when decorated method called on unextracted handin

    **Example:**

    .. code-block:: python

        class Handin:
            ...

            @is_extracted
            def unextract(self, ...):
                ...

    """
    @wraps(func)
    def magic(handin: 'Handin', *args, **kwargs):
        if not handin.extracted:
            e = (
                f'attempting to call method on unextracted '
                f'handin {handin}'
                )
            raise ValueError(e)
        else:
            # run method as usual if it is extracted
            return func(handin, *args, **kwargs)

    return magic


class User:
    """

    User class to give an interface to the user and their permissions.

    :ivar uname: The user's login
    :vartype uname: str
    :ivar hta: Whether or not the user is an HTA
    :vartype hta: bool
    :ivar ta: Whether or not the user is a TA
    :vartype ta: bool
    """

    def __init__(self, uname: str) -> None:
        """

        make a new User

        :param uname: CS login of user
        :type uname: str

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

    Provides interface with logs, grades, and rubrics, files, etc.

    :ivar proj_dir: If not a group asgn, None. If is a group_asgn,
                    the name of the common directory to use
                    (for multi-assignment projects). For example, "project3"
    :vartype proj_dir: Optional[str]
    :ivar full_name: Full name of assignment (i.e. "Homework 2")
    :vartype full_name: str
    :ivar mini_name: Directory name of assignment (i.e. "homework2")
    :vartype mini_name: str
    :ivar due_date: Datetime of the assignment's due date
    :vartype due_date: datetime
    :ivar due: Whether or not the assignment deadline has passed
    :vartype due: bool
    :ivar started: Whether or not grading has started for this assignment
    :vartype started: bool
    :ivar group_asgn: Whether or not the assignment is a group
                      assignment (i.e. True for projects)
    :vartype group_asgn: bool
    :ivar anonymous: True if the assignment is being graded anonymously
    :vartype anonymous: bool
    :ivar log_path: Directory path for log files
    :vartype log_path: str
    :ivar rubric_path: Directory path for rubric files
    :vartype rubric_path: str
    :ivar grade_path: Directory path for grade files
    :vartype grade_path: str
    :ivar files_path: Directory path where students' handins will be copied
    :vartype files_path: str
    :ivar test_path: JSON path where anonymization information for this
                     assignment will be stored.
    :vartype test_path: str
    :ivar blocklist_path: JSON parth where blocklist information for this
                          assignment will be stored
    :vartype blocklist_path: str
    :ivar grading_completed: whether or not grading has been completed for
                             this assignment
    :ivar _json: JSON data for this assignment from assignments.json
    :vartype _json: dict
    :ivar _login_to_id_map: a map from login to anonymous ID for this asgn
    :vartype _login_to_id_map: Dict[str, int]
    :ivar _id_to_login_map: a map from anonymous ID to login for this asgn
    :vartype _id_to_login_map: Dict[int, str]

    :raises KeyError: if key is not in the assignments.json thing

    """
    def __init__(self, key: str, load_if_started: bool = True) -> None:
        """

        Create a new assignment based on the key from /ta/assignments.json

        :param key: Key of assignment to load (i.e. 'Homework 4')
        :type key: str
        :param load_if_started: whether or not to fully load the
                          assignment and all its Questions, defaults to False
        :type load_if_started: bool, optional
        :raises: ValueError if attempting to load unstarted assignment

        """
        self.full_name: str = key
        self.mini_name: str = full_asgn_name_to_dirname(self.full_name)

        self._json: AssignmentData = asgn_data['assignments'][self.full_name]
        self.due_date: dt = dt.strptime(self._json['due'], '%m/%d/%Y %I:%M%p')
        self.due: bool = self.due_date < dt.now()
        self.started: bool = self._json['grading_started']

        self.group_asgn: bool
        self.proj_dir: Optional[str]
        if self._json['group_data'] is not None:
            self.group_asgn = True
            group_dir = self._json['group_data']['multi_part_name']
            self.proj_dir = pjoin(proj_base_path, group_dir + '.json')
        else:
            self.group_asgn = False
            self.proj_dir = None

        self.anonymous: bool = self._json['anonymous']
        self.log_path: str = pjoin(log_base_path, self.mini_name)
        self.rubric_path: str = pjoin(rubric_base_path, self.mini_name)
        self.grade_path: str = pjoin(grade_base_path, self.mini_name)
        self.files_path: str = pjoin(s_files_base_path, self.mini_name)
        self.test_path: str = pjoin(test_base_path, self.mini_name)
        self.anon_path: str = pjoin(anon_base_path,
                                    f'{self.mini_name}.json')
        self.blocklist_path: str = pjoin(blocklist_path,
                                         f'{self.mini_name}.json')
        self.bracket_path: str = pjoin(rubric_base_path,
                                       self.mini_name,
                                       'bracket.json')
        self.grading_completed = self._json['grading_completed']
        self.loaded: bool = False

        if self.started and load_if_started:
            self.load()

    @is_started
    def load(self):
        """

        Loads the assignment (checks all paths are proper and
        loads all assignment questions)
        :raises AssertionError: invalid assignment

        """
        # checking that assignment has correct paths
        n = self.full_name
        assert pexists(self.log_path), \
            f'started assignment "{n}" with no log directory'
        assert pexists(self.rubric_path), \
            f'started assignment "{n}" with no rubric directory'
        assert pexists(self.grade_path), \
            f'started assignment "{n}" with no grade directory'
        assert pexists(self.blocklist_path), \
            f'started assignment "{n}" with no blocklist file'
        assert pexists(self.files_path), \
            f'started assignment "{n}" with no student code directory'
        
        if not self.anonymous:
            with locked_file(self.anon_path) as f:
                data: Dict[str, int] = json.load(f)

            self._login_to_id_map: Dict[str, int] = data
            self._id_to_login_map: Dict[int, str] = {data[k]: k for k in data}

        self._load_questions()
        self.loaded = True
        return self

    @is_started
    def _load_questions(self) -> None:
        """load all log files, creating Question instances stored into
        self.questions.
        """
        questions = []
        for qnumb, q in enumerate(self._json['questions']):
            question = Question(self, qnumb)
            questions.append(question)

        self.questions: List[Question] = questions

    @is_started
    def get_question(self, ndx: int) -> 'Question':
        """

        get a question by index (0 indexed)

        :param ndx: Index of question (0 index)
        :type ndx: int
        :returns: Question corresponding to that index
        :rtype: Question
        :raises: IndexError if no question with corresponding index

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
        """

        Get anonymous ID of student by login

        :param login: Student CS login
        :type login: str
        :returns: Anonymous ID for student by login
        :rtype: int
        :raises: ValueError: Student has no anonymous ID for this assignment

        """
        if self.anonymous:
            raise ValueError('Cannot get login on anonymous assignment')

        #  first try using cached info
        if login in self._login_to_id_map:
            return self._login_to_id_map[login]

        #  next try reloading anonymization information
        with locked_file(self.anon_path) as f:
            data: Dict[str, int] = json.load(f)

        try:
            self._login_to_id_map[login] = data[login]
            self._id_to_login_map[data[login]] = login
            return data[login]
        except KeyError:
            #  then fail
            raise ValueError(f'login {login} does not exist in map for {self}')

    @is_started
    def id_to_login(self, ident: int) -> str:
        """

        Get anonymous ID of student by login

        :param ident: Student anonymous ID for this assignment
        :type ident: int
        :returns: Login of student with ident id
        :rtype: str
        :raises: ValueError: No student with anon ID for this assignment

        """
        if self.anonymous:
            raise ValueError('Cannot get login on anonymous assignment')

        #  first try using cached info
        if ident in self._id_to_login_map:
            return self._id_to_login_map[ident]

        #  next try reloading anonymization information
        with locked_file(self.anon_path) as f:
            data: Dict[str, int] = json.load(f)

        for login in data:
            if data[login] == ident:
                self._id_to_login_map[ident] = login
                self._login_to_id_map[login] = ident
                return login

        #  then fail
        raise ValueError(f'id {ident} does not exist in map for {self}')

    def moss(self,
             moss_lang: Optional[str] = None,
             extension: Optional[str] = None
             ) -> None:
        moss_path = pjoin(BASE_PATH, 'tabin/mossScript')

        if extension is None:
            find_cmd = ['find', self.files_path, '-name', '*.*']
        else:
            find_cmd = ['find', self.files_path, '-name',
                        f'*.{extension.lstrip(".")}']

        if moss_lang is None:
            moss_cmd = ['xargs', moss_path]
        else:
            if moss_lang not in moss_langs:
                print(f'WARNING: Language {moss_lang} not supported by MOSS')
                print('Running without any language constraint.')
                print('Press enter to continue.')
                input()
                moss_cmd = ['xargs', moss_path]
            else:
                moss_cmd = ['xargs', moss_path, '-l', moss_lang]

        print(f'Finding files: {" ".join(find_cmd)}')
        print(f'Mossing: {" ".join(moss_cmd)}')
        find = subprocess.Popen(find_cmd, stdout=subprocess.PIPE)
        subprocess.call(moss_cmd, stdin=find.stdout)

    def __repr__(self) -> str:
        """ representation of instance (i.e. for printing) """
        return f'Assignment(name="{self.full_name}")'


class Question:
    """

    Class for questions (Assignments are made up of a list of questions)

    :ivar completed_count: number of handins graded
    :vartype completed_count: int
    :ivar flagged_count: number of handins flagged for review
    :vartype flagged_count: int
    :ivar grading_started: whether or not grading has started (TODO: remove?)
    :vartype grading_started: bool
    :ivar has_flagged: whether or not there are flagged handins
                       for this question
    :vartype has_flagged: bool
    :ivar has_incomplete: whether or not there are incomplete handins
                          for this question
    :vartype has_incomplete: bool
    :ivar assignment: assignment this question is from
    :vartype assignment: Assignment
    :ivar code_filename: code filename of this question (i.e. maze.arr)
    :vartype code_filename: str
    :ivar grade_path: path that grades of this question will be stored in
    :vartype grade_path: str
    :ivar handin_count: total number of handins for this question
    :vartype handin_count: int
    :ivar handins: list of handins for this question
    :vartype handins: List[Handin]
    :ivar log_filepath: filepath for the log file for this question
    :vartype log_filepath: str
    :ivar _qnumb: question number
    :vartype _qnumb: int
    :ivar rubric_filepath: filepath for the base rubric for this question
    :vartype rubric_filepath: str
    :ivar test_path: base filepath for the testsuite for this question, or
                     None if there is no testsuite for this question.
    :vartype test_path: Optional[str]
    :ivar _json: JSON for this question from /ta/assignments.json
    :vartype _json: dict

    """
    def __init__(self, parent_assignment: Assignment, q_ndx: int) -> None:
        """

        makes a Question instance. I highly recommend against direct
        instantiation (let Assignment class
        do it)

        Todo: make :code:`Question` nested class of :code:`Assignment`?
        would probably allow for :code:`HTA_Question` and :code:`HTA_Handin`
        classes which could be helpful

        :param parent_assignment: assignment corresponding to this question
        :type parent_assignment: Assignment
        :param q_ndx: question number (used to get info from assignments.json)
        :type q_ndx: int
        :raises: ValueError

        **Example:**

        >>> Question(Assignment("Homework 4"), 0)

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

        self.assignment: Assignment = parent_assignment
        self._qnumb: int
        self._qnumb = qn = q_ndx + 1
        self.grade_path: str = pjoin(parent_assignment.grade_path, f'q{qn}')
        self.rubric_filepath: str = pjoin(parent_assignment.rubric_path,
                                          f'q{qn}.json')
        self.log_filepath: str = pjoin(parent_assignment.log_path,
                                       f'q{qn}.json')

        self.code_filename: str = self._json['filename']

        self.test_path: Optional[str]
        if self._json['ts_lang'] is None:
            self.test_path = None
        else:
            test_filename = f'q{qn}.{lang_dict[self._json["ts_lang"]]}'
            self.test_path = pjoin(parent_assignment.test_path, test_filename)

        self.load_handins()

    @require_resource(pjoin(BASE_PATH, 'handin-loading-lock.lock'))
    def load_handins(self) -> None:
        """

        set self.handins based on the questions log file

        """
        with locked_file(self.log_filepath) as f:
            data = json.load(f)

        handins = []
        for raw_handin in data:
            handins.append(Handin(self, raw_handin.pop('id'), **raw_handin))

        self.handins: List['Handin'] = handins
        self.handin_count: int = len(self.handins)

        self.grading_started = self.assignment.started
        self.has_incomplete = any(map(lambda h: not h.complete, self.handins))
        self.has_flagged = any(map(lambda h: h.flagged, self.handins))

        # how many handins for this question have been completed
        self.completed_count = len([x for x in self.handins if x.complete])
        self.flagged_count = len([x for x in self.handins if x.flagged])

    def ta_handins(self, user: User) -> List['Handin']:
        """

        return all handins for the given user

        :param user: user for whom to find handins
        :type user: User
        :returns: handins that user is grading
        :rtype: List[Handin]

        """
        return [h for h in self.handins if (
            h.grader == user.uname or h.grader == 'eberkowi')]

    def html_data(self, user: User) -> HTMLData:
        """

        given a user, return a dictionary with the data that will be used
        to populate that TA's view of already extracted handins to grade

        :param user: user for whom to get html data
        :type user: User
        :returns: the data required by the web app to allow the TA
                  to grade handins for this question
        :rtype: HTMLData

        """

        # refresh the handins to make sure outdated information isnt loaded
        # potentially unnecessary but I think it's a good idea just in case
        self.load_handins()

        user_handins = self.ta_handins(user)  # get this ta's handins to grade

        unext_logins: Optional[List[str]] = None
        if not self.assignment.anonymous:
            unext_logins = []
            for h in self.handins:
                if not (h.extracted or h.blocklisted_by(user.uname)):
                    unext_logins.append(self.assignment.id_to_login(h.id))

        hdata: HTMLData = {
            'ta_handins':         [h.get_rubric_data() for h in user_handins],
            'handin_count':       len(self.handins),
            'complete_count':     self.completed_count,
            'anonymous':          self.assignment.anonymous,
            'unextracted_logins': unext_logins
        }

        return hdata

    @require_resource()
    def get_random_handin(self, user: User) -> Optional['Handin']:
        """

        Get a random handin gradeable by the user

        :param user: user for whom to get a handin
        :type user: User
        :returns: None if there are no more gradeable handins
            for this question and user, or a randomly selected Handin otherwise
        :rtype: Optional[Handin]

        """

        # refresh handins, in case someone else has extracted in the meantime
        self.load_handins()

        gradeable = [h for h in self.handins if h.gradeable_by(user.uname)]
        if not gradeable:  # no gradeable handins for this TA
            return None
        else:
            return random.choice(gradeable)

    def get_handin_by_id(self, ident: int) -> 'Handin':
        """

        get handin by anon id for this question

        :param ident: anonymous identifier of student for this assignment
        :type ident: int
        :returns: the Handin of the relevant student for this question
        :rtype: Handin
        :raises: ValueError: no handin with anon id ident

        """
        for handin in self.handins:
            if handin.id == ident:
                return handin

        raise ValueError(f'No handin with id {ident}')

    def add_handin_to_log(self, ident: int) -> None:
        """

        add a new handin to the question's log file

        :param ident: anonymous identifier of the new handin
        :type ident: int

        """
        new_data: LogItem = {'id': ident, 'flag_reason': None,
                             'complete': False, 'grader': None}
        data: Log
        with json_edit(self.log_filepath) as data:
            data.append(new_data)

        self.load_handins()  # ugh idk concurrency is annoying

    def copy_rubric(self) -> Rubric:
        """

        return the JSON rubric of this question following the spec from
        custom_types.py

        :returns: base rubric for this question
        :rtype: Rubric

        """
        with locked_file(self.rubric_filepath) as f:
            return json.load(f)

    @require_resource()
    def rewrite_rubric(self, rubric: Rubric) -> None:
        """

        given a new rubric, check the rubric and write it into the questions
        rubric file.

        :param rubric: The updated base rubric for this question.
        :type rubric: Rubric

        """
        loaded_rubric_check(rubric)
        with locked_file(self.rubric_filepath, 'w') as f:
            json.dump(rubric, f, indent=2, sort_keys=True)

    def add_ungiven_comment(self,
                            category: Optional[str],
                            comment: str) -> bool:
        """

        try to add a comment to the rubric & all extracted students; do
        nothing if the comment is already a global comment

        :param category: the category to give the comment in, or
                         None if giving a general comment
        :type category: Optional[str]
        :param comment: the comment to add to the ungiven comments list
        :type comment: str
        :returns: whether or not the comment was added (True if added, False
                  if the comment was already a global comment)
        :rtype: bool

        """
        def add_comment(rubric: Rubric) -> None:
            """ helper to take in a path and add the global comment to
            the rubric in that file """
            if category is None:
                comments = rubric['comments']
            else:
                comments = rubric['rubric'][category]['comments']

            comments['un_given'].append(comment)
            comments['un_given'] = remove_duplicates(comments['un_given'])

        rubric = self.copy_rubric()
        if category is None:
            cs = rubric['comments']
            if comment in cs['un_given'] or comment in cs['given']:
                return False
        else:
            cs = rubric['rubric'][category]['comments']
            if comment in cs['un_given'] or comment in cs['given']:
                return False

        print('starting')
        self.magic_update(add_comment)
        print('ending')
        return True

    def magic_update(self, func: Callable[[Rubric], None]) -> None:
        """

        using a rubric updating function, changes a) the base rubric, and
        b) each extracted rubric. updated rubrics are checked for validity
        before file writing (as of after homework 8 2018 rip)

        This is most easily done in asgnipython

        :param func: a function that takes in a rubric, returns None, and
                     mutates the rubric.
        :type func: Callable[[Rubric], None]
        :raises TypeError: invalid input types
        :raises AssertionError: func improperly modifies rubrics

        **Example**:

        .. code-block:: python

            asgn = HTA_Assignment("Homework 6")
            qn = asgn.questions[0]

            def updater(rubric):
                items = rubric['rubric']['Functionality']['rubric_items']
                items[2]['options'][3]['point-val'] = 5

            qn.magic_update(updater)

        """
        if not callable(func):
            raise TypeError('func must be callable')

        self.load_handins()
        d: Rubric = self.copy_rubric()
        func(d)
        loaded_rubric_check(d)
        self.rewrite_rubric(d)

        for handin in self.handins:
            if not handin.extracted:
                continue

            d = handin.get_rubric()
            func(d)
            handin.write_grade(d)

    def __repr__(self):
        return f'Question(file={self.code_filename})'


class Handin:
    """

    class for individual handin (question specific)

    :ivar question: the Question this handin is for
    :vartype question: Question
    :ivar id: anonymous assignment identifier for the handin's student
    :vartype id: int
    :ivar complete: whether or not this handin has been graded
    :vartype complete: bool
    :ivar extracted: whether or not this handin has been extracted
    :vartype extracted: bool
    :ivar grader: None if unextracted, login of TA if is extracted
    :vartype grader: Optional[str]
    :ivar flagged: Whether or not the handin is flagged
    :vartype flagged: bool
    :ivar flag_reason: None if unflagged, the flag reason if flagged
    :vartype flag_reason: Optional[str]
    :ivar filepath: filepath of the students' code file for this question
    :vartype filepath: str
    :ivar grade_path: JSON path of this students' grade rubric
    :vartype grade_path: str
    :ivar handin_path: Directory path of the students' handed in files
    :vartype handin_path: str
    :ivar login: None if anonymous assignment, student's login if
                 non-anonymous assignment
    :vartype login: Optional[str]

    """

    def __init__(self, question: Question, ident: int, complete: bool,
                 grader: Optional[str], flag_reason: Optional[str]) -> None:
        """

        Handin class (question specific). Used for managing invdividual handins

        :param question: Question that this handin is for
        :type question: Question
        :param ident: anonymous id of the handin
        :type ident: int
        :param complete: whether or not grading of handin is complete
        :type complete: bool
        :param grader: None if handin unextracted, and the
                       login of the TA grading the handin if it has
        :type grader: Optional[str]
        :param flag_reason: None if unflagged, and the flag reason
                            if flagged
        :type flag_reason: Optional[str]

        """
        self.question: Question = question
        self.id: int = ident
        self.complete: bool = complete
        self.extracted: bool = (grader is not None)
        self.grader: Optional[str] = grader
        self.flagged: bool = flag_reason is not None
        self.flag_reason: Optional[str] = flag_reason

        self.grade_path = pjoin(question.grade_path,
                                f'student-{self.id}.json')
        self.handin_path = pjoin(self.question.assignment.files_path,
                                 f'student-{self.id}')
        self.filepath = pjoin(self.handin_path,
                              self.question.code_filename)

        self.login: Optional[str]
        if not self.question.assignment.anonymous:
            self.login = self.question.assignment.id_to_login(self.id)
        else:
            self.login = None

    @is_extracted
    def get_rubric(self) -> Rubric:
        """

        get the rubric for this handin only; must be extracted

        :returns: rubric of this handin
        :rtype: Rubric

        """
        with locked_file(self.grade_path) as f:
            d = json.load(f)
            return d

    @is_extracted
    def get_rubric_data(self) -> Dict[str, Any]:
        """

        collect information about the student's grade rubric

        :returns: a dictionary with the rubric for this handin along with some
                  other metadata
        :rtype: Dict[str, any]

        """
        rdata: Dict[str, Any] = {}
        rdata['id'] = self.id
        rdata['student-name'] = self.login
        rdata['flagged'] = self.flagged
        rdata['complete'] = self.complete
        rdata['rubric'] = self.get_rubric()
        rdata['filename'] = self.question.code_filename
        rdata['sfile-link'] = self.handin_path
        return rdata

    def get_code(self, with_tests: bool = False) -> str:
        """

        get student's code for this handin as a string, or an error string
        if the code is not JSON decodable (it needs to be for the grading app)

        if with_tests is True, appends the testing file for this question
        to the end.

        :returns: student code string or error string if code is not decodable
        :rtype: str

        """
        filepath = pjoin(self.handin_path, self.question.code_filename)
        if not pexists(filepath):
            return (
                    f'No submission (or code issue). '
                    f'Check {self.handin_path} to make sure'
                   )
        elif os.path.splitext(filepath)[1] == '.zip':
            msg = 'Submission is a zip file; open in file viewer'
            return msg
        else:
            # should probably convert this to locked read at some point JIC
            try:
                with open(filepath, encoding='utf-8') as f:
                    code = f.read()
                
                if with_tests and pexists(self.question.test_path):
                    code += f'# {"-" * 20} TA TESTS {"-" * 20}\n'
                    with open(self.question.test_path, encoding='utf-8') as f:
                        code += f.read()

                json.dumps(code)

            except UnicodeDecodeError:
                code = (
                        f'Student code not decodable. Look at original handin'
                        f' in\n{filepath}\nand contact HTA if necessary'
                        )
                return code

            return code

    def write_line(self, **kwargs) -> None:
        """

        update the log file for this handin

        :param \*\*kwargs:

                         - grader (str): login of the handin grader

                         - flag_reason (str): explanation why the handin is
                           flagged

                         - complete (bool): whether or not handin is complete


        """
        with locked_file(self.question.log_filepath) as f:
            data: Log = json.load(f)

        for handin in data:
            if handin['id'] == self.id:
                if 'grader' in kwargs:
                    handin['grader'] = kwargs['grader']

                if 'flag_reason' in kwargs:
                    handin['flag_reason'] = kwargs['flag_reason']

                if 'complete' in kwargs:
                    handin['complete'] = kwargs['complete']

                break

        with locked_file(self.question.log_filepath, 'w') as f:
            json.dump(data, f, indent=2, sort_keys=True)

    @require_resource(pjoin(BASE_PATH, 'ta/question_extract_resource'))
    def start_grading(self, ta: str) -> None:
        """

        given a TA username, start grading this handin

        :param ta: login of ta grading this handin
        :type ta: str

        """
        assert not self.extracted, 'cannot start grading on extracted handin'
        self.write_line(grader=ta, flag_reason=None, complete=False)
        shutil.copyfile(self.question.rubric_filepath, self.grade_path)
        self.grader = ta
        self.extracted = True

    @require_resource()
    @is_extracted
    def unextract(self) -> None:
        """

        unextract handin; gets rid of grade rubric

        """
        self.write_line(grader=None, extracted=False, flag_reason=None)
        os.remove(self.grade_path)
        self.grader = None
        self.extracted = False
        self.complete = False

    @is_extracted
    def flag(self, msg: str = '') -> None:
        """

        flag a handin with an optional message

        :param msg: the flag reason, defaults to ''
        :type msg: str, optional

        """
        self.write_line(flag_reason=msg)
        self.flagged = True

    @is_extracted
    def unflag(self) -> None:
        """

        unflag handin, reset flag message if there was one

        """
        self.write_line(flag_reason=None)
        self.flagged = False

    @is_extracted
    def set_complete(self) -> bool:
        """

        handin grading complete, checks if complete first
        :returns: whether or not the handin was already complete
        :rtype: bool
        """
        if self.check_complete():
            self.write_line(complete=True)
            self.complete = True
            return True
        else:
            return False

    def write_grade(self, rubric: Rubric) -> None:
        """

        write the grade rubric

        :param rubric: new rubric to write into grade file
        :type rubric: Rubric

        """
        loaded_rubric_check(rubric)
        with locked_file(self.grade_path, 'w') as f:
            json.dump(rubric, f, indent=2, sort_keys=True)

    @is_extracted
    def save_data(self,
                  data: dict,
                  new_comments: Dict[str, Any],
                  emoji: bool) -> None:
        """

        Saves new data from grading app to rubric file

        :param data: a dict of category keys and
                     (rubric_item -> rubric_value) dict values
        :type data: Dict[str, Dict[str, Optional[int]]]
        :param new_comments: a tuple of general new comments to give and a
                             dictionary of (category -> comments to give)
        :type new_comments: Tuple[List[str], Dict[str, List[str]]]
        :param emoji: Whether or not this rubric has deserved an emoji!
        :type emoji: bool
        :returns: whether or not the operation was succesfully completed
        :rtype: bool

        """

        rubric: Rubric = self.get_rubric()

        rubric['emoji'] = emoji

        # update comments irregardless of whether rubric is complete
        update_comments(rubric['comments'], new_comments['general'])
        for cat in new_comments['categorized']:
            update_comments(rubric['rubric'][cat]['comments'],
                            new_comments['categorized'][cat])

        for cat in data:
            rub_cat = rubric['rubric'][cat]
            fudge_points = float(data[cat]['fudge'])
            rub_cat['fudge_points'][0] = fudge_points
            for ndx in data[cat]['options']:
                val = data[cat]['options'][ndx]
                rub_cat['rubric_items'][int(ndx)]['selected'] = val

        self.write_grade(rubric)

    def check_complete(self) -> bool:
        """ check if rubric is complete (any unfilled rubric options) """
        rubric: Rubric = self.get_rubric()
        for cat in rubric['rubric']:
            for item in rubric['rubric'][cat]['rubric_items']:
                if item['selected'] is None:
                    return False

        return True

    def gradeable_by(self, uname: str) -> bool:
        """

        checks if handin is gradeable by input login;
        checks if the student is blocklisted by the TA or if the
        handin has already been extracted (False if either are true)

        :param uname: login of TA who is attempting to grade
        :type uname: str
        :returns: whether or not the TA can grade this handin based on
                  blocklists and the handin being extracted already
        :rtype: bool

        """
        return not (self.blocklisted_by(uname) or self.extracted)

    def blocklisted_by(self, ta: str) -> bool:
        """

        determines if a TA can grade this handin

        :param ta: login of the TA to check
        :type ta: str
        :returns: whether the handin's student is blocklisted by TA
        :rtype: bool

        """
        bl_path = self.question.assignment.blocklist_path
        with locked_file(bl_path) as f:
            data = json.load(f)

        return ta in data and self.id in data[ta]

    @is_extracted
    def generate_report_str(self, rubric: Optional[Rubric] = None) -> str:
        """

        return a report string for this handin (this question only)
        formatted so that no lines are over 74 characters, indentation
        is all pretty, etc. uses rubric if provided, otherwise loads
        the handins' rubric

        :param rubric: the handins rubric or None (default) if the rubric
                       should be loaded
        :type rubric: Optional[Rubric], optional
        :returns: the report string
        :rtype: str

        """
        rub: Rubric = rubric if rubric is not None else self.get_rubric()
        grader: str = self.grader if self.grader is not None else 'No grader'
        return get_handin_report_str(rub, grader, self.question)

    @is_extracted
    def generate_grade_report(self) -> Tuple[str, Dict[str, int]]:
        """

        get the formatted handin report_str and a dictionary with one key per
        category, values being the numeric score the student received in that
        category (for this question only)
        **Note**: no grades can below a 0; as such, any negative grades will
        be rounded up to 0

        :returns: a tuple with the report string and the comments dictionary
        :rtype: Tuple[str, Dict[str, int]]
        :raises: ValueError if the handin is incomplete

        """
        rubric: Rubric = self.get_rubric()
        report_str = self.generate_report_str(rubric)
        grade = {}
        for key in rubric['rubric']:
            # set grade for this category
            grade[key] = rubric['rubric'][key]['fudge_points'][0]
            for rubric_item in rubric['rubric'][key]['rubric_items']:
                sel_ndx = rubric_item['selected']
                if sel_ndx is None:
                    e = (
                         f'Invalid generate_grade_report call on '
                         f'{self}'
                        )
                    raise ValueError(e)

                grade[key] += rubric_item['options'][sel_ndx]['point_val']

        for key in grade:  # ceil all grades to 0
            if grade[key] < 0:
                grade[key] = 0

        return report_str, grade

    def run_test(self) -> str:
        """

        Runs the testsuite for this handin and returns the results

        :returns: testsuite results
        :rtype: str

        """
        test_type = self.question._json['ts_lang']
        if test_type is None:
            return 'No defined testsuite'
        elif test_type == 'Pyret':
            return self.pyret_test()
        elif test_type == 'Python':
            return self.python_test()
        else:
            return 'Invalid test extension (contact HTA)'

    def python_test(self) -> str:
        """

        Runs python testsuite for this handin, returning the results

        :returns: the results of the testsuite as a string
        :rtype: str

        """
        assert self.question.test_path is not None
        test_filepath = self.question.test_path
        if not pexists(test_filepath):
            return 'No testsuite for this question'

        cmd = [pjoin(BASE_PATH, 'tabin', 'python-test'),
               test_filepath, self.filepath]
        return subprocess.check_output(cmd).decode('utf-8')

    def pyret_test(self) -> str:
        """

        Runs pyret testsuite for this handin, returning the results

        :returns: the results of the testsuite as a string
        :rtype: str

        """
        assert self.question.test_path is not None
        test_filepath = self.question.test_path
        if not pexists(test_filepath):
            return 'No testsuite for this question'

        cmd = [pjoin(BASE_PATH, 'tabin', 'pyret-test'),
               test_filepath, self.filepath]
        return subprocess.check_output(cmd).decode('utf-8')

        # if not pexists(filepath):
        #     return 'No handin or missing handin'

        # test_dir = pjoin(self.handin_path, 'TA_TESTS')
        # if not pexists(test_dir):
        #     os.mkdir(test_dir)

        # if not pexists(self.question.test_path):
        #     return 'No test file for this question: contact HTA'

        # test_filepath = pjoin(test_dir,
        #                       os.path.split(self.question.test_path)[1])
        # if not pexists(test_filepath):
        #     shutil.copyfile(self.question.test_path, test_filepath)

        #     with locked_file(test_filepath, 'r') as f:
        #         lines = f.readlines()
        #         relpath = os.path.relpath(filepath, test_dir)
        #         lines.insert(0, f'import file("{relpath}") as SC\n')

        #     with locked_file(test_filepath, 'w') as f:
        #         f.writelines(lines)

        # cmd = [pjoin(BASE_PATH, 'tabin', 'pyret-test'),
        #        filepath, test_filepath, test_dir]

        # return subprocess.check_output(cmd).decode('utf-8')

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

    Get list of started assignments

    :returns: list of started assignments (unloaded)
    :rtype: List[Assignment]

    """
    assignments = []
    for key in sorted(asgn_data['assignments']):
        asgn = Assignment(key, load_if_started=False)
        if asgn.started:
            assignments.append(asgn)

    return assignments


def all_asgns() -> List[Assignment]:
    """

    Get list of all assignments

    :returns: list of all assignments (unloaded)
    :rtype: List[Assignment]

    """
    assignments = []
    for key in sorted(asgn_data['assignments']):
        asgn = Assignment(key, load_if_started=False)
        assignments.append(asgn)

    return assignments
