import csv
import zipfile
from typing import Set

import yagmail

from classes import *
from custom_types import *
from hta_helpers import *

anon_map_path: str = pjoin(BASE_PATH, 'hta/grading/anonymization')
handin_base_path: str = pjoin(BASE_PATH, 'hta/handin/students')

grade_base_path: str = pjoin(BASE_PATH, 'hta/grades')

final_grade_path: str = pjoin(BASE_PATH, 'ta', 'grading', 'grades')


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

    def __init__(self, *args, **kwargs):
        """[summary]

        creates HTA_Assignment

        :param \*args: any args to use in Assignment initialization
        :param \*\*kwargs: any keyword args to use in Assignment initialization
        """
        # initialize TA version of Assignment class
        super().__init__(*args, **kwargs)

        if self.anonymous:
            jpath = f'{self.mini_name}.json'
            self.anon_path = pjoin(anon_map_path, jpath)
        else:
            assert self.anon_path != '', 'error with anon path tell eli'

        if self.started:  # load list of logins that handed in this assignment
            with locked_file(self.anon_path) as f:
                d = json.load(f)

            self.login_handin_list = list(d.keys())

        self.handin_path = handin_base_path

        assert os.path.exists(grade_base_path), \
            f'{grade_base_path} directory does not exist'
        self.emails_sent = self._json['sent_emails']
        self.groups_loaded = False

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
        if not os.path.exists(self.rubric_path):
            err = (
                   f'Rubric directory for "{self}" does not exist '
                   f'(should be in {self.rubric_path})'
                   )
            raise OSError(err)

        for i in range(len(self._json['questions'])):
            qn = i + 1
            rubric_filepath = pjoin(self.rubric_path,
                                    f'q{qn}.json')
            if not os.path.exists(rubric_filepath):
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

        if not os.path.exists(self.bracket_path):
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

        idents = range(1, len(submitted_students) + 1)
        random.shuffle(idents)
        for i, login in enumerate(submitted_students):
            anon_map[login] = idents[i]

        with locked_file(self.anon_path, 'w') as f:
            json.dump(anon_map, f, sort_keys=True, indent=2)

        self.__login_to_id_map: Dict[str, int]
        self.__login_to_id_map = anon_map
        self.__id_to_login_map: Dict[int, str]
        self.__id_to_login_map = {anon_map[k]: k for k in anon_map}

    def _create_logs(self):
        """

        creates a log file for this assignment. should only be called while
        creating the assignment

        :raises ValueError: log file has already been created

        """
        if os.path.exists(self.log_path):
            e = 'create_log called on a log that already exists'
            raise ValueError(e)
        else:
            os.makedirs(self.log_path)

        # create a log file for each question in the assignment
        log_data = []
        for ident in self.__id_to_login_map:
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
        with locked_file(self.anon_path) as f:
            data = json.load(f)
        try:
            return int(data[login])
        except KeyError:
            raise ValueError(f'login {login} does not exist in map for {self}')

    def id_to_login(self, id: int) -> str:
        """

        Get anonymous ID of student by login

        :param ident: Student anonymous ID for this assignment
        :type ident: int
        :returns: Login of student with ident id
        :rtype: str
        :raises: ValueError: No student with anon ID for this assignment

        """
        with locked_file(self.anon_path) as f:
            data = json.load(f)

        for k in data:
            if data[k] == id:
                return str(k)

        raise ValueError(f'id {id} does not exist in map for {self}')

    def _transfer_handins(self) -> None:
        """

        takes handins from the handin folder, anonymizes them, and puts them
        in the TA folder. zip files are extracted to a new folder


        :raises ValueError: No submission for student in handin directory
                            (empty directory login/mini_name)

        """
        for student in self.__login_to_id_map:
            ident = self.__login_to_id_map[student]
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
            has_graded_handin = False
            for q in self.questions:
                try:
                    h = q.get_handin_by_id(ident)
                    if h.complete:
                        has_graded_handin = True

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

            self.delete_student_handin(login, override=True)
        except ValueError:
            pass

        rand_id = self.__get_new_id()
        final_path = latest_submission_path(self.handin_path,
                                            login,
                                            self.mini_name)
        if final_path is None:
            raise ValueError(f"No handin for {login}")
        elif not os.path.exists(final_path):
            e = 'latest_submission_path returned nonexisting path'
            raise ValueError(e)

        with locked_file(self.anon_path) as f:
            data = json.load(f)

        data[login] = rand_id
        with locked_file(self.anon_path, 'w') as f:
            json.dump(data, f, indent=2, sort_keys=True)

        dest = pjoin(self.files_path, f'student-{rand_id}')
        shutil.copytree(final_path, dest)
        for f in os.listdir(dest):
            fname, ext = os.path.splitext(f)
            if ext == '.zip':
                full_path = pjoin(dest, f)
                new_fname = f'{fname}-extracted'
                new_dest = pjoin(dest, new_fname)
                with zipfile.ZipFile(full_path, 'r') as zf:
                    zf.extractall(new_dest)

        self.__load_questions()
        for question in self.questions:
            question.add_handin_to_log(rand_id)

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
            print(f'DELETING {ident}')
        except ValueError:
            e = f'{login} does not have a handin that\'s being graded'
            raise ValueError(e)

        dest = pjoin(self.files_path, f'student-{ident}')
        if os.path.exists(dest):
            shutil.rmtree(dest)

        with locked_file(self.anon_path) as f:
            data = json.load(f)

        data.pop(login)

        with locked_file(self.anon_path, 'w') as f:
            json.dump(data, f, indent=2, sort_keys=True)

        with locked_file(self.blocklist_path) as f:
            data = json.load(f)

        for k in data:
            data[k] = [i for i in data[k] if i != ident]

        with locked_file(self.blocklist_path, 'w') as f:
            json.dump(data, f, indent=2, sort_keys=True)

        for q in self.questions:
            try:
                h = q.get_handin_by_id(ident)
            except ValueError:
                print(f'Could not delete {q}')
                continue
            if os.path.exists(h.grade_path):
                os.remove(h.grade_path)

            with locked_file(q.log_filepath) as f:
                data = json.load(f)

            data = [d for d in data if d['id'] != ident]
            with locked_file(q.log_filepath, 'w') as f:
                json.dump(data, f, indent=2, sort_keys=True)

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
            handins = self.questions[0].handins
            handin_logins = [self.id_to_login(h.id) for h in handins]
        else:
            handin_logins = students

        for student in handin_logins:
            if self.group_asgn:
                ohs = handin_logins[:]
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

    def get_report_data(self) -> List[Tuple[str, RawGrade, str]]:
        """

        get list of information for reports for this assignment

        :returns: a list of 3-tuples:
                  (login, <numeric grade data>, <grade report>)
                  with one 3-tuple for each student that was graded on this
                  assignment. grade data is the RawGrade representation of
                  the student's grade, and grade report is the string of
                  the student's grade report
        :rtype: List[Tuple[str, RawGrade, str]]

        """
        logins = student_list()
        handins = self.get_handin_dict(logins)
        data = []
        for student in handins:
            d = self._generate_report(handins=handins[student],
                                      login=student,
                                      soft=True,
                                      overrides=self.emails_sent)
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
        grade_dir = pjoin(grade_base_path, login, self.mini_name)
        report_path = pjoin(grade_dir, 'report.txt')
        grade_path = pjoin(grade_dir, 'grade.json')
        override_r_p = pjoin(grade_dir, 'report-override.txt')
        override_g_p = pjoin(grade_dir, 'grade-override.json')
        return os.path.exists(report_path) or os.path.exists(override_r_p)

    def generate_one_report(self,
                            login: str,
                            soft: bool = True,
                            overrides: bool = False
                            ) -> Tuple[str, RawGrade, str]:
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
        :rtype: Tuple[str, RawGrade, str]

        """
        ident = self.login_to_id(login)
        ps: List[Optional[Handin]] = []
        for q in self.questions:
            try:
                ps.append(q.get_handin_by_id(ident))
            except ValueError:
                ps.append(None)

        return self._generate_report(ps,
                                     login,
                                     soft=soft,
                                     overrides=overrides)

    def _generate_report(self,
                         handins: List[Optional[Handin]],
                         login: str,
                         soft=True,
                         overrides=False
                         ) -> Tuple[str, RawGrade, str]:
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
        :param soft: whether or not to only return the report information,
                     rather than writing it into files; defaults to ``True``
        :type soft: bool, optional
        :param overrides: whether or not to generate override reports
                          defaults to ``False``
        :type overrides: bool, optional
        :returns: a (login, raw student grade, grade report) 3-tuple
        :rtype: Tuple[str, RawGrade, str]

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
        if self.group_asgn:
            try:
                anon_ident = self.login_to_id(login)
            except ValueError:
                anon_ident = -1  # make this better to handin person's id
        else:
            try:
                anon_ident = self.login_to_id(login)
            except ValueError:
                # re-raise error if the student handed something in but doesn't
                # have an anonymous ID associated with them
                for handin in handins:
                    if handin is not None:
                        raise

            anon_ident = -1

        assert self.started  # at the very least grading should be started
        final_path = latest_submission_path(self.handin_path,
                                            login,
                                            self.mini_name)
        if final_path is not None and '-late' in final_path:
            late = True
        else:
            late = False

        grade_dir = pjoin(grade_base_path, login, self.mini_name)
        report_path = pjoin(grade_dir, 'report.txt')
        summary_path = pjoin(grade_dir, 'rubric-summary.txt')
        grade_path = pjoin(grade_dir, 'grade.json')
        override_r_p = pjoin(grade_dir, 'report-override.txt')
        override_g_p = pjoin(grade_dir, 'grade-override.json')
        if overrides and not soft:
            report_path = override_r_p
            grade_path = override_g_p
            if os.path.exists(report_path):
                # if making overrides would overwrite an override...
                print(f'Copying existing override for {login} to backup files')
                shutil.copy(report_path,
                            pjoin(grade_dir, 'report-override-backup.txt'))
                shutil.copy(grade_path,
                            pjoin(grade_dir, 'grade-override-backup.json'))

        if (os.path.exists(override_r_p) != os.path.exists(override_g_p)):
            err = (
                   f'For {self}, student {login} must have both '
                   f'report-override.txt and grade-override.json'
                  )
            raise TypeError(err)
        if os.path.exists(override_r_p):
            # by extension both exist because of last check
            with locked_file(override_r_p) as f:
                full_string = f.read()

            with locked_file(override_g_p) as f:
                given_grade = json.load(f)

            return login, given_grade, full_string

        summary_str = ''
        for handin in handins:
            if handin is None:
                continue
            summary_str += f'{handin.question}\n'
            cmd = [pjoin(BASE_PATH, 'tabin', 'cs111-rubric-info'),
                   handin.grade_path]
            try:
                p_sum = subprocess.check_output(cmd)
            except subprocess.CalledProcessError:
                p_sum = 'Error getting summary'

            summary_str += p_sum
            summary_str += ('-' * 20)

        # make this more rigorous later
        grade: RawGrade = get_empty_raw_grade(self)
        full_string = f'{self.full_name} grade report for {login}\n\n'
        for i, handin in enumerate(handins):
            if handin is None:
                full_string += f'Question {i + 1}: No handin\n\n'
                continue

            report_text, report_grade = handin.generate_grade_report()
            full_string += report_text
            for key in report_grade:
                if key in grade:
                    grade[key] += report_grade[key]
                else:
                    grade[key] = report_grade[key]

        final_grades: RawGrade = determine_grade(grade, late, self)

        grade_string = 'Grade Summary\n'
        for key in final_grades:
            grade_string += f'  {key}: {final_grades[key]}\n'

        if late:
            grade_string += '(Late deduction applied)'

        full_string += f'\n{grade_string}\n'

        if soft:
            return login, grade, full_string

        # write appropriate files
        if not os.path.isdir(grade_dir):
            assert not os.path.exists(grade_dir)
            os.makedirs(grade_dir)

        code_src = pjoin(self.files_path, f'student-{anon_ident}')
        code_dest = pjoin(grade_dir, 'code')
        with locked_file(report_path, 'w') as f:
            f.write(full_string)

        with locked_file(grade_path, 'w') as f:
            json.dump(final_grades, f, indent=2, sort_keys=True)

        with locked_file(summary_path, 'w') as f:
            f.write(summary_str)

        try:
            os.symlink(code_src, code_dest)
        except OSError:
            pass  # already exists, no need to do anything

        return login, final_grades, full_string

    def send_email(self,
                   login: str,
                   student_email: str,
                   yag: yagmail.sender.SMTP) -> None:
        """

        sends report email to student using yagmail

        :param login: CS login of student to send email to
        :type login: str
        :param student_email: email address of student (or recipient)
        :type student_email: str
        :param yag: yag instance to use to send the email
        :type yag: yagmail.Sender.SMTP

        """
        assert self.grading_completed
        subject = f'{self.full_name} Grade Report'
        gb = pjoin(grade_base_path, login, self.mini_name)
        if 'report-override.txt' in os.listdir(gb):
            f = pjoin(gb, 'report-override.txt')
        else:
            f = pjoin(gb, 'report.txt')

        print(f'Report sent to {login}')
        with locked_file(f) as fl:
            grade = fl.read()

        yag.send(to=student_email,
                 subject=subject,
                 contents=[f'<pre>{grade}</pre>'])

    def reset_grading(self, confirm: bool) -> None:
        """

        remove the assignment log; there is no recovering the data.
        grade files are *not* deleted. do that by hand if needed.

        :param confirm: confirmation boolean (to indicate knowledge of what
                        this method does)
        :type confirm: bool

        """
        if not confirm:
            e = "Must call reset_grading with boolean confirm argument"
            raise ValueError(e)
        try:
            shutil.rmtree(self.log_path)
            print('Removed log path...')
        except Exception:
            pass
        try:
            shutil.rmtree(self.grade_path)
            print('Removed grade path...')
        except Exception:
            pass
        try:
            shutil.rmtree(self.files_path)
            print('Removed student files path...')
        except Exception:
            pass
        try:
            os.remove(self.blocklist_path)
            print('Removed blocklists...')
        except Exception:
            pass
        try:
            os.remove(self.anon_path)
            try:
                os.remove(pjoin(anon_base_path, f'{self.mini_name}.json'))
            except OSError:
                pass

            print('Removed anonymization mapping...')
        except Exception:
            pass

        # now set grading_started in the assignments.json to False
        with locked_file(asgn_data_path) as f:
            data = json.load(f)

        data['assignments'][self.full_name]['grading_started'] = False
        with locked_file(asgn_data_path, 'w') as f:
            json.dump(data, f, indent=2, sort_keys=True)

        self.started = False
        print('Assignment records removed.')

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
        with locked_file(asgn_data_path) as f:
            asgn_data = json.load(f)

        asgn_data['assignments'][self.full_name]['grading_completed'] = True
        with locked_file(asgn_data_path, 'w') as f:
            json.dump(asgn_data, f, indent=2, sort_keys=True)

    def set_emails_sent(self):
        """

        sets sent_emails in assignments.json to true for this assignment

        """
        with locked_file(asgn_data_path) as f:
            d = json.load(f)

        d['assignments'][self.full_name]['sent_emails'] = True

        with locked_file(asgn_data_path, 'w') as f:
            json.dump(d, f, indent=2, sort_keys=True)

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
                if not os.path.exists(d_base):
                    os.makedirs(d_base)

                os.symlink(src, dest)

        # step 3 : update json
        with locked_file(asgn_data_path) as f:
            d = json.load(f)

        d['assignments'][self.full_name]['anonymous'] = False
        with locked_file(asgn_data_path, 'w') as f:
            json.dump(d, f, sort_keys=True, indent=2)

    def __repr__(self):
        return f'HTA-{super().__repr__()}'


class Course:
    def __init__(self, base_path: str = '/course/cs0111') -> None:
        assert os.path.exists(base_path), \
            f"base path {base_path} doesn't exist"
        self.base_path = base_path
        self.lab_base_path = pjoin(self.base_path,
                                   'ta/grading/data/labs')
        self.lab_exception_path = pjoin(BASE_PATH,
                                        'hta/lab_exceptions.txt')

    def get_grade_dict(self,
                       students: Optional[List[str]] = None,
                       tas: Optional[List[str]] = None
                       ) -> Dict[str, Dict[str, str]]:
        return {}

    def get_drill_data(self,
                       canvas_data_path: str,
                       columns: List[int],
                       students: Optional[List[str]] = None,
                       tas: Optional[List[str]] = None,
                       ) -> Dict[str, Tuple[Set[str], Set[str]]]:
        def email_to_user(u: str) -> str:
            return u.replace('@brown.edu', '')

        def descr_to_drill(d: str) -> str:
            return d.split(' ')[2]

        # (complete, incomplete)
        drill_data: Dict[str, Tuple[Set[str], Set[str]]]
        drill_data = defaultdict(lambda: (set(), set()))
        with open(canvas_data_path) as f:
            lines = list(csv.reader(f))

        header = lines[0]
        for line in lines[1:]:
            login = email_to_user(line[3])
            for col in range(6, 23):
                drill = f'drill{descr_to_drill(header[col])}'
                if drill == 'drill18':
                    continue

                if line[col] == '':
                    drill_data[login][1].add(drill)
                else:
                    float(line[col])
                    drill_data[login][0].add(drill)

        return drill_data

    def get_drill_grades(self,
                         canvas_data_path: str,
                         columns: List[int],
                         students: Optional[List[str]] = None,
                         tas: Optional[List[str]] = None
                         ) -> Dict[str, Grade]:
        data = self.get_drill_data(canvas_data_path, columns, students, tas)
        grades: Dict[str, Grade] = {}
        total = len(columns)
        for student in data:
            complete, _ = data[student]
            grades[student] = f'{len(complete)} / {total}'

        return grades

    def get_lab_data(self,
                     students: Optional[List[str]] = None,
                     tas: Optional[List[str]] = None,
                     ) -> Dict[str, Tuple[Set[str], Set[str]]]:
        lab_data: Dict[str, set] = defaultdict(set)
        all_labs = set()
        f_system = os.walk(self.lab_base_path)
        root, folds, _ = next(f_system)
        for lab_dirname in folds:
            lab_fold = pjoin(root, lab_dirname)
            all_labs.add(lab_dirname)
            for f in os.listdir(lab_fold):
                if 'checkoff' not in f:
                    continue

                fp = pjoin(lab_fold, f)
                lines = line_read(fp)

                for student in lines:
                    lab_data[student].add(lab_dirname)

        lines = line_read(self.lab_exception_path, delim=' ')
        for line in lines:
            login = line[0]
            lab = line[1]
            lab_data[login].add(lab)

        if students is None:
            login_set = set(lab_data.keys())
        else:
            login_set = set(students)

        set_tas: Set[str]
        if tas is None:
            set_tas = set()
        else:
            set_tas = set(tas)

        data: Dict[str, Tuple[Set[str], Set[str]]] = {}
        to_gen = login_set.difference(set_tas)
        for student in to_gen:
            attended = lab_data[student]
            unattended = all_labs.difference(attended)
            data[student] = (attended, unattended)

        return data

    def get_lab_grades(self,
                       students: Optional[List[str]] = None,
                       tas: Optional[List[str]] = None,
                       ) -> Dict[str, Grade]:
        data = self.get_lab_data(students, tas)
        grades: Dict[str, Grade] = {}
        numb_labs = max(map(lambda v: len(v[0]) + len(v[1]),
                            data.values()))
        for student in data:
            attended, _ = data[student]
            grades[student] = f'{len(attended)} / {numb_labs}'

        return grades

    def get_grading_app_data(self,
                             students: Optional[List[str]],
                             tas: Optional[List[str]]
                             ) -> Dict[str, Dict[str, Grade]]:
        return {}

    def get_summaries(self) -> Dict[str, str]:
        return {}

    def _write_summaries(self) -> None:
        pass

    def send_summaries(self) -> None:
        pass

    def generate_gradebook(self, path: str, tas: Optional[List[str]]) -> None:
        """
        generates gradebook for course, writing into tsv file
        uses the course_customization "grade_to_columns" function to determine
        columns, and has one row for each student.
        :param path: path to put tsv file in (should include filename)
        :param tas: optional list of logins to ignore (i.e. the course TAs)
        :return: None
        """
        pass


def get_hta_asgn_list() -> List[HTA_Assignment]:
    """

    Get list of all assignments

    :returns: list of all assignments (unloaded)
    :rtype: List[HTA_Assignment]

    """
    assignments = []
    for key in sorted(asgn_data['assignments'].keys()):
        asgn = HTA_Assignment(key)
        assignments.append(asgn)

    return assignments


def magic_update(question: Question, func: Callable[[Rubric], None]) -> None:
    """

    using a rubric updating function, changes a) the base rubric, and b) each
    extracted rubric. updated rubrics are checked for validity before file
    writing (as of after homework 8 2018 rip)

    This is most easily done in asgnipython

    :param question: the question for which to update all rubrics
    :type question: Question
    :param func: a function that takes in a rubric, returns None, and mutates
                 the rubric.
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

        magic_update(qn, updater)

    """
    if not isinstance(question, Question):
        raise TypeError('question must be a Question instance')
    if not callable(func):
        raise TypeError('func must be callable')

    question.load_handins()
    d = question.copy_rubric()
    func(d)
    loaded_rubric_check(d)
    question.rewrite_rubric(d)

    for handin in question.handins:
        if not handin.extracted:
            continue

        d = handin.get_rubric()
        func(d)
        handin.write_grade(d)
