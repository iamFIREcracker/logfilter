#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

from .logfilter import StringVar
from ._compact import tkinter


class Filter(object):
    """
    Proxy of `Tkinter.Entry`, with an additional method to easily set the
    content of the text entry.
    """

    def __init__(self, parent, **options):
        """
        Constructor.

        @param options the list of options for the `Tkinter.Entry` constructor;
                       an additional 'value' option could be specified in order
                       to set the initial value of the filter.
        """
        # Store the variable, otherwise the callback won't be invoked;  it
        # is like tkinter makes use of weakrefs
        self._var = StringVar(options.pop('value', ''))

        options.update(textvariable=self._var)
        self._proxy = tkinter.Entry(parent, **options)

    def __getattr__(self, name):
        return getattr(self._proxy, name)

    def set(self, value):
        """
        Sets the value of the filter.

        @param value the new filter value.
        """
        self._proxy.delete(0, tkinter.END)
        self._proxy.insert(0, value)


class FilterWithPlaceholder(object):
    """
    Extension (by composition!) of the `Filter` class, enabling users to
    specify a _placeholder_ for the widget (i.e. text appearing within the 
    widget whenever the widget is empty).
    
    This widget also exposes two custom events, namely `<<TypingIn>>` and
    `<<TypingOut``, published when someone starts / finish to type into the
    widget.
    """

    def __init__(self, parent, **options):
        """
        Constructor.

        @param options the list of options of the `Tkinter.Frame` constructor;
                       an additional 'placeholder' option could be specified
                       in order to set the placeholder for the filter.
        """
        self._placeholder = options.pop('placeholder', '')

        options.update(value=self._placeholder)
        self._proxy = Filter(parent, **options)

        def _on_focus_in_event(evt):
            if self.get() == self._placeholder:
                self.set('')
            self.event_generate('<<TypingIn>>')
        self._proxy.bind('<FocusIn>', _on_focus_in_event)

        def _on_focus_out_event(evt):
            if self.get() == '':
                self.set(self._placeholder)
            self.event_generate('<<TypingOut>>')
        self._proxy.bind('<FocusOut>', _on_focus_out_event)

    def __getattr__(self, name):
        return getattr(self._proxy, name)


class FilterBar(object):
    """
    An horizontal frame of filters enabling users to add/remove filters
    dynamically (i.e. a filter is automatically removes whenever its content
    is an empty string;  a filter is pushed on the right of the frame whenever
    someone starts typing into the left-most filter).
    """

    def __init__(self, parent, **kwargs):
        self._proxy = tkinter.Frame(parent, **kwargs)

        last_filter = FilterWithPlaceholder(self._proxy,
                                            placeholder='<Add new>',
                                            foreground='#999')
        last_filter.grid(row=0, column=0, sticky='EW')

        def _on_typing_in_event(evt):
            filter_ = FilterWithPlaceholder(self)
            filter_.grid(row=0, column=len(self._filters), sticky='EW')
            filter_.focus_force()

            def _on_typing_out_event(evt):
                if filter_.get() == '':
                    filter_.grid_remove()
            filter_.bind('<<TypingOut>>', _on_typing_out_event)

            last_filter.grid(row=0, column=len(self._filters) + 1)

            self._filters = self._filters[:-1] + [filter_] + [last_filter]
        last_filter.bind('<<TypingIn>>', _on_typing_in_event)
        self._filters = [last_filter]

    def __getattr__(self, name):
        return getattr(self._proxy, name)

    def get_filter_values(self):
        """
        Gets the values of the filters currently configured.

        @return the filter values.
        """
        return [f.get() for f in self._filters[:-1]] # Ignore placeholder