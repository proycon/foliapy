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

