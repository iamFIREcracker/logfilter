#!/usr/bin/env python

""" Module handling compatibility between python 2 and python 3
"""

import sys

# True if we are running on Python 3.
PY3 = sys.version_info[0] == 3


if PY3:
    import tkinter
    import tkinter.filedialog as filedialog
else:
    import Tkinter as tkinter
    import tkFileDialog as filedialog


if PY3:
    import queue
else:
    import Queue as queue


if PY3:
    filter = filter
else:
    from itertools import ifilter as filter


if PY3:
    range = range
else:
    range = xrange


if PY3:
    func_get_name = lambda f: f.__name__
else:
    func_get_name = lambda f: f.func_name
