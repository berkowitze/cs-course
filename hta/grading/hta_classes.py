from classes import *
from hta_helpers import *

anon_map_path = os.path.join(BASE_PATH, 'hta/grading/anonymization')
handin_base_path = os.path.join(BASE_PATH, 'hta/handin/students')

# TA's blocklisting students
blocklist_path_1 = os.path.join(BASE_PATH, 'ta', 't-s-blocklist.txt')

# Student's blocklisting TA's (private to TA's)
blocklist_path_2 = os.path.join(BASE_PATH, 'hta', 's-t-blocklist.txt')

grade_base_path = os.path.join(BASE_PATH, 'hta/grades')

class HTA_Assignment(Assignment):
    def __init__(self, *args, **kwargs):
        super(HTA_Assignment, self).__init__(*args, **kwargs)
        self.anon_path = os.path.join(anon_map_path,
                                      '%s.csv' % self.mini_name)
        self.handin_path = handin_base_path
        self.bracket_path = os.path.join(rubric_base_path,
                                         self.mini_name,
                                         'bracket.json')
        assert os.path.exists(grade_base_path), \
            '%s directory does not exist' % grade_base_path
        walker = os.walk(grade_base_path)
        try:
            info = walker.next()
            mini_list = os.listdir(os.path.join(info[0], info[1][0]))
            self.reports_generated = self.mini_name in mini_list
        except IndexError:
            self.reports_generated = False

        self.bracket_exists = os.path.exists(self.bracket_path)

    def init_grading(self):
        assert not self.started, \
            'Cannot init_grading on started %s' % repr(self)
        self.create_log()
        self.started = True
        self.load_questions()
        self.transfer_handins()
        self.blocklist_map = self.setup_blocklist()
        self.record_start()

    def get_blocklists(self):
        tas = np.loadtxt(ta_path, dtype=str)
        htas = np.loadtxt(hta_path, dtype=str)
        # combine list of TAs
        all_tas = np.append(tas, htas)
        # hashmap with [] as default for students blacklisted by each TA
        mapping = dict((ta, []) for ta in all_tas)
        with open(blocklist_path_1) as f:
            bl1 = f.read().strip().split('\n')

        with open(blocklist_path_2) as f:
            bl2 = f.read().strip().split('\n')
        
        # combine the two bloclists, get rid of empty rows
        bl = filter(lambda i: i != '', bl1 + bl2)
        for row in bl:
            mapping[row[0]].append(row[1])

        return mapping

    def login_to_id(self, login):
        lines = list(csv.reader(open(self.anon_path)))
        for line in lines:
            if line[0] == login:
                return line[1]

        raise Exception('login %s does not exist in map' % login)

    def id_to_login(self, id):
        lines = list(csv.reader(open(self.anon_path)))
        for line in lines:
            if line[1] == str(id):
                return line[0]

        raise Exception('id %s does not exist in map' % id)

    def transfer_handins(self):
        ''' takes handins from the handin folder, anonymizes them,
            and puts them in the (TODO) TA folder '''
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
            sub_paths.append((student, ids[i], os.path.join(sub_path, latest)))
        
        # get a random id for every student
        ids = random.sample(range(len(students)), len(students))
        with open(self.anon_path, 'w') as f:
            writer = csv.writer(f)
            for student, id, path in sub_paths:
                writer.writerow([student, id])
                dest = os.path.join(self.s_files_path, 'student-%s' % id)
                shutil.copytree(path, dest)

        for _, id, _ in sub_paths:
            for question in self.logs:
                question.add_handin(id)

    def setup_blocklist(self):
        mapping = self.get_blocklists()
        with open(self.blocklist_path, 'a') as f:
            for key in mapping:
                for student in mapping[key]:
                    f.write('%s,%s\n' % (key, int(self.login_to_id(student))))

    def create_log(self):
        if os.path.exists(self.log_path):
            raise Exception('create_log called on a log that already exists')
        else:
            os.makedirs(self.log_path)
        # create a log file for each question in the assignment

        logs = []
        for i, q in enumerate(self['questions']):
            qlog_path = self.qnumb_to_log_path(i + 1)
            qgrade_path = self.qnumb_to_grade_path(i + 1)
            os.makedirs(qgrade_path)
            logs.append(qlog_path)
            with open(qlog_path, 'w') as f:
                writer = csv.writer(f)
                writer.writerow(['student', 'ta', 'status', 'flagged'])
                f.flush()

    def generate_report(self, data, student_id, soft=True):
        grade = {}
        anon_ident = data['id']
        problems = data['problems']
        
        full_string = '%s grade report for %s\n\n' % (self.full_name, student_id)
        for handin in problems:
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
            return student_id, final_grades, grade
        # write appropriate files
        grade_dir = os.path.join(grade_base_path,
                                 '%s/%s' % (student_id, self.mini_name))
        if not os.path.isdir(grade_dir):
            assert not os.path.exists(grade_dir)
            print grade_dir
            os.makedirs(grade_dir)

        report_path = os.path.join(grade_dir, 'report.txt')
        grade_path  = os.path.join(grade_dir, 'grade.json')
        code_src    = os.path.join(self.s_files_path, 'student-%s' % anon_ident)
        code_dest   = os.path.join(grade_dir, 'code')
        with open(report_path, 'w') as f:
            f.write(full_string)

        with open(grade_path, 'w') as f:
            json.dump(final_grades, f, indent=2)

        try:
            os.symlink(code_src, code_dest)
        except OSError:
            pass

    def use_brackets(self, grade):
        possibilities = ["No Grade", "Fail", "Check Minus", "Check", "Check Plus"]
        # no grade ONLY comes from a None in the grade dictionary
        with open(self.bracket_path) as f:
            brackets = json.load(f)

        # makes sure brackets is a valid bracket file
        for key in grade:
            if key == '_COMMENTS':
                continue
            assert key in brackets, \
                '%s brackets file does not have all grade categories (%s)' % (self.mini_name, key)

        for key in brackets:
            assert key in grade, \
                '%s brackets file has extra grade category (%s)' % (self.mini_name, key)

        final_grade = {}
        for key in brackets:
            ranges = brackets[key]
            cgrade = grade[key]

            # determine_grade comes from helpers file
            final_grade[key] = determine_grade(possibilities, ranges, cgrade)

        return final_grade

    def reset_assignment(self):
        ''' remove the assignment log; there is no recovering the data.
        grade files are *not* deleted. do that by hand if you want to. '''
        # TODO should probably not be doing this much try/except here
        try:
            shutil.rmtree(self.log_path)
        except:
            pass
        try:
            shutil.rmtree(self.grade_path)
        except:
            pass
        try:
            shutil.rmtree(self.s_files_path)
        except:
            pass
        try:
            os.remove(self.blocklist_path)
        except:
            pass
        try:
            os.remove(self.anon_path)
        except:
            pass

        with FileLock(asgn_data_path) as f:
            data = json.load(f)

        data['assignments'][self.full_name]['grading_started'] = False
        with FileLock(asgn_data_path, 'w') as f:
            json.dump(asgn_data, f, indent=4)

        self.started = False
        print 'Assignment records removed.'

    def record_start(self):
        with FileLock(asgn_data_path) as f:
            asgn_data = json.load(f)

        asgn_data['assignments'][self.full_name]['grading_started'] = True
        with FileLock(asgn_data_path, 'w') as f:
            json.dump(asgn_data, f, indent=4)

    def record_finish(self):
        with open():
            pass

    def status(self):
        gradign_started = self.started
        if started:
            for q in self.logs:
                print q.has_incomplete

        return grading_started
        # grading_completed = 
        # reports_generated = grading_completed and


if __name__ == '__main__':
    hw = raw_input('Enter assignment: ')
    asgn = HTA_Assignment(hw)
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '-R':

        asgn.reset_assignment()
    else:
        asgn.init_grading()

