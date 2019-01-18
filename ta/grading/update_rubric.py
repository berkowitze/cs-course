import json
import sys
from typing import Any, List, Dict

from mypy_extensions import TypedDict

from custom_types import (Comments, Rubric, RubricCategory,
                          RubricItem, RubricOption)


class _OldComment(TypedDict):
    comment: str
    value: bool


def _update_comments(comments: List[_OldComment]) -> Comments:
    """
    update old comments to new comments
    :param comments: old comments
    :return: new comments
    """
    given = [c['comment'] for c in comments if c['value']]
    un_given = [c['comment'] for c in comments if not c['value']]
    res: Comments = {'given': given, 'un_given': un_given}
    return res


def _update_rubric_items(items: List[dict]) -> List[RubricItem]:
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
                            selected=sel_ndx,
                            options=opts)
        new_items.append(n_item)

    return new_items


def update_rubric(old_rubric: Dict[str, Any]) -> Rubric:
    """
    given a rubric of the old style (version < 2.0), update it to a rubric of
    new style (2.0+)
    :param old_rubric:
    :return:
    """
    gen_comments: Comments = _update_comments(old_rubric.pop('_COMMENTS'))
    new_rubric: Dict[str, RubricCategory] = {}
    for key in list(old_rubric.keys()).copy():
        cat_data = old_rubric.pop(key)
        cat_comments = _update_comments(cat_data['comments'])
        cat_rub = _update_rubric_items(cat_data['rubric_items'])
        new_cat = RubricCategory(comments=cat_comments, rubric_items=cat_rub)
        new_rubric[key] = new_cat

    final_rubric: Rubric = Rubric(comments=gen_comments, rubric=new_rubric)
    return final_rubric


if __name__ == '__main__':
    with open(sys.argv[1]) as f:
        data: Dict[str, Any] = json.load(f)

    final_rubric = update_rubric(data)

    with open(sys.argv[1].replace('.json', '') + '-new.json', 'w') as f:
        json.dump(final_rubric, f, indent=2, sort_keys=True)
