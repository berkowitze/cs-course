import csv
import zipfile
import yagmail

from typing import Set, Iterable
from classes import *
from custom_types import *
from hta_helpers import *
from datetime import datetime

anon_map_path: str = pjoin(BASE_PATH, 'hta/grading/anonymization')
handin_base_path: str = pjoin(BASE_PATH, 'hta/handin/students')

grade_base_path: str = pjoin(BASE_PATH, 'hta/grades')

final_grade_path: str = pjoin(BASE_PATH, 'ta/grading/grades')
GradeData = Tuple[str, Optional[RawGrade], Grade, str]


class HTA_Assignment(Assignment):
    """

    HTA version of Assignment (TA version is just Assignment)
    initialized with full homework name

    :ivar emails_sent: whether or not grade reports have been sent
                       for this assignment
    :vartype emails_sent: bool
    :ivar groups_loaded: whether or not group data has been loaded for this
                         assignment (False by default)
    :vartype groups_loaded: bool
    :ivar handin_path: path that handins for this assignment are in
    :vartype handin_path: str


    **Example**:

    >>> HTA_Assignment("Homework 3")

    .. automethod:: __init__

    .. automethod:: _generate_report

    """

    def __init__(self, *args, **kwargs) -> None:
        """

        creates HTA_Assignment

        :param \*args: any args to use in Assignment initialization
        :param \*\*kwargs: any keyword args to use in Assignment initialization
        """

        super().__init__(*args, **kwargs)
        # initialize TA version of Assignment class

        # load list of logins that handed in this assignment
        if self.started and self.loaded:
            with locked_file(self.anon_path) as f:
                d = json.load(f)

            self.login_handin_list = list(d.keys())

        self.handin_path = handin_base_path

        assert pexists(grade_base_path), \
            f'{grade_base_path} directory does not exist'

        self.sfiles_base_path = pjoin(s_files_base_path, self.mini_name)

        # We also use emails_sent as boolean value for whether grading has
        # completed or not (in addition to already sending the emails)
        self.emails_sent = self._json['emails_sent']
        self.groups_loaded = False

    def load(self) -> None:
        super().load()
        if self.anonymous:
            jpath = f'{self.mini_name}.json'
            self.anon_path = pjoin(anon_map_path, jpath)
        else:
            assert self.anon_path != '', 'error in anon path tell eli'
        with locked_file(self.anon_path) as f:
            data: Dict[str, int] = json.load(f)

        self._login_to_id_map: Dict[str, int] = data
        self._id_to_login_map: Dict[int, str] = {data[k]: k for k in data}

    def init_grading(self) -> None:
        """

        starts grading for this assignment

        """
        assert not self.started, f'Cannot init_grading on started {self}'
        self._check_startable()
        self._setup_anon_map()
        self._create_logs()
        self._transfer_handins()
        self._setup_blocklist()
        self._setup_grade_dir()
        self._record_start()
        print('Grading started.')

    def _check_startable(self) -> None:
        """

        checks that grading can start for the assignment

        :raises OSError: proper files do not exist for the assignment

        """
        if not pexists(self.rubric_path):
            err = (
                   f'Rubric directory for {self} does not exist '
                   f'(should be in {self.rubric_path})'
                   )
            raise OSError(err)

        for i in range(len(self._json['questions'])):
            qn = i + 1
            rubric_filepath = pjoin(self.rubric_path,
                                    f'q{qn}.json')
            if not pexists(rubric_filepath):
                err = (
                       f'{self} does not have rubric for {qn} '
                       f'(should be in {rubric_filepath})'
                      )
                raise OSError(err)

            try:
                rubric_check(rubric_filepath)
            except (AssertionError, KeyError) as e:
                err = f'Invalid rubric file {rubric_filepath}'
                raise ValueError(err) from e

        if not pexists(self.bracket_path):
            print(f'Warning: No bracket for {self.full_name}.')

    def _setup_anon_map(self):
        """

        setup anonymous mapping (login -> id) for this assignment
        generates random unique ID for each student that submitted
        and puts the data into a JSON file in ta/grading/data/anonymization
        or hta/grading/anonymization (depending on if the assignment is
        being graded anonymously or not).

        """
        sub_paths = []
        anon_map: Dict[str, int] = {}

        file_sys = os.walk(self.handin_path)
        students = next(file_sys)[1]
        submitted_students = []
        for i, student in enumerate(students):
            final_path = latest_submission_path(self.handin_path,
                                                student,
                                                self.mini_name)
            if final_path is None:
                continue  # student didn't submit for this hw

            submitted_students.append(student)

        idents = list(range(1, len(submitted_students) + 1))
        random.shuffle(idents)
        for i, login in enumerate(submitted_students):
            anon_map[login] = idents[i]

        with locked_file(self.anon_path, 'w') as f:
            json.dump(anon_map, f, sort_keys=True, indent=2)

        self._login_to_id_map: Dict[str, int] = anon_map
        self._id_to_login_map: Dict[int, str]
        self._id_to_login_map = {anon_map[k]: k for k in anon_map}
        self.login_handin_list: List[str] = submitted_students

    def _create_logs(self):
        """

        creates a log file for this assignment. should only be called while
        creating the assignment

        :raises ValueError: log file has already been created

        """
        if pexists(self.log_path):
            e = 'create_log called on a log that already exists'
            raise ValueError(e)
        else:
            os.makedirs(self.log_path)

        # create a log file for each question in the assignment
        log_data = []
        for ident in self._id_to_login_map:
            log_item: LogItem = {'id': ident, 'flag_reason': None,
                                 'complete': False, 'grader': None}
            log_data.append(log_item)

        logs = []
        for i, q in enumerate(self._json['questions']):
            qn = i + 1
            log_filepath = pjoin(self.log_path,
                                 f'q{qn}.json')

            with locked_file(log_filepath, 'w') as f:
                json.dump(log_data, f)

    def _setup_blocklist(self) -> None:
        """

        sets up blocklist for assignment (puts data into JSON file)

        """
        mapping = get_blocklists()
        data: Dict[str, List[int]] = defaultdict(list)
        for ta in mapping:
            for student in mapping[ta]:
                try:
                    ident = self.login_to_id(student)
                    data[ta].append(ident)
                except ValueError:  # no submission for this student
                    continue

        with locked_file(self.blocklist_path, 'w') as f:
            json.dump(data, f, indent=2, sort_keys=True)

    def _setup_grade_dir(self):
        """

        make required directories for storing student grades

        """
        for i, q in enumerate(self._json['questions']):
            qn = i + 1
            grade_path = pjoin(self.grade_path, f'q{qn}')
            os.makedirs(grade_path)

    def login_to_id(self, login: str) -> int:
        """

        Get anonymous ID of student by login

        :param login: Student CS login
        :type login: str
        :returns: Anonymous ID for student by login
        :rtype: int
        :raises: ValueError: Student has no anonymous ID for this assignment

        """

        if login in self._login_to_id_map:
            return self._login_to_id_map[login]

        with locked_file(self.anon_path) as f:
            data = json.load(f)
        try:
            ident = data[login]
        except KeyError:
            raise ValueError(f'login {login} does not exist in map for {self}')
        else:
            self._login_to_id_map[login] = ident
            self._id_to_login_map[ident] = login
            return ident

    def id_to_login(self, ident: int) -> str:  # override Assignment version
        """

        Get anonymous ID of student by login

        :param ident: Student anonymous ID for this assignment
        :type ident: int
        :returns: Login of student with ident id
        :rtype: str
        :raises: ValueError: No student with anon ID for this assignment

        """
        if ident in self._id_to_login_map:
            return self._id_to_login_map[ident]

        with locked_file(self.anon_path) as f:
            data = json.load(f)

        for login in data:
            if data[login] == ident:
                self._id_to_login_map[ident] = login
                self._login_to_id_map[login] = ident
                return login

        raise ValueError(f'id {ident} does not exist in map for {self}')

    def _transfer_handins(self) -> None:
        """

        takes handins from the handin folder, anonymizes them, and puts them
        in the TA folder. zip files are extracted to a new folder


        :raises ValueError: No submission for student in handin directory
                            (empty directory login/mini_name)

        """
        os.mkdir(self.files_path)
        for student in self._login_to_id_map:
            ident = self._login_to_id_map[student]
            sub_path = latest_submission_path(self.handin_path,
                                              student,
                                              self.mini_name)
            assert sub_path is not None, \
                f'invalid student {student} in anon map'

            dest = pjoin(self.files_path, f'student-{ident}')
            shutil.copytree(sub_path, dest)
            for f in os.listdir(dest):
                fname, ext = os.path.splitext(f)
                if ext == '.zip':
                    full_path = pjoin(dest, f)
                    new_fname = f'{fname}-extracted'
                    new_dest = pjoin(dest, new_fname)
                    with zipfile.ZipFile(full_path, 'r') as zf:
                        zf.extractall(new_dest)

    def add_new_handin(self, login: str) -> None:
        """

        Add new handin to this Assignment

        :param login: student CS login of the new handin
        :type login: str
        :raises ValueError: message specific

        """
        try:
            ident = self.login_to_id(login)
            has_handin = True
        except ValueError:
            has_handin = False

        if has_handin:
            has_graded_handin = False
            for q in self.questions:
                try:
                    h = q.get_handin_by_id(ident)
                    if h.complete:
                        has_graded_handin = True
                        break

                except ValueError:
                    # no handin for this question
                    pass

            if has_graded_handin:
                base = (
                        f'Student {login} resubmitted {self.full_name} after '
                        f'grading completed. Not adding to grading app; '
                        f'handle manually.'
                       )
                raise ValueError(base)
            else:
                self.delete_student_handin(login, override=True)

        ident = self.__get_new_id()
        final_path = latest_submission_path(self.handin_path,
                                            login,
                                            self.mini_name)
        if final_path is None:
            raise ValueError(f"No handin for {login}")

        with json_edit(self.anon_path) as data:
            data[login] = ident

        dest = pjoin(self.files_path, f'student-{ident}')
        shutil.copytree(final_path, dest)
        for f in os.listdir(dest):
            fname, ext = os.path.splitext(f)
            if ext == '.zip':
                full_path = pjoin(dest, f)
                new_fname = f'{fname}-extracted'
                new_dest = pjoin(dest, new_fname)
                with zipfile.ZipFile(full_path, 'r') as zf:
                    zf.extractall(new_dest)

        self._id_to_login_map[ident] = login
        self._login_to_id_map[login] = ident

        self._load_questions()
        for question in self.questions:
            question.add_handin_to_log(ident)

    def __get_new_id(self) -> int:
        """

        get an unused anonymous id to use

        :returns: anonymous id
        :rtype: int

        """
        with locked_file(self.anon_path) as f:
            data = json.load(f)

        if len(data) > 0:
            return max(data.values()) + 1
        else:
            return 0

    def delete_student_handin(self,
                              login: str,
                              override: bool = False) -> None:
        """

        remove a student's handins for this assignment

        :param login: login of the student's handins to remove
        :type login: str
        :param override: required to be True to operate, just a check to make
                         sure this method isn't used lightly.
                         defaults to ``False``
        :type override: bool, required

        """
        if not override:
            print(f'Confirm removal of {login} handin from grading app [y/n]')
            if input('> ').lower() != 'y':
                return

        try:
            ident = self.login_to_id(login)
            print(f'Deleting ID {ident} from {self.full_name}')
        except ValueError:
            e = f'{login} does not have a handin that\'s being graded'
            raise ValueError(e)

        dest = pjoin(self.files_path, f'student-{ident}')
        if pexists(dest):
            shutil.rmtree(dest)

        with json_edit(self.anon_path) as data:
            data.pop(login)

        with json_edit(self.blocklist_path) as data:
            for k in data:
                data[k] = [i for i in data[k] if i != ident]

        for q in self.questions:
            try:
                h = q.get_handin_by_id(ident)
            except ValueError:
                print(f'Could not delete handin for {q}')
                continue
            if pexists(h.grade_path):
                os.remove(h.grade_path)

            # remove from log
            with locked_file(q.log_filepath) as f:
                data = json.load(f)

            new_data = [d for d in data if d['id'] != ident]

            with locked_file(q.log_filepath, 'w') as f:
                json.dump(new_data, f, indent=2, sort_keys=True)

        self._id_to_login_map.pop(ident, None)
        self._login_to_id_map.pop(login, None)

    def load_groups(self):
        """

        load group data for this assignment (must be a group assignment)

        :raises AssertionError: run on non-group assignment

        """
        assert self.group_asgn, 'cannot get project partner of non group asgn'
        with locked_file(self.proj_dir) as f:
            self.groups = json.load(f)

        self.groups_loaded = True

    def proj_partners(self, student: str) -> List[str]:
        """

        get list of partners for student on this assignment (must be a group
        assignment)

        :param student: CS login for student
        :type student: str
        :returns: list of CS logins of the student's partners
        :rtype: List[str]
        :raises ValueError: no partner data for student
        :raises AssertionError: run on non-group assignment

        """
        assert self.group_asgn, 'cannot get project partner of non group asgn'
        if not self.groups_loaded:
            self.load_groups()

        for group in self.groups:
            if student in group:
                ogs = group[:]
                ogs.remove(student)
                return ogs

        raise ValueError(f'Student {student} does not have partner')

    def all_handin_logins(self) -> Set[str]:
        logins: Set[str] = set()
        for q in self.questions:
            logins = logins.union(self.id_to_login(h.id) for h in q.handins)

        return logins

    def _group_check(self):
        assert self.group_asgn
        students = self.all_handin_logins()
        for student in students:
            partners = self.proj_partners(student)
            for p in partners:
                if p in students:
                    pass

    def get_handin_dict(self,
                        students: Optional[List[str]] = None
                        ) -> Dict[str, List[Optional[Handin]]]:
        """

        get a dictionary of students' handins for this assignment

        :param students: list of student logins for whom to collect handins.
                         defaults to ``None``
        :type students: Optional[List[str]]
        :returns: dictionary of student login keys and list of handins for
                  this assignment as the values
        :rtype: Dict[str, List[Handin]]

        """
        d: Dict[str, List[Optional[Handin]]] = defaultdict(list)
        if students is None:
            handin_logins = self.all_handin_logins()
        else:
            handin_logins = set(students)

        for student in handin_logins:
            if self.group_asgn:
                ohs = handin_logins.copy()
                ohs.remove(student)
                partners = self.proj_partners(student)
                for p in partners:
                    if p in ohs:
                        e = f'Multiple students in {student} group submitted'
                        raise ValueError(e)
            try:
                anon_id = self.login_to_id(student)
                if (int(anon_id) not in handin_logins) and self.group_asgn:
                    raise ValueError('All good')

            except ValueError:
                if self.group_asgn:
                    partners = self.proj_partners(student)
                    if partners == []:
                        d[student] = [None for h in self.questions]
                        continue
                    elif len(partners) == 1:
                        d[student] = d[partners[0]]
                    else:
                        e = (
                             f'currently doesn\'t work for 3 person groups'
                             f' (notify authorities) (attempt for {student}'
                            )

                        raise NotImplementedError(e)
                else:
                    # no handin for any question
                    d[student] = [None for h in self.questions]
                    continue

            for q in self.questions:
                handin: Optional[Handin]
                try:
                    handin = q.get_handin_by_id(anon_id)
                except ValueError:
                    # student didn't hand in this question
                    print(f'No {self.full_name} handin for {student}')
                    handin = None

                d[student].append(handin)

        return d

    def get_report_data(self) -> List[GradeData]:
        """

        get list of information for reports for this assignment

        :returns: a list of 3-tuples:
                  (login, <numeric grade data>, <grade report>)
                  with one 3-tuple for each student that was graded on this
                  assignment. grade data is the RawGrade representation of
                  the student's grade, and grade report is the string of
                  the student's grade report
        :rtype: List[Tuple[str, RawGrade, Grade, str]]

        """
        logins = student_list()
        handins = self.get_handin_dict(logins)
        data = []
        for student in handins:
            d = self._generate_report(handins=handins[student],
                                      login=student,
                                      write_files=False)
            data.append(d)

        return data

    def generate_all_reports(self):
        """
        :raises: NotImplementedError
        """
        # call _generate_report with data, student_id, soft at some point
        raise NotImplementedError

    def report_already_generated(self, login: str) -> bool:
        """

        returns whether or not a report and grade have already been generated
        for this student for this assignment

        :param login: CS login of student
        :type login: str
        :returns: whether or not a report has been generated for this student
        :rtype: bool

        """
        report_fp = pjoin(grade_base_path, login, self.mini_name, 'report.txt')
        return pexists(report_fp)

    def generate_one_report(self,
                            login: str,
                            write_files: bool = False
                            ) -> GradeData:
        """

        generate full grade report for a single student for this assignment

        :param login: login to generate report for
        :type login: str
        :param soft: whether or not to only return the report data rather than
                     writing it to a file. defaults to ``True``
        :type soft: bool, optional
        :param overrides: whether or not a report should be written as an
                          override report (for grade complaints).
                          defaults to ``False``
        :type overrides: bool, optional
        :returns: a (login, <numeric grade data>, <grade report>) 3-tuple
        :rtype: Tuple[str, RawGrade, Grade, str]

        """
        ident = self.login_to_id(login)
        handins: List[Optional[Handin]] = []
        for q in self.questions:
            try:
                handins.append(q.get_handin_by_id(ident))
            except ValueError:
                handins.append(None)

        return self._generate_report(handins, login, write_files=write_files)

    def _get_path_to_code(self, login: str) -> str:
        """
        """
        try:
            handin_id = self.login_to_id(login)
        except ValueError as e:
            if self.group_asgn:
                partners = self.proj_partners(login)
                for partner in partners:
                    if partner in self._login_to_id_map:
                        handin_id = self.login_to_id(partner)
                        break
                else:
                    raise ValueError(f'No login/partner for {login}') from e
            else:
                raise

        return pjoin(self.files_path, f'student-{handin_id}')

    def _generate_report(self,
                         handins: List[Optional[Handin]],
                         login: str,
                         write_files: bool = False
                         ) -> GradeData:
        """

        given a list of Handins and student login,
        generate a report for that student.
        the third argument, soft, represents whether or not to write the grades
        to corresponding grade files. returns the students (nonanonymous) id,
        the grade (dictionary), and the text of the report.

        :param handins: List of Handins/None if no Handin for that question
        :type handins: List[Optional[Handin]]
        :param login: login of student generating report
        :type login: str
        :param write_files: whether or not to write generated grade reported
                            data to report files.
                            True: writes to files and returns 4-tuple
                            False: returns 4-tuple
                     rather than writing it into files; defaults to ``False``
        :type write_files: bool, optional
        :returns: a (login, raw student grade, grade report) 3-tuple
        :rtype: Tuple[str, RawGrade, Grade, str]

        **Note**: This method needs a *lot* of cleanup. Ideas in source code.

        """
        # this needs some serious cleanup
        # Cleanup todos:
        # TODO: separate string generation and writing logic
        # TODO: make lateness a handin attribute (means it needs to be
        #       available on TA side of things, so probably through log files)
        # TODO: clean up getting anonymous id for both group and non group asgn
        # TODO: put generation of rubric summary in different method
        # TODO: put override/backup/general report location files in method

        grade_dir = pjoin(grade_base_path, login, self.mini_name)
        report_path = pjoin(grade_dir, 'report.txt')
        summary_path = pjoin(grade_dir, 'rubric-summary.txt')
        grade_path = pjoin(grade_dir, 'grade.json')
        backup_dir = pjoin(grade_dir, 'grade-backups')

        final_path = latest_submission_path(self.handin_path,
                                            login,
                                            self.mini_name)

        late = (final_path is not None and '-late' in final_path)

        if write_files and pexists(grade_path):
            try:
                os.mkdir(backup_dir)
            except FileExistsError:
                pass

            dt_str = datetime.now().strftime('%Y-%m-%d--%H-%M-%S')
            report_bfp = pjoin(backup_dir, f'report--{dt_str}.txt')
            summary_bfp = pjoin(backup_dir, f'rubric-summary--{dt_str}.txt')
            grade_bfp = pjoin(backup_dir, f'grade--{dt_str}.json')

            shutil.copy(report_path, report_bfp)
            shutil.copy(summary_path, summary_bfp)
            shutil.copy(grade_path, grade_bfp)

        summary_str = ''
        for handin in handins:
            if handin is None:  # no handin for this question
                continue

            summary_str += f'{handin.question}\n'
            cmd = [pjoin(BASE_PATH, 'tabin', 'rubric-info'),
                   handin.grade_path]
            try:
                p_sum = subprocess.check_output(cmd).decode()
            except subprocess.CalledProcessError:
                p_sum = 'Error getting summary'

            summary_str += p_sum
            summary_str += ('-' * 20)

        # make this more rigorous later
        raw_grade: RawGrade = get_empty_raw_grade(self)
        full_string = f'{self.full_name} grade report for {login}\n\n'
        for i, handin in enumerate(handins):
            if handin is None:
                full_string += f'Question {i + 1}: No handin\n\n'
                continue

            report_text, report_grade = handin.generate_grade_report()
            full_string += report_text
            for key in report_grade:
                if key in raw_grade and raw_grade[key] is not None:
                    raw_grade[key] += report_grade[key]
                else:
                    raw_grade[key] = report_grade[key]

        final_grade: Grade = determine_grade(raw_grade, late, self)

        grade_string = 'Grade Summary\n'
        if isinstance(final_grade, dict):
            for key in final_grade:
                grade_string += f'  {key}: {final_grade[key]}\n'
        elif isinstance(final_grade, (int, float, str)):
            grade_string += f'  Grade: {str(final_grade)}\n'

        if late:
            grade_string += '(Late deduction applied)'

        full_string += f'\n{grade_string}\n'
        if not write_files:
            return login, raw_grade, final_grade, full_string

        # write appropriate files
        if not os.path.isdir(grade_dir):
            assert not pexists(grade_dir)
            os.makedirs(grade_dir)

        try:
            anon_ident = self.login_to_id(login)
            code_src = pjoin(self.files_path, f'student-{anon_ident}')
            code_dest = pjoin(grade_dir, 'code')
            os.symlink(code_src, code_dest)
        except (ValueError, OSError):
            pass

        with locked_file(report_path, 'w') as f:
            f.write(full_string)

        with locked_file(grade_path, 'w') as f:
            json.dump(final_grade, f, indent=2, sort_keys=True)

        with locked_file(summary_path, 'w') as f:
            f.write(summary_str)

        return login, raw_grade, final_grade, full_string

    def send_emails(self,
                    yag: yagmail.sender.SMTP,
                    logins: Optional[List[str]] = None
                    ) -> None:
        """

        sends email reports to a list of students

        :param yag: a yagmail SMTP instance (should have email send_from from
                    assignments.json)
        :type yag: yagmail.sender.SMTP
        :param logins: if None, sends to all students who handed assignment
                       in. otherwise, sends to all students in this list
        :type logins: Optional[List[str]]

        """
        if logins is None:
            to_send = self.login_handin_list
        else:
            to_send = logins

        data = []
        # preloads this list to make sure there are no errors that will come up
        # halfway through sending emails
        for login in to_send:
            email = login_to_email(login)
            rep = self.get_generated_grade_report(login)
            data.append((login, email, rep))

        subject = f'{self.full_name} Grade Report'
        for login, email, report in data:
            if CONFIG.test_mode:
                send_to = CONFIG.test_mode_emails_to
            else:
                send_to = email

            print(f'Sending {login} report to {send_to}')
            yag.send(to=send_to,
                     subject=subject,
                     contents=[f'<pre>{report}</pre>'])

    def get_generated_grade_report(self, login: str) -> str:
        grade_fp = pjoin(grade_base_path, login, self.mini_name, 'report.txt')
        with locked_file(grade_fp) as f:
            grade = f.read()

        return grade

    def reset_grading(self, confirm: bool, quiet: bool = False) -> None:
        """

        remove the assignment log; there is no recovering the data.
        grade files *are* deleted.
        rubric files *are not* deleted. do that by hand if needed.

        :param confirm: confirmation boolean (to indicate knowledge of what
                        this method does)
        :type confirm: bool

        """
        def printer(s):
            if not quiet:
                print(s)

        if not confirm:
            printer("Must call reset_grading with boolean confirm argument")
            printer(f"{self} not reset.")
            return
        try:
            shutil.rmtree(self.log_path)
            printer('Removed log path...')
        except Exception:
            pass
        try:
            shutil.rmtree(self.grade_path)
            printer('Removed grade path...')
        except Exception:
            pass
    #try:
        shutil.rmtree(self.files_path)
     #       printer('Removed student files path...')
	#except Exception:
	    #pass
        try:
            os.remove(self.blocklist_path)
            printer('Removed blocklists...')
        except Exception:
            pass
        try:
            os.remove(self.sfiles_base_path)
            printer('Removed TA versions of the handins...')
        except Exception:
            pass
        try:
            os.remove(self.anon_path)
            try:
                os.remove(pjoin(anon_base_path, f'{self.mini_name}.json'))
            except OSError:
                pass

            printer('Removed anonymization mapping...')
        except Exception:
            pass

        # now set grading_started in the assignments.json to False
        with json_edit(asgn_data_path) as data:
            data['assignments'][self.full_name]['grading_started'] = False
            data['assignments'][self.full_name]['grading_completed'] = False
            data['assignments'][self.full_name]['emails_sent'] = False

        self.started = False
        printer('Assignment records removed.')

    @require_resource()
    def _record_start(self) -> None:
        """

        sets grading_started in assignments.json to true for this assignment

        """
        with json_edit(asgn_data_path) as data:
            data['assignments'][self.full_name]['grading_started'] = True

        self.started = True

    @require_resource()
    def record_finish(self):
        """

        sets grading_completed in assignments.json to true for this assignment

        """
        with json_edit(asgn_data_path) as data:
            asgn = asgn_data['assignments'][self.full_name]
            asgn['grading_completed'] = True

    @require_resource
    def set_emails_sent(self):
        """

        sets emails_sent in assignments.json to true for this assignment

        """
        with json_edit(asgn_data_path) as data:
            data['assignments'][self.full_name]['emails_sent'] = True

    def deanonymize(self):
        """

        deanonymize this assignment so TAs can regrade

        """
        # step 1 : move anonymization file from HTA to TA
        dest = pjoin(anon_base_path, f'{self.mini_name}.json')
        src = self.anon_path
        os.rename(src, dest)

        # step 2 : give TAs links to the grade files
        # use defaultdict so don't have to check if key exists
        ta_handins = defaultdict(lambda: set())
        for question in self.questions:
            for handin in question.handins:
                if handin.grader:
                    ta_handins[handin.grader].add(handin.id)

        for ta in ta_handins:
            d_base = pjoin(final_grade_path, ta, self.mini_name)
            ids = ta_handins[ta]
            for ident in ids:
                login = self.id_to_login(ident)
                src = pjoin(grade_base_path, login, self.mini_name)
                dest = pjoin(d_base, login)
                if not pexists(d_base):
                    os.makedirs(d_base)

                os.symlink(src, dest)

        # step 3 : update json
        with json_edit(asgn_data_path) as data:
            data['assignments'][self.full_name]['anonymous'] = False

    @is_started
    def table_summary(self) -> List[Tuple[str, int, int, int]]:
        """

        get a summary of the questions on this assignment

        :returns: list of (question filename, # handins, # graded, # flagged)
                  4-tuples
        :rtype: List[Tuple[str, int, int, int]]

        """
        rows = []
        for question in self.questions:
            row = (question.code_filename,
                   question.handin_count,
                   question.completed_count,
                   question.flagged_count)
            rows.append(row)

        return rows

    def max_grades(self) -> Dict[str, int]:
        """ returns dictionary of `category` -> `max category grade` """
        maxes = defaultdict(int)
        for q in self.questions:
            rub = q.copy_rubric()
            for cat in rub['rubric']:
                cat_val = 0
                for item in rub['rubric'][cat]['rubric_items']:
                    opts = item['options']
                    cat_val += max([opt['point_val'] for opt in opts])

                maxes[cat] += cat_val

        return maxes

    def __repr__(self):
        return f'HTA-{super().__repr__()}'


def get_hta_asgn_list() -> List[HTA_Assignment]:
    """

    Get list of all assignments

    :returns: list of all assignments (unloaded)
    :rtype: List[HTA_Assignment]

    """
    assignments = []
    for key in sorted(asgn_data['assignments'].keys()):
        asgn = HTA_Assignment(key, load_if_started=False)
        assignments.append(asgn)

    return assignments
