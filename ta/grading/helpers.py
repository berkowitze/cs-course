# Author: 'Eli Berkowitz'
# Email:  'eliberkowitz@gmail.com'

import json
import os
from contextlib import contextmanager
from functools import wraps
from typing import Generator

from filelock import FileLock

from custom_types import *

BASE_PATH: str = '/course/cs0111'
def_res_path: str = os.path.join(BASE_PATH, 'resource-lock.lock')


@contextmanager
def locked_file(filename: str, mode: str = 'r') -> Generator:
    """ this will ensure no file is opened across different processes """
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


def require_resource(resource: str = def_res_path):
    """ use require_resource as a decorator when writing a function that you
    don't want to be run simultaneously; for example, if you don't want to run
    extract_handin at the same time on two different TA's computers
    you'd do something like:

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
    given a path to a json file, return the data in that json file
    also checking that the path exists (with AssertionErrors raised
    for invalid input, so that they can be caught along with other
    AssertionErrors raised in rubric/bracket checking functions below
    if necessary). works for Rubrics and Brackets
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
    """ given a path to a rubric JSON file
        /course/.../ta/grading/data/rubrics/.../q1.json
    determines whether or not the rubric is valid (should follow spec in
    custom_types). raises assertion error if invalid
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

    data: Rubric = json_file_with_check(path)
    assert isinstance(data, dict)  # loaded rubric is a dictionary
    assert check_comments(data['comments'])

    assert isinstance(data['rubric'], dict)  # rubric key exists
    assert all(map(check_rubric_category, data['rubric'].values()))


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
          be the new given key of this Comments block
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
