#! /usr/bin/env python
# -*- coding: utf8 -*-

from __future__ import print_function


import os
import sys
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name = "FoLiA",
    version = "2.1.3", #edit LIBVERSION in __init__.py as well
    author = "Maarten van Gompel",
    author_email = "proycon@anaproy.nl",
    description = ("An extensive library for processing FoLiA documents. FoLiA stands for Format for Linguistic Annotation and is a very rich XML-based format used by various Natural Language Processing tools."),
    license = "GPL",
    keywords = "nlp computational_linguistics folia format",
    url = "https://github.com/proycon/foliapy",
    packages=['folia'],
    long_description=read('README.rst'),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Topic :: Text Processing :: Linguistic",
        "Programming Language :: Python :: 3",
        "Operating System :: POSIX",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    ],
    zip_safe=False,
    include_package_data=True,
    package_data = {'folia': ['tests/test.sh'] },
    install_requires=['lxml >= 2.2','rdflib'],
    entry_points = { 'console_scripts': [] }
)
