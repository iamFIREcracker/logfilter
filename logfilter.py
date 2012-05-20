#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import time
import threading
import Tkinter
import Queue
from itertools import imap
from argparse import ArgumentParser


POLLING_INTERVAL = 100 # milliseconds
BATCH_LIMIT = 20


def extract_elemets(queue):
    """
    Extract elements from the synchronized queue, without blocking.

    @param queue synchronized blocking queue
    """
    limit = min(queue.qsize(), BATCH_LIMIT)
    try:
        while limit:
            yield queue.get(0)
    except Queue.Empty:
        return


class Gui(object):

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
        self.append_text(extract_elemets(self.queue))
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
    for line in imap(regexp_filter(*filters), tail_f(filename)):
        if stop.isSet():
            break

        if not line:
            time.sleep(interval)
            continue

        queue.put(line)


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
    gui = Gui(quit, apply_filter)

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
    _main1();
