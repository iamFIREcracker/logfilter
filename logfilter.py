#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import time
import threading
import Tkinter
import Queue
from argparse import ArgumentParser
from itertools import ifilter



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


def debug(func):
    def wrapper(*args, **kwargs):
        print '{0}: entering'.format(func.func_name)
        func(*args, **kwargs)
        print '{0}: exiting...'.format(func.func_name)
    return wrapper


def extract_elemets(queue, limit):
    """
    Extract at most `limit` elements from the queue, without blocking.

    @param queue synchronized blocking queue
    @param limit maximum number of elements to extract
    """
    limit = min(queue.qsize(), limit)
    try:
        while limit:
            yield queue.get(0)
    except Queue.Empty:
        return


class Gui(Tkinter.Tk):

    def __init__(self, parent, **kwargs):
        Tkinter.Tk.__init__(self, parent) #super(Tkinter.Tk, self).__init__(parent)
        self.parent = parent

        self.on_quit_listener = (NULL_LISTENER, (), {})
        self.on_new_filter_listener = (NULL_LISTENER, (), {})

        self._initialize(**kwargs)

    def _initialize(self, filters, limit):
        """
        Initialize the layout of the GUI
        """
        container1 = Tkinter.Frame(self)
        self.filter_strings = [Tkinter.StringVar() for i in xrange(filters)]
        entries = [Tkinter.Entry(container1, textvariable=filter_string)
                    for filter_string in self.filter_strings]
        button = Tkinter.Button(
                container1, text="Filter", command=self.on_button_click)
        container2 = Tkinter.Frame(self)
        self.text = Tkinter.Text(
                container2, bg='#222', fg='#eee', wrap=Tkinter.NONE)
        self._limit = limit;
        self._lines = 0
        scrollbar1 = Tkinter.Scrollbar(container2)
        container3 = Tkinter.Frame(self)
        scrollbar2 = Tkinter.Scrollbar(container3, orient=Tkinter.HORIZONTAL)

        self.grid()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.protocol('WM_DELETE_WINDOW', self.on_close)
        self.bind('<Escape>', self.on_quit)

        # Container1
        container1.grid(row=0, column=0, sticky='EW')
        for i in xrange(len(entries)):
            container1.grid_columnconfigure(i, weight=1)

        # Filter entry
        for (i, entry) in enumerate(entries):
            entry.focus_force()
            entry.grid(row=0, column=i, sticky='EW')
            entry.bind("<Return>", self.on_press_enter)

        # Filter button
        button.grid(row=0, column=len(entries), sticky='EW')

        # Container 2
        container2.grid(row=1, column=0, sticky='NSEW')
        container2.grid_rowconfigure(0, weight=1)
        container2.grid_columnconfigure(0, weight=1)

        # Text area
        self.text.grid(row=0, column=0, sticky='NSEW')
        self.text.config(yscrollcommand=scrollbar1.set)
        self.text.config(xscrollcommand=scrollbar2.set)
        self.text.config(state=Tkinter.DISABLED)
        map(lambda (name, color): self.text.tag_configure(name, foreground=color),
            TAG_PALETTE)

        # Vertical Scrollbar
        scrollbar1.grid(row=0, column=1, sticky='NS')
        scrollbar1.config(command=self.text.yview)

        # Container 3
        container3.grid(row=2, column=0, sticky='EW')
        container3.grid_columnconfigure(0, weight=1)

        # Horizontal scrollbar
        scrollbar2.grid()
        scrollbar2.grid(row=0, column=0, sticky='EW')
        scrollbar2.config(command=self.text.xview)

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
        self._cached_filters = map(re.compile, filter_strings)
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

    def scroll_bottom(self):
        """
        Scroll to the bottom of the text area.
        """
        self.text.yview(Tkinter.MOVETO, 1.0)

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
        self.text.config(state=Tkinter.NORMAL)
        self.text.delete(1.0, Tkinter.END)
        self.text.config(state=Tkinter.DISABLED)
        self._lines = 0

    def append_text(self, lines):
        """
        Append input lines into the text area and scroll to the bottom.

        Additionally, raise the window on top of windows stack.

        @param lines iterable containing the lines to be added.
        """
        scroll = False
        self.text.config(state=Tkinter.NORMAL)
        for line in lines:
            scroll = True
            print TAG_PALETTE
            for ((tag, color), regexp) in zip(TAG_PALETTE, self._cached_filters):
                m = regexp.search(line)
                if m is None:
                    continue

                print tag, color, regexp
                self.text.insert(Tkinter.END, line[:m.start()])
                self.text.insert(Tkinter.END, line[m.start():m.end()], tag)
                self.text.insert(Tkinter.END, line[m.end():])

                self._lines += 1
                if self._lines <= self._limit:
                    break

                self.text.delete(1.0, '{0}+1l'.format(1.0))
                self._lines -= 1
                break
        self.text.config(state=Tkinter.DISABLED)

        if scroll:
            self.raise_()
            self.scroll_bottom()


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
            where = f.tell()
            line = f.readline()
            if not line:
                f.seek(where)

            yield line


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
            '-n', '--num-filters', dest='filters', default=NUM_FILTERS,
            type=int, help='Number of filters to apply to log file',
            metavar='FILTERS')
    parser.add_argument(
            '-l', '--limit', dest='limit', default=LINES_LIMIT, type=int,
            help='Number of lines to display in the text area', metavar='LIMIT')

    return parser


def _main():
    parser = _build_parser()
    args = parser.parse_args()

    filter_queue = Queue.Queue()
    lines_queue = Queue.Queue()

    gui = Gui(None, filters=args.filters, limit=args.limit)
    gui.register_listener('quit', quit, filter_queue, lines_queue)
    gui.register_listener('new_filter', apply_filters, gui, filter_queue)

    filter_thread_spawner = threading.Thread(
            target=filter_thread_spawner_body,
            args=(args.filename, args.interval, filter_queue, lines_queue))
    filter_thread_spawner.start()

    gui_updater = threading.Thread(
            target=gui_updater_body,
            args=(gui, lines_queue))
    gui_updater.start()

    gui.mainloop()


def _main1():
    # Create the communication queue shared between working thread and Gui
    com_queue = Queue.Queue()

    # Create and start the working thread
    stop = threading.Event()
    parser = _build_parser()
    args = parser.parse_args()
    worker = threading.Thread(
            target=file_observer_body,
            args=(args.filename, args.interval, args.filters, com_queue, stop))
    worker.start()

    # Create the gui, and enter the mainloop
    gui = Gui(com_queue)
    gui.mainloop()

    # graceful exit
    stop.set()
    worker.join()



if __name__ == '__main__':
    _main();
