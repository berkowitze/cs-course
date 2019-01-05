from typing import Dict, List, Optional, Union

from mypy_extensions import TypedDict


class Comments(TypedDict):
    given: List[str]
    un_given: List[str]


class RubricOption(TypedDict):
    point_val: int
    descr: str


class RubricItem(TypedDict):
    descr: str
    selected: Optional[int]
    items: List[RubricOption]


class RubricCategory(TypedDict):
    comments: Comments
    rubric_items: List[RubricItem]


class Rubric(TypedDict):
    comments: Comments
    rubric: Dict[str, RubricCategory]


class BracketItem(TypedDict):
    grade: str
    upper_bound_inclusive: float


Bracket = Dict[str, List[BracketItem]]

RawGrade = Dict[str, Optional[Union[int, float]]]
Grade = Union[int, float, str, Dict[str, str], Dict[str, int]]


class LogItem(TypedDict):
    id: int
    complete: bool
    flag_reason: Optional[bool]
    grader: Optional[str]


class HTMLData(TypedDict):
    ta_handins: List[dict]
    handin_count: int
    complete_count: int
    anonymous: bool
    unextracted_logins: Optional[List[str]]


Log = List[LogItem]

if __name__ == '__main__':
    # example of Comments
    c: Comments = {"given": ["C1"], "un_given": []}

    # example of RubricOption
    ropt1: RubricOption = {"point_val": 3, "descr": 'hi'}
    ropt2: RubricOption = {"point_val": 2, "descr": 'bye'}

    # examples of RubricItems
    ri1: RubricItem = {"descr": 'hi', "selected": 0, "items": [ropt1]}
    ri2: RubricItem = {"descr": 'hi', "selected": 1, "items": [ropt1, ropt2]}
    ri3: RubricItem = {"descr": 'hi', "selected": 1, "items": [ropt1, ropt2]}

    # example of RubricCategory
    rc1: RubricCategory = {"comments": c, "rubric_items": [ri1, ri2]}

    # examples of Rubric
    r1: Rubric = {"comments": c, "rubric": {"Functionality": rc1}}

    # examples of BracketItem
    bi1: BracketItem = {"grade": "Check", "upper_bound_inclusive": 10.0}
    bi2: BracketItem = {"grade": "Check Plus", "upper_bound_inclusive": 14.0}

    # example of Bracket
    b1: Bracket = {"Functionality": [bi1, bi2]}
