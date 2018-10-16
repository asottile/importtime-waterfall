[![Build Status](https://travis-ci.org/asottile/importtime-waterfall.svg?branch=master)](https://travis-ci.org/asottile/importtime-waterfall)

importtime-waterfall
====================

Generate waterfalls from `-Ximporttime` tracing.

## install

`pip install importtime-waterfall`

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

(this is the default display).  Display the output as a tree.  This doesn't
really add much on top of what `python -Ximporttime` already displays (but was
useful for developing / debugging this tool).  I guess it's in human order
instead of reversed so that's something 🤷.

Times displayed next to the module names are self-times in μs.

```console
$ importtime-waterfall importtime_waterfall
importtime_waterfall (419)
  argparse (864)
    re (599)
      enum (661)
      sre_compile (270)
        _sre (109)
        sre_parse (336)
          sre_constants (339)
      copyreg (161)
    gettext (1056)
      locale (820)
  datetime (768)
    time (234)
    math (57)
    _datetime (154)
  json (254)
    json.decoder (446)
      json.scanner (481)
        _json (193)
    json.encoder (443)
  subprocess (628)
    signal (1030)
    errno (101)
    _posixsubprocess (40)
    select (51)
    selectors (543)
      collections.abc (184)
    threading (578)
      traceback (394)
        linecache (162)
          tokenize (911)
            token (178)
      _weakrefset (217)
  typing (1469)
```

## success stories

I used this to find a [24% speedup in `flake8`'s startup][flake8-speedup].

## nitty-gritty how it works

`importtime-waterfall` imports the profiled module in a subprocess while
setting the [`-Ximporttime`][x-importtime] flag.  `importtime-waterfall` takes
picks the best-of-5 (by total time) and uses that result.  It parses the
"import time:" lines and then outputs.

[har-spec]: http://www.softwareishard.com/blog/har-12-spec/
[har-viewer]: http://www.softwareishard.com/har/viewer/
[xclip]: https://github.com/astrand/xclip
[flake8-speedup]: https://gitlab.com/pycqa/flake8/merge_requests/250
[x-importtime]: https://docs.python.org/3/using/cmdline.html#envvar-PYTHONPROFILEIMPORTTIME
