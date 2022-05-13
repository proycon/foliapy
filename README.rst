FoLiA Library for Python
================================

.. image:: https://github.com/proycon/foliapy/actions/workflows/foliapy.yml/badge.svg?branch=master
    :target: https://github.com/proycon/foliapy/actions/

.. image:: http://readthedocs.org/projects/foliapy/badge/?version=latest
	:target: http://foliapy.readthedocs.io/en/latest/?badge=latest
	:alt: Documentation Status

.. image:: http://applejack.science.ru.nl/lamabadge.php/foliapy
   :target: http://applejack.science.ru.nl/languagemachines/

.. image:: https://www.repostatus.org/badges/latest/active.svg
   :alt: Project Status: Active – The project has reached a stable, usable state and is being actively developed.
   :target: https://www.repostatus.org/#active

.. image:: https://img.shields.io/pypi/v/folia
   :alt: Latest release in the Python Package Index
   :target: https://pypi.org/project/folia/

.. image:: https://zenodo.org/badge/DOI/10.5281/zenodo.594143.svg
   :target: https://doi.org/10.5281/zenodo.594143

This Python module provides an extensive library for parsing, creating and otherwise processing documents in the `Format
for Linguistic Annotation <https://proycon.github.io/folia>`_, aka `FoLiA <https://proycon.github.io/folia>`_. It has
been in active development since 2010 and used by numerous Natural Language Processing (NLP) tools.

This library used to be part of `PyNLPL <https://github.com/proycon/pynlpl>`_ (``pynlpl.formats.folia``), but has been
migrated to this standalone library in spring 2019.

Acknowledgement
----------------------------

FoLiA development is funded in the scope of the larger CLARIN-NL project and its successor CLARIAH.


The following modules are available:

* ``folia.main`` - The main library
* ``folia.setdefinition`` - A module for FoLiA Set Definitions
* ``folia.fql`` - Support for the FoLiA Query Language (FQL)


Installation
--------------------

Download and install the latest stable version directly from the Python Package
Index with ``pip install folia`` (or ``pip3`` for Python 3.7+ on most
systems). For global installations prepend ``sudo``.

Alternatively, clone this repository and run ``python setup.py install`` (or
``python3 setup.py install`` for Python 3 on most system. Prepend ``sudo`` for
global installations.

The Python FoLiA library is also included in our `LaMachine <https://proycon.github.io/LaMachine>`_ distribution.

Documentation
--------------------

API Documentation and tutorials can be found `here <https://foliapy.readthedocs.io/en/latest/>`_ .


