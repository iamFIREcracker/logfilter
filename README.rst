=========
logfilter
=========

**logfilter** is a python application handy for real-time processing of very long
log files.

Take the command ``tail -f``, combine it with ``grep -e PATTER [-e PATTERN
...]``, and add a simple GUI enabling users to choose the the log file to
observe and the filters to use:  well, that is the essence of **logfilter** (or
as other would say, **logfilter** in a nutshell).


Dependencies
============

- Python 2.7
- Tkinter support.


Install
=======

**logfilter** can be installed using either the Bitbucket mercurial repository,
or the Python Package Index (PyPI).  If you feel lucky and you don't mind using
a possibly unstable application in order to benefit of the latest project
features, then choose the former.  On the other hand, if you don't want to spend
time filing bug reports due to crashing applications, then the latter would be
definitely the better option (.. I hope).

Mercurial
---------

From sources::

    cd /wherever/you/want
    hg clone https://bitbucket.org/iamFIREcracker/logfilter
    python setup.py install


PyPI
----

From sources::

    cd /path/to/workspace
    wget http://pypi.python.org/packages/source/o/logfilter/logfilter-0.1.0.tar.gz
    tar zxvf logfilter-0.1.0.tar.gz
    cd logfilter-0.1.0
    python setup.py install

From the PyPI::

    pip install logfilter


Usage
=====

To give you an overview of configuration options of **logfilter**, this is the
output of ``python logfiter.py -h``::

    usage: logfilter.py [-h] [-s SLEEP_INTERVAL] [-f NUM_FILTERS] [-l LIMIT]
                        [-e FILTERS]
                        [FILENAME]

    Filter the content of a file, dynamically

    positional arguments:
    FILENAME              Filename to filter.

    optional arguments:
    -h, --help            show this help message and exit
    -s SLEEP_INTERVAL, --sleep-interval SLEEP_INTERVAL
                            Sleep SLEEP_INTERVAL seconds between iterations
    -f NUM_FILTERS, --num-filters NUM_FILTERS
                            Number of filters to apply to log file
    -l LIMIT, --limit LIMIT
                            Number of lines to display in the text area
    -e FILTERS, --regexp FILTERS
                            Filter presets

Don't be scared, you don't need to configure them all to start the application;
the GUI indeed, will let you customize them later.  However, consider to use
command line options to create handy aliases or shortcuts.

For example, imagine you are about to work with log files containing among the
other things, Java stack traces.  You could think about launching the
application with the following options, in order to get notified as soon as
a new exception (and relative stack trace) is added to the observed file::

    python logfilter.py -e '([Ee]xception|\tat)' LOGFILE.log

Moreover, imagine you working on a new module being part of bigger project (all
the log traces coming from such a module, have a special `FOO` keyword
associated); then, to follow the live behaviour of the module while still
observing exceptional events coming from the rest of the application, you could
launch the logfilter with the following options::

    python logfilter.py -e '([Ee]xception|\tat)' -e FOO LOGFILE.log
