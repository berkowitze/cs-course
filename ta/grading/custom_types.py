from mypy_extensions import TypedDict
from typing import Optional, Any, Dict, List, NewType, Union
from dataclasses import dataclass
class Comments(TypedDict):
    given: List[str]
    un_given: List[str]


class RubricOption(TypedDict):
    point_val: int
    descr: str


class RubricItem(TypedDict):
    descr: str
    default: Optional[int]
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

Bracket = NewType('Bracket', Dict[str, List[BracketItem]])
JSON = Union[Dict, List, str, int, bool, float, None]
