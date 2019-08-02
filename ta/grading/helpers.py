# Author: 'Eli Berkowitz'
# Email:  'eliberkowitz@gmail.com'

import json
import os
import string
import sys
from os.path import join as pjoin
from os.path import exists as pexists
from contextlib import contextmanager
from functools import wraps
from typing import Generator, Callable, Any, List, Optional, Dict, Mapping

from filelock import FileLock

from custom_types import (Rubric, RubricCategory, RubricItem, RubricOption,
                          Bracket, BracketItem, Comments, AssignmentJson)
from config import CONFIG

BASE_PATH: str = CONFIG.base_path
res_path: str = pjoin(BASE_PATH, 'resource-lock.lock')

moss_langs = ("c", "cc", "java", "ml", "pascal", "ada", "lisp", "scheme",
              "haskell", "fortran", "ascii", "vhdl", "perl", "matlab",
              "python", "mips", "prolog", "spice", "vb", "csharp",
              "modula2", "a8086", "javascript", "plsql")


import subprocess
import sys

lang_dict = {
    'Python': 'py',
    'Pyret': 'arr'
}

if sys.platform == 'darwin':
    def open_folder(path):
        subprocess.check_call(['open', '--', path])
elif sys.platform == 'linux2':
    def open_folder(path):
        subprocess.check_call(['xdg-open', '--', path])
elif sys.platform == 'win32':
    def open_folder(path):
        subprocess.check_call(['explorer', path])
else:
    def open_folder(path):
        raise ValueError(f'{sys.platform} not supported')

@contextmanager
def locked_file(filename: str, mode: str = 'r') -> Generator:
    """
    Yield a locked file to be used for safe, one at a time reading/writing

    :param filename: filename of path to open
    :param mode: mode to open in (should only be read append or write)
                 opens in read mode by default ("r")
    :return: locked file to use

    **Example:**

    .. code-block:: python

        with locked_file('hello.txt') as f:
            text = f.read()

    """
    if CONFIG.test_mode and False:
        print(f'locked_file({filename!r}, {mode!r})')

    if not (mode == 'r' or mode == 'a' or mode == 'w'):
        base = 'Can only open locked file in r, w, or a mode (just in case)'
        raise ValueError(base)

    if mode == 'r' and not pexists(filename):
        raise OSError(f'File {filename} not found.')

    lock_path = filename + '.lock'
    lock = FileLock(lock_path, timeout=10)  # throw error after 10 seconds
    with lock, open(filename, mode) as f:
        try:
            yield f
        finally:
            # after file is closed, attempt to remove the .lock
            # file; the file is only clutter, it won't have an impact
            # on anything, so don't try too hard
            try:
                os.unlink(lock_path)
            except NameError:
                raise
            except FileNotFoundError:
                pass


@contextmanager
def json_edit(filename: str) -> Generator:
    """

    Enables quickly editing JSON files using with block.
    Note: this only allows mutation of the data in the JSON file;
    if you need to completely change a JSON file, this is not the
    write function to use.

    :param filename: filepath of the JSON file to modify
    :type filename: str
    :raises TypeError: invalid modification to the JSON file

    **Example**:

    >>> with json_edit('hello.json') as data:
    ...     data['hi'].append(4)

    **Example**:

    .. code-block:: python

        with locked_file('hello.json') as f:
            data = json.load(f)

        # operations with data
        with locked_file('hello.json', 'w') as f:
            json.dump(data, f, sort_keys=True, indent=2)

        ## THIS CAN BE REWRITTEN AS:

        with json_edit('hello.json') as data:
            # operations with data

    """
    with locked_file(filename) as f:
        data = json.load(f)

    yield data
    # failure here means the json was modified to be invalid json
    to_write = json.dumps(data, indent=2, sort_keys=True)
    with locked_file(filename, 'w') as f:
        f.write(to_write)


def require_resource(resource: str = res_path) -> Callable[[Callable], Any]:
    """

    use require_resource as a decorator when writing a function that you
    shouldn't be run simultaneously

    :param resource: resource to lock while the function is being run
                     (set by default, but can be overrided if needed)
    :return: a decorator to be used around a function/method as required

    .. code-block:: python

        @require_resource()
        def extract_handin(...):
            ...

    """
    def decorator(f):
        @wraps(f)
        def magic(*args, **kwargs):
            """ runs the wrapped functions while a lock is acquired """
            with FileLock(resource, timeout=10):
                return f(*args, **kwargs)

        return magic

    return decorator


def json_file_with_check(path: str):
    """

    returns data in JSON file after checking that it contains valid JSON

    :param path: the path of the JSON file
    :return: the data in the JSON file
    :raises AssertionError: invalid JSON file (filename or data in file)

    """
    assert pexists(path), f'json path {path} does not exist'
    assert os.path.splitext(path)[1] == '.json', \
        f'json path {path} has invalid extension'

    with locked_file(path) as f:
        try:
            data = json.load(f)
        except ValueError:
            raise AssertionError(f'JSON invalid ({path})')
        else:
            return data


def rubric_check(path: str) -> None:
    """

    Check validity of rubric by path

    :param path: path of rubric to check
    :return: None as long as rubric is valid
    :raises AssertionError: invalid rubric

    """
    rubric: Rubric = json_file_with_check(path)
    loaded_rubric_check(rubric)


def loaded_rubric_check(rubric: Rubric) -> None:
    """

    :param rubric: rubric to check
    :type rubric: Rubric
    :return: nothing if the rubric is valid
    :raises AssertionError, KeyError: invalid rubric

    """

    def p(s):
        return f'\nInvalid section of rubric: \n{s}\n'

    def has_keys(d: Mapping, keys: List[str]) -> bool:
        """ makes sure d has only the keys specified """
        return all([k in d for k in keys]) and all([k in keys for k in d])

    def check_rubric_category(rc: RubricCategory) -> bool:
        assert has_keys(rc, ['fudge_points', 'comments', 'rubric_items']), p(rc)
        assert check_comments(rc['comments']), rc['comments']
        assert isinstance(rc['rubric_items'], list), rc['rubric_items']
        assert all([check_item(ri) for ri in rc['rubric_items']]), \
                p(rc['rubric_items'])
        assert isinstance(rc['fudge_points'], list), p(rc)
        assert isinstance(rc['fudge_points'][0], (int, float)), p(rc)
        assert isinstance(rc['fudge_points'][1], (int, float)), p(rc)
        assert len(rc['fudge_points']) == 2, p(rc)
        return True

    def check_item(ri: RubricItem) -> bool:
        assert has_keys(ri, ['descr', 'selected', 'options']), p(ri)
        assert isinstance(ri['descr'], str), p(ri['descr'])
        assert isinstance(ri['selected'], (type(None), int)), p(ri['selected'])
        assert isinstance(ri['options'], list), p(ri['options'])
        assert all([check_opt(opt) for opt in ri['options']]), p(ri['options'])
        return True

    def check_opt(ro: RubricOption):
        assert has_keys(ro, ['point_val', 'descr']), p(ro)
        assert isinstance(ro, dict), p(ro)
        assert isinstance(ro['point_val'], (int, float)), p(ro)
        assert isinstance(ro['descr'], str), p(ro['descr'])
        return True

    def check_comments(comments: Comments) -> bool:
        assert has_keys(comments, ['given', 'un_given']), p(comments)
        assert isinstance(comments, dict), p(comments)
        assert isinstance(comments['given'], list), p(comments['given'])
        assert isinstance(comments['un_given'], list), p(comments['un_given'])
        assert all([isinstance(s, str) for s in comments['given']]), \
                p(comments['given'])
        assert all([isinstance(s, str) for s in comments['un_given']]), \
                p(comments['un_given'])
        return True

    assert has_keys(rubric, ['rubric', 'comments', 'emoji']), p(rubric.keys())
    assert isinstance(rubric['emoji'], bool)
    assert check_comments(rubric['comments']), p(rubric['comments'])

    assert isinstance(rubric, dict), p('Entire rubric should be dict')
    assert isinstance(rubric['rubric'], dict), \
            p('rubric subcategory should be dict')  # rubric key is dict
    vals = rubric['rubric'].values()
    assert all([check_rubric_category(rc) for rc in vals])


def bracket_check(path: str) -> None:
    """

    given path to a bracket file, checks that it is a valid bracket
    file, raising an error if it is not

    :param path: path to bracket file
    :type path: str
    :returns: None if the rubric is valid
    :rtype: None
    :raises AssertionError, KeyError: Invalid bracket file

    """
    def check_bracket_item(bi: BracketItem) -> bool:
        assert isinstance(bi, dict)
        assert isinstance(bi['grade'], str)
        assert isinstance(bi['upper_bound_inclusive'], (int, float))
        return True

    def check_bracket_cat(bc: List[BracketItem]) -> bool:
        assert isinstance(bc, list)
        assert all(map(check_bracket_item, bc))
        return True

    data: Bracket = json_file_with_check(path)
    assert isinstance(data, dict)
    assert all(map(check_bracket_cat, data.values()))


def update_comments(comments: Comments, new_given: List[str]) -> None:
    """

    modify `comments` to update given comments to match new_given
    and un_given comments to have all un_given comments

    :param comments: a Comments dictionary (with given and un_given keys)
    :type comments: Comments
    :param new_given:  a list of comments that the TA has assigned to
                       be the new given comments of this Comments block
    :type new_given: List[str]
    :returns: None

    """

    # all comments that had been given but are not being given now
    # are added to the un_given list
    new_ungiven = [c for c in comments['given'] if c not in new_given]
    comments['un_given'].extend(new_ungiven)

    # reset given comments to the new_given comments
    comments['given'] = new_given

    sv = set(comments['given'])  # local variable to speed up contains checking
    # comments in un_given that are now being given are removed
    comments['un_given'] = [c for c in comments['un_given'] if c not in sv]


def line_read(filename: str, delim: Optional[str] = None) -> list:
    """

    read lines from a file. returns list of strings with whitespace
    right-stripped with delim=None, or list of lists of strings with
    whitespace stripped with delim=str
    (I don't use csv module because I'm unsure exactly how it parses lines
    and it sometimes has weird results; this way there's full control)

    :param filename: name of file to open
    :type filename: str
    :param delim: if None, reads filename as list of strings, otherwise will
                  split each line on delim. defaults to None
    :type delim: Optional[str], optional
    :returns: if delim is None, a list of strings (one string for each
              line). if delim is not None, a list of lists of strings, one
              list for each line in the file and that list contains the split
              up line based on delim
    :rtype: list

    **example**:

    >>> line_read('students.txt')
    ['student-login-1', 'student-login-2', ...]
    >>> line_read('students.csv', delim=',')
    [['student-login-1', 'student-email-1', 'student-name-1'],
     ['student-login-2', 'student-email-2', 'student-name-2'],
     ...]


    """
    with locked_file(filename) as f:
        raw: str = f.read()

    lines = [line.rstrip() for line in raw.strip().split('\n')]
    if delim is not None:
        return [line.split(delim) for line in lines]
    else:
        return lines


def remove_duplicates(lst: list) -> list:
    """

    removes all duplicates from the input list. order is maintained.
    input list is not modified. linear runtime.

    :param lst: any list
    :type lst: list
    :returns: the same list as lst with any duplicates removed
    :rtype: list

    """

    # Create an empty list to store unique elements
    unique_list: list = []
    unique_set: set = set()

    # Iterate over the original list and for each element
    # add it to uniqueList, if its not already there.
    for elem in lst:
        if elem not in unique_set:
            unique_list.append(elem)
            unique_set.add(elem)

    return unique_list


def red(s: str) -> str:
    """

    given a string s, return s wrapped in the escape characters required
    to print the string in a red color to the terminal (ANSI codes)

    """
    return f'\033[31m{s}\033[0m'


def green(s: str) -> str:
    """

    given a string s, return s wrapped in the escape characters required
    to print the string in a green color to the terminal (ANSI codes)

    """
    return f'\033[32m{s}\033[0m'


def col_str_to_num(col: str) -> int:
    """

    convert a spreadsheet column letter to the number, starting from 1,
    corresponding to that column

    example:

    >>> col_str_to_num("C")
    3

    :param col: column to convert
    :type col: str
    :returns: the number of the column that col corresponds to
    :rtype: int

    """
    num = 0
    for c in col:
        if c in string.ascii_letters:
            num = num * 26 + (ord(c.upper()) - ord('A')) + 1

    return num


def col_num_to_str(n: int) -> str:
    """

    convert a spreadsheet column number to the corresponding column, starting
    from n = 1 corresponding to A

    example:

    >>> col_num_to_str(4)
    'D'
    >>> col_num_to_str(27)
    'AA'

    :param n: column number to convert
    :type col: int
    :returns: the column label that n corresponds to
    :rtype: str

    """
    string = ''
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        string = chr(65 + remainder) + string

    return string


def check_assignments(data: AssignmentJson):
    ecol = col_str_to_num(CONFIG.handin.end_col)
    for asgn in data['assignments']:
        for q in data['assignments'][asgn]['questions']:
            qcol = col_str_to_num(q['col'])
            if qcol > ecol:
                e = (f'assignments.json assignment {asgn} has question '
                     f'{q["filename"]} referencing column {qcol}, which\n'
                     f'is over the end_col "{ecol} (set in assignments.json)'
                     )
                raise ValueError(e)
