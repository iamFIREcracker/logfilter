#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import datetime
import os
import re
import time
import subprocess
import threading
from argparse import ArgumentParser
from collections import deque
from collections import namedtuple
from itertools import cycle
from itertools import takewhile

from ._compact import filedialog
from ._compact import filter
from ._compact import func_get_name
from ._compact import tkinter
from ._compact import queue
from ._compact import range


"""Number of lines to collect before telling the gui to refresh."""
_BATCH_LIMIT = 200

"""Default event listener."""
_NULL_LISTENER = lambda *a, **kw: None

"""Gui polling job interval"""
_POLL_INTERVAL = 66

"""Stop message used to stop threads."""
_STOP_MESSAGE = None


FOREGROUND = '#F8F8F2'
BACKGROUND = '#1B1D1E'
CURRENTLINEBACKGROUND = '#232728'
LINENRBACKGROUND = '#AAAAAA'
SELECTFOREGROUND = FOREGROUND
SELECTBACKGROUND = '#403D3D'

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

"""Default initial directory used by the file chooser widget"""
_INITIALDIR = os.path.expanduser('~')

"""Number of string filters."""
NUM_FILTERS = 1

"""Number of lines to display on screen."""
LINES_LIMIT = 8000

"""Special scroll limit value to use a kind of infinite scroll buffer."""
LINES_UNLIMITED = -1

"""Default sleep interval"""
SLEEP_INTERVAL = 1.0

"""Catch all filter"""
CATCH_ALL = ['^']

"""End of file sentinel"""
EOF = object()

"""List of env variables to check while editing a file"""
EDITORS = 'LFEDITOR VISUAL EDITOR'.split(' ')

"""Sentinel to check wether selected line has been initialized or not"""
UNSELECTED = object()


def debug(func):
    """
    Decorator which prints a message before and after a function execution.
    """
    NOW = lambda: datetime.datetime.now()

    def wrapper(*args, **kwargs):
        print('{now}: {fname}: entering'.format(
            now=NOW(), fname=func_get_name(func)))
        func(*args, **kwargs)
        print('{now}: {fname}: exiting...'.format(
            now=NOW(), fname=func_get_name(func)))
    return wrapper


def StringVar(default):
    """
    Return a new (initialized) `tkinter.StringVar.

    @param default default string value
    """
    s = tkinter.StringVar()
    s.set(default)
    return s


def BooleanVar(default):
    """
    Return a new (initialized) `tkinter.BooleanVar`.

    @param default default boolean value
    """
    b = tkinter.BooleanVar()
    b.set(default)
    return b



"""Tag object used by the `Text` widget to hanndle string coloring."""
Tag = namedtuple('Tag', 'name pattern settings'.split())


class Gui(tkinter.Tk):

    def __init__(self, parent, **kwargs):
        tkinter.Tk.__init__(self, parent)

        self._schedule_queue = queue.Queue()

        self.on_quit_listener = (_NULL_LISTENER, (), {})
        self.on_new_filter_listener = (_NULL_LISTENER, (), {})

        self._initialize(**kwargs)

        self._update()

    def _initialize(self, font, filename, filters, scroll_limit):
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
        container1 = tkinter.Frame(self)
        container1.grid(row=1, column=0, sticky='EW')
        for i in range(len(filters)):
            container1.grid_columnconfigure(i, weight=1)

        self.filter_strings = [StringVar(f) for f in filters]
        entries = [tkinter.Entry(container1, textvariable=filter_string)
                    for filter_string in self.filter_strings]
        for (i, entry) in enumerate(entries):
            entry.focus_force()
            entry.grid(row=0, column=i, sticky='EW')
            entry.bind("<Return>", self.on_press_enter_event)

        button = tkinter.Button(
                container1, text="Filter", command=self.on_press_enter)
        button.grid(row=0, column=len(filters), sticky='EW')

        # Container2
        self.text = Text(
                self, foreground=FOREGROUND, background=BACKGROUND,
                selectforeground=SELECTFOREGROUND,
                selectbackground=SELECTBACKGROUND,
                inactiveselectbackground=SELECTBACKGROUND,
                font=font, wrap=tkinter.NONE,
                highlightthickness=0, takefocus=0, bd=0)
        self.text.grid(row=2, column=0, sticky='NSEW')
        self.text.configure_scroll_limit(scroll_limit)
        self.text.set_filename(filename)

    def _update(self):
        """
        Poll the schedule queue for new actions.
        """
        for i in range(10):
            try:
                (func, args, kwargs) =  self._schedule_queue.get(False)
                #print '- schedule_queue', self._schedule_queue.qsize()
            except queue.Empty:
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
        filter_strings = [s.get() for s in self.filter_strings]
        self.text.set_filename(filename)
        self.text.configure_tags(
                Tag(n, f, {'foreground': c})
                for ((n, c), f) in zip(cycle(_TAG_PALETTE), filter_strings))
        (func, args, kwargs) = self.on_new_filter_listener
        args = [filename, filter_strings] + list(args)
        func(*args, **kwargs)

    @debug
    def on_press_enter_event(self, event):
        self.on_press_enter()

    def raise_(self):
        """
        Raise the window on the top of windows stack.

        The method is supposed to be invoked by the gui thread, hence it should
        be used in pair with `schedule`.
        """
        #self.attributes('-topmost', True)
        #self.attributes('-topmost', False)
        self.lift()
        self.focus_force()

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

        The method schedule the action to the giu thread, hence it is to be
        considered thread-safe.
        """
        def wrapped():
            self.text.clear()
        self.schedule(wrapped)

    def append_text(self, lines):
        """
        Append input lines into the text area and scroll to the bottom.

        Additionally, raise the window on top of windows stack.

        The method schedule the action to the giu thread, hence it is to be
        considered thread-safe.

        @param lines iterable containing the lines to be added.
        """
        def wrapped():
            self.text.append(lines)
            if self.text.raise_on_output:
                self.raise_()
        self.schedule(wrapped)


class FileChooser(tkinter.Frame):
    """
    Widget used to select a file from the file-system.
    """

    def __init__(self, parent, **kwargs):
        tkinter.Frame.__init__(self, parent)
        self.on_press_enter_listener = (_NULL_LISTENER, (), {})

        self._initialize(**kwargs)

    def _initialize(self, filename):
        """
        Initialize the file chooser widget.
        """
        self.grid_columnconfigure(0, weight=1)

        self.filename = StringVar(filename)
        entry = tkinter.Entry(self, textvariable=self.filename)
        entry.bind("<Return>", self.on_press_enter_event)
        entry.grid(row=0, column=0, sticky='EW')

        button = tkinter.Button(
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
        prev = self.filename.get()
        initialdir = os.path.dirname(prev) if prev else _INITIALDIR

        filename = filedialog.askopenfilename(
                parent=self, initialdir=initialdir, title='Choose a file')
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


class Text(tkinter.Frame):
    """
    Extension of the `Tk.Text` widget which add support to colored strings.

    The main goal of the widget is to extend the `#insert` method to add support
    for string coloring, depending on an input tags.
    """

    def __init__(self, parent, **kwargs):
        tkinter.Frame.__init__(self, parent)
        self._scroll_limit = LINES_LIMIT
        self._scroll_on_output = BooleanVar(True)
        self._raise_on_output = BooleanVar(True)
        self._wrap_text = BooleanVar(False)
        self._greedy_coloring = BooleanVar(False)
        self._lines = 0
        self._line_numbers = deque()
        self._filename = ''
        self._selected_line = UNSELECTED
        self._tags = []

        self._initialize(**kwargs)

    def _initialize(self, **kwargs):
        """
        Initialize the text widget.
        """
        linepanel = tkinter.Text(
                self, width=7, padx=7, highlightthickness=0, takefocus=0, bd=0,
                background=BACKGROUND, foreground=LINENRBACKGROUND,
                state='disabled')
        text = tkinter.Text(self, **kwargs)
        vert_scroll = tkinter.Scrollbar(self)
        horiz_scroll = tkinter.Scrollbar(self, orient=tkinter.HORIZONTAL)
        popup = tkinter.Menu(self, tearoff=0)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        popup.add_command(label="Edit".ljust(20), command=self.edit)
        popup.add_command(label="Clear".ljust(20), command=self.clear)
        popup.add_separator()
        popup.add_checkbutton(
                label="Wrap Text".ljust(20),
                onvalue=True, offvalue=False, variable=self._wrap_text,
                command=self.wrap_text)
        popup.add_checkbutton(
                label="Greedy coloring".ljust(20),
                onvalue=True, offvalue=False, variable=self._greedy_coloring)
        popup.add_separator()
        popup.add_checkbutton(
                label="Auto scroll".ljust(20),
                onvalue=True, offvalue=False, variable=self._scroll_on_output)
        popup.add_checkbutton(
                label="Auro raise".ljust(20),
                onvalue=True, offvalue=False, variable=self._raise_on_output)

        linepanel.grid(row=0, column=0, sticky='NSW')
        linepanel.config(yscrollcommand=self._on_scroll_change(vert_scroll, text))

        text.tag_config('currentline', background=CURRENTLINEBACKGROUND)
        text.tag_config('selection', background=SELECTBACKGROUND)
        text.grid(row=0, column=1, sticky='NSEW')
        text.config(yscrollcommand=self._on_scroll_change(vert_scroll, linepanel))
        text.config(xscrollcommand=horiz_scroll.set)
        text.config(state=tkinter.DISABLED)
        text.bind("<Button-1>", self._highlight_current)
        text.bind("<Button-3>", self._show_popup)
        text.bind("<<Selection>>", self._on_selection_change)

        vert_scroll.grid(row=0, column=2, sticky='NS')
        vert_scroll.config(command=self._on_scrollbar_change(text, linepanel))

        horiz_scroll.grid(row=1, column=1, sticky='EW')
        horiz_scroll.config(command=text.xview)

        self.linepanel = linepanel
        self.text = text
        self.popup = popup


    def _on_scroll_change(self, scrollbar, *widgets):
        def inner(*args):
            scrollbar.set(*args)
            [w.yview('moveto', args[0]) for w in widgets]
        return inner

    def _on_scrollbar_change(self, *widgets):
        def inner(*args):
            print(*args)
            [w.yview(*args) for w in widgets]
        return inner

    def _clear_selection(self):
        try:
            self.text.tag_remove("sel", "sel.first", "sel.last")
        except tkinter.TclError:
            pass

    def _clear_current(self):
        if self._selected_line is not UNSELECTED:
            line_end = self.text.index("{0} + 1 lines".format(self._selected_line))
            self.text.tag_remove("currentline", self._selected_line, line_end)
            self._selected_line = UNSELECTED

    def _highlight_current(self, event):
        # Clear old current line
        self._clear_current()

        # .. and highlight the new line
        newline = self.text.index(
                "@{0},{1} linestart".format(event.x, event.y))
        if int(float(newline)) <= self._lines:
            self._selected_line = newline
            line_end = self.text.index("{0} + 1 lines".format(self._selected_line))
            self.text.tag_add("currentline", self._selected_line, line_end)

        # Finally, hide the menu
        self.popup.unpost()

    def _on_selection_change(self, event):
        try:
            if self.text.get("sel.first", "sel.last"):
                self._clear_current();
        except tkinter.TclError:
            pass

    def _show_popup(self, event):
        self._clear_selection()
        self._highlight_current(event)
        self.popup.post(event.x_root, event.y_root)

    def configure_scroll_limit(self, scroll_limit):
        """
        Chache the widget scroll limit.

        @param limit new scroll limit.
        """
        self._scroll_limit = scroll_limit

    def set_filename(self, filename):
        """
        Set the name of the file from which we will receive updates.

        @param filename filename
        """
        self._filename = filename

    def configure_tags(self, tags):
        """
        Configure text tags.

        @param tags collection of `Tag` items
        """
        self._tags = list(tags)
        [self.text.tag_config(t.name, t.settings) for t in self._tags]

    def clear(self):
        """
        Clear the text widget.
        """
        self.text.config(state=tkinter.NORMAL)
        self.text.delete(1.0, tkinter.END)
        self.text.config(state=tkinter.DISABLED)
        self._lines = 0
        self._line_numbers = deque()

    def _get_editor(self):
        """
        Return the editor to use to open the current file.

        The function will look for environment variables in the given order:
        LFEDITOR, VISUAL and finally EDITOR
        """
        for name in EDITORS:
            if name in os.environ:
                return os.environ[name]

    def _get_row(self):
        """
        Get the file row associated with the mouse event.
        """
        index = int(float(self._selected_line)) - 1
        if index >= len(self._line_numbers):
            if self._line_numbers:
                return str(self._line_numbers[-1])
            else:
                return str(1)
        else:
            # Deques are not optimized for random access, but given that the
            # edit operation is not so frequent, we can just tolerate that
            return str(self._line_numbers[index])

    def edit(self):
        """
        Open the current file inside your preferred editor.
        """
        cmd = self._get_editor()
        cmd = cmd.replace('FILE', self._filename)
        cmd = cmd.replace('ROW', self._get_row())
        subprocess.Popen(cmd, shell=True)

    def wrap_text(self):
        wrap = tkinter.CHAR if self._wrap_text.get() else tkinter.NONE
        self.text.config(wrap=wrap)

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

        self.linepanel.config(state=tkinter.NORMAL)
        self.text.config(state=tkinter.NORMAL)

        for (i, line) in lines:
            start = self.text.index('{0} - 1 lines'.format(tkinter.END))
            end = self.text.index(tkinter.END)

            self.text.insert(tkinter.END, line)
            self.linepanel.insert(tkinter.END, '{0:>7}\n'.format(i))
            [highlight_tag(t) for t in list(self._tags)]

            self._lines += 1
            self._line_numbers.append(i)
            if (self._scroll_limit != LINES_UNLIMITED
                    and self._lines > self._scroll_limit):
                # delete from row 1, column 0, to row 2, column 0 (first line)
                self.linepanel.delete(1.0, 2.0)
                self.text.delete(1.0, 2.0)
                self._lines -= 1
                self._line_numbers.popleft()

                if self._selected_line is not UNSELECTED:
                    self._selected_line = self.text.index(
                            "{0} - 1 lines".format(self._selected_line))

        self.text.config(state=tkinter.DISABLED)
        self.linepanel.config(state=tkinter.DISABLED)

        # Scroll to the bottom
        if self._scroll_on_output.get():
            self.linepanel.yview(tkinter.MOVETO, 1.0)
            self.text.yview(tkinter.MOVETO, 1.0)

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
        while True:
            count = tkinter.IntVar()
            index = self.text.search(pattern, start, end, count=count, regexp=True)
            if not index:
                return

            match_end = '{0}+{1}c'.format(index, count.get())
            self.text.tag_add(tag_name, index, match_end)
            start = match_end

            if not self._greedy_coloring.get():
                return

    @property
    def raise_on_output(self):
        return self._raise_on_output.get()


#
# Taken from: http://effbot.org/zone/tkinter-autoscrollbar.htm
#
class AutoScrollbar(tkinter.Scrollbar):
    # a scrollbar that hides itself if it's not needed.  only
    # works if you use the grid geometry manager.
    def set(self, lo, hi):
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            # grid_remove is currently missing from Tkinter!
            self.tk.call("grid", "remove", self)
        else:
            self.grid()
        tkinter.Scrollbar.set(self, lo, hi)

    def pack(self, **kw):
        raise tkinter.TclError("cannot use pack with this widget")

    def place(self, **kw):
        raise tkinter.TclError("cannot use place with this widget")


@debug
def filter_thread_spawner_body(catchall, lines, interval, filter_queue,
        lines_queue):
    """
    Spawn a file filter thread as soon as a filter is read from the queue.

    @param catchall flag indicating all the lines of the file should be returned
    @param lines line used to skip stale lines
    @param interval polling interval
    @param filter_queue message queue containing the filter to apply
    @param lines_queue message queue containing the lines to pass to the gui
    """
    stop = None
    worker = None
    while True:
        item = filter_queue.get()
        if worker is not None:
            stop.set()
            worker.join()

        if item == _STOP_MESSAGE:
            break

        (filename, filters) = item
        if catchall:
            filters = CATCH_ALL
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

    @param lines number of lines to buffer (if equal to LINES_UNLIMITED, then
                 all the lines will be buffered)
    @param iterable iterable containing lines to be processed.
    """
    def noteof(aggregate):
        (i, line) = aggregate
        return line is not EOF

    lines = lines if lines != LINES_UNLIMITED else None
    # Fill the buffer of lines, untill an EOF is received
    for line in deque(takewhile(noteof, iterable), maxlen=lines):
        yield line
    yield next(iterable)

    # Now return each item produced by the iterable
    for line in iterable:
        yield line


def lineenumerate(iterable):
    """
    Return a generator which prepend a line number in front of each line
    extracted from the given iterable.

    The function properly takes into account EOF messages by yielding them
    without increase the line number.
    """
    i = 1
    for line in iterable:
        yield (i, line)
        if line is not EOF:
            i += 1

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
            yield EOF

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
    regexps = [re.compile(exp) for exp in exps]

    def wrapper(aggregate):
        """
        Match input string with the set of preloaded regular expressions.

        If an empty string, that will be interpreted as EOF and then a fake
        match will be generated (to wake up possibly blocked callers).

        @param line string to check for regular expressions matches.
        @return True 
        """
        (i, line) = aggregate
        return line == EOF or any([reg.search(line) for reg in regexps])

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
    for (i, line) in filter(grep_e(*filters), last(lines, lineenumerate(tail_f(filename)))):
        if stop.isSet():
            break

        if (line is EOF and line_buffer) or (len(line_buffer) == _BATCH_LIMIT):
            lines_queue.put(line_buffer)
            #print '+', len(line_buffer), 'qsize', lines_queue.qsize()
            line_buffer = []

        if line is EOF:
            # We reched the EOF, hence wait for new content
            time.sleep(interval)
            continue

        line_buffer.append((i, line))


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

        gui.append_text(lines)


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
    gui.clear_text()
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
    parser.add_argument(
            '-a', '--catch-all', dest='catchall', default=False,
            help='Catch all the lines and highlight those matching filters',
            action='store_true')
    parser.add_argument(
            '--font', dest='font', help='Font used by the application')

    return parser


def _main():
    parser = _build_parser()
    args = parser.parse_args()

    # create the array of filters
    filters = args.filters if args.filters else []
    num_filters = max(len(filters), args.num_filters)
    empty_filters = num_filters - len(filters)
    filters += [''] * empty_filters

    # create communication queues, shared between threads
    filter_queue = queue.Queue()
    lines_queue = queue.Queue()

    gui = Gui(
            None, font=args.font, filename=args.filename, filters=filters,
            scroll_limit=args.limit)
    gui.register_listener('quit', quit, filter_queue, lines_queue)
    gui.register_listener('new_filter', apply_filters, gui, filter_queue)
    if args.filename and args.filters:
        gui.on_press_enter()

    filter_thread_spawner = threading.Thread(
            target=filter_thread_spawner_body,
            args=(args.catchall, args.limit, args.interval, filter_queue,
                lines_queue))
    filter_thread_spawner.start()

    gui_updater = threading.Thread(
            target=gui_updater_body, args=(gui, lines_queue))
    gui_updater.start()

    gui.mainloop()



if __name__ == '__main__':
    _main()
