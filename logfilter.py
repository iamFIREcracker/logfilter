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

        self.on_quit_listener = NULL_LISTENER
        self.on_button_click_listener = NULL_LISTENER
        self.on_press_enter_listener = NULL_LISTENER

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
        self.quit()
        self.on_quit_listener()

    def on_button_click(self):
        self.on_button_click_listener(self.filter_string.get())

    def on_press_enter(self, event):
        self.on_press_enter_listener(self.filter_string.get())

    def schedule(self, function, *args, **kwargs):
        """
        Ask the event loop to schedule given function with arguments

        @param function function to schedule
        @param args positional arguments for the fuction
        @param kwargs named arguments for the function
        """
        self.after_idle(function, *args, **kwargs)

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


class Gui1(object):

    def __init__(self, queue):
        self.queue = queue
        self._initialize()

    def _initialize(self):
        self.root = Tkinter.Tk()
        container1 = Tkinter.Frame(self.root)
        self.filter_string = Tkinter.StringVar()
        entry = Tkinter.Entry(container1, textvariable=self.filter_string)
        container2 = Tkinter.Frame(self.root)
        self.text = Tkinter.Text(container2, bg='#222', fg='#eee')
        scrollbar = Tkinter.Scrollbar(container2)

        # Root
        self.root.grid()
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.bind('<Escape>', self.quit)

        # Container1
        container1.grid(row=0, column=0, sticky='EW')
        container1.grid_columnconfigure(0, weight=1)

        # Filter entry
        entry.grid(row=0, column=0, sticky='EW')
        entry.bind("<Return>", self.press_enter_cb)

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

        #scrollbar.pack(fill=Tkinter.Y, side=Tkinter.RIGHT)
        #self.text.pack(expand=True, fill=Tkinter.BOTH, side=Tkinter.LEFT)

    def quit(self, event):
        self.root.quit()

    def press_enter_cb(self, event):
        print 'Press enter cb' + self.filter_string.get()
        

    def mainloop(self):
        self.root.after(POLLING_INTERVAL, self._periodic)
        self.root.mainloop()

    def _periodic(self):
        self.append_text(extract_elemets(self.queue, BATCH_LIMIT))
        self.root.after(POLLING_INTERVAL, self._periodic)

    def append_text(self, lines):
        scroll = False
        self.text.config(state=Tkinter.NORMAL)
        for line in lines:
            scroll = True
            self.text.insert(Tkinter.END, line)
        self.text.config(state=Tkinter.DISABLED)

        if scroll:
            self.root.lift()
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

    @param *exps list of regular expressions representing filter criteria.
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


def filter_body(filename, interval, filters, queue, stop):
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
    for line in imap(regexp_filter(*filters), tail_f(filename)):
        if stop.isSet():
            queue.put(STOP_MESSAGE)
            break

        if not line:
            time.sleep(interval)
            continue

        queue.put(line)


def gui_update_body(gui, queue):
    """
    Body function of the thread in charge of update the gui text area.

    @param gui `Gui` object to update.
    @param queue synchronized queue containing lines used to update the gui.
    """
    while True:
        items = extract_elemets(BATCH_LIMIT)
        if not all(item != STOP_MESSAGE for item in items):
            break

        gui.schedule(gui.append_text, items)


def working_thread_listener(queue):
    """"""
    


def quit():
    """
    Invoked by the GUI when the main window has been closed.
    """


def apply_filter(queue):
    """
    Invoked by the GUI when a new filter is entered.

    @param queue message queue shared with working thread.
    """
    queue.put(None)


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
    gui = Gui(None)
    gui.mainloop()


def _main1():
    # Create the communication queue shared between working thread and Gui
    com_queue = Queue.Queue()

    # Create and start the working thread
    stop = threading.Event()
    parser = _build_parser()
    args = parser.parse_args()
    worker = threading.Thread(
            target=filter_body,
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
