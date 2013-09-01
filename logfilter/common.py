#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
from collections import namedtuple

from ._compact import func_get_name
from ._compact import tkinter


def _var(ctor, default, callback=None):
    """
    Creates a Tkinter variable, initialize it and possibly trace it.

    @param default the variable initial value
    @param callback function to invoke whenever the variable changes its value
    @return the created variable
    """
    var = ctor()
    var.set(default)
    if callback:
        var.trace('w', callback)
    return var


def StringVar(default, callback=None):
    """
    Return a new (initialized) `tkinter.StringVar.

    @param default the variable initial value
    @param callback function to invoke whenever the variable changes its value
    @return the created variable
    """
    return _var(tkinter.StringVar, default, callback)


def BooleanVar(default, callback=None):
    """
    Return a new (initialized) `tkinter.BooleanVar`.

    @param default the variable initial value
    @param callback function to invoke whenever the variable changes its value
    @return the created variable
    """
    return _var(tkinter.BooleanVar, default, callback)


def debug(func):
    """
    Decorator which prints a message before and after a function execution.
    """
    now = datetime.datetime.now

    def wrapper(*args, **kwargs):
        print('{now}: {fname}: entering'.format(
            now=now(), fname=func_get_name(func)))
        func(*args, **kwargs)
        print('{now}: {fname}: exiting...'.format(
            now=now(), fname=func_get_name(func)))
    return wrapper


"""Tag object used by the `Text` widget to hanndle string coloring."""
Tag = namedtuple('Tag', 'name pattern settings'.split())
