**logfilter** is a python application handy for real-time processing of very
long log files.

Take the command ``tail -f``, combine it with ``grep -e PATTER [-e PATTERN
...]``, and add a simple GUI enabling users to choose the log file to monitor
and the filters to use:  well, that is the essence of **logfilter** (or as other
would say, **logfilter** in a nutshell).


Dependencies
============

- Python with Tkinter support


Install
=======

**logfilter** can be installed using either the Bitbucket mercurial repository,
or the Python Package Index (PyPI).  If you feel lucky and you don't mind using
a possibly unstable application in order to benefit of the latest project
features, then choose the former.  On the other hand, if you don't want to spend
time filing bug reports due to crashing applications, then the latter would be
definitely the better option (... I hope).

From sources::

    cd /wherever/you/want
    hg clone https://bitbucket.org/iamFIREcracker/logfilter
    python setup.py install


From the PyPI::

    pip install logfilter


Usage
=====

To give you an idea of the configuration options available for **logfilter**,
this is the help of the application::


    usage: logfilter [-h] [-s SLEEP_INTERVAL] [-l LIMIT] [-e FILTERS]
                    [--font FONT] [--version]
                    [FILENAME]

    Filter the content of a file, dynamically

    positional arguments:
    FILENAME              Filename to filter.

    optional arguments:
    -h, --help            show this help message and exit
    -s SLEEP_INTERVAL, --sleep-interval SLEEP_INTERVAL
                            Sleep SLEEP_INTERVAL seconds between iterations
    -l LIMIT, --limit LIMIT
                            Number of lines to display in the text area
    -e FILTERS, --regexp FILTERS
                            Filter presets
    --font FONT           Font used by the application
    --version             print the application version and quit

Don't be scared, you don't need to configure all of them to start the
application;  the GUI indeed, will let you customize them later.  However,
consider to use command line options to create handy aliases or shortcuts.

For example, imagine you are about to work with log files containing among the
other things, Java stack traces.  You could think about launching the
application with the following options, in order to get notified as soon as
a new exception (and relative stack trace) is added to the observed file::

    python logfilter.py -e '([Ee]xception|\tat)' LOGFILE.log

Moreover, imagine you working on a new module being part of bigger project (all
the log traces coming from such a module, have a special ``FOO`` keyword
associated); then, to follow the live behavior of the module while still
observing exceptional events coming from the rest of the application, you could
start **logfilter** with the following options::

    python logfilter.py -e '([Ee]xception|\tat)' -e FOO LOGFILE.log


Edit files
----------

Since version *0.6.0dev*, it is possible to configure **logfilter** to open the
monitored file with an external editor.

The application will look for *special* environment variables (i.e.
``LFEDITOR`` first, then ``VISUAL`` and finally ``EDITOR``) containing
information regarding the external application to launch to edit the file at the
line of interest.

For example, to make ``gvim`` your external editor, run ``logfilter`` as
follows::

    LFEDITOR="gvim FILE +ROW" logfilter LOGFILE.log -e FOO

Otherwise, if you are on Windows and prefer to use ``TextPad``::

    set LFEDITOR="C:\Programs\TextPad 4\TextPad.exe" FILE(ROW,0)& logfilter

The ``FILE`` and ``ROW`` markers will be automatically replaced by **logfilter**
with the name of the monitored file and with the current selected line
respectively.


Changelog
=========

0.8.0dev:

- ISSUE-31: it is now possible to add or remove filters dynamically at run-time
  (i.e. a new filter can be added focusing the text box containing the text
  ``<Add new>``, while old ones can be removed by blanking their text box).
  Contenxtually with this change, the command line switches `-f` and
  `--num-filters` have been removed.
- ISSUE-29: add popup entry to enable/disable passthru behaviour (i.e. display
  all the lines and highlight only those bits matching filters).  Contextually,
  the command line switches `-a` and `--catch-all` have been removed.
- The application does not quit anymore if the `Escape` key is pressed.
- Add `--version` command line switch.

0.7.0dev (2012-12-08):

- ISSUE-24: fix a bug where the selected text of the current line was not
  highlighted properly
- ISSUE-27: add `--font` command line option to configure the font
- ISSUE-28: fix a bug where multiple line end up being selected when a new line
  was rendered in the text widget
- ISSUE-25: fix PY3K compatibility (there was a problem with local imports)

0.6.0dev (2012-12-01):

- ISSUE-23: add popup menu entry to disable *raise on output*
- ISSUE-19: add popup menu entry to enable line greedy coloring (multiple
  matches for the same filter in the same line)
- ISSUE-21: add support for opening the current file in a configured external
  editor

0.5.0dev (2012-10-17):

- ISSUE-18: add a catch-all filter (enabled with ``-a`` or ``--catch-all``)
  which force the application to output all the lines of the file.  Moreover,
  the lines matching filters expressions, will be highlighted as well
- ISSUE-15: remember last user directory while opening the file chooser dialog
  multiple times
- ISSUE-16: add a popup menu entry which disable the *scroll on output* behavior

0.4.0dev (2012-09-22):

- Fix a bug where matched strings were not colored when the number of filters
  was greater than the size of the color palette
- Install the application as a gui script (on Windows, do not open
  a ``cmd.exe``)

0.3.1dev (2012-08-10):

- Add right-click menu with an entry to clear the text widget (issue #10)
- Better window focus management on new content read from the file (issue #12)
- Add configuration setting to enable infinite scroll (issue #11)

0.2.1dev (2012-07-07):

- Add python 3.2 compatibility

0.1.2dev (2012-06-27):

- Better packaging (create a console script to run logfilter)

0.1.1 (2012-06-25):

- Add MANIFEST.in file (issue #9)

0.1.0 (2012-06-02):

- First public release
