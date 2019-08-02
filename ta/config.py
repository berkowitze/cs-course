from typing import Optional

# change to the directory in which the grading app resides
__base_path__ = '/course/cs00' # '__' just to keep things clean when importing

class HandinConfig:
    # minutes after submission up to which student won't be
    # penalized for lateness
    handin_late_buffer = 10

    # if True, students submitting in buffer will get
    # confirmation email as if they submitted late
    warn_students_in_buffer = True

    # hours after which assignment submission without an extension is cut off
    # can be overriden for each assignment
    # the handin_late_buffer is added to this
    # None if students cannot submit late
    default_late_deadline: Optional[int] = 24

    # number of late days each student gets (individual assignments only)
    late_days = 0

    # allow use of late days on projects (not implemented yet)
    late_days_on_projects = False
    spreadsheet_id = '1fcYiiVecWeSyMzdHIgtrX5x_TfzVYkV97AIkizFkiHY'
    sheet_name = 'Handins'

    # column that emails are dumped into
    student_email_col = 'B'

    # column that the assignment name is dumped into
    assignment_name_col = 'C'
    start_col = 'A'

    # this will need to be expanded if you have lots of assignments/questions
    end_col = 'AT'

    # 2 if there's a header, 1 otherwise
    start_row = 2

    test_sheet_ssid = '1r1sqsA8fp-1NZi5tMPc0P_LcLS4Zm_DAaUlmtTG7KFI' # shrug
    test_sheet_name = 'testing'
    log_path = f'{__base_path__}/hta/handin/submission_log.txt'
    handin_path = f'{__base_path__}/hta/handin/students'
    test_log_path = f'{__base_path__}/hta/handin/test_submission_log.txt'

    @classmethod
    def get_range(cls, test_mode: bool = False) -> str:
        if not test_mode:
            return f'%s!%s%s:%s' % (cls.sheet_name, cls.start_col,
                                    cls.start_row,  cls.end_col)
        else:
            return f'%s!%s%s:%s' % (cls.test_sheet_name, cls.start_col,
                                    cls.start_row,       cls.end_col)

    @classmethod
    def get_ssid(cls, test_mode: bool = False) -> str:
        if not test_mode:
            return cls.spreadsheet_id
        else:
            return cls.test_sheet_ssid

    @classmethod
    def get_sub_log(cls, test_mode: bool = False) -> str:
        if not test_mode:
            return cls.log_path
        else:
            return cls.test_log_path


class CONFIG:
    # this needs a loooot of cleanup
    
    base_path = __base_path__

    # generally keep False
    test_mode = False

    # all emails (grade reports/complaints, errors, etc.) sent from this
    # you need the password!
    email_from = 'csci0111@brown.edu'

    email_errors_to = ['eliberkowitz@gmail.com', 'wpatter1@cs.brown.edu']

    # email of the HTAs
    hta_email = 'eliberkowitz@gmail.com'

    # when in test mode, send all emails to this address instead of
    # students/tas
    test_mode_emails_to = 'eliberkowitz@gmail.com'

    handin = HandinConfig
    supported_test_suites = ['Python', 'Pyret', '']

    error_handler_email = 'eliberkowitz@gmail.com'
    error_handler_name = 'Eli'
    hta_name = 'Will'

