import csv
import zipfile
from typing import Set

from classes import *
from custom_types import *
from hta_helpers import *

anon_map_path: str = os.path.join(BASE_PATH, 'hta/grading/anonymization')
handin_base_path: str = os.path.join(BASE_PATH, 'hta/handin/students')

grade_base_path: str = os.path.join(BASE_PATH, 'hta/grades')

final_grade_path: str = os.path.join(BASE_PATH, 'ta', 'grading', 'grades')


class HTA_Assignment(Assignment):
    """ HTA version of Assignment (TA version is just Assignment)
    initialized with full homework name:
        HTA_Assignment("Homework 3")
    """

    def __init__(self, *args, **kwargs):
        # initialize TA version of Assignment class
        super(HTA_Assignment, self).__init__(*args, **kwargs)
        # then set some HTA only attributes
        if self.anonymous:
            jpath = '%s.json' % self.mini_name
            self.anon_path = os.path.join(anon_map_path, jpath)
        else:
            assert self.anon_path != '', 'error with anon path tell eli'

        if self.started:  # load list of logins that handed in this assignment
            # probably useless to do this but is used in asgn hub
            with locked_file(self.anon_path) as f:
                d = json.load(f)

            self.login_handin_list = list(d.keys())

        self.handin_path = handin_base_path
        
        assert os.path.exists(grade_base_path), \
            '%s directory does not exist' % grade_base_path
        self.grading_completed = self._json['grading_completed']
        self.emails_sent = self._json['sent_emails']
        self.bracket_exists = os.path.exists(self.bracket_path)
        self.groups_loaded = False

    def init_grading(self) -> None:
        assert not self.started, \
            'Cannot init_grading on started %s' % repr(self)
        self.check_startable()
        # make log files (/ta/grading/data/logs/mini_name)
        self.create_log()
        self.started = True

        # transfer handins from hta/handin to ta/grading/data/sfiles
        # and set up anonymization
        self.transfer_handins()
        self.setup_blocklist()
        self.record_start()  # update assignments.json

    def check_startable(self):
        """ raise an error if the proper files do not exist for
        the assignment """
        if not os.path.exists(self.rubric_path):
            base = 'Rubric directory for "%s" does not exist (should be in %s)'
            raise OSError(base % (self, self.rubric_path))

        for i in range(len(self._json['questions'])):
            qn = Question(self, i)
            if not os.path.exists(qn.rubric_filepath):
                base = '%s does not have rubric for %s (should be in %s)'
                raise OSError(base % (self, qn, qn.rubric_filepath))

        if not self.bracket_exists:
            base = '%s does not have bracket file (should be in %s)'
            raise OSError(base % (self, self.bracket_path))

    def setup_blocklist(self):
        mapping = get_blocklists()
        data = defaultdict(list)
        for ta in mapping:
            for student in mapping[ta]:
                try:
                    ident = self.login_to_id(student)
                    data[ta].append(ident)
                except ValueError:  # no submission for this student
                    continue

        with locked_file(self.blocklist_path, 'w') as f:
            json.dump(data, f, indent=2, sort_keys=True)

    def login_to_id(self, login: str) -> int:
        with locked_file(self.anon_path) as f:
            data = json.load(f)
        try:
            return int(data[login])
        except KeyError:
            raise ValueError(f'login {login} does not exist in map for {self}')

    def id_to_login(self, id: int) -> str:
        with locked_file(self.anon_path) as f:
            data = json.load(f)

        for k in data:
            if data[k] == id:
                return str(k)

        raise ValueError(f'id {id} does not exist in map for {self}')

    def transfer_handins(self):
        """ takes handins from the handin folder, anonymizes them,
            and puts them in the TA folder; zip files with be extracted
            to a new folder (hopefully) """
        sub_paths = []

        file_sys = os.walk(self.handin_path)
        students = next(file_sys)[1]
        ids = random.sample(list(range(len(students))), len(students))
        for i, student in enumerate(students):
            final_path = latest_submission_path(self.handin_path,
                                                student,
                                                self.mini_name)
            if final_path is None:
                continue  # student didn't submit for this hw
            elif not os.path.exists(final_path):
                e = 'latest_submission_path returned nonexisting path'
                raise ValueError(e)

            sub_paths.append((student, ids[i], final_path))

        # set up a file that maps anon id back to student id,
        # and copy over student files

        data = {}
        for student, id, _ in sub_paths:
            data[student] = id

        with locked_file(self.anon_path, 'w') as f:
            json.dump(data, f, sort_keys=True, indent=2)

        for student, id, path in sub_paths:
            dest = os.path.join(self.files_path, 'student-%s' % id)
            shutil.copytree(path, dest)
            for f in os.listdir(dest):
                fname, ext = os.path.splitext(f)
                if ext == '.zip':
                    full_path = os.path.join(dest, f)
                    new_fname = '%s-extracted' % fname
                    new_dest = os.path.join(dest, new_fname)
                    with zipfile.ZipFile(full_path, 'r') as zf:
                        zf.extractall(new_dest)

        self.__load_questions()
        for _, id, _ in sub_paths:
            for question in self.questions:
                question.add_handin_to_log(id)

    def add_new_handin(self, login: str) -> None:
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
                base = 'Student %s resubmitted %s after grading completed.'
                base += ' Not adding to grading app; handle manually.'
                base = base % (login, self.full_name)
                return

            self.delete_student_handin(login, override=True)
        except ValueError:
            pass

        rand_id = self.get_new_id()
        final_path = latest_submission_path(self.handin_path,
                                            login,
                                            self.mini_name)
        if final_path is None:
            raise ValueError("No handin for %s" % login)
        elif not os.path.exists(final_path):
            e = 'latest_submission_path returned nonexisting path'
            raise ValueError(e)

        with locked_file(self.anon_path) as f:
            data = json.load(f)

        data[login] = rand_id
        with locked_file(self.anon_path, 'w') as f:
            json.dump(data, f, indent=2, sort_keys=True)

        dest = os.path.join(self.files_path, 'student-%s' % rand_id)
        shutil.copytree(final_path, dest)
        for f in os.listdir(dest):
            fname, ext = os.path.splitext(f)
            if ext == '.zip':
                full_path = os.path.join(dest, f)
                new_fname = '%s-extracted' % fname
                new_dest = os.path.join(dest, new_fname)
                with zipfile.ZipFile(full_path, 'r') as zf:
                    zf.extractall(new_dest)

        self.__load_questions()
        for question in self.questions:
            question.add_handin_to_log(rand_id)

    def get_new_id(self) -> int:
        with locked_file(self.anon_path) as f:
            data = json.load(f)

        if len(data) > 0:
            return max(data.values()) + 1
        else:
            return 0

    def delete_student_handin(self, login: str,
                              override: bool = False) -> None:
        if not override:
            print('Confirm removal of %s handin from grading app [y/n]' % login)
            if input('> ').lower() != 'y':
                return

        try:
            ident = self.login_to_id(login)
            print('DELETING %s' % ident)
        except ValueError:
            e = '%s does not have a handin that\'s being graded' % login
            raise ValueError(e)

        dest = os.path.join(self.files_path, f'student-{ident}')
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
                print("Could not delete %s" % q)
                continue
            if os.path.exists(h.grade_path):
                os.remove(h.grade_path)

            with locked_file(q.log_filepath) as f:
                data = json.load(f)

            data = [d for d in data if d['id'] != ident]
            with locked_file(q.log_filepath, 'w') as f:
                json.dump(data, f, indent=2, sort_keys=True)

    def create_log(self):
        if os.path.exists(self.log_path):
            raise Exception('create_log called on a log that already exists')
        else:
            os.makedirs(self.log_path)
        # create a log file for each question in the assignment

        logs = []
        for i, q in enumerate(self._json['questions']):
            q = Question(self, i)
            os.makedirs(q.grade_path)  # probably shouldnt do this here
            with locked_file(q.log_filepath, 'w') as f:
                json.dump([], f, indent=2, sort_keys=True)

    def load_groups(self):
        with locked_file(self.proj_dir) as f:
            self.groups = json.load(f)

        self.groups_loaded = True

    def proj_partners(self, student):
        assert self.group_asgn, 'cannot get project partner of non group asgn'
        if not self.groups_loaded:
            self.load_groups()

        for group in self.groups:
            if student in group:
                ogs = group[:]
                ogs.remove(student)
                return ogs

        e = 'Student %s does not have partner (cs111-project-pair unrun?)'
        raise ValueError(e % student)

    def get_handin_dict(self, students, user):
        # str wrapping all d[student] because a mix of unicode and str
        # is annoying
        d = defaultdict(lambda: [])
        handin_logins = [self.id_to_login(h.id) for h in self.questions[0].handins]
        for student in handin_logins:
            if self.group_asgn:
                ohs = handin_logins[:]
                ohs.remove(student)
                partners = self.proj_partners(student)
                for p in partners:
                    if p in ohs:
                        e = 'Multiple students in %s group submitted' % student
                        raise ValueError(e)
            try:
                anon_id = self.login_to_id(student)
                if (int(anon_id) not in handin_logins) and self.group_asgn:
                    raise ValueError('All good')

            except ValueError:
                if self.group_asgn:
                    partners = self.proj_partners(student)
                    if partners == []:
                        d[str(student)] = [None for h in self.questions]
                        continue
                    elif len(partners) == 1:
                        d[str(student)] = d[str(partners[0])]
                    else:
                        e = "currently doesn't work for 3 person groups"
                        e += " (notify authorities)"
                        e += " (%s)" % student
                        raise NotImplementedError(e)
                else:
                    # no handin for any question
                    d[str(student)] = [None for h in self.questions]
                    continue

            for q in self.questions:
                try:
                    handin = q.get_handin_by_id(anon_id)
                except ValueError:
                    # student didn't hand in this question
                    print('No %s handin for %s' % (self.full_name, student))
                    handin = None

                d[str(student)].append(handin)

        return d

    def get_report_data(self, user):
        """ given a User class (i.e. User("eberkowi")) return
        a list of 3-tuples, (login, <numeric grade data>, <grade report>)
        with one 3-tuple for each student that was graded on this asgn.
        grade data is a dictionary of category-value pairs, and grade
        report is the string for the student's grade report
        note: User input is useless, but can't easily get rid of it (TODO) """
        logins = student_list()
        handins = self.get_handin_dict(logins, user)
        data = []
        for student in handins:
            d = self.generate_report(handins[student],
                                     student_id=student,
                                     soft=True,
                                     overrides=self.emails_sent)
            data.append(d)

        return data

    def generate_all_reports(self):
        # call generate_report with data, student_id, soft at some point
        raise NotImplementedError

    def report_already_generated(self, login):
        grade_dir = os.path.join(grade_base_path,
                                 '%s/%s' % (login, self.mini_name))
        report_path = os.path.join(grade_dir, 'report.txt')
        grade_path = os.path.join(grade_dir, 'grade.json')
        override_r_p = os.path.join(grade_dir, 'report-override.txt')
        override_g_p = os.path.join(grade_dir, 'grade-override.json')
        return os.path.exists(report_path) or os.path.exists(override_r_p)

    def generate_one_report(self, login, user, soft=True, overrides=False):
        id = self.login_to_id(login)
        ps = []
        for q in self.questions:
            try:
                ps.append(q.get_handin_by_id(id))
            except ValueError:
                pass

        return self.generate_report(ps, login, soft=soft, overrides=overrides)

    def generate_report(self, problems, student_id, soft=True, overrides=False):
        # this needs some serious cleanup
        """ given a list of Handins and either a (nonanonymous) student id,
        generate a report for that student.
        the third argument, soft, represents whether or not to write the grades
        to corresponding grade files. returns the students (nonanonymous) id,
        the grade (dictionary), and the text of the report """
        if self.group_asgn:
            try:
                anon_ident = self.login_to_id(student_id)
            except ValueError:
                anon_ident = -1  # make this better to handin person's id
        else:
            try:
                anon_ident = self.login_to_id(student_id)
            except ValueError:
                # re-raise error if the student handed something in but doesn't
                # have an anonymous ID associated with them
                for p in problems:
                    if p is not None:
                        raise

            anon_ident = -1

        assert self.started  # at the very least grading should be started
        final_path = latest_submission_path(self.handin_path,
                                            student_id,
                                            self.mini_name)
        if final_path is not None and '-late' in final_path:
            late = True
        else:
            late = False

        grade_dir = os.path.join(grade_base_path,
                                 '%s/%s' % (student_id, self.mini_name))
        report_path = os.path.join(grade_dir, 'report.txt')
        summary_path = os.path.join(grade_dir, 'rubric-summary.txt')
        grade_path = os.path.join(grade_dir, 'grade.json')
        override_r_p = os.path.join(grade_dir, 'report-override.txt')
        override_g_p = os.path.join(grade_dir, 'grade-override.json')
        if overrides and not soft:
            report_path = override_r_p
            grade_path = override_g_p
            if os.path.exists(report_path):
                # if making overrides would overwrite an override...
                print('Copying existing override for %s to backup files' % student_id)
                shutil.copy(report_path,
                            os.path.join(grade_dir, 'report-override-backup.txt'))
                shutil.copy(grade_path,
                            os.path.join(grade_dir, 'grade-override-backup.json'))

        if not (os.path.exists(override_r_p) == os.path.exists(override_g_p)):
            base = 'For %s, student %s must have both report-override.txt '
            base += 'and grade-override.json'
            raise TypeError(base % (self, student_id))
        if os.path.exists(override_r_p):
            # by extension both exist because of last check
            with locked_file(override_r_p) as f:
                full_string = f.read()

            with locked_file(override_g_p) as f:
                grade = json.load(f)

            return student_id, grade, full_string

        summary_str = ''
        for p in problems:
            if p is None:
                continue
            summary_str += '%s\n' % p.question
            cmd = [os.path.join(BASE_PATH, 'tabin', 'cs111-rubric-info'),
                   p.grade_path]
            try:
                p_sum = subprocess.check_output(cmd)
            except subprocess.CalledProcessError:
                p_sum = 'Error getting summary'

            summary_str += p_sum
            summary_str += '-' * 20

        # make this more rigorous later
        grade = get_empty_raw_grade(self)
        full_string = f'{self.full_name} grade report for {student_id}\n\n'
        for i, handin in enumerate(problems):
            if handin is None:
                full_string += 'Question %s: No handin\n\n' % (i + 1)
                continue

            report_text, report_grade = handin.generate_grade_report()
            full_string += report_text
            for key in report_grade:
                if key in grade:
                    grade[key] += report_grade[key]
                else:
                    grade[key] = report_grade[key]

        final_grades = self.use_brackets(grade, late=late)

        grade_string = 'Grade Summary\n'
        for key in final_grades:
            grade_string += '  %s: %s\n' % (key, final_grades[key])

        if late:
            grade_string += '(Late deduction applied)'

        full_string += '\n%s\n' % grade_string

        if soft:
            return student_id, grade, full_string

        # write appropriate files
        if not os.path.isdir(grade_dir):
            assert not os.path.exists(grade_dir)
            os.makedirs(grade_dir)

        code_src = os.path.join(self.files_path, 'student-%s' % anon_ident)
        code_dest = os.path.join(grade_dir, 'code')
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

        return student_id, final_grades, full_string

    def send_email(self, student_id, student_email, yag):
        """ takes in a student_id and a yag instance
        (yag = yagmail.SMTP(...)), and sends a report email to the student """
        assert self.grading_completed
        subject = '%s Grade Report' % self.full_name
        gb = os.path.join(grade_base_path, student_id, self.mini_name)
        if 'report-override.txt' in os.listdir(gb):
            f = os.path.join(gb, 'report-override.txt')
        else:
            f = os.path.join(gb, 'report.txt')

        print('Report sent to %s' % student_id)
        with locked_file(f) as fl:
            grade = fl.read()

        yag.send(to=student_email,
                 subject=subject,
                 contents=['<pre>%s</pre>' % grade])

    def reset_grading(self, confirm):
        """ remove the assignment log; there is no recovering the data.
        grade files are *not* deleted. do that by hand if you want to. """
        # should probably not need this much try/except todo
        if confirm != True:
            raise ("Must call reset_grading with boolean confirm argument")
        try:
            shutil.rmtree(self.log_path)
            print('Removed log path...')
        except:
            pass
        try:
            shutil.rmtree(self.grade_path)
            print('Removed grade path...')
        except:
            pass
        try:
            shutil.rmtree(self.files_path)
            print('Removed student files path...')
        except:
            pass
        try:
            os.remove(self.blocklist_path)
            print('Removed blocklists...')
        except:
            pass
        try:
            os.remove(self.anon_path)
            try:
                os.remove(os.path.join(anon_base_path,
                                       '%s.json' % self.mini_name))
                # os.remove(self.ta_anon_path)
            except OSError:
                pass

            print('Removed anonymization mapping...')
        except:
            pass

        # now set grading_started in the assignments.json to False
        with locked_file(asgn_data_path) as f:
            data = json.load(f)

        data['assignments'][self.full_name]['grading_started'] = False
        with locked_file(asgn_data_path, 'w') as f:
            json.dump(data, f, indent=2, sort_keys=True)

        self.started = False
        print('Assignment records removed.')

    def record_start(self):
        with locked_file(asgn_data_path) as f:
            asgn_data = json.load(f)

        asgn_data['assignments'][self.full_name]['grading_started'] = True
        with locked_file(asgn_data_path, 'w') as f:
            json.dump(asgn_data, f, indent=2, sort_keys=True)

    def record_finish(self):
        raise NotImplementedError

    def set_emails_sent(self):
        with locked_file(asgn_data_path) as f:
            d = json.load(f)

        d['assignments'][self.full_name]['sent_emails'] = True

        with locked_file(asgn_data_path, 'w') as f:
            json.dump(d, f, indent=2, sort_keys=True)

    def status(self):
        raise NotImplementedError("Status method not implemented")

    def deanonymize(self):
        # step 1 : move anonymization file from HTA to TA
        dest = os.path.join(anon_base_path, '%s.json' % self.mini_name)
        src = self.anon_path
        os.rename(src, dest)

        # step 2 : give TAs links to the grade files
        # use defaultdict so don't have to check if key exists
        ta_handins = defaultdict(lambda: set())
        for question in self.questions:
            for handin in question.handins:
                if handin.grader:
                    ta_handins[handin.grader].add(handin.id)

        grade_dir = os.path.join(grade_base_path, '%s/%s')
        for ta in ta_handins:
            d_base = os.path.join(final_grade_path, ta, self.mini_name)
            ids = ta_handins[ta]
            for id in ids:
                login = self.id_to_login(id)
                src = grade_dir % (login, self.mini_name)
                dest = os.path.join(d_base, login)
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
        return f'HTA-{repr(super(HTA_Assignment, self))}'

class Course:
    def __init__(self, base_path: str = '/course/cs0111') -> None:
        assert os.path.exists(base_path), f"base path {base_path} doesn't exist"
        self.base_path = base_path
        self.lab_base_path = os.path.join(self.base_path,
                                          'ta/grading/data/labs')
        self.lab_exception_path = os.path.join(BASE_PATH,
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
                drill = 'drill%s' % descr_to_drill(header[col])
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
            lab_fold = os.path.join(root, lab_dirname)
            all_labs.add(lab_dirname)
            for f in os.listdir(lab_fold):
                if 'checkoff' not in f:
                    continue

                fp = os.path.join(lab_fold, f)
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

def get_full_asgn_list():
    with locked_file(asgn_data_path) as f:
        data = json.load(f)

    return list(map(HTA_Assignment, sorted(data['assignments'].keys())))

def magic_update(question, func):
    """ given a Question and a function that takes in a rubric (dictionary)
    and mutates it. changes a) the base rubric, and b) each
    extracted rubric by applying func to those rubrics """
    if not isinstance(question, Question):
        raise TypeError('question must be a Question instance')
    if not callable(func):
        raise TypeError('func must be callable')

    question.load_handins()
    d = question.copy_rubric()
    new_data = func(d)
    with locked_file(question.rubric_filepath, 'w') as f:
        json.dump(new_data, f, indent=2, sort_keys=True)

    for handin in question.handins:
        if not handin.extracted:
            continue
        d = handin.get_rubric()
        func(d)
        if d is None:
            raise ValueError('Rubric was replaced with non-rubric')

        handin.write_grade(d)

