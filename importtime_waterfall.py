from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from dataclasses import field
from typing import Sequence

IMPORT_TIME = 'import time:'


@dataclass(frozen=True)
class Import:
    name: str
    self_time: int
    children: list[Import]
    _cumulative_time: int | None = field(default=None, init=False, repr=False)

    @property
    def cumulative_time(self) -> int:
        # TODO: use functools.cached_property after dropping Python 3.7
        if self._cumulative_time is not None:
            return self._cumulative_time
        rv = self.self_time + sum(c.cumulative_time for c in self.children)
        object.__setattr__(self, '_cumulative_time', rv)
        return rv


def graph(root: Import, max_depth: int, hide_under: int) -> int:
    def children(x: Import) -> list[Import]:
        return sorted(
            x.children,
            key=lambda x: x.cumulative_time,
            reverse=True,
        )

    def pp(x: Import, depth: int = 0) -> None:
        if max_depth and depth >= max_depth:
            return
        if hide_under and x.cumulative_time < hide_under:
            return

        if x.cumulative_time != x.self_time:
            times_str = f'{x.cumulative_time}, {x.self_time}'
        else:
            times_str = f'{x.self_time}'
        print(f'{"  " * depth}{x.name} ({times_str})')

        for imp in children(x):
            pp(imp, depth=depth + 1)

    for imp in children(root):
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
    def run() -> tuple[float, subprocess.CompletedProcess[str]]:
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('module')
    parser.add_argument('--include-interpreter-startup', action='store_true')
    parser.add_argument('--max-depth', type=int, default=0)
    parser.add_argument('--hide-under', type=int, default=0)

    mut = parser.add_mutually_exclusive_group()
    mut.add_argument('--graph', dest='fmt', action='store_const', const=None)
    mut.add_argument('--har', dest='fmt', action='store_const', const='har')
    args = parser.parse_args()

    res = best_of(args.module)

    root = Import(name='root', self_time=0, children=[])
    import_stack = [root]

    for line in reversed(res.stderr.splitlines()):
        if line.startswith(IMPORT_TIME):
            line = line[len(IMPORT_TIME):]
            self_time_s, _, name_s = line.split('|')
            try:
                self_time = int(self_time_s)
            except ValueError:  # headers
                continue

            name = name_s.lstrip()
            imp = Import(name=name, self_time=self_time, children=[])

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
        return graph(root, args.max_depth, args.hide_under)


if __name__ == '__main__':
    raise SystemExit(main())
