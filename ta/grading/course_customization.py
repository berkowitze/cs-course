from __future__ import annotations

import os
import json
import random
import urllib.parse
from textwrap import fill
from typing import Sequence, TYPE_CHECKING

from custom_types import *
from helpers import locked_file, BASE_PATH

if TYPE_CHECKING:
    from classes import Question, Assignment

spath = os.path.join(BASE_PATH, 'hta/grading/regrading/settings.json')
with locked_file(spath) as f:
    regrade_settings = json.load(f)

emoji_path = os.path.join(BASE_PATH, 'ta/asciianimals')
emojis = os.listdir(emoji_path)

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
    empty_grade: RawGrade = {}
    for q in asgn.questions:
        q_rub = q.copy_rubric()
        empty_grade.update({cat: None for cat in q_rub['rubric']})

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
    max_grades = asgn.max_grades()  # cat -> max possible grade
    final_grade = {}
    for cat in raw_grade:
        if raw_grade[cat] is None:
            final_grade[cat] = "No handin"
            continue

        max_grade = max_grades[cat]
        grade_val = max(raw_grade[cat], 0)
        final_grade[cat] = f"{grade_val} / {max_grade}"

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
    def comment_section(category: str, comments: List[str]) -> str:
        if not comments:
            return ''

        pre_string = '    '
        s = ''
        for comment in comments:
            comment_lines = fill(comment, 74,
                                 initial_indent=f'{pre_string}- ',
                                 subsequent_indent=f'{pre_string}  ')
            s += f'{comment_lines}\n\n'

        return s

    def grade_section(rc: RubricCategory) -> str:
        gs = ''
        for item in rc['rubric_items']:
            assert item['selected'] is not None, 'unselected rubric item'
            opt = item['options'][item['selected']]
            pts = opt['point_val']
            descr = opt['descr']
            max_pts = max([opt['point_val'] for opt in item['options']])
            gs += f'    {pts} / {max_pts} - {item["descr"]}: {descr}\n'
        
        gs += '\n'
        return gs

    report_str = f'Question {question._qnumb}: {question.code_filename}\n'
    for cat in rubric['rubric']:
        given_cs = rubric['rubric'][cat]['comments']['given']
        report_str += f'  {cat}\n'
        report_str += grade_section(rubric['rubric'][cat])
        report_str += comment_section(cat, given_cs)

    gen_comments = rubric['comments']['given']
    report_str += comment_section('General Comments', gen_comments)

    if rubric['emoji']:
        emoji = random.choice(emojis)
        em_path = os.path.join(emoji_path, emoji)
        with locked_file(em_path) as f:
            emoji_text = f.read()

        report_str += f'\n{emoji_text}\n\n'

    asgn_lnk = urllib.parse.quote(question.assignment.full_name)
    
    lnk_temp = regrade_settings['request-form-filled-link']
    complaint_lnk = lnk_temp.format(assignment_name=asgn_lnk,
                                    indicated_question=question._qnumb)
    report_str += f'Please direct any grade complaint/question to: {complaint_lnk}'
    report_str += f'\n\n{"-" * 74}\n'
    return report_str
