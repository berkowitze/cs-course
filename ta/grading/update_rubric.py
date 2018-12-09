import json
import sys
from custom_types import *
from mypy_extensions import TypedDict
from typing import List, Dict, Optional, Any

class OldComment(TypedDict):
    comment: str
    value: bool


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


with open(sys.argv[1]) as f:
    data: Dict[str, Any] = json.load(f)

def update_comments(comments: List[OldComment]) -> Comments:
    given = [c['comment'] for c in comments if c['value']]
    un_given = [c['comment'] for c in comments if not c['value']]
    return {'given': given, 'un_given': un_given}

def update_rubric(items: List[dict]) -> List[RubricItem]:
    new_items: List[RubricItem] = []
    for item in items:
        if item['default'] is None:
            def_ndx = None
        else:
            def_ndx = item['options'].index(item['default'])

        if item.get('value', None) is None:
            sel_ndx = None
        else:
            sel_ndx = item['options'].index(item['value'])

        zipped_opts = zip(item['point-val'], item['options'])
        opts = [RubricOption(descr=v, point_val=d) for (d, v) in zipped_opts]
        n_item = RubricItem(descr=item['name'],
                            default=def_ndx,
                            selected=sel_ndx,
                            items=opts)
        new_items.append(n_item)

    return new_items


gen_comments: Comments = update_comments(data.pop('_COMMENTS'))
new_rubric: Dict[str, RubricCategory] = {}
for key in list(data.keys()).copy():
    cat_data = data.pop(key)
    cat_comments = update_comments(cat_data['comments'])
    cat_rub = update_rubric(cat_data['rubric_items'])
    new_cat = RubricCategory(comments=cat_comments, rubric_items=cat_rub)
    new_rubric[key] = new_cat

final_rubric: Rubric = Rubric(comments=gen_comments, rubric=new_rubric)
with open(sys.argv[1].replace('.json', '') + '-new.json', 'w') as f:
    json.dump(final_rubric, f, indent=2, sort_keys=True)

