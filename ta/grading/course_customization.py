from __future__ import annotations

import json
from textwrap import fill
from typing import Sequence, TYPE_CHECKING

from custom_types import *
from helpers import locked_file

if TYPE_CHECKING:
    from classes import Question, Assignment


def increasing(lst: Sequence[float]) -> bool:
    """

    returns whether or not the input list is increasing (non-decreasing)
    (all numbers larger or equal to than previous numbers)

    :param lst: sequence of numbers
    :type lst: Sequence[float]
    :returns: True if lst is non-decreasing, False otherwise
    :rtype: bool

    """
    rst = lst[1:]
    while rst:
        if lst[0] > lst[1]:
            return False
        rst = lst[1:]

    return True


def full_asgn_name_to_dirname(asgn_name: str) -> str:
    """

    :param asgn_name: full name of assignment
    :type asgn_name: str
    :returns: the string of the directory name to be used for that assignment.
              this directory name will be used for all grading app related
              filesystems
    :rtype: str

    **Example**:

    >>> full_asgn_name_to_dirname("Homework 3")
    "homework3"

    """
    return asgn_name.lower().replace(' ', '')


def get_empty_raw_grade(asgn: Assignment) -> RawGrade:
    """

    create a dictionary with one key for every category on this assignment

    :param asgn: assignment to get empty raw grade for
    :type asgn: Assignment
    :returns: empty raw grade for this assignment
    :rtype: RawGrade

    **Example**:

    >>> get_empty_raw_grade(Assignment("Homework 4"))
    {"Functionality": None, "Design": None}

    """
    with locked_file(asgn.bracket_path) as f:
        bracket: Bracket = json.load(f)

    empty_grade: RawGrade = {k: None for k in bracket.keys()}
    return empty_grade


def determine_grade(raw_grade: RawGrade,
                    late: bool,
                    asgn: Assignment
                    ) -> Grade:
    """

    given a raw grade (i.e. category -> float dictionary), determine the
    student's full grade (i.e. category -> string dictionary)

    :param raw_grade: a raw grade (defined in custom_types)
    :type raw_grade: RawGrade
    :param asgn: the Assignment for which to determine the grade
    :type asgn: Assignment
    :param late: whether or not the student handed in the assignment late
    :type late: bool
    :returns: The grade to give the student (following spec from custom_types)
    :rtype: Grade

    **Example**:

    >>> determine_grade({"Functionality": 20, "Design": 12}, "Homework1")
    32
    >>> determine_grade({"Functionality": 12, "Design": 4}, "Homework 6")
    {"Functionality": "Check Plus", "Design": "Check Minus"}

    """
    def use_bracket(b_item: List[BracketItem],
                    score: Union[int, float]
                    ) -> str:
        bounds = [k['upper_bound_inclusive'] for k in b_item]
        if not increasing(bounds):
            raise ValueError('Bounds must increase throughout bracket')

        for i, item in enumerate(b_item):
            if score <= item['upper_bound_inclusive']:
                cg = item['grade']
                if not late:
                    return cg
                elif late and i == 0:
                    # lowest grade anyway...
                    return cg
                else:
                    # go down a grade bracket
                    ng = b_item[i - 1]['grade']
                    return f"{cg} -> {ng}"

        g = b_item[-1]['grade']
        print(f'Warning: grade above uppermost bound. Giving {g}')
        return g

    # "No Handin" only comes from a None in the grade dictionary
    with locked_file(asgn.bracket_path) as f:
        brackets: Bracket = json.load(f)

    assert brackets.keys() == raw_grade.keys(), 'invalid rubric'

    final_grade = {}
    for cat in brackets:
        cg = raw_grade[cat]
        if cg is None:
            final_grade[cat] = "No handin"
        else:
            if brackets[cat] == "Numeric":
                if late:
                    g = f'{cg} -> {cg - 1}'
                    final_grade[cat] = g
                else:
                    final_grade[cat] = str(cg)
            else:
                final_grade[cat] = use_bracket(brackets[cat], cg)

    return final_grade


def get_handin_report_str(rubric: Rubric,
                          grader_login: str,
                          question: Question) -> str:
    """

    Make a report string that will be sent to the student with all relevant
    grade information

    :param rubric: rubric for the student
    :type rubric: Rubric
    :param grader_login: login of the grader for the assignment
    :type grader_login: str
    :param question: question that was graded for this rubric
    :type question: Question
    :returns: report string
    :rtype: str

    """
    report_str = f'{question.code_filename}\n'
    pre_string = '  '  # each problem is nested by pre_string in email
    for cat in rubric['rubric']:
        given_cs = sorted(rubric['rubric'][cat]['comments']['given'],
                          key=lambda s: -len(s))
        given_cs.sort(key=lambda s: -len(s))
        for comment in given_cs:
            comment_lines = fill(comment, 74,
                                 initial_indent=(pre_string * 2 + '- '),
                                 subsequent_indent=(pre_string * 3))
            report_str += f'{comment_lines}\n\n'

    gen_comments = sorted(rubric['comments']['given'], key=lambda s: -len(s))
    for comment in gen_comments:
        comment_lines = fill(comment, 74, initial_indent=f'{pre_string}- ')
        report_str += f'{comment_lines}\n\n'

    report_str += f'Grader: {grader_login} ({grader_login}@cs.brown.edu)'
    report_str += f'\n\n{"-" * 74}\n'
    return report_str
