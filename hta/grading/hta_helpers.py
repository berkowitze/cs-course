import json
import os
from collections import defaultdict
from typing import Dict, List, Optional

from helpers import locked_file

BASE_PATH = '/course/cs0111'

def load_students() -> List[List[str]]:
    """reads students from the hta/groups/students.csv file 
    
    Returns:
        List[str]: list of (login, email, name)
    """
    path = os.path.join(BASE_PATH, 'hta', 'groups', 'students.csv')
    return line_read(path, delim=",")

def student_list() -> List[str]:
    """list of student logins from hta/groups/students.txt
    
    Returns:
        List[str]: list of logins of students in the class
    """
    path = os.path.join(BASE_PATH, "hta", "groups", "students.txt")
    return line_read(path)


def email_to_login(email: str) -> str:
    """Converts brown email to CS login
    
    Args:
        email (str): Student's Brown email (aliases will not work)
    
    Returns:
        str: Student's CS login
    
    Raises:
        ValueError: when email not found
    """
    students = load_students()
    for student in students:
        if student[1] == email:
            return student[0]

    raise ValueError(f'Student {email} not found.')


def login_to_email(login: str) -> str:
    """Convert CS login to full Brown email
    
    Args:
        login (str): CS login of student
    
    Returns:
        str: Brown email of student (no aliases)
    
    Raises:
        ValueError: Student with input login not found
    """
    students = load_students()
    for student in students:
        if student[0] == login:
            return student[1]

    raise ValueError(f'Student {login} not found.')


def argmax(lst: List[int]) -> int:
    """Get index of maximum integer of input list
    
    Args:
        lst (List[int]): list of non-negative integers
    
    Returns:
        int: Index of maximum integer in lst
    
    Raises:
        ValueError: Cannot input a list with repeated values
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
    """Returns None if no submission for this student on this assignment,
    and the path of the student's latest submission if they did submit
    
    Args:
        base (str): base path (i.e. /course/cs0111/hta/handin/students)
        login (str): cs login of student
        mini_name (str): directory name of assignment (i.e. homework2)
    
    Returns:
        Optional[str]: None if login has no handin for mini_name, and
        the path of the latest submission for login if they do
    """
    sub_path = os.path.join(base, login, mini_name)
    if not os.path.exists(sub_path):
        return None

    submissions = [f for f in os.listdir(sub_path) if 'submission' in f]
    sub_numbs = [int(f.split('-')[0]) for f in submissions]
    latest = submissions[argmax(sub_numbs)]
    return os.path.join(sub_path, latest)


def line_read(filename: str, delim: Optional[str] = None) -> list:
    """read lines from a file. returns list of strings with whitespace
    right-stripped with delim=None, or list of lists of strings with
    whitespace stripped with delim=str
    (I don't use csv module because I'm unsure exactly how it parses lines
    and it sometimes has weird results; this way there's full control)
    
    Args:
        filename (str): name of file to open
        delim (Optional[str], optional): if None, reads filename as
        list of strings, otherwise will split each line on delim
        i.e. delim=',' a line 'hi,there' -> ['hi', 'there']
    
    Returns:
        list: if delim is None, a list of strings (one string for each
        line). if delim is not None, a list of lists of strings, one
        list for each line in the file and that list contains the split
        up line based on delim
    """
    with locked_file(filename) as f:
        raw: str = f.read()

    lines = [line.rstrip() for line in raw.strip().split('\n')]
    if delim is not None:
        return [line.split(delim) for line in lines]
    else:
        return lines
