class HandinConfig:
    # minutes after submission up to which student won't be
    # penalized for lateness
    handin_late_buffer = 10

    # if true, students submitting in buffer will get
    # confirmation email as if they submitted late
    warn_students_in_buffer = True

    # hours after which assignment submission without an extension is cut off
    # can be overriden for each assignment
    # the handin_late_buffer is added to this
    default_late_deadline = 24

    late_days = 3
    spreadsheet_id = '1ekM3rwsYOfo7xKdJDl1ub1MZgb3L2-8rzKtbzw2jGI8'
    sheet_name = 'handins'
    student_email_col = 'B'
    start_col = 'A'
    end_col = 'AT'
    start_row = 2
    assignment_name_col = 'C'
    log_path = '/course/cs0111/hta/handin/submission_log.txt'
    handin_path = '/course/cs0111/hta/handin/students'

    @classmethod
    def get_range(cls) -> str:
        return f'%s!%s%s:%s' % (cls.sheet_name, cls.start_col,
                                cls.start_row,  cls.end_col)


class CONFIG:
    base_path = '/course/cs0111'
    test_mode = True
    email_from = 'csci0111@brown.edu'
    email_errors_to = 'elias_berkowitz@brown.edu'
    hta_email = 'elias_berkowitz@brown.edu'
    test_mode_emails_to = 'elias_berkowitz@brown.edu'
    handin = HandinConfig
