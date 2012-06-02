#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import re
import time
import threading
import tkFileDialog
import Tkinter
import Queue
from argparse import ArgumentParser
from collections import deque
from collections import namedtuple
from functools import partial
from itertools import ifilter
from itertools import takewhile
from operator import methodcaller
from operator import ne



"""Number of lines to collect before telling the gui to refresh."""
_BATCH_LIMIT = 100

"""Default event listener."""
_NULL_LISTENER = lambda *a, **kw: None

"""Gui polling job interval"""
_POLL_INTERVAL = 66

"""Stop message used to stop threads."""
_STOP_MESSAGE = None

"""Tag color palette."""
_TAG_PALETTE = (
        ('red', '#E52222'),
        ('green', '#A6E32D'),
        ('yellow', '#FD951E'),
        ('blue', '#C48DFF'),
        ('magenta', '#FA2573'),
        ('cyan', '#67D9F0')
    )

"""Application title template"""
_TITLE = 'logfilter: {filename}'


"""Number of string filters."""
NUM_FILTERS = 1

"""Number of lines to display on screen."""
LINES_LIMIT = 8000

"""Default sleep interval"""
SLEEP_INTERVAL = 1.0



def debug(func):
    """
    Decorator which prints a message before and after a function execution.
    """
    NOW = lambda: datetime.datetime.now()

    def wrapper(*args, **kwargs):
        print '{now}: {fname}: entering'.format(now=NOW(), fname=func.func_name)
        func(*args, **kwargs)
        print '{now}: {fname}: exiting...'.format(now=NOW(), fname=func.func_name)
    return wrapper


def StringVar(default):
    """
    Return a new (initialized) `Tkinter.StringVar.

    @param default default string value
    """
    s = Tkinter.StringVar()
    s.set(default)
    return s



"""Tag object used by the `Text` widget to hanndle string coloring."""
Tag = namedtuple('Tag', 'name pattern settings'.split())


class Gui(Tkinter.Tk):

    def __init__(self, parent, **kwargs):
        Tkinter.Tk.__init__(self, parent) #super(Tkinter.Tk, self).__init__(parent)

        self._schedule_queue = Queue.Queue()

        self.on_quit_listener = (_NULL_LISTENER, (), {})
        self.on_new_filter_listener = (_NULL_LISTENER, (), {})

        self._initialize(**kwargs)

        self._update()

    def _initialize(self, filename, filters, scroll_limit):
        """
        Initialize the layout of the GUI
        """
        self.grid()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.protocol('WM_DELETE_WINDOW', self.on_close)
        self.bind('<Escape>', self.on_quit)

        # Container 0
        self.file_chooser = FileChooser(self, filename=filename)
        self.file_chooser.grid(row=0, column=0, sticky='EW')
        self.file_chooser.register_listener('press_enter', self.on_press_enter)

        # Container1
        container1 = Tkinter.Frame(self)
        container1.grid(row=1, column=0, sticky='EW')
        for i in xrange(len(filters)):
            container1.grid_columnconfigure(i, weight=1)

        self.filter_strings = [StringVar(f) for f in filters]
        entries = [Tkinter.Entry(container1, textvariable=filter_string)
                    for filter_string in self.filter_strings]
        for (i, entry) in enumerate(entries):
            entry.focus_force()
            entry.grid(row=0, column=i, sticky='EW')
            entry.bind("<Return>", self.on_press_enter_event)

        # Container2
        self.text = Text(self, bg='#222', fg='#eee', wrap=Tkinter.NONE)
        self.text.grid(row=2, column=0, sticky='NSEW')
        self.text.configure_scroll_limit(scroll_limit)

    def _update(self):
        """
        Poll the schedule queue for new actions.
        """
        for i in xrange(10):
            try:
                (func, args, kwargs) =  self._schedule_queue.get(False)
                #print 'schedule_queue', self._schedule_queue.qsize()
            except Queue.Empty:
                break

            self.after_idle(func, *args, **kwargs)
        self.after(_POLL_INTERVAL, self._update)

    @debug
    def on_close(self):
        (func, args, kwargs) = self.on_quit_listener
        func(*args, **kwargs)
        self.quit()

    @debug
    def on_quit(self, event):
        self.on_close()

    @debug
    def on_press_enter(self):
        filename = self.file_chooser.get_filename()
        self.title(_TITLE.format(filename=filename))
        filter_strings = map(lambda s: s.get(), self.filter_strings)
        self.text.configure_tags(
                Tag(n, f, {'foreground': c})
                    for ((n, c), f) in zip(_TAG_PALETTE, filter_strings))
        (func, args, kwargs) = self.on_new_filter_listener
        args = [filename, filter_strings] + list(args)
        func(*args, **kwargs)

    @debug
    def on_press_enter_event(self, event):
        self.on_press_enter()

    def raise_(self):
        """
        Raise the window on the top of windows stack.
        """
        self.attributes('-topmost', True)
        self.attributes('-topmost', False)

    def register_listener(self, event, func, *args, **kwargs):
        """
        Register a listener for the specified named event.

        @param func function to schedule
        @param args positional arguments for the fuction
        @param kwargs named arguments for the function
        """
        if event not in ['quit', 'new_filter']:
            raise ValueError("Invalid event name: " + event)

        if event == 'quit':
            self.on_quit_listener = (func, args, kwargs)
        elif event == 'new_filter':
            self.on_new_filter_listener = (func, args, kwargs)

    def schedule(self, func, *args, **kwargs):
        """
        Ask the event loop to schedule given function with arguments

        @param func function to schedule
        @param args positional arguments for the fuction
        @param kwargs named arguments for the function
        """
        self._schedule_queue.put((func, args, kwargs))

    def clear_text(self):
        """
        Delete all the text contained in the text area.
        """
        self.text.clear()
        self._lines = 0

    def append_text(self, lines):
        """
        Append input lines into the text area and scroll to the bottom.

        Additionally, raise the window on top of windows stack.

        @param lines iterable containing the lines to be added.
        """
        self.text.append(lines)
        self.raise_()


class FileChooser(Tkinter.Frame):
    """
    Widget used to select a file from the file-system.
    """

    def __init__(self, parent, **kwargs):
        Tkinter.Frame.__init__(self, parent)
        self.on_press_enter_listener = (_NULL_LISTENER, (), {})

        self._initialize(**kwargs)

    def _initialize(self, filename):
        """
        Initialize the file chooser widget.
        """
        self.grid_columnconfigure(0, weight=1)

        self.filename = StringVar(filename)
        entry = Tkinter.Entry(self, textvariable=self.filename)
        entry.bind("<Return>", self.on_press_enter_event)
        entry.grid(row=0, column=0, sticky='EW')

        button = Tkinter.Button(
                self, text="Select file", command=self.on_button_click)
        button.grid(row=0, column=1)

    @debug
    def on_press_enter(self):
        (func, args, kwargs) = self.on_press_enter_listener
        func(*args, **kwargs)

    @debug
    def on_press_enter_event(self, event):
        self.on_press_enter()

    @debug
    def on_button_click(self):
        """
        Open a filechooser dialog and set the internal filename.
        """
        filename = tkFileDialog.askopenfilename(
                parent=self, title='Choose a file')
        if filename:
            self.filename.set(filename)

    def get_filename(self):
        """
        Return the content of the filename entry.

        @return the filename entry content.
        """
        return self.filename.get()

    def register_listener(self, event, func, *args, **kwargs):
        """
        Register a listener for the specified named event.

        @param func function to schedule
        @param args positional arguments for the fuction
        @param kwargs named arguments for the function
        """
        if event not in ['press_enter']:
            raise ValueError("Invalid event name: " + event)

        if event == 'press_enter':
            self.on_press_enter_listener = (func, args, kwargs)


class Text(Tkinter.Frame):
    """
    Extension of the `Tk.Text` widget which add support to colored strings.

    The main goal of the widget is to extend the `#insert` method to add support
    for string coloring, depending on an input tags.
    """

    def __init__(self, parent, **kwargs):
        Tkinter.Frame.__init__(self, parent)
        self._scroll_limit = LINES_LIMIT
        self._num_lines = 0
        self._tags = []

        self._initialize(**kwargs)

    def _initialize(self, **kwargs):
        """
        Initialize the text widget.
        """
        text = Tkinter.Text(self, **kwargs)
        vert_scroll = Tkinter.Scrollbar(self)
        horiz_scroll = Tkinter.Scrollbar(self, orient=Tkinter.HORIZONTAL)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        text.grid(row=0, column=0, sticky='NSEW')
        text.config(yscrollcommand=vert_scroll.set)
        text.config(xscrollcommand=horiz_scroll.set)
        text.config(state=Tkinter.DISABLED)

        vert_scroll.grid(row=0, column=1, sticky='NS')
        vert_scroll.config(command=text.yview)

        horiz_scroll.grid(row=1, column=0, sticky='EW')
        horiz_scroll.config(command=text.xview)

        self.text = text

    def configure_scroll_limit(self, scroll_limit):
        """
        Chache the widget scroll limit.

        @param limit new scroll limit.
        """
        self._scroll_limit = scroll_limit

    def configure_tags(self, tags):
        """
        Configure text tags.

        @param tags collection of `Tag` items
        """
        self._tags = list(tags)
        map(lambda t: self.text.tag_config(t.name, t.settings), self._tags)

    def clear(self):
        """
        Clear the text widget.
        """
        self.text.config(state=Tkinter.NORMAL)
        self.text.delete(1.0, Tkinter.END)
        self.text.config(state=Tkinter.DISABLED)
        self._lines = 0

    def append(self, lines):
        """
        Append given lines to the text widget and try to color them.

        @param lines lines to add
        """

        def highlight_tag(tag):
            """
            Helper function simply used to adapt function signatures.
            """
            self._highlight_pattern(start, end, tag.pattern, tag.name)

        self.text.config(state=Tkinter.NORMAL)

        for line in lines:
            start = self.text.index('{0} - 1 lines'.format(Tkinter.END))
            end = self.text.index(Tkinter.END)

            self.text.insert(Tkinter.END, line)
            map(highlight_tag, list(self._tags))

            self._lines += 1
            if self._lines > self._scroll_limit:
                # delete from row 1, column 0, to row 2, column 0 (first line)
                self.text.delete(1.0, 2.0)
                self._lines -= 1

        self.text.config(state=Tkinter.DISABLED)

        # Scroll to the bottom
        self.text.yview(Tkinter.MOVETO, 1.0)

    def _highlight_pattern(self, start, end, pattern, tag_name):
        """
        Highlight the input pattern with the settings associated with the tag.

        Given a tag and a patter, the function will match only the first
        occurrence of the patter.

        @param start start search index
        @param stop stop search index
        @param pattern string pattern matching the tag
        @param tag_name name of the tag to associate with matching strings
        """
        count = Tkinter.IntVar()
        index = self.text.search(pattern, start, end, count=count, regexp=True)
        if not index:
            return

        match_end = '{0}+{1}c'.format(index, count.get())
        self.text.tag_add(tag_name, index, match_end)


@debug
def filter_thread_spawner_body(lines, interval, filter_queue, lines_queue):
    """
    Spawn a file filter thread as soon as a filter is read from the queue.

    @param lines line used to skip stale lines
    @param interval polling interval
    @param filter_queue message queue containing the filter to apply
    @param lines_queue message queue containing the lines to pass to the gui
    """
    stop = None
    worker = None
    while True:
        item = filter_queue.get()
        #print 'Received filters: {0}'.format(filters)
        if worker is not None:
            stop.set()
            worker.join()

        if item == _STOP_MESSAGE:
            break

        (filename, filters) = item
        stop = threading.Event()
        worker = threading.Thread(
            target=file_observer_body,
            args=(filename, lines, interval, filters, lines_queue, stop))
        worker.start()


def last(lines, iterable):
    """
    Yield last `lines` lines, extracted from `iterable`.

    Flush the buffer of lines if an empty string is received (EOF).  When this
    happens, the function will return all the new lines generated.

    @param lines number of lines to buffer
    @param iterable iterable containing lines to be processed.
    """
    # Fill the buffer of lines, untill an EOF is received
    for line in deque(takewhile(partial(ne, ''), iterable), maxlen=lines):
        yield line
    yield ''

    # Now return each item produced by the iterable
    for line in iterable:
        yield line


def tail_f(filename):
    """
    Emulate the behaviour of `tail -f`.

    Keep reading from the end of the file, and yield lines as soon as they are
    added to the file.  The function yields an empty string when the EOF is
    reached:  this let the caller wait a small amount of time before trying to
    read new data.

    @param filename name of the file to observe
    """
    with open(filename) as f:
        while True:
            for line in f:
                yield line
            yield ''

            # Kind of rewind
            where = f.tell()
            f.seek(where)


def grep_e(*exps):
    """
    Emulate the behaviour of `grep -e PATTERN [-e PATTERN ...]`.

    Return a function which will try to match an input string against the set
    of loaded regular expressions.

    @param exps list of regular expressions
    """
    regexps = map(re.compile, exps)

    def wrapper(line):
        """
        Match input string with the set of preloaded regular expressions.

        If an empty string, that will be interpreted as EOF and then a fake
        match will be generated (to wake up possibly blocked callers).

        @param line string to check for regular expressions matches.
        @return True 
        """
        return line == '' or any(map(methodcaller('search', line), regexps))

    return wrapper


@debug
def file_observer_body(filename, lines, interval, filters, lines_queue, stop):
    """
    Body function of thread waiting for file content changes.

    The thread will poll `filename` every `iterval` seconds looking for new
    lines;  as soon as new lines are read from the file, these are filtered
    depeding on `filters`, and the ones matching given criteria are put into the
    synchronized `lines_queue`.

    @param filename filename to poll
    @param lines limit the number of lines produced by calling `tail_f`
    @param interval polling interval
    @param filters iterable of regexp filters to apply to the file content
    @param lines_queue synchronized queue containing lines matching criteria
    @param stop `threading.Event` object, used to stop the thread.
    """
    line_buffer = []
    for line in ifilter(grep_e(*filters), last(lines, tail_f(filename))):
        if stop.isSet():
            break

        if (not line and line_buffer) or (len(line_buffer) == _BATCH_LIMIT):
            lines_queue.put(line_buffer)
            print '+', len(line_buffer), 'qsize', lines_queue.qsize()
            line_buffer = []

        if not line:
            # We reched the EOF, hence wait for new content
            time.sleep(interval)
            continue

        line_buffer.append(line)


def gui_updater_body(gui, lines_queue):
    """
    Body function of the thread in charge of update the gui text area.

    @param gui `Gui` object to update.
    @param lines_queue message queue containing lines used to update the gui.
    """
    while True:
        lines = lines_queue.get()
        #print '-', lines_queue.qsize()
        if lines == _STOP_MESSAGE:
            break

        gui.schedule(gui.append_text, lines)


@debug
def quit(filter_queue, lines_queue):
    """
    Invoked by the GUI when the main window has been closed.
    """
    filter_queue.put(_STOP_MESSAGE)
    lines_queue.put(_STOP_MESSAGE)


@debug
def apply_filters(filename, filters, gui, filter_queue):
    """
    Invoked by the GUI when a new filter is entered.

    Clear the gui and queue the received filter into the shared synchronized
    queue.

    @param filename the name of the file to analyze
    @param gui `Gui` object to update.
    @param filters collection of string filters
    @param filter_queue message queue shared with working thread.
    """
    gui.schedule(gui.clear_text)
    filter_queue.put((filename, filter(None, filters)))


def _build_parser():
    """
    Return a command-line arguments parser.
    """
    parser = ArgumentParser(
            description='Filter the content of a file, dynamically')

    parser.add_argument(
            'filename', default='', nargs='?', help='Filename to filter.',
            metavar='FILENAME')
    parser.add_argument(
            '-s', '--sleep-interval', dest='interval', default=SLEEP_INTERVAL,
            type=float, help='Sleep SLEEP_INTERVAL seconds between iterations',
            metavar='SLEEP_INTERVAL')
    parser.add_argument(
            '-f', '--num-filters', dest='num_filters', default=NUM_FILTERS,
            type=int, help='Number of filters to apply to log file',
            metavar='NUM_FILTERS')
    parser.add_argument(
            '-l', '--limit', dest='limit', default=LINES_LIMIT, type=int,
            help='Number of lines to display in the text area', metavar='LIMIT')
    parser.add_argument(
            '-e', '--regexp', dest='filters', action='append',
            help='Filter presets', metavar='FILTERS')

    return parser


def _main():
    parser = _build_parser()
    args = parser.parse_args()
    # create the array of filters
    num_filters = max(len(args.filters), args.num_filters)
    empty_filters = num_filters - len(args.filters)
    filters = args.filters + [''] * empty_filters

    limit = args.limit / _BATCH_LIMIT / 32
    limit = 0
    filter_queue = Queue.Queue(limit)
    lines_queue = Queue.Queue(limit)

    gui = Gui(None, filename=args.filename, filters=filters, scroll_limit=args.limit)
    gui.register_listener('quit', quit, filter_queue, lines_queue)
    gui.register_listener('new_filter', apply_filters, gui, filter_queue)
    if args.filename and args.filters:
        gui.on_press_enter()

    filter_thread_spawner = threading.Thread(
            target=filter_thread_spawner_body,
            args=(args.limit, args.interval, filter_queue,
                lines_queue))
    filter_thread_spawner.start()

    gui_updater = threading.Thread(
            target=gui_updater_body,
            args=(gui, lines_queue))
    gui_updater.start()

    gui.mainloop()



if __name__ == '__main__':
    _main()
