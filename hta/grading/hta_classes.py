from classes import *
import zipfile
from hta_helpers import *
import numpy as np
import subprocess

anon_map_path = os.path.join(BASE_PATH, 'hta/grading/anonymization')
handin_base_path = os.path.join(BASE_PATH, 'hta/handin/students')

# TA's blocklisting students
blocklist_path_1 = os.path.join(BASE_PATH, 'ta', 't-s-blocklist.txt')

# Student's blocklisting TA's (private to TA's)
blocklist_path_2 = os.path.join(BASE_PATH, 'hta', 's-t-blocklist.txt')

grade_base_path = os.path.join(BASE_PATH, 'hta/grades')

class HTA_Assignment(Assignment):
    def __init__(self, *args, **kwargs):
        # initialize TA version of Assignment class
        super(HTA_Assignment, self).__init__(*args, **kwargs)
        # then set some HTA only attributes
        self.anon_path = os.path.join(anon_map_path,
                                      '%s.csv' % self.mini_name)
        if self.started: # load list of logins that handed in this assignment
            with open(self.anon_path) as f:
                lines = f.read().strip().split('\n')

            login_handin_list = []
            for line in lines:
                s = line.split(',')[0].strip()
                login_handin_list.append(s)

            self.login_handin_list = login_handin_list

        self.handin_path = handin_base_path
        self.bracket_path = os.path.join(rubric_base_path,
                                         self.mini_name,
                                         'bracket.json')
        assert os.path.exists(grade_base_path), \
            '%s directory does not exist' % grade_base_path
        self.grading_completed = self.json['grading_completed']
        self.emails_sent = self.json['sent_emails']
        self.bracket_exists = os.path.exists(self.bracket_path)

    def init_grading(self):
        assert not self.started, \
            'Cannot init_grading on started %s' % repr(self)
        self.check_startable()
        # make log files (/ta/grading/data/logs/mini_name)
        self.create_log()
        self.started = True

        # transfer handins from hta/handin to ta/grading/data/sfiles
        # and set up anonymization
        self.transfer_handins()
        self.blocklist_map = self.setup_blocklist() # set up blocklist
        self.record_start() # update assignments.json

        # self.load_questions() # load questions after all else is set up

    def check_startable(self):
        ''' raise an error if the proper files do not exist for
        the assignment '''
        if not os.path.exists(self.rubric_path):
            base = 'Rubric directory for "%s" does not exist (should be in %s)'
            raise OSError(base % (self, self.rubric_path))

        for i in range(len(self.json['questions'])):
            qn = Question(self, i)
            if not os.path.exists(qn.rubric_filepath):
                base = '%s does not have rubric for %s (should be in %s)'
                raise OSError(base % (self, qn, qn.rubric_filepath))

        if not self.bracket_exists:
            base = '%s does not have bracket file (should be in %s)'
            raise OSError(base % (self, self.bracket_path))
            
    def get_blocklists(self):
        print ta_path, hta_path
        tas = np.loadtxt(ta_path, dtype=str)
        htas = np.loadtxt(hta_path, dtype=str)
        # combine list of TAs
        all_tas = np.append(tas, htas)
        # dictionary with [] as default for students blacklisted by each TA
        mapping = dict((ta, []) for ta in all_tas)
        with locked_file(blocklist_path_1) as f:
            lines = f.read().strip().split('\n')
            bl1 = map(lambda l: map(str.strip, l),
                      map(lambda a: a.split(','), lines))

        with locked_file(blocklist_path_2) as f:
            lines = f.read().strip().split('\n')
            bl2 = map(lambda l: map(str.strip, l),
                      map(lambda a: a.split(','), lines))
        
        # combine the two blocklists, get rid of empty rows
        bl = [l for l in bl1 + bl2 if len(l) == 2]
        for row in bl:
            mapping[row[0]].append(row[1]) # add student to TA's list

        return mapping

    def setup_blocklist(self):
        mapping = self.get_blocklists()
        students = student_list()
        with open(self.blocklist_path, 'a') as f:
            for ta in mapping:
                for student in mapping[ta]:
                    if student in students:
                        line = '%s,%s\n'
                        try:
                            ident = int(self.login_to_id(student))
                            f.write('%s,%s\n' % (ta, ident))
                        except ValueError:
                            pass

    def login_to_id(self, login):
        lines = list(csv.reader(open(self.anon_path)))
        for line in lines:
            if line[0] == login:
                return line[1]

        e = 'login %s does not exist in map for %s'
        raise ValueError(e % (login, self)) 

    def id_to_login(self, id):
        lines = list(csv.reader(open(self.anon_path)))
        for line in lines:
            if line[1] == str(id):
                return line[0]

        e = 'id %s does not exist in map for %s'
        raise ValueError(e % (login, self))

    def transfer_handins(self):
        ''' takes handins from the handin folder, anonymizes them,
            and puts them in the TA folder; zip files with be extracted
            to a new folder (hopefully) '''
        sub_paths = []
        students = list(os.walk(self.handin_path))[0][1]
        ids = random.sample(range(len(students)), len(students))
        for i, student in enumerate(students):
            sub_path = os.path.join(self.handin_path, student, self.mini_name)
            if not os.path.exists(sub_path):
                continue # student didn't submit for this hw

            submissions = filter(lambda f: 'submission' in f,
                                 list(next(os.walk(sub_path)))[1])
            sub_numbs = map(lambda fname: int(fname.split('-')[0]),
                            submissions)
            latest = submissions[np.argmax(sub_numbs)]
            final_path = os.path.join(sub_path, latest)
            sub_paths.append((student, ids[i], final_path))
        
        # get a random id for every student
        ids = random.sample(range(len(students)), len(students))
        # set up a file that maps anon id back to student id, 
        # and copy over student files
        if self.anonymous:
            base_anon_path = self.anon_path
        else:
            base_anon_path = self.ta_anon_path
        with open(base_anon_path, 'w') as f:
            writer = csv.writer(f)
            for student, id, path in sub_paths:
                writer.writerow([student, id])
        
        if not self.anonymous: # make a link in the HTA folder as well
            try:
                os.symlink(base_anon_path, self.anon_path)
            except OSError:
                if not os.path.isdir(self.anon_path):
                    print '/hta/anonymization probably doesn\'t exist'

                raise

        for student, id, path in sub_paths:
            dest = os.path.join(self.s_files_path, 'student-%s' % id)
            shutil.copytree(path, dest)
            subprocess.check_output(['chgrp', '-R', 'cs-0111ta', dest])
            subprocess.check_output(['chmod', '-R', '770', dest])
            for f in os.listdir(dest):
                fname, ext = os.path.splitext(f)
                if ext == '.zip':
                    full_path = os.path.join(dest, f)
                    new_fname = '%s-extracted' % fname
                    new_dest  = os.path.join(dest, new_fname)
                    with zipfile.ZipFile(full_path, 'r') as zf:
                        zf.extractall(new_dest)

        self.load_questions()
        for _, id, _ in sub_paths:
            for question in self.questions:
                question.add_handin_to_log(id)

    def create_log(self):
        if os.path.exists(self.log_path):
            raise Exception('create_log called on a log that already exists')
        else:
            os.makedirs(self.log_path)
        # create a log file for each question in the assignment

        logs = []
        for i, q in enumerate(self.json['questions']):
            q = Question(self, i)
            os.makedirs(q.grade_path) # probably shouldnt do this here
            with open(q.log_filepath, 'w') as f:
                writer = csv.writer(f)
                writer.writerow(['student', 'ta', 'status',
                                 'flagged', 'explanation'])
                f.flush()

    def get_empty_grade(self, set_to=0):
        ''' create a dictionary with one key for every theme on this assignment,
        with values of set_to (0 by default)'''
        empty_grade = {}
        for q in self.questions:
            rubric = q.copy_rubric()
            for k in rubric.keys(): # for each category/theme
                if k == '_COMMENTS' or k in empty_grade:
                    # ignore already-added keys
                    continue

                empty_grade[k] = set_to

        return empty_grade

    def get_handin_dict(self, students, user):
        d = {}
        for student in students:
            try:
                anon_id = self.login_to_id(student)
            except ValueError:
                # no handin for any question
                d[student] = [None for h in self.questions]
                continue

            d[student] = []
            for q in self.questions:
                try:
                    handin = q.get_handin_by_sid(anon_id, user)
                except ValueError:
                    # student didn't hand in this question
                    print 'No %s handin for %s' % (self.full_name, student)
                    handin = None

                d[student].append(handin)

        return d

    def generate_all_reports(self):
        # call generate_report with data, student_id, soft at some point
        raise NotImplementedError

    def generate_report(self, problems, student_id, soft=True, overrides=False):
        ''' given a list of Handins and either a (nonanonymous) student id,
        generate a report for that student.
        the third argument, soft, represents whether or not to write the grades
        to corresponding grade files. returns the students (nonanonymous) id,
        the grade (dictionary), and the text of the report '''
        try:
            anon_ident = self.login_to_id(student_id)
        except ValueError:
            # re-raise error if the student handed something in but doesn't
            # have an anonymous ID associated with them
            for p in problems:
                if p is not None:
                    raise

            anon_ident = -1

        assert self.started # at the very least grading should be started

        grade_dir = os.path.join(grade_base_path,
                         '%s/%s' % (student_id, self.mini_name))
        report_path  = os.path.join(grade_dir, 'report.txt')
        grade_path   = os.path.join(grade_dir, 'grade.json')
        override_r_p = os.path.join(grade_dir, 'report-override.txt')
        override_g_p = os.path.join(grade_dir, 'grade-override.json')
        if overrides:
            report_path = override_r_p
            grade_path = override_g_p
            if os.path.exists(report_path):
                # if making overrides would overwrite an override...
                print 'Copying existing override for %s to backup files' % student_id
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
            
        # make this more rigorous later
        grade = self.get_empty_grade(set_to=0)
        full_string = '%s grade report for %s\n\n' % (self.full_name, student_id)
        if all(map(lambda p: p is None, problems)):
            # if no problems were handed in for the assignment
            # full_string += 'No handin.\n\n'
            for key in grade:
                grade[key] = None
        else:
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

        final_grades = self.use_brackets(grade)
        grade_string = 'Grade Summary\n'
        for key in final_grades:
            grade_string += '  %s: %s\n' % (key, final_grades[key])

        full_string += '\n%s\n' % grade_string
        
        if soft:
            return student_id, grade, full_string

        # write appropriate files
        if not os.path.isdir(grade_dir):
            assert not os.path.exists(grade_dir)
            os.makedirs(grade_dir)

        code_src    = os.path.join(self.s_files_path, 'student-%s' % anon_ident)
        code_dest   = os.path.join(grade_dir, 'code')
        with open(report_path, 'w') as f:
            f.write(full_string)

        with open(grade_path, 'w') as f:
            json.dump(final_grades, f, indent=2, sort_keys=True)

        try:
            os.symlink(code_src, code_dest)
        except OSError:
            pass # already exists, no need to do anything

        return student_id, final_grades, full_string

    def use_brackets(self, grade):
        ''' given a grade dictionary with numeric grades, determine the
        text grades from the possibilities list (defined in function)'''
        def use_bracket(bracket, grade):
            bounds = map(lambda k: k['upper_bound'], bracket)
            if not increasing(bounds):
                raise ValueError('Bounds must increase throughout bracket')
            for item in bracket:
                if grade <= item['upper_bound']:
                    return item['grade']

            g = bracket[-1]['grade']
            print 'Warning: grade above uppermost bound. Giving %s' % g
            return g

        # "No Handin" ONLY comes from a None in the grade dictionary
        with open(self.bracket_path) as f:
            brackets = json.load(f)

        # makes sure brackets is a valid bracket file
        for key in grade:
            if key == '_COMMENTS':
                continue

            if key not in brackets:
                base = '%s bracket file does not have key %s, only has %s'
                raise OSError(base % (self.mini_name, key, brackets.keys()))

        for key in brackets:
            assert key in grade, \
                '%s brackets file has extra grade category (%s)' % (self.mini_name, key)

        final_grade = {}
        for key in brackets:
            final_grade[key] = use_bracket(brackets[key], grade[key])

        return final_grade

    def send_email(self, student_id, student_email, yag):
        ''' takes in a student_id and a yag instance
        (yag = yagmail.SMTP(...)), and sends a report email to the student '''
        assert self.grading_completed
        subject = '%s Grade Report' % self.full_name
        gb = os.path.join(grade_base_path, student_id, self.mini_name)
        if 'report-override.txt' in os.listdir(gb):
            f = os.path.join(gb, 'report-override.txt')
        else:
            f = os.path.join(gb, 'report.txt')

        print 'Report sent to %s' % student_id
        with open(f) as fl:
            grade = fl.read()

        yag.send(to=student_email,
                 subject=subject,
                 contents=['<pre>%s</pre>' % grade])


    def reset_grading(self, confirm):
        ''' remove the assignment log; there is no recovering the data.
        grade files are *not* deleted. do that by hand if you want to. '''
        # should probably not need this much try/except todo
        if confirm != True:
            raise("Must call reset_grading with boolean confirm argument")
        try:
            shutil.rmtree(self.log_path)
            print 'Removed log path...'
        except:
            pass
        try:
            shutil.rmtree(self.grade_path)
            print 'Removed grade path...'
        except:
            pass
        try:
            shutil.rmtree(self.s_files_path)
            print 'Removed student files path...'
        except:
            pass
        try:
            os.remove(self.blocklist_path)
            print 'Removed blocklists...'
        except:
            pass
        try:
            os.remove(self.anon_path)
            try:
                os.remove(self.ta_anon_path)
            except OSError:
                pass

            print 'Removed anonymization mapping...'
        except:
            pass

        # now set grading_started in the assignments.json to False
        with locked_file(asgn_data_path) as f:
            data = json.load(f)

        data['assignments'][self.full_name]['grading_started'] = False
        with locked_file(asgn_data_path, 'w') as f:
            json.dump(data, f, indent=2, sort_keys=True)

        self.started = False
        print 'Assignment records removed.'

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
        raise NotImplementedError

    def __repr__(self):
        return 'HTA-' + super(HTA_Assignment, self).__repr__()
        
def get_full_asgn_list():
    with locked_file(asgn_data_path) as f:
        data = json.load(f)

    return map(HTA_Assignment, sorted(data['assignments'].keys()))


