import json
import os
import urllib.parse

from datetime import datetime
from filelock import FileLock, Timeout
from functools import lru_cache
from helpers import (BASE_PATH, CONFIG, col_str_to_num,
                     locked_file, json_edit)
from typing import Optional, List
from dataclasses import dataclass

extension_path = os.path.join(BASE_PATH, 'hta/grading/extensions.json')
late_days_path = os.path.join(BASE_PATH, 'hta/handin/late_days.json')


def get_used_late_days(login: str) -> List[str]:
    with locked_file(late_days_path) as f:
        data = json.load(f)

    if login in data:
        return data[login]
    else:
        return []


def add_late_day(login: str, asgn: str) -> bool:
    with json_edit(late_days_path) as data:
        login_dat = set(data.get(login, []))
        if len(login_dat) >= CONFIG.handin.late_days:
            return False

        login_dat.add(asgn)
        data[login] = list(login_dat)
        return True


def url_to_gid(url: str) -> Optional[str]:
    """

    take a Google Drive file url and extract the ID from it

    **example**:

    >>> u = "https://drive.google.com/open?id=id-of-filename"
    >>> url_to_gid(u)
    'id-of-filename'

    :param url: URL to parse, or None (which returns None). url should have
                parameter ?id=<id-returned>
    :type url: str
    :returns: ID of URL

    """

    if url == '':
        return None

    o = urllib.parse.urlparse(url)
    try:
        return urllib.parse.parse_qs(o.query)['id'][0]
    except KeyError:
        raise ValueError(f'URL in spreadsheet has invalid format\nURL: {url}')


def load_students():
    path = os.path.join(BASE_PATH, 'ta/groups/students.csv')
    students = []
    with locked_file(path, 'r') as f:
        lines = map(str.strip, f.read().strip().split('\n'))
        for line in lines:
            row = line.split(',')
            if len(row) != 3:
                e = 'row %s in students.txt invalid, lines=%s'
                raise IndexError(e % (row, lines))
            username = row[0]
            email = row[1]
            students.append((email, username))

    students.append(('csci0111@brown.edu', 'csci0111', 'HTA Account'))

    return students


def email_to_login(email):
    students = load_students()
    for student in students:
        if student[0] == email:
            return student[1]

    raise ValueError('Student %s not found.' % email)


def login_to_email(login):
    students = load_students()
    for student in students:
        if student[1] == login:
            return student[0]

    raise ValueError('Student %s not found.' % login)


@lru_cache(10)
def confirmed_responses(filename=CONFIG.handin.log_path):
    with locked_file(filename, 'r') as f:
        lines = f.read().strip().split('\n')
        if not lines or lines == ['']:
            return []
        else:
            return set(map(int, lines))


def timestamp_to_datetime(timestamp):
    ''' given a timestamp from a Google Form submission sheet, turn it
    into a datetime object and return the datetime '''
    return datetime.strptime(timestamp, '%m/%d/%Y %H:%M:%S')


def make_span(text: str, color: Optional[str] = None) -> str:
    """

    make a HTML span with the input text and optionally a css color

    **example**:
    >>> make_span("Hello there", "green")
    '<span style="color: green">'Hello There</span>'

    :param text: text of the span element
    :type text: a plaintext string
    :param color: the color to make the span, or None for black
    :type color: Optional[int]
    :rtype: str
    :returns: The HTML for a span with `text` as input and `color` as the color

    """
    if color is None:
        return f'<span>{text}</span>'
    else:
        return f'<span style="color: {color}">{text}</span>'


@dataclass
class Extension:
    login: str
    asgn: str
    until: datetime


def load_extensions():
    with locked_file(extension_path) as f:
        return [Extension(**ext) for ext in json.load(f)]

