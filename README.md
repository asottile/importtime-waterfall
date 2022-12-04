[![Build Status](https://dev.azure.com/asottile/asottile/_apis/build/status/asottile.importtime-waterfall?branchName=main)](https://dev.azure.com/asottile/asottile/_build/latest?definitionId=44&branchName=main)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/asottile/importtime-waterfall/main.svg)](https://results.pre-commit.ci/latest/github/asottile/importtime-waterfall/main)

importtime-waterfall
====================

Generate waterfalls from `-Ximporttime` tracing.

## install

```bash
pip install importtime-waterfall
```

_note_: `importtime-waterfall` requires python3.7+

## usage

`importtime-waterfall` provides a single executable by the same name.

`importtime-waterfall` takes a module name as a positional argument.  This is
the module that will be profiled.

### `--include-interpreter-startup`

Include tracing information of modules that are always imported as part of
interpreter startup.  These are usually not interesting and so they are left
out by default.

### `--har`

Output as an [HTTP Archive][har-spec] or "HAR" file.  Yes these aren't actual
HTTP requests but it's an easy way to get a visualization using a standardized
data format.

HAR unfortunaly doesn't have microsecond resolution so all times in the HAR
output are * 1000 (1 μs => 1ms).

The easiest way to use the output of this is to paste it into a
[har viewer][har-viewer].

I use the following:

```console
$ importtime-waterfall importtime_waterfall --har | xclip -selection c
```

[xclip][xclip] takes the output and puts it onto the clipboard.
Alternatively, you can redirect to a file (`> foo.har`) and upload it that way.

Once pasted into the viewer you can inspect the output.

The blocked import time is represented as "waiting" (purple) and the self time
is represented as "receiving" (grey).  Generally when looking for slow modules
look for ones with large grey chunks.

![](/img/waterfall.png)

### `--graph`

(this is the default display).  Display the output as a tree.  This cleans up
the output of `python -Ximporttime` a bit: it is top-down instead of bottom-up,
and the imports of a module are sorted by cumulative time.

Times displayed next to the module names are cumulative and self time, in μs;
if they are equal, only one is shown.

```console
$ importtime-waterfall importtime_waterfall
importtime_waterfall (39642, 1293)
  argparse (17987, 1140)
    re (8292, 741)
      functools (3830, 743)
        collections (3029, 1000)
          heapq (661, 273)
            _heapq (388)
          operator (596, 503)
            _operator (93)
          reprlib (320)
          keyword (239)
          itertools (127)
          _collections (86)
        _functools (58)
      sre_compile (2127, 1109)
        sre_parse (931, 499)
          sre_constants (432)
        _sre (87)
      enum (1310, 927)
        types (383)
      copyreg (284)
    shutil (5821, 806)
      bz2 (2954, 480)
        threading (1091, 759)
          _weakrefset (332)
        warnings (576)
        _bz2 (428)
        _compression (379)
      lzma (866, 396)
        _lzma (470)
      zlib (417)
      grp (366)
      fnmatch (269)
      errno (87)
      pwd (56)
    gettext (2734, 1476)
      locale (1258)
  dataclasses (7687, 939)
    inspect (5709, 1939)
      linecache (1807, 246)
        tokenize (1561, 1274)
          token (287)
      dis (1333, 593)
        opcode (740, 414)
          _opcode (326)
      importlib.machinery (630, 330)
        importlib (300)
    copy (1039, 325)
      weakref (516)
      org.python.core (198, 19)
        org.python (179, 20)
          org (159)
  subprocess (4462, 673)
    signal (1068)
    selectors (1009, 711)
      collections.abc (298)
    contextlib (699)
    select (437)
    _posixsubprocess (411)
    msvcrt (165)
  typing (2964)
  json (2816, 365)
    json.decoder (1660, 648)
      json.scanner (1012, 598)
        _json (414)
    json.encoder (791)
  datetime (2157, 965)
    math (679)
    _datetime (513)
  __future__ (276)
```

### `--max-depth` and `--hide-under`

These options add filtering to `--graph`.
They are useful for getting a nice text summary.

`--max-depth` limits the depth of the tree:

```
$ importtime-waterfall importtime_waterfall --max-depth 2
importtime_waterfall (39407, 1273)
  argparse (17851, 1124)
  dataclasses (7734, 919)
  subprocess (4469, 647)
  typing (2945)
  json (2713, 374)
  datetime (2151, 955)
  __future__ (271)
```

`--hide-under` hides modules with cumulative time under a certain value:

```
$ importtime-waterfall importtime_waterfall --max-depth 2 --hide-under 3000
importtime_waterfall (39136, 1260)
  argparse (17807, 1135)
  dataclasses (7675, 920)
  subprocess (4349, 630)
```

## success stories

I used this to find a [24% speedup in `flake8`'s startup][flake8-speedup].

## nitty-gritty how it works

`importtime-waterfall` imports the profiled module in a subprocess while
setting the [`-Ximporttime`][x-importtime] flag.  `importtime-waterfall`
picks the best-of-5 (by total time) and uses that result.  It parses the
"import time:" lines and then outputs.

[har-spec]: http://www.softwareishard.com/blog/har-12-spec/
[har-viewer]: http://www.softwareishard.com/har/viewer/
[xclip]: https://github.com/astrand/xclip
[flake8-speedup]: https://gitlab.com/pycqa/flake8/merge_requests/250
[x-importtime]: https://docs.python.org/3/using/cmdline.html#envvar-PYTHONPROFILEIMPORTTIME
