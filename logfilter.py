#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import time
import threading
import Tkinter
import Queue
from itertools import imap
from argparse import ArgumentParser


STOP_MESSAGE = None
POLLING_INTERVAL = 100 # milliseconds
BATCH_LIMIT = 20
NULL_LISTENER = lambda *a, **kw: None


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

    def __init__(self, parent):
        Tkinter.Tk.__init__(self, parent) #super(Tkinter.Tk, self).__init__(parent)
        self.parent = parent

        self.on_quit_listener = (NULL_LISTENER, (), {})
        self.on_new_filter_listener = (NULL_LISTENER, (), {})

        self._initialize()

    def _initialize(self):
        """
        Initialize the layout of the GUI
        """
        container1 = Tkinter.Frame(self)
        self.filter_string = Tkinter.StringVar()
        entry = Tkinter.Entry(container1, textvariable=self.filter_string)
        button = Tkinter.Button(
                container1, text="Filter", command=self.on_button_click)
        container2 = Tkinter.Frame(self)
        self.text = Tkinter.Text(container2, bg='#222', fg='#eee')
        scrollbar = Tkinter.Scrollbar(container2)

        self.grid()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.bind('<Escape>', self.on_quit)

        # Container1
        container1.grid(row=0, column=0, sticky='EW')
        container1.grid_columnconfigure(0, weight=1)

        # Filter entry
        entry.grid(row=0, column=0, sticky='EW')
        entry.bind("<Return>", self.on_press_enter)

        # Filter button
        button.grid(row=0, column=1, sticky='EW')

        # Container 2
        container2.grid(row=1, column=0, sticky='NSEW')
        container2.grid_rowconfigure(0, weight=1)
        container2.grid_columnconfigure(0, weight=1)

        # Text area
        self.text.grid(row=0, column=0, sticky='NSEW')
        self.text.config(yscrollcommand=scrollbar.set)
        self.text.config(state=Tkinter.DISABLED)

        # Scrollbar
        scrollbar.grid(row=0, column=1, sticky='NS')
        scrollbar.config(command=self.text.yview)

    def on_quit(self, event):
        print 'Gui.on_quit'
        (func, args, kwargs) = self.on_quit_listener
        func(*args, **kwargs)
        self.quit()

    def on_button_click(self):
        print 'Gui.on_button_click'
        filter_string = self.filter_string.get()
        (func, args, kwargs) = self.on_new_filter_listener
        args = [filter_string] + list(args) 
        func(*args, **kwargs)

    def on_press_enter(self, event):
        print 'Gui.on_press_enter'
        filter_string = self.filter_string.get()
        (func, args, kwargs) = self.on_new_filter_listener
        args = [filter_string] + list(args) 
        func(*args, **kwargs)

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
            self.text.insert(Tkinter.END, line)
        self.text.config(state=Tkinter.DISABLED)

        if scroll:
            self.lift()
            self.text.yview(Tkinter.MOVETO, 1.0)


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
            yield line

            if not line:
                f.seek(where)


def first_not_none(iterable):
    """
    Extract the first not None element from input iterable
    """
    for item in iterable:
        if item:
            return item


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
        return first_not_none(
                imap(lambda r: line if r.match(line) else None, regexps))

    return wrapper


def filter_thread_spawner_body(filename, interval, filter_queue, lines_queue):
    """
    Spawn a file filter thread as soon as a filter is read from the queue.

    @param filename name of the file to pass to the working thread
    @param interval polling interval
    @param filter_queue message queue containing the filter to apply
    @param lines_queue message queue containing the lines to pass to the gui
    """
    print 'filter_thread_spawner_body: starting ..'
    stop = None
    worker = None
    while True:
        filter_string = filter_queue.get()
        print 'Received filter: {0}'.format(filter_string)
        if worker is not None:
            stop.set()
            worker.join()

        if filter_string == STOP_MESSAGE:
            break

        stop = threading.Event()
        worker = threading.Thread(
            target=file_observer_body,
            args=(filename, interval, (filter_string,), lines_queue, stop))
        worker.start()
    print 'filter_thread_spawner_body: exiting ..'


def file_observer_body(filename, interval, filters, queue, stop):
    """
    Body function of thread waiting for file content changes.

    The thread will poll `filename` every `iterval` seconds looking for new
    lines;  as soon as new lines are read from the file, these are filtered
    depeding on `filters`, and the one matching given criteria are put into the
    synchronized `queue`.

    @param filename filename to poll
    @param interval polling interval
    @param filters iterable of regexp filters to apply to the file content
    @param queue synchronized queue containing lines matching criteria
    @param stop `threading.Event` object, used to stop the thread.
    """
    print 'file_observer_body: starting ..'
    for line in imap(regexp_filter(*filters), tail_f(filename)):
        if stop.isSet():
            queue.put(STOP_MESSAGE)
            break

        if not line:
            time.sleep(interval)
            continue

        queue.put(line)
    print 'file_observer_body: exiting ..'


def gui_updater_body(gui, lines_queue):
    """
    Body function of the thread in charge of update the gui text area.

    @param gui `Gui` object to update.
    @param lines_queue message queue containing lines used to update the gui.
    """
    while True:
        line = lines_queue.get()
        print 'Received line: {0}'.format(line),
        if line == STOP_MESSAGE:
            break

        gui.schedule(gui.append_text, (line,))


def quit(filter_queue, lines_queue):
    """
    Invoked by the GUI when the main window has been closed.
    """
    print '__main__.quit'
    filter_queue.put(STOP_MESSAGE)
    lines_queue.put(STOP_MESSAGE)


def apply_filter(filter_string, gui, filter_queue):
    """
    Invoked by the GUI when a new filter is entered.

    Clear the gui and queue the received filter into the shared synchronized
    queue.

    @param gui `Gui` object to update.
    @param filter_string string filter
    @param filter_queue message queue shared with working thread.
    """
    print '__main__.apply_filter'
    gui.clear_text()
    filter_queue.put(filter_string)


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

    return parser


def _main():
    parser = _build_parser()
    args = parser.parse_args()
    
    filter_queue = Queue.Queue()
    lines_queue = Queue.Queue()

    gui = Gui(None)
    gui.register_listener('quit', quit, filter_queue, lines_queue)
    gui.register_listener('new_filter', apply_filter, gui, filter_queue)

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
            target=file_observer,
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
