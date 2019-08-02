from typing import Optional

# remove this assert after fixing __base_path__
assert False, 'replace __base_path__!'
# change to the directory in which the grading app resides
__base_path__ = '/course/cs00' # '__' just to keep things clean when importing

# check that repo has been initialized
with open(__base_path__ + '/initialized.txt') as f:
    dat = f.read().strip()
if dat != 'yes':
    raise ValueError('Initialize the repo using `bash hta/setupper.sh`')

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

    # remove the assertion once you replace the handin ssid
    assert False, 'must insert handin ssid'
    spreadsheet_id = 'SSID HERE'
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


class RegradeConfig:
    # remove this assert after adding the 4 links below
    assert False, 'must configure regrade information (the 4 things below, instructions in ta/config-instructions.txt)'
    request_ssid = "1q0jC_3WmuF-Anhm4AOzd931wjAHqesAXNtT-gIICqn0"
    response_ssid = "1b7mDx_xCAIs9R23mSNtJHKuvP9VAPDYWMwaNTc-Q0CA"
    regrade_instructions = "https://docs.google.com/document/d/1xWOYBp_9_GIg3ON_z2zFUfE8RBGoPLi7ZBQgmplTuqQ"
    response_form_filled_link = "https://docs.google.com/forms/d/1Hs43pFSoRDhkE7MMfInY6ZCYuX5HpWFJAoqHdYELhfs/viewform?usp=pp_url&entry.2102360043={assignment_name}&entry.1573848516={indicated_question}&entry.660184789={student_ID}"
    request_form_filled_link = "https://docs.google.com/forms/d/1ePAeYr-f59DT57QjkgjxgKOPDRPgaajnfsKrMqSVCYI/viewform?usp=pp_url&entry.1832652590={assignment_name}&entry.1252387205={indicated_question}"

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
    regrade = RegradeConfig
    supported_test_suites = ['Python', 'Pyret', '']

    error_handler_email = 'eliberkowitz@gmail.com'
    error_handler_name = 'Eli'

    # remove this assert after replacing the hta_name
    assert False
    hta_name = 'Will'
    lang_dict = {
        'Python': 'py',
        'Pyret': 'arr'
    }
