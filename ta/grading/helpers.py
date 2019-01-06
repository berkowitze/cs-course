# Author: 'Eli Berkowitz'
# Email:  'eliberkowitz@gmail.com'

import json
import os
from contextlib import contextmanager
from functools import wraps
from typing import Generator, Callable, Any

from filelock import FileLock

from custom_types import *

BASE_PATH: str = '/course/cs0111'
def_res_path: str = os.path.join(BASE_PATH, 'resource-lock.lock')


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
    if not (mode == 'r' or mode == 'a' or mode == 'w'):
        base = 'Can only open locked file in r, w, or a mode (just in case)'
        raise ValueError(base)
    
    lock_path = filename + '.lock'
    lock = FileLock(lock_path, timeout=10)  # throw error after 10 seconds
    with lock, open(filename, mode) as f:
        yield f

        # after file is closed, attempt to remove the .lock
        # file; the file is only clutter, it won't have an impact
        # on anything, so don't try too hard
        try:
            os.unlink(lock_path)
        except NameError:
            raise
        except FileNotFoundError:
            pass


def require_resource(resource: str = def_res_path) -> Callable[[Callable], Any]:
    """ use require_resource as a decorator when writing a function that you
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
            with FileLock(resource):
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
    assert os.path.exists(path), f'json path {path} does not exist'
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
    :raises AssertionError: invalid rubric

    """

    def check_rubric_category(rc: RubricCategory) -> bool:
        assert check_comments(rc['comments'])
        assert isinstance(rc['rubric_items'], list)
        assert all(map(check_item, rc['rubric_items']))
        return True

    def check_item(ri: RubricItem) -> bool:
        assert isinstance(ri['descr'], str)
        assert isinstance(ri['selected'], (type(None), int))
        assert isinstance(ri['items'], list)
        assert all(map(check_opt, ri['items']))
        return True

    def check_opt(ro: RubricOption):
        assert isinstance(ro, dict)
        assert isinstance(ro['point_val'], int)
        assert isinstance(ro['descr'], str)
        return True

    def check_comments(comments: Comments) -> bool:
        assert isinstance(comments, dict)
        assert isinstance(comments['given'], list)
        assert isinstance(comments['un_given'], list)
        assert all(map(lambda s: isinstance(s, str),
                       comments['given']))
        assert all(map(lambda s: isinstance(s, str),
                       comments['un_given']))
        return True

    assert isinstance(rubric, dict)  # loaded rubric is a dictionary
    assert check_comments(rubric['comments'])

    assert isinstance(rubric['rubric'], dict)  # rubric key exists
    assert all(map(check_rubric_category, rubric['rubric'].values()))


def bracket_check(path: str) -> None:
    """ given path to a bracket file, checks that it is a valid bracket
    file, raising an assertion error if it is not """
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
    inputs:
        - comments, a Comments dictionary (given and un_given keys)
        - new_given, a list of comments that the TA has assigned to
          be the new given comments of this Comments block
    output: None
    effect: modify `comments` to update given comments to match new_given
    and un_given comments to have all un_given comments """

    # all comments that had been given but are not being given now
    # are added to the un_given list
    new_ungiven = [c for c in comments['given'] if c not in new_given]
    comments['un_given'].extend(new_ungiven)

    # reset given comments to the new_given comments
    comments['given'] = new_given

    sv = set(comments['given'])  # local variable to speed up contains checking
    # comments in un_given that are now being given are removed
    comments['un_given'] = [c for c in comments['un_given'] if c not in sv]
