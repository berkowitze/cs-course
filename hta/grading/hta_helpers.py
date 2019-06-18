import json
import os
from collections import defaultdict
from typing import Dict, List, Optional

from helpers import locked_file, line_read, CONFIG

BASE_PATH = CONFIG.base_path


def load_students() -> List[List[str]]:
    """

    reads students from the hta/groups/students.csv file

    :returns: list of (login, email, name) of all enrolled students
    :rtype: List[List[str]]

    """
    path = os.path.join(BASE_PATH, 'hta/groups/students.csv')
    return line_read(path, delim=",")


def student_list() -> List[str]:
    """

    list of student logins from hta/groups/students.txt

    :returns: list of logins of students in the class
    :rtype: List[str]

    """
    path = os.path.join(BASE_PATH, 'hta/groups/students.txt')
    return line_read(path)


def email_to_login(email: str) -> str:
    """

    Converts brown email to CS login

    :param email: student's Brown email (aliases will not work)
    :type email: str
    :returns: student's CS login
    :rtype: str
    :raises ValueError: email not found in students.csv

    """
    students = load_students()
    for student in students:
        if student[1] == email:
            return student[0]

    raise ValueError(f'Student {email} not found.')


def login_to_email(login: str) -> str:
    """

    Convert CS login to full Brown email

    :param login: CS login of student
    :type login: str
    :returns: student's full Brown email
    :rtype: str
    :raises ValueError: Student with login not found in students.csv

    """
    students = load_students()
    for student in students:
        if student[0] == login:
            return student[1]

    raise ValueError(f'Student {login} not found.')


def argmax(lst: List[int]) -> int:
    """

    Get index of maximum integer of input list

    :param lst: list of non-negative integers
    :type lst: List[int]
    :returns: index of maximum integer in lst
    :rtype: int
    :raises ValueError: cannot operate on input list with repeated values

    """
    max_val = -1
    max_ndx = -1
    if len(set(lst)) != len(lst):
        raise ValueError(f'Repeated values in argmax: got {lst}')

    for ndx, val in enumerate(lst):
        if val > max_val:
            max_val = val
            max_ndx = ndx

    return max_ndx


def latest_submission_path(base: str,
                           login: str,
                           mini_name: str
                           ) -> Optional[str]:
    """

    Returns None if no submission for this student on this assignment,
    and the path of the student's latest submission if they did submit

    :param base: handin base path (i.e. /course/cs0050/hta/handin/students)
    :type base: str
    :param login: login of student to get submission path for
    :type login: str
    :param mini_name: minified assignment name (i.e. homework3)
    :type mini_name: str
    :returns: None if login has no handin for mini_name, and
              the path of the latest submission for login if they do
    :rtype: Optional[str]

    **example**:

    >>> latest_submission_path('/course/cs0050/hta/handin/students',
                               'eberkowi',
                               'homework4')
    '/course/cs0050/hta/handin/students/eberkowi/homework4/5-submission'
    >>> latest_submission_path('/course/cs0050/hta/handin/students',
                               'eberkowi',
                               'homework3')
    None

    """
    sub_path = os.path.join(base, login, mini_name)
    if not os.path.exists(sub_path):
        return None

    submissions = [f for f in os.listdir(sub_path) if 'submission' in f]
    sub_numbs = [int(f.split('-')[0]) for f in submissions]
    latest = submissions[argmax(sub_numbs)]
    return os.path.join(sub_path, latest)


def get_blocklists() -> Dict[str, List[str]]:
    """

    Get blocklist data from both TAs blocklisting students and
    students blocklisting TAs

    :returns: a dictionary of ta logins as the keys and lists of
              students blocklisted as the values
    :rtype: Dict[str, List[str]]

    """
    bl1 = os.path.join(BASE_PATH, 'ta/t-s-blocklist.json')
    bl2 = os.path.join(BASE_PATH, 'hta/s-t-blocklist.json')
    with locked_file(bl1) as f:
        ts_bl = json.load(f)

    with locked_file(bl2) as f:
        st_bl = json.load(f)

    for ta in st_bl:
        if ta not in ts_bl:
            ts_bl[ta] = []

        ts_bl[ta].extend(st_bl[ta])

    for ta in ts_bl:
        ts_bl[ta] = list(set(ts_bl[ta]))

    return ts_bl
