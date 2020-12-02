from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
import time
from typing import Any
from typing import NamedTuple
from typing import Optional
from typing import Sequence
from typing import Tuple

from colorama import Back
from colorama import Style

IMPORT_TIME = 'import time:'

terminal_width: Optional[int]
try:
    terminal_width = os.get_terminal_size().columns
except OSError:
    terminal_width = None


class Import(NamedTuple):
    name: str
    self_time: int
    cumulative_time: int
    children: Any  # List['Import']  # python/mypy#731


def get_max_time(x: Import, cumulative: bool) -> int:
    return max(
        [x.cumulative_time if cumulative else x.self_time] +
        [get_max_time(child, cumulative) for child in x.children],
    )


def graph(root: Import, cumulative: bool) -> int:
    max_self_time = get_max_time(root, cumulative)

    def pp(x: Import, depth: int = 0) -> None:
        time = x.cumulative_time if cumulative else x.self_time

        output = f'{"  " * depth}{x.name} ({time})'
        if terminal_width is not None:
            output = output.ljust(terminal_width, ' ')
            num_red_chars = int(time / max_self_time * terminal_width)
            left, right = output[:num_red_chars], output[num_red_chars:]
            print(f'{Back.RED}{left}{Style.RESET_ALL}{right}')
        else:
            print(output)
        for imp in x.children:
            pp(imp, depth=depth + 1)

    for imp in root.children:
        pp(imp)
    return 0


def har(root: Import) -> int:
    dt = datetime.datetime(1991, 7, 5)
    har_out = {
        'log': {
            'version': '1.2',
            'creator': {'name': 'python', 'version': sys.version},
            'browser': {'name': 'python', 'version': sys.version},
            'pages': [{
                'startedDateTime': dt.isoformat(timespec='milliseconds') + 'Z',
                'id': 'page0',
                'title': f'`import {root.children[-1].name}` {sys.version}',
                'pageTimings': {'onContentLoad': -1, 'onLoad': -1},
            }],
            'entries': [],
        },
    }

    def visit(x: Import) -> None:
        nonlocal dt

        start = dt

        dt += datetime.timedelta(milliseconds=1)

        for imp in x.children:
            visit(imp)

        dt += datetime.timedelta(milliseconds=x.self_time - 1)

        diff = dt - start
        time = diff.seconds * 1000 + diff.microseconds // 1000
        assert isinstance(har_out['log']['entries'], list)  # trust me mypy
        har_out['log']['entries'].append({
            'page_ref': 'page0',
            'startedDateTime': start.isoformat(timespec='milliseconds') + 'Z',
            'time': time,
            'request': {
                'method': 'GET',
                'url': x.name,
                'httpVersion': 'HTTP/0.0',
                'cookies': [],
                'headers': [],
                'queryString': [],
                'headersSize': 0,
                'bodySize': 0,
            },
            'response': {
                'status': 200,
                'statusText': 'OK',
                'httpVersion': 'HTTP/0.0',
                'cookies': [],
                'headers': [],
                'content': {'size': 0, 'mimeType': 'text/x-python'},
                'redirectURL': '',
                'headersSize': 0,
                'bodySize': 0,
            },
            'cache': {},
            'timings': {
                'blocked': 0,
                'dns': 0,
                'connect': 0,
                'ssl': 0,
                'send': 0,
                'wait': time - x.self_time,
                'receive': x.self_time,
            },
            'serverIpAddress': '0.0.0.0',
        })

    for imp in root.children:
        visit(imp)

    print(json.dumps(har_out, separators=(',', ':')))
    return 0


def best_of(mod: str, *, n: int = 5) -> subprocess.CompletedProcess[str]:
    def run() -> Tuple[float, subprocess.CompletedProcess[str]]:
        before = time.time()
        ret = subprocess.run(
            (sys.executable, '-Ximporttime', '-c', f'import {mod}'),
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            encoding='UTF-8',
        )
        return time.time() - before, ret

    best_time, best = run()
    for _ in range(n):
        candidate_time, candidate = run()
        if candidate_time < best_time:
            best_time, best = candidate_time, candidate
    return best


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('module')
    parser.add_argument('--include-interpreter-startup', action='store_true')

    mut = parser.add_mutually_exclusive_group()
    mut.add_argument('--graph', dest='fmt', action='store_const', const=None)
    mut.add_argument('--har', dest='fmt', action='store_const', const='har')
    mut.add_argument(
        '--cumulative',
        dest='cumulative',
        action='store_const',
        const=True,
        default=False,
    )
    args = parser.parse_args()

    res = best_of(args.module)

    root = Import(name='root', self_time=0, cumulative_time=0, children=[])
    import_stack = [root]

    for line in reversed(res.stderr.splitlines()):
        if line.startswith(IMPORT_TIME):
            line = line[len(IMPORT_TIME):]
            self_time_s, cumulative_time_s, name_s = line.split('|')
            try:
                self_time = int(self_time_s)
                cumulative_time = int(cumulative_time_s)
            except ValueError:  # headers
                continue

            name = name_s.lstrip()
            imp = Import(
                name=name,
                self_time=self_time,
                cumulative_time=cumulative_time, children=[],
            )

            depth = (len(name_s) - len(name) - 1) / 2 + 1
            while len(import_stack) > depth:
                import_stack.pop()
            import_stack[-1].children.insert(0, imp)
            import_stack.append(imp)

    root.children[:] = [
        imp for imp in root.children
        if imp.name == args.module or args.include_interpreter_startup
    ]

    if args.fmt == 'har':
        return har(root)
    else:
        return graph(root, cumulative=args.cumulative)


if __name__ == '__main__':
    exit(main())
