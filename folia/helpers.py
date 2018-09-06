#!/usr/bin/env python
#-*- coding:utf-8 -*-

from __future__ import print_function, unicode_literals, division, absolute_import

from sys import stderr, version


def u(s, encoding = 'utf-8', errors='strict'):
    #ensure s is properly unicode.. wrapper for python 2.6/2.7,
    if version < '3':
        #ensure the object is unicode
        if isinstance(s, unicode):
            return s
        else:
            return unicode(s, encoding,errors=errors)
    else:
        #will work on byte arrays
        if isinstance(s, str):
            return s
        else:
            return str(s,encoding,errors=errors)

def b(s):
    #ensure s is bytestring
    if version < '3':
        #ensure the object is unicode
        if isinstance(s, str):
            return s
        else:
            return s.encode('utf-8')
    else:
        #will work on byte arrays
        if isinstance(s, bytes):
            return s
        else:
            return s.encode('utf-8')

def isstring(s): #Is this a proper string?
    return isinstance(s, str) or (version < '3' and isinstance(s, unicode))

def sum_to_n(n, size, limit=None): #from http://stackoverflow.com/questions/2065553/python-get-all-numbers-that-add-up-to-a-number
    """Produce all lists of `size` positive integers in decreasing order
    that add up to `n`."""
    if size == 1:
        yield [n]
        return
    if limit is None:
        limit = n
    start = (n + size - 1) // size
    stop = min(limit, n - size + 1) + 1
    for i in range(start, stop):
        for tail in sum_to_n(n - i, size - 1, i):
            yield [i] + tail
