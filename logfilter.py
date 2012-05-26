#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import time
import threading
import Tkinter
import Queue
from argparse import ArgumentParser
from collections import namedtuple
from itertools import ifilter



"""Application title template"""
TITLE = 'logfilter: {filename}'

"""Number of lines to collect before telling the gui to refresh."""
BATCH_LIMIT = 50

"""Number of string filters."""
NUM_FILTERS = 1

"""Number of lines to display on screen."""
LINES_LIMIT = 8000

"""Tag color palette."""
TAG_PALETTE = (
        ('red', '#E52222'),
        ('green', '#A6E32D'),
        ('yellow', '#FD951E'),
        ('blue', '#C48DFF'),
        ('magenta', '#FA2573'),
        ('cyan', '#67D9F0')
    )

"""Stop message used to stop threads."""
STOP_MESSAGE = None

"""Default event listener."""
NULL_LISTENER = lambda *a, **kw: None

"""Tag object used by the `Text` widget to hanndle string coloring."""
Tag = namedtuple('Tag', 'name pattern settings'.split())


def debug(func):
    """
    Decorator which prints a message before and after a function execution.
    """
    def wrapper(*args, **kwargs):
        print '{0}: entering'.format(func.func_name)
        func(*args, **kwargs)
        print '{0}: exiting...'.format(func.func_name)
    return wrapper


def StringVar(default):
    """
    Return a new (initialized) `Tkinter.StringVar.

    @param default default string value
    """
    s = Tkinter.StringVar()
    s.set(default)
    return s


class Gui(Tkinter.Tk):

    def __init__(self, parent, **kwargs):
        Tkinter.Tk.__init__(self, parent) #super(Tkinter.Tk, self).__init__(parent)
        self.parent = parent

        self.on_quit_listener = (NULL_LISTENER, (), {})
        self.on_new_filter_listener = (NULL_LISTENER, (), {})

        self._initialize(**kwargs)

    def _initialize(self, filters, scroll_limit):
        """
        Initialize the layout of the GUI
        """
        container1 = Tkinter.Frame(self)
        self.filter_strings = [StringVar(f) for f in filters]
        entries = [Tkinter.Entry(container1, textvariable=filter_string)
                    for filter_string in self.filter_strings]
        button = Tkinter.Button(
                container1, text="Filter", command=self.on_button_click)

        container2 = Tkinter.Frame(self)
        self.text = Text(container2, bg='#222', fg='#eee', wrap=Tkinter.NONE)
        self.text.configure_scroll_limit(scroll_limit)

        self.grid()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.protocol('WM_DELETE_WINDOW', self.on_close)
        self.bind('<Escape>', self.on_quit)

        # Container1
        container1.grid(row=0, column=0, sticky='EW')
        for i in xrange(len(entries)):
            container1.grid_columnconfigure(i, weight=1)
        for (i, entry) in enumerate(entries):
            entry.focus_force()
            entry.grid(row=0, column=i, sticky='EW')
            entry.bind("<Return>", self.on_press_enter)
        button.grid(row=0, column=len(entries), sticky='EW')

        # Container2
        container2.grid(row=1, column=0, sticky='EW')
        container2.grid_columnconfigure(0, weight=1)
        self.text.grid(row=0, column=0, sticky='NSEW')

    @debug
    def on_close(self):
        (func, args, kwargs) = self.on_quit_listener
        func(*args, **kwargs)
        self.quit()

    @debug
    def on_quit(self, event):
        self.on_close()

    @debug
    def on_button_click(self):
        filter_strings = map(lambda s: s.get(), self.filter_strings)
        self.text.configure_tags(
                Tag(n, f, {'foreground': c})
                    for ((n, c), f) in zip(TAG_PALETTE, filter_strings))
        (func, args, kwargs) = self.on_new_filter_listener
        args = [filter_strings] + list(args)
        func(*args, **kwargs)

    @debug
    def on_press_enter(self, event):
        self.on_button_click()

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
        self.after_idle(func, *args, **kwargs)

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
def filter_thread_spawner_body(filename, interval, filter_queue, lines_queue):
    """
    Spawn a file filter thread as soon as a filter is read from the queue.

    @param filename name of the file to pass to the working thread
    @param interval polling interval
    @param filter_queue message queue containing the filter to apply
    @param lines_queue message queue containing the lines to pass to the gui
    """
    stop = None
    worker = None
    while True:
        filters = filter_queue.get()
        print 'Received filters: {0}'.format(filters)
        if worker is not None:
            stop.set()
            worker.join()

        if filters == STOP_MESSAGE:
            break

        stop = threading.Event()
        worker = threading.Thread(
            target=file_observer_body,
            args=(filename, interval, filters, lines_queue, stop))
        worker.start()


def tail_f(filename):
    """
    Emulate the behaviour of `tail -f`.

    Keep reading from the end of the file, and yeald lines as soon as they are
    added to the file.

    @param filename name of the file to observe
    """
    with open(filename) as f:
        while True:
            for line in f:
                yield line
            yield ""

            # Kind of rewind
            where = f.tell()
            f.seek(where)


def regexp_filter(*exps):
    """
    Create a reg exp filter function to be passed to built-in `ifilter` func.

    @param exps list of regular expressions representing filter criteria.
    """
    regexps = map(re.compile, exps)

    def wrapper(line):
        """
        Return True if the input string matches one of the outer level criteria.

        @param gen string to be tested with the outer level criteria.
        """
        return line == '' or any(map(lambda r: r.search(line), regexps))

    return wrapper


@debug
def file_observer_body(filename, interval, filters, lines_queue, stop):
    """
    Body function of thread waiting for file content changes.

    The thread will poll `filename` every `iterval` seconds looking for new
    lines;  as soon as new lines are read from the file, these are filtered
    depeding on `filters`, and the one matching given criteria are put into the
    synchronized `lines_queue`.

    @param filename filename to poll
    @param interval polling interval
    @param filters iterable of regexp filters to apply to the file content
    @param lines_queue synchronized queue containing lines matching criteria
    @param stop `threading.Event` object, used to stop the thread.
    """
    lines = []
    for line in ifilter(regexp_filter(*filters), tail_f(filename)):
        if stop.isSet():
            break

        if (not line and lines) or (len(lines) == BATCH_LIMIT):
            lines_queue.put(lines)
            lines = []

        if not line:
            # We reched the EOF, hence wait for new content
            time.sleep(interval)
            continue

        lines.append(line)


@debug
def gui_updater_body(gui, lines_queue):
    """
    Body function of the thread in charge of update the gui text area.

    @param gui `Gui` object to update.
    @param lines_queue message queue containing lines used to update the gui.
    """
    while True:
        lines = lines_queue.get()
        if lines == STOP_MESSAGE:
            break

        gui.schedule(gui.append_text, lines)


@debug
def quit(filter_queue, lines_queue):
    """
    Invoked by the GUI when the main window has been closed.
    """
    filter_queue.put(STOP_MESSAGE)
    lines_queue.put(STOP_MESSAGE)


@debug
def apply_filters(filters, gui, filter_queue):
    """
    Invoked by the GUI when a new filter is entered.

    Clear the gui and queue the received filter into the shared synchronized
    queue.

    @param gui `Gui` object to update.
    @param filters collection of string filters
    @param filter_queue message queue shared with working thread.
    """
    gui.clear_text()
    filter_queue.put(filter(None, filters))


def _build_parser():
    """
    Return a command-line arguments parser.
    """
    parser = ArgumentParser(
            description='Filter the content of a file, dynamically')

    parser.add_argument(
            '-f', '--filename', dest='filename', required=True,
            help='Filename to filter.', metavar='FILENAME')
    parser.add_argument(
            '-i', '--interval', dest='interval', required=True, type=float,
            help='Timeout interval to wait before checking for updates',
            metavar='INTERVAL')
    parser.add_argument(
            '-n', '--num-filters', dest='num_filters', default=NUM_FILTERS,
            type=int, help='Number of filters to apply to log file',
            metavar='NUM_FILTERS')
    parser.add_argument(
            '-l', '--limit', dest='limit', default=LINES_LIMIT, type=int,
            help='Number of lines to display in the text area', metavar='LIMIT')
    parser.add_argument(
            'filters', nargs='*', help='Filter presets', metavar='FILTERS')

    return parser


def _main():
    parser = _build_parser()
    args = parser.parse_args()
    # create the array of filters
    num_filters = max(len(args.filters), args.num_filters)
    empty_filters = num_filters - len(args.filters)
    filters = args.filters + [''] * empty_filters

    filter_queue = Queue.Queue()
    lines_queue = Queue.Queue()

    gui = Gui(None, filters=filters, scroll_limit=args.limit)
    gui.title(TITLE.format(filename=args.filename))
    gui.register_listener('quit', quit, filter_queue, lines_queue)
    gui.register_listener('new_filter', apply_filters, gui, filter_queue)
    if args.filters:
        gui.on_button_click()

    filter_thread_spawner = threading.Thread(
            target=filter_thread_spawner_body,
            args=(args.filename, args.interval, filter_queue, lines_queue))
    filter_thread_spawner.start()

    gui_updater = threading.Thread(
            target=gui_updater_body,
            args=(gui, lines_queue))
    gui_updater.start()

    gui.mainloop()



if __name__ == '__main__':
    _main();
