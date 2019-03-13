##############################################################################
FoLiA Python Library
##############################################################################

This Python module provides an extensive library for parsing, creating and otherwise processing documents in the `Format
for Linguistic Annotation <https://proycon.github.io/folia>`_, aka `FoLiA <https://proycon.github.io/folia>`_. It has
been in active development since 2010 and used by numerous Natural Language Processing (NLP) tools.

This tutorial will introduce the FoLiA Python library. The FoLiA library provides an Application Programming Interface
for the reading, creation and manipulation of FoLiA XML documents. The library is written for Python 3.5 and above.

Prior to reading this document, it is recommended to first read the `FoLiA documentation
<https://folia.readthedocs.io>`_ itself and familiarise yourself with the format and underlying paradigm. It is
especially important to understand the way FoLiA handles sets/classes, declarations, common attributes such as
annotator/annotatortype and the distinction between various kinds of annotation categories such as token annotation and
span annotation.

This Python library is also the foundation of the `FoLiA Tools <https://github.com/proycon/foliatools>`_ collection,
which consists of various command line utilities to perform common tasks on FoLiA documents. If you’re merely interested
in performing a certain common task, such as a single query or conversion, you might want to check there if it contains
is a tool that does what you want already.

Contents:

.. toctree::
    :maxdepth: 3
    :glob:

    *

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

