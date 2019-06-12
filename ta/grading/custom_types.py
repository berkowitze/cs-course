from typing import Dict, List, Optional, Union

from mypy_extensions import TypedDict


class Comments(TypedDict):
    """

    comments class (for rubrics)

    :ivar given: the given comments
    :vartype given: List[str]
    :ivar un_given: the ungiven coments (to be suggested)
    :vartype un_given: List[str]

    """
    given: List[str]
    un_given: List[str]


class RubricOption(TypedDict):
    """

    individual rubric option (each option in a select dropdown
    in the grading app as of 2.0)

    :var point_val: how many points this option is worth
    :vartype point_val: int
    :ivar descr: the description of this rubric option
    :vartype descr: str

    """
    point_val: int
    descr: str


class RubricItem(TypedDict):
    """

    rubric item (collection of rubric options and a description)

    :param descr: the description for this item
    :type descr: str
    :param selected: the selected option, or None if there is nothing selected
    :type selected: Optional[int]
    :param options: rubric options for this RubricItem
    :type options: List[RubricOption]

    """
    descr: str
    selected: Optional[int]
    options: List[RubricOption]


class RubricCategory(TypedDict):
    """

    rubric category (i.e. Functionality)

    :param comments: the comments given for this category
    :type comments: Comments
    :param rubric_items: the rubric items for this category
    :type rubric_items: List[RubricItem]
    :param fudge_points: a list of [selected fudge points, max fudge points]
                         floats; for base rubrics, the first element
                         should usually be 0.0
    :type fudge_points: List[float]

    """
    comments: Comments
    rubric_items: List[RubricItem]
    fudge_points: List[float]


class Rubric(TypedDict):
    """

    full rubric type

    :param comments: general comments
    :type comments: Comments
    :param rubric: rubric categories for this rubric
    :type rubric: Dict[str, RubricCategory]
    :param emoji: whether or not to put an animal text art emoji on
                  the student's grade report :)
    :type emoji: bool

    """
    comments: Comments
    rubric: Dict[str, RubricCategory]
    emoji: bool


class BracketItem(TypedDict):
    """

    individual bracket item (cutoffs and grade description)

    :param grade: the grade to give if the student's grade lies in this
                  bracket item.
    :type grade: str
    :param upper_bound_inclusive: the cutoff for a grade to be in this
                                  grade category (inclusive on the upper bound)
    :type upper_bound_inclusive: float

    """
    grade: str
    upper_bound_inclusive: float


#: Bracket type, which is a category -> list of bracket items
#: dictionary
Bracket = Dict[str, List[BracketItem]]


#: Raw grade type, which is collected from RubricCategories
#: across assignments for each question
RawGrade = Dict[str, Optional[Union[int, float]]]

#: Final grade type, which is what is used for grade reports and
#: gradebooks
Grade = Union[int, float, str, Dict[str, str], Dict[str, int]]


class HTMLData(TypedDict):  # TODO: can this be better?
    """

    data that is transmitted to the grading app to populate the TA's
    view and options for a specific Question

    :param ta_handins: handins that this TA has extracted
    :type ta_handins: List[dict]
    :param handin_count: number of handins there are to grade for this question
    :type handin_count: int
    :param complete_count: number of handins completed for this question
    :type complete_count: int
    :param anonymous: whether or not this question is being graded anonymously
    :type anonymous: bool
    :param unextracted_logins: list of logins that are unextracted for this
                               Question, or None if the assignment is being
                               graded anonymously
    :type unextracted_logins: Optional[List[str]]

    """
    ta_handins: List[dict]
    handin_count: int
    complete_count: int
    anonymous: bool
    unextracted_logins: Optional[List[str]]


class LogItem(TypedDict):
    """

    log item (for individual Handin with particular Question)

    :param id: anonymous ID of handin
    :type id: int
    :param complete: whether or not grading is complete for this handin
    :type complete: bool
    :param flag_reason: the flag reason, or None if the handin is unflagged
    :type flag_reason: Optional[str]
    :param grader: login string of grader if handin is extracted, None if not
    :type grader: Optional[str]

    """
    id: int
    complete: bool
    flag_reason: Optional[str]
    grader: Optional[str]

# "assignments": {
#   "CS18 Bridgework - BSTs": {
#     "anonymous": false,
#     "due": "02/01/2019 05:00PM",
#     "grading_completed": false,
#     "grading_started": false,
#     "group_data": null,
#     "late_due": "02/02/2019 01:00PM",
#     "questions": [
#       {
#         "col": "AJ",
#         "filename": "bsts.arr",
#         "ts_lang": "arr"
#       }
#     ],
#     "sent_emails": false
#   },


class QuestionData(TypedDict):  # currently unused
    col: str  # column the question is in in the Google Doc
    ts_lang: str  # testsuite language
    filename: str  # change to list of strings


class GroupData(TypedDict):
    partner_col: Optional[str]  # none if partner data not being collected
    multi_part_name: str  # i.e. project3 for design check & main handin


class AssignmentData(TypedDict):  # currently unused
    anonymous: bool
    due: str
    grading_started: bool
    grading_completed: bool
    emails_sent: bool
    # TODO: make this due_late again for key order niceness lul
    late_due: str
    group_data: Optional[GroupData]
    questions: List[QuestionData]


class AssignmentJson(TypedDict):
    aa_README: List[str]
    assignments: Dict[str, AssignmentData]


#: Log type, which are used to track progress on question grading
Log = List[LogItem]

if __name__ == '__main__':
    # example of Comments
    c: Comments = {"given": ["C1"], "un_given": []}

    # example of RubricOption
    ropt1: RubricOption = {"point_val": 3, "descr": 'hi'}
    ropt2: RubricOption = {"point_val": 2, "descr": 'bye'}

    # examples of RubricItems
    ri1: RubricItem = {"descr": 'hi', "selected": 0, "options": [ropt1]}
    ri2: RubricItem = {"descr": 'hi', "selected": 1, "options": [ropt1, ropt2]}
    ri3: RubricItem = {"descr": 'hi', "selected": 1, "options": [ropt1, ropt2]}

    # example of RubricCategory
    rc1: RubricCategory = {"comments": c, "rubric_items": [ri1, ri2],
                           "fudge_points": [0.0, 10.0]}

    # examples of Rubric
    r1: Rubric = {"comments": c,
                  "rubric": {"Functionality": rc1},
                  "emoji": True}

    # examples of BracketItem
    bi1: BracketItem = {"grade": "Check", "upper_bound_inclusive": 10.0}
    bi2: BracketItem = {"grade": "Check Plus", "upper_bound_inclusive": 14.0}

    # example of Bracket
    b1: Bracket = {"Functionality": [bi1, bi2]}
