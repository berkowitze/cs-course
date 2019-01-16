import sys
from typing import Callable, List, Optional

import tabulate


def ez_prompt(prompt: str,
              checker: Optional[Callable[[str], bool]] = None,
              fail_check_msg: Optional[str] = None,
              raise_on_ctrl_c: bool = False) -> Optional[str]:
    try:
        resp = input(prompt)
        if checker is None:
            return resp
        else:
            if checker(resp):
                return resp
            else:
                print(f"Invalid input ({fail_check_msg})...")
                return ez_prompt(prompt, checker, fail_check_msg)
    except KeyboardInterrupt:
        if raise_on_ctrl_c:
            raise
        else:
            return None


def int_prompt(maximum: int, prompt: str = '> ',
               minimum: int = 1) -> Optional[int]:
    retry = False
    valid_str = f'Number must be between {minimum} and {maximum}...'
    while True:
        p = f'{"(invalid input) " if retry else ""}{prompt}'
        resp = ez_prompt(p)
        if resp is None:
            return None
        try:
            int_resp = int(resp)
        except ValueError:
            retry = True
        else:
            if int_resp < minimum or int_resp > maximum:
                print(valid_str)
                continue

            return int_resp


def opt_prompt(opts: List[str],
               prompt: str = '> ',
               pre_string: str = ''
               ) -> Optional[int]:
    for (i, opt) in enumerate(opts):
        print(f'{pre_string}{i + 1}. {opt}')

    return int_prompt(len(opts), prompt=prompt)


def table_prompt(rows: List[list],
                 header: List[str],
                 prompt: Optional[str] = None) -> Optional[int]:
    header.insert(0, '#')
    for i, row in enumerate(rows):
        row.insert(0, str(i + 1))

    print(tabulate.tabulate(rows, header))
    print('')
    if prompt:
        print(prompt)

    return int_prompt(len(rows))


def yn_prompt(pre_text: str = None) -> Optional[bool]:
    retry = False
    while True:
        prompt = f'{pre_text} {"(invalid input) " if retry else ""}[y/n]: '
        resp = ez_prompt(prompt)
        if resp is None:
            return None
        else:
            resp = resp.lower()

        if resp == 'y':
            return True
        elif resp == 'n':
            return False
        else:
            retry = True
