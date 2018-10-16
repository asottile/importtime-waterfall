import argparse
import datetime
import json
import subprocess
import sys
import time
from typing import Any
from typing import NamedTuple
from typing import Optional
from typing import Sequence
from typing import Tuple

IMPORT_TIME = 'import time:'


class Import(NamedTuple):
    name: str
    self_time: int
    children: Any  # List['Import']  # python/mypy#731


def graph(root: Import) -> int:
    def pp(x: Import, depth: int = 0) -> None:
        print(f'{"  " * depth}{x.name} ({x.self_time})')
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


def best_of(mod: str, *, n: int = 5) -> subprocess.CompletedProcess:
    def run() -> Tuple[float, subprocess.CompletedProcess]:
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
        return graph(root)


if __name__ == '__main__':
    exit(main())
