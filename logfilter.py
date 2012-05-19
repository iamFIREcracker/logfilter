#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import time
from itertools import ifilter
from argparse import ArgumentParser



def tail_f(filename, timeout=1.0):
    """
    Emulate the behaviour of `tail -f`.

    Keep reading from the end of the file, and yeald lines as soon as they are
    added to the file.

    @param filename name of the file to observe
    @param timeout timeout interval to wait before checking for new content
    """
    with open(filename) as f:
        while True:
            where = f.tell()
            line = f.readline()
            if not line:
                time.sleep(timeout)
                f.seek(where)
            else:
                yield line


def regexp_filter(*exps):
    """
    Create a reg exp filter function to be passed to built-in `ifilter` func.

    @param *exps list of regular expressions representing filter criteria.
    """
    regexps = map(re.compile, exps)

    def wrapper(line):
        """
        Return True if the input string matches one of the outer level criteria.

        @param gen string to be tested with the outer level criteria.
        """
        return any(map(lambda r: r.match(line), regexps))

    return wrapper


def _build_parser():
    """
    Return a command-line arguments parser.
    """
    parser = ArgumentParser(description='Filter the content of a file, dynamically')

    parser.add_argument(
            '-f', '--filename', dest='filename', required=True,
            help='Filename to filter.', metavar='FILENAME')
    parser.add_argument(
            '-i', '--interval', dest='interval', required=True, type=float,
            help='Timeout interval to wait before checking for updates',
            metavar='INTERVAL')
    parser.add_argument(
            dest='filters', nargs='+',
            help='Filters to apply to the file content', metavar="FILTER")

    return parser


def _main():
    parser = _build_parser()
    args = parser.parse_args()

    tail_f_gen = tail_f(args.filename, args.interval)
    for line in ifilter(regexp_filter(*args.filters), tail_f_gen):
        print line,



if __name__ == '__main__':
    _main();
