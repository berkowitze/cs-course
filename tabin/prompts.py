import sys

from typing import Callable, Iterable, List, Optional, Set, Union

import tabulate

from datetime import datetime
from helpers import red


def ez_prompt(prompt: str,
              checker: Optional[Callable[[str], bool]] = None,
              fail_check_msg: Optional[str] = None,
              raise_on_ctrl_c: bool = False,
              exit_on_ctrl_c: bool = False) -> Optional[str]:
    assert not (raise_on_ctrl_c and exit_on_ctrl_c), \
        'cannot raise and exit on ctrl-c'
    try:
        resp = input(prompt)
    except KeyboardInterrupt:
        if raise_on_ctrl_c:
            raise
        elif exit_on_ctrl_c:
            print('\nExiting...')
            sys.exit(1)
        else:
            return None
    else:  # executed if resp = input(prompt) succeeds
        if checker is None:
            return resp
        else:
            if checker(resp):
                return resp
            else:
                print(f"Invalid input ({fail_check_msg})...")
                return ez_prompt(prompt, checker, fail_check_msg,
                                 raise_on_ctrl_c, exit_on_ctrl_c)


def int_prompt(maximum: int, prompt: str = '> ',
               minimum: int = 1, **kwargs) -> Optional[int]:
    retry = False
    valid_str = f'Number must be between {minimum} and {maximum}...'
    while True:
        p = f'{"(invalid input) " if retry else ""}{prompt}'
        resp = ez_prompt(p, **kwargs)
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
               pre_string: str = '',
               **kwargs) -> Optional[int]:
    for (i, opt) in enumerate(opts):
        print(f'{pre_string}{i + 1}. {opt}')

    return int_prompt(len(opts), prompt=prompt, **kwargs)


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


def yn_prompt(pre_text: str = None, **kwargs) -> Optional[bool]:
    retry = False
    while True:
        if pre_text is None:
            prompt = f'{"(invalud input) " if retry else ""}[y/n]: '
        else:
            prompt = f'{pre_text} {"(invalid input) " if retry else ""}[y/n]: '

        resp = ez_prompt(prompt, **kwargs)
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


def toggle_prompt(options: List[str],
                  toggled: Optional[Union[List[str], Set[str]]] = None,
                  **kwargs
                  ) -> Optional[Set[str]]:
    UP = "\033[F"
    if toggled is None:
        toggled = set()
    else:
        toggled = set(toggled)

    doit = True
    while True:  # eli having fun oops
        opts = [red(f) if f in toggled else f for f in options]
        for i, f in enumerate(options):
            if f in toggled:
                print(f'{i + 1}. {red(f)}')
            else:
                print(f'{i + 1}. {f}')

        row_resp = ez_prompt('> \033[K', **kwargs)
        if row_resp is None:
            doit = False
            break
        if not row_resp:
            break
        try:
            file_row = int(row_resp)
            f = options[file_row - 1]
        except (ValueError, IndexError):
            print(f'  Invalid input (must be # between 1 '
                  f'and {len(options)})')
        else:
            invalid = False
            if f in toggled:
                toggled.remove(f)
            else:
                toggled.add(f)
            print('\033[F' * (len(options) + 2))

    if not doit:
        return None
    else:
        return toggled


def date_prompt(readable_format: str = 'mm/dd/yyyy hh:mm [a/p]m',
                datetime_format: str = '%m/%d/%Y %I:%M %p',
                default: Optional[datetime] = None,
                after: Optional[datetime] = None,
                after_msg: Optional[str] = None,
                enforce_after: bool = False,
                **kwargs) -> Optional[datetime]:
    while True:
        inp = ez_prompt(f'[{readable_format}] > ', **kwargs)
        if inp is None:
            return None
        if not inp and default is not None:
            # user entered blank and there is a defualt value
            return default
        try:
            date = datetime.strptime(inp, '%m/%d/%Y %I:%M %p')
        except ValueError:
            print('Invalid date.')
        else:
            if after is None:
                return date
            elif date < after:
                if after_msg is None:
                    print('Invalid date.')
                else:
                    print(after_msg)

                if not enforce_after:
                    print('Continue anyway?')
                    if yn_prompt(**kwargs):
                        return date
                else:
                    continue
            else:
                return date

