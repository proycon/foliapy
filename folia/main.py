#% -*- coding: utf-8 -*-
#----------------------------------------------------------------
# FoLiA Library for Python
#    by Maarten van Gompel
#   Centre for Language & Speech Technology, Radboud University Nijmegen
#   & KNAW Humanities Cluster
#
#   https://proycon.github.io/folia
#   httsp://github.com/proycon/foliapy
#   proycon AT anaproy DOT nl
#
#   Module for reading, editing and writing FoLiA XML
#
#   Licensed under GPLv3
#
#----------------------------------------------------------------

#pylint: disable=redefined-builtin,trailing-whitespace,superfluous-parens,bad-classmethod-argument,wrong-import-order,wrong-import-position,ungrouped-imports


import sys

from copy import copy, deepcopy
from datetime import datetime
from collections import OrderedDict
import inspect
import itertools
import glob
import os
import re
import io
import multiprocessing
import bz2
import gzip
import random
import unicodedata
from socket import getfqdn


from lxml import etree as ElementTree
from lxml.builder import ElementMaker

from io import StringIO,  BytesIO #pylint: disable=wrong-import-order,ungrouped-imports
from urllib.request import urlopen #pylint: disable=E0611,wrong-import-order,ungrouped-imports
stderr = sys.stderr
stdout = sys.stdout

from folia.helpers import u, isstring, sum_to_n
from folia.foliaset import SetDefinition, DeepValidationError
from folia import LIBVERSION



#foliaspec:version:FOLIAVERSION
#The FoLiA version
FOLIAVERSION = "2.5.3"

#foliaspec:namespace:NSFOLIA
#The FoLiA XML namespace
NSFOLIA = "http://ilk.uvt.nl/folia"

ElementTree.register_namespace("folia",NSFOLIA)
NSMAP = {None: NSFOLIA, 'xml' : "http://www.w3.org/XML/1998/namespace", 'xlink':"http://www.w3.org/1999/xlink"}
E = ElementMaker(namespace=NSFOLIA,nsmap=NSMAP)
RXE = ElementMaker(namespace="http://relaxng.org/ns/structure/1.0",nsmap={None:'http://relaxng.org/ns/structure/1.0' , 'folia': "http://ilk.uvt.nl/folia", 'xml' : "http://www.w3.org/XML/1998/namespace",'a':"http://relaxng.org/ns/annotation/0.9" })

nslen = len(NSFOLIA) + 2

if 'TMPDIR' in os.environ:
    TMPDIR = os.environ['TMPDIR']
else:
    TMPDIR = "/tmp/" #will be used for downloading temporary data (external subdocuments)

DOCSTRING_GENERIC_ATTRIBS = """    id (str): An ID for the element. IDs must be unique for the entire document. They may not contain colons or spaces, and must start with a letter. (they must adhere to XML's NCName type). This is a generic FoLiA attribute.
    set (str): The FoLiA set for this element. This is a generic FoLiA attribute.
    cls (str): The class for this element. This is a generic FoLiA attribute.
    processor (str): The ID of the processor of this annotation. This is a generic FoLiA attribute that replaces annotator/annotatortype.
    annotator (str): A name or ID for the annotator. This is a generic FoLiA attribute but is mostly replaced by ``processor``.
    annotatortype: Should be either ``AnnotatorType.MANUAL`` or ``AnnotatorType.AUTO``, indicating whether the annotation was performed manually or by an automated process. This is a generic FoLiA attribute but is mostly replaced by ``processor``.
    confidence (float): A value between 0 and 1 indicating the degree of confidence the annotator has that this the annotation is correct.. This is a generic FoLiA attribute.
    n (int): An index number to indicate the element is part of an sequence (does not affect the placement of the element).
    src (str): Speech annotation attribute, refers to a media file (audio/video) that this element describes. This is a generic FoLiA attribute.
    speaker (str): Speech annotation attribute: a name or ID of the speaker. This is a generic FoLiA attribute.
    begintime (str): Speech annotation attribute: the time (in ``hh:mm:ss.mmm`` format, relative to the media file in ``src``) when the audio that this element describes starts. This is a generic FoLiA attribute.
    endtime (str): Speech annotation attribute: the time (in ``hh:mm:ss.mmm`` format, relative to the media file in ``src``) when the audio that this element describes starts. This is a generic FoLiA attribute.
    textclass (str): Refers to the textclass from which this annotation is derived (defaults to "current")>. This is a generic FoLiA attribute.
    contents (list): Alternative for ``*args``, exists for purely syntactic reasons.
"""

DEFAULT_TEXT_SET = "https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/text.foliaset.ttl"
DEFAULT_PHON_SET = "https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/phon.foliaset.ttl"

ILLEGAL_UNICODE_CONTROL_CHARACTERS = {} #XML does not like unicode control characters
for ordinal in range(0x20):
    if chr(ordinal) not in '\t\r\n':
        ILLEGAL_UNICODE_CONTROL_CHARACTERS[ordinal] = None

class Mode:
    MEMORY = 0 #The entire FoLiA structure will be loaded into memory. This is the default and is required for any kind of document manipulation.
    XPATH = 1 #The full XML structure will be loaded into memory, but conversion to FoLiA objects occurs only upon querying. The full power of XPath is available.

#Serialisation form
class Form:
    NORMAL = 0
    EXPLICIT = 1 #Serialises in a more explicit way, not relying on defaults

class AnnotatorType:
    UNSET = None
    AUTO = "auto"
    MANUAL = "manual"

class ProcessorType(AnnotatorType): #superset of AnnotatorType
    GENERATOR = "generator"
    DATASOURCE = "datasource"

#foliaspec:attributes
#Defines all common FoLiA attributes (as part of the Attrib enumeration)
class Attrib:
    ID, CLASS, ANNOTATOR, CONFIDENCE, N, DATETIME, BEGINTIME, ENDTIME, SRC, SPEAKER, TEXTCLASS, METADATA, IDREF, SPACE, TAG = range(15)

#foliaspec:annotationtype
#Defines all annotation types (as part of the AnnotationType enumeration)
class AnnotationType:
    TEXT, TOKEN, DIVISION, PARAGRAPH, HEAD, LIST, FIGURE, WHITESPACE, LINEBREAK, SENTENCE, POS, LEMMA, DOMAIN, SENSE, SYNTAX, CHUNKING, ENTITY, CORRECTION, ERRORDETECTION, PHON, SUBJECTIVITY, MORPHOLOGICAL, EVENT, DEPENDENCY, TIMESEGMENT, GAP, QUOTE, NOTE, REFERENCE, RELATION, SPANRELATION, COREFERENCE, SEMROLE, METRIC, LANG, STRING, TABLE, STYLE, PART, UTTERANCE, ENTRY, TERM, DEFINITION, EXAMPLE, PHONOLOGICAL, PREDICATE, OBSERVATION, SENTIMENT, STATEMENT, ALTERNATIVE, RAWCONTENT, COMMENT, DESCRIPTION, HYPHENATION, HIDDENTOKEN, MODALITY, EXTERNAL, HSPACE, ETYMOLOGY = range(59)



class NoSuchAnnotation(Exception):
    """Exception raised when the requested type of annotation does not exist for the selected element"""

class NoSuchText(Exception):
    """Exception raised when the requested type of text content does not exist for the selected element"""

class NoSuchPhon(Exception):
    """Exception raised when the requested type of phonetic content does not exist for the selected element"""

class InconsistentText(Exception):
    """Exception raised when the the text of a structural element is inconsistent with text on deeper levels"""

class DuplicateAnnotationError(Exception):
    pass

class DuplicateIDError(Exception):
    """Exception raised when an identifier that is already in use is assigned again to another element"""

class InvalidReference(Exception):
    """Exception raised when an identifier points to something that does not exist"""

class NoCommonAncestor(Exception):
    """Exception raised when two elements do not share a common ancestor"""

class NoDefaultError(Exception):
    pass

class DeclarationError(Exception):
    """Exception raised when there is an issue with missing declarations"""

class UnresolvableTextContent(Exception):
    pass

class MalformedXMLError(Exception):
    pass

class ParseError(Exception):
    def __init__(self, msg, cause=None):
        self.cause = cause
        Exception.__init__(self, msg)


class ModeError(Exception):
    pass

class MetaDataError(Exception):
    pass

class DocumentNotLoaded(Exception): #for alignments to external documents
    pass

class GenerateIDException(Exception):
    pass

class CorrectionHandling:
    EITHER,CURRENT, ORIGINAL = range(3)

class Annotator:
    """Links to a Processor"""
    def __init__(self, processor_id, doc):
        if isinstance(processor_id, Processor): processor_id = processor_id.id #some flexibility, allow passing either Processor instances or ID as str
        self.processor_id = processor_id
        self.doc = doc

    def __call__(self):
        return self.doc.provenance[self.processor_id]

    def __str__(self):
        return self().name

class Processor:
    def __init__(self, name, type=ProcessorType.AUTO, id=None, version=None, document_version=None, folia_version=None, command=None, host=None, user=None, begindatetime=None, enddatetime=None, src=None, format=None,resourcelink=None, parent=None, metadata=None):
        self.name = name
        if id is None:
            self.id = "proc." + makencname(self.name.lower()) + "."  + ("%08x" % random.getrandbits(32)) #assign ID with random elements if none provided
        else:
            self.id = id
        if type not in (ProcessorType.MANUAL, ProcessorType.AUTO, ProcessorType.GENERATOR, ProcessorType.DATASOURCE): #superset of AnnotatorType
            raise ParseError("Invalid processor type: " + str(type))
        self.type = type
        self.version = str(version) if version is not None else None
        self.folia_version = str(folia_version) if folia_version is not None else None
        self.document_version = str(document_version) if document_version is not None else None
        self.command = command
        self.host = host
        self.user = user
        self.begindatetime = begindatetime
        self.enddatetime = enddatetime
        self.processors = []
        if metadata:
            self.metadata = NativeMetaData(**metadata)
        else:
            self.metadata = NativeMetaData()
        self.src = src
        self.format = format
        self.resourcelink = resourcelink
        self.parent = parent

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if key in ('type','command','host','user','begindatetime','enddatetime','src','format','resourcelink') and value:
                setattr(self, key, value)
            elif key in ('version','folia_version','document_version') and value:
                setattr(self, key, str(value))

    def insert(self, index, processor):
        assert isinstance(processor, Processor)
        self.processors.insert(index, processor)
        processor.parent = self

    def append(self, processor):
        assert isinstance(processor, Processor)
        self.processors.append(processor)
        processor.parent = self

    @staticmethod
    def create(*args, **kwargs):
        """Creates (instantiates) a new processor and tries to detect as much as possible automatically. Example in combination with the instantiation of a new document::

            doc = folia.Document(id="example", processor=Processor.create(name="my-tool", version="0.1"))

        """
        try:
            executable = os.path.basename(sys.argv[0])
            kwargs['command'] = " ".join([executable] + sys.argv[1:])
        except:
            executable = None

        kwargs['host'] = getfqdn()
        kwargs['begindatetime'] = datetime.now()
        kwargs['folia_version'] = FOLIAVERSION
        if 'USER' in os.environ:
            kwargs['user'] = os.environ['USER']

        if 'name' not in kwargs:
            if executable:
                kwargs['name'] = executable
            else:
                raise ValueError("Unable to infer a name for the processor, please specify name= parameter")

        processor = Processor(**kwargs)

        if 'generator' not in kwargs or not kwargs['generator']:
            #Add a subprocessor with generator information about this FoLiA library
            try:
                #ensure the subprocessor doesn't already exist
                processor[processor.id+'.generator']
            except KeyError: #good, this is what we want:
                if processor.id+'.generator' not in processor:
                    processor.append(Processor(id=processor.id+'.generator', name="foliapy", type=ProcessorType.GENERATOR, version=LIBVERSION, folia_version=FOLIAVERSION, src="https://github.com/proycon/foliapy"))
        return processor





    @classmethod
    def parsexml(Class, node): #pylint: disable=bad-classmethod-argument
        if node.tag == '{' + NSFOLIA + '}processor':
            begindatetime = node.attrib.get('begindatetime', None)
            if begindatetime: begindatetime = parse_datetime(begindatetime)
            enddatetime = node.attrib.get('enddatetime', None)
            if enddatetime: enddatetime = parse_datetime(enddatetime)
            processor = Processor(node.attrib['name'],id=node.attrib['{http://www.w3.org/XML/1998/namespace}id'],  type=node.attrib.get('type', ProcessorType.AUTO), version=node.attrib.get('version',None), document_version=node.attrib.get('document_version', None), folia_version=node.attrib.get('folia_version', None), command=node.attrib.get('command', None),host=node.attrib.get('host', None),user=node.attrib.get('user', None),begindatetime=begindatetime,enddatetime=enddatetime, resourcelink=node.attrib.get('resourcelink', None), src=node.attrib.get('src',None), format=node.attrib.get('format',None))
            for subnode in node:
                if not isinstance(subnode, ElementTree._Comment): #pylint: disable=protected-access
                    if subnode.tag == '{' + NSFOLIA + '}processor':
                        processor.processors.append(Processor.parsexml(subnode))
                    elif subnode.tag == '{' + NSFOLIA + '}meta':
                        if subnode.text:
                            processor.metadata[subnode.attrib['id']] = subnode.text
                    else:
                        raise ParseError("Unexpected element in Processor: " + subnode.tag)
            return processor
        raise ValueError("Invalid node passed" + node.tag)

    def xml(self):
        """Serialises the processor to XML"""
        attribs = {}
        attribs['{http://www.w3.org/XML/1998/namespace}id'] = self.id
        for key in ('name','type', 'version','document_version', 'folia_version','command','host','user','begindatetime','enddatetime', 'src', 'format', 'resourcelink'):
            if hasattr(self,key) and getattr(self,key) is not None:
                attribs[key] = getattr(self, key)
                if isinstance(attribs[key], datetime):
                    attribs[key] = attribs[key].strftime("%Y-%m-%dT%H:%M:%S")
        elements = []
        if isinstance(self.metadata, NativeMetaData): #serialize metadata on the processor
            for key, value in self.metadata.items():
                elements.append(E.meta(value,id=key) )
        #serialize subprocessors
        for subprocessor in self:
            elements.append(subprocessor.xml())
        return E.processor(*elements, **attribs)

    def json(self):
        """Serialises the processor to a dictionary suitable for JSON output"""
        jsonnode = {}
        jsonnode['id'] = self.id
        for key in ('name','type', 'version','document_version', 'folia_version','command','host','user','begindatetime','enddatetime', 'src','format','resourcelink'):
            if hasattr(self,key) and getattr(self,key) is not None:
                jsonnode[key] = getattr(self, key)
                if isinstance(jsonnode[key], datetime):
                    jsonnode[key] = jsonnode[key].strftime("%Y-%m-%dT%H:%M:%S")
        jsonnode['processors'] = []
        jsonnode['metadata'] = {}
        if isinstance(self.metadata, NativeMetaData): #serialize metadata on the processor
            for key, value in self.metadata.items():
                jsonnode['metadata'][key] = value
        #serialize subprocessors
        for subprocessor in self:
            jsonnode['processors'].append(subprocessor.json())
        return jsonnode

    def __getitem__(self, id):
        for processor in self.processors:
            if processor.id == id:
                return processor
            else:
                #recursive
                try:
                    return processor[id]
                except KeyError:
                    pass
        raise KeyError(id)

    def __len__(self):
        return len(self.processors)

    def __iter__(self):
        for processor in self.processors:
            yield processor

    def __bool__(self):
        return True

    def last(self):
        if len(self.processors) > 0:
            return self.processors[-1]
        else:
            raise ValueError("No processors")

    def match(self, processor):
        """Check if this processor matches against a dictionary of processor attributes (all supplied attributes must match and that suffices)"""
        if isinstance(processor, Processor):
            processor = processor.json() #we need a dict
        assert isinstance(processor, dict)
        for key, value in processor.items():
            if key not in ('parent','processors') and getattr(self, key) != value:
                return False
        return True

class Provenance:
    def __init__(self):
        self.processors = []

    def append(self, processor):
        assert isinstance(processor, Processor)
        self.processors.append(processor)
        return processor

    def insert(self, index, processor):
        assert isinstance(processor, Processor)
        self.processors.insert(index, processor)
        processor.parent = self

    def __getitem__(self, id):
        if isinstance(id, Processor):
            id = id.id #let's not be too picky about whether we get an ID or a Processor instance
        elif not isinstance(id, str):
            raise Exception("Expected Processor instance or processor ID, got " + repr(id))


        for processor in self.processors:
            if processor.id == id:
                return processor
            else:
                #recurse into subprocessors
                try:
                    return processor[id]
                except KeyError:
                    pass
        raise KeyError("No such processor in provenance chain: " + str(id))


    def __contains__(self, id):
        if isinstance(id, Processor): id = id.id
        for processor in self.processors:
            if processor.id == id:
                return True
            else:
                try:
                    return processor[id]
                except KeyError:
                    pass
        return False

    def __len__(self):
        return len(self.processors)

    def __iter__(self):
        for processor in self.processors:
            yield processor

    def __bool__(self):
        return bool(len(self.processors))

    def last(self):
        if len(self.processors) > 0:
            return self.processors[-1]
        else:
            raise ValueError("No processors")

    def xml(self):
        processors = [ processor.xml() for processor in self ]
        return E.provenance(*processors)

    def xmlstring(self, pretty_print=False, form = Form.NORMAL):
        """Serialises this FoLiA element and all its contents to XML."""
        return str(ElementTree.tostring(self.xml(form=form), xml_declaration=False, pretty_print=pretty_print, encoding='utf-8'),'utf-8')

    def json(self):
        return { "processors": [ processor.json() for processor in self ] }

def checkversion(version, REFVERSION=FOLIAVERSION):
    """Checks FoLiA version, returns 1 if the document is newer than the library, -1 if it is older, 0 if it is equal"""
    try:
        for refversion, docversion in zip([int(x) for x in REFVERSION.split('.')], [int(x) for x in version.split('.')]):
            if docversion > refversion:
                return 1 #doc is newer than library
            elif docversion < refversion:
                return -1 #doc is older than library
        return 0 #versions are equal
    except ValueError:
        raise ValueError("Unable to parse document FoLiA version, invalid syntax")

def parsetime(s):
    """Internal function to parse the time parses time in HH:MM:SS.mmm format.

    Returns:
        a four-tuple ``(hours,minutes,seconds,milliseconds)``
    """
    try:
        fields = s.split('.')
        subfields = fields[0].split(':')
        H = int(subfields[0])
        M = int(subfields[1])
        S = int(subfields[2])
        if len(subfields) > 3:
            m = int(subfields[3])
        else:
            m = 0
        if len(fields) > 1:
            m = int(fields[1])
        return (H,M,S,m)
    except:
        raise ValueError("Invalid timestamp, must be in HH:MM:SS.mmm format: " + s)


def norm_spaces(s):
    r"""Normalize spaces, splits on all kinds of whitespace and rejoins. Also removes control characters"""
    #remove control characters
    s = "".join(c for c in s if unicodedata.category(c)[0]!="C" or c in ('\n','\t'))
    return " ".join(( x for x in re.split(r"\s+",s) if x))

def is_space(c):
    return c in (" ","\n","\r","\t", chr(0x00a0), chr(0x1680), chr(0x2000), chr(0x2001), chr(0x2003),chr(0x2004), chr(0x2005), chr(0x2006), chr(0x2007), chr(0x2008), chr(0x2009), chr(0x200a), chr(0x2028), chr(0x2029), chr(0x202f), chr(0x205f), chr(0x3000))

def postprocess_spaces(s):
    r"""Postprocessing for spaces, translates temporary \0 bytes to spaces if they are are not preceeded by whitespace"""
    s2 = ""
    for i, c in enumerate(s):
        if c == "\0":
            if i > 0 and not is_space(s[i-1]):
                s2 += " "
            #null byte is dropped otherwise
        else:
            s2 += c
    return s2


def parse_datetime(s): #source: http://stackoverflow.com/questions/2211362/how-to-parse-xsddatetime-format
    """Returns (datetime, tz offset in minutes) or (None, None)."""
    m = re.match(r""" ^
        (?P<year>-?[0-9]{4}) - (?P<month>[0-9]{2}) - (?P<day>[0-9]{2})
        T (?P<hour>[0-9]{2}) : (?P<minute>[0-9]{2}) : (?P<second>[0-9]{2})
        (?P<microsecond>\.[0-9]{1,6})?
        (?P<tz>
        Z | (?P<tz_hr>[-+][0-9]{2}) : (?P<tz_min>[0-9]{2})
        )?
        $ """, s, re.X)
    if m is not None:
        values = m.groupdict()
        #if values["tz"] in ("Z", None):
        #    tz = 0
        #else:
        #    tz = int(values["tz_hr"]) * 60 + int(values["tz_min"])
        if values["microsecond"] is None:
            values["microsecond"] = 0
        else:
            values["microsecond"] = values["microsecond"][1:]
            values["microsecond"] += "0" * (6 - len(values["microsecond"]))
        values = dict((k, int(v)) for k, v in values.items() if not k.startswith("tz"))
        try:
            return datetime(**values) # , tz
        except ValueError:
            pass
    return None


def xmltreefromstring(s):
    """Internal function, deals with different Python versions, unicode strings versus bytes, and with the leak bug in lxml"""
    if isinstance(s,str):
        s = s.encode('utf-8')
    try:
        return ElementTree.parse(BytesIO(s), ElementTree.XMLParser(collect_ids=False, huge_tree=True))
    except TypeError:
        return ElementTree.parse(BytesIO(s), ElementTree.XMLParser()) #older lxml, may leak!!!!

def xmltreefromfile(filename):
    """Internal function to read an XML file"""
    try:
        return ElementTree.parse(filename, ElementTree.XMLParser(collect_ids=False, huge_tree=True))
    except TypeError:
        return ElementTree.parse(filename, ElementTree.XMLParser()) #older lxml, may leak!!

def annotationtype2str(annotationtype):
    """Find the 'label' for the declarations dynamically (aka: AnnotationType --> String)"""
    assert annotationtype is not None
    for key, value in vars(AnnotationType).items():
        if value == annotationtype:
            return key
    return None

def str2annotationtype(s):
    """Find annotation type by label dynamically (aka: String --> AnnotationType)"""
    s = s.upper()
    for key, value in vars(AnnotationType).items():
        if key.upper() == s:
            return value
    raise ValueError

def commonancestors(Class, *args):
    """Generator function to find common ancestors of a particular type for any two or more FoLiA element instances.

    The function produces all common ancestors of the type specified, starting from the closest one up to the most distant one.

    Parameters:
        Class: The type of ancestor to find, should be the :class:`AbstractElement` class or any subclass thereof (not an instance!). May also be a tuple of classes.
        *args: The elements to find the common ancestors of, elements are instances derived from :class:`AbstractElement`

    Yields:
        instance derived from :class:`AbstractElement`: A common ancestor of the arguments, an instance of the specified ``Class``.
    """

    commonancestors = None #pylint: disable=redefined-outer-name
    for sibling in args:
        ancestors = list( sibling.ancestors(Class) )
        if commonancestors is None:
            commonancestors = copy(ancestors)
        else:
            removeancestors = []
            for a in commonancestors: #pylint: disable=not-an-iterable
                if not a in ancestors:
                    removeancestors.append(a)
            for a in removeancestors:
                commonancestors.remove(a)
    if commonancestors:
        for commonancestor in commonancestors:
            yield commonancestor

class AbstractElement:
    """Abstract base class from which all FoLiA elements are derived.

    This class implements many generic methods that are available on all FoLiA elements.

    To see if an element is a FoLiA element, as opposed to any other python object, do::

        isinstance(x, AbstractElement)

    Generic FoLiA attributes can be accessed on all instances derived from this class:

    * ``element.id``        (str) - The unique identifier of the element
    * ``element.set``       (str) - The set the element pertains to.
    * ``element.cls``       (str) - The assigned class, i.e. the actual value of \
    the annotation, defined in the set.  Classes correspond with tagsets in this case of many annotation types. \
    Note that since *class* is already a reserved keyword in python, the library consistently uses ``cls`` everywhere.
    * ``element.annotator`` (str) - The name or ID of the annotator who added/modified this element
    * ``element.annotatortype`` - The type of annotator, can be either ``folia.AnnotatorType.MANUAL`` or ``folia.AnnotatorType.AUTO``
    * ``element.confidence`` (float) - A confidence value expressing
    * ``element.datetime``  (datetime.datetime) - The date and time when the element was added/modified.
    * ``element.n``         (str) - An ordinal label, used for instance in enumerated list contexts, numbered sections, etc..

    The following generic attributes are specific to a speech context:

    * ``element.src``       (str) - A URL or filename referring the an audio or video file containing the speech. Access this attribute using the ``element.speaker_src()`` method, as it is inheritable from ancestors.
    * ``element.speaker``   (str) -  The name of ID of the speaker. Access this attribute using the ``element.speech_speaker()`` method, as it is inheritable from ancestors.
    * ``element.begintime`` (4-tuple) - The time in the above source fragment when the phonetic content of this element starts, this is a ``(hours, minutes,seconds,milliseconds)`` tuple.
    * ``element.endtime``   (4-tuple) - The time in the above source fragment when the phonetic content of this element ends, this is a ``(hours, minutes,seconds,milliseconds)`` tuple.

    Not all attributes are allowed, unset or unavailable attributes will always default to ``None``.

    Note:
        This class should never be instantiated directly, as it is abstract!

    See also:
        :meth:`AbstractElement.__init__`
    """

    def __init__(self, doc, *args, **kwargs):
        """Constructor for most FoLiA elements.

        Parameters:
            doc (:class:`Document`): The FoLiA document this element will pertain to. It will not be automatically added though.
            *args: Child elements to add to this element, mostly instances derived from :class:`AbstractElement`

        Keyword Arguments:
        {generic_attribs}
            generate_id_in (:class:`AbstractElement`): Instead of providing an explicit ID, the library can attempt to automatically generate an ID based on a convention where suffixes are applied to the ID of the parent element. This keyword argument takes the intended parent element (an instance derived from :class:`AbstractElement`) as value.


        Not all of the generic FoLiA attributes are applicable to all elements. The class properties ``REQUIRED_ATTRIBS`` and ``OPTIONAL_ATTRIBS`` prescribe which are required or allowed.

        """.format(generic_attribs=DOCSTRING_GENERIC_ATTRIBS)


        if not isinstance(doc, Document) and not doc is None:
            raise Exception("Expected first parameter to be instance of Document, got " + str(type(doc)))
        self.doc = doc
        self.parent = None
        self.data = []


        kwargs = self.parsecommonarguments(doc, **kwargs)
        for child in args:
            self.append(child)
        if 'contents' in kwargs:
            if isinstance(kwargs['contents'], list):
                for child in kwargs['contents']:
                    self.append(child)
            else:
                self.append(kwargs['contents'])
            del kwargs['contents']

        for key in kwargs:
            if key[0] == '{': #this is a parameter in a different alien namespace, ignore it
                continue
            else:
                raise ValueError("Parameter '" + key + "' not supported by " + self.__class__.__name__)


    def __getattr__(self, attr):
        """Internal method"""
        #overriding getattr so we can get defaults here rather than needing a copy on each element, saves memory
        if attr in ('set','cls','processor', 'confidence','datetime','n','href','src','speaker','begintime','endtime','xlinktype','xlinktitle','xlinklabel','xlinkrole','xlinkshow','label', 'textclass', 'metadata','exclusive', 'preservespace'):
            return None
        elif attr == 'tags':
            return []
        elif attr == 'annotator':
            if self.processor:
                return self.processor.name
            else:
                return None
        elif attr == 'annotatortype':
            if self.processor:
                return self.processor.type
            else:
                return None
        else:
            return super(AbstractElement, self).__getattribute__(attr)


    #def __del__(self):
    #    if self.doc and self.doc.debug:
    #        print >>stderr, "[FoLiA DEBUG] Removing " + repr(self)
    #    for child in self.data:
    #        del child
    #    self.doc = None
    #    self.parent = None
    #    del self.data

    def parsecommonarguments(self, doc, **kwargs):
        """Internal function to parse common FoLiA attributes and sets up the instance accordingly. Do not invoke directly."""

        self.doc = doc #The FoLiA root document
        annotationtype = self.ANNOTATIONTYPE
        required = self.REQUIRED_ATTRIBS
        allowed = self.OPTIONAL_ATTRIBS

        if required is None:
            required = tuple()
        if allowed is None:
            allowed = tuple()

        supported = required + allowed


        if 'generate_id_in' in kwargs:
            try:
                kwargs['id'] = kwargs['generate_id_in'].generate_id(self.__class__)
            except GenerateIDException:
                pass #ID could not be generated, just skip
            del kwargs['generate_id_in']



        if 'id' in kwargs:
            if Attrib.ID not in supported:
                raise ValueError("ID is not supported on " + self.__class__.__name__)
            isncname(kwargs['id'])
            self.id = kwargs['id']
            del kwargs['id']
        elif Attrib.ID in required:
            raise ValueError("ID is required for " + self.__class__.__name__)
        else:
            self.id = None


        if 'set' in kwargs:
            #a set was specified
            if Attrib.CLASS not in supported and not self.SETONLY:
                raise ValueError("Set is not supported on " + self.__class__.__name__)
            if kwargs['set']:
                self.set = kwargs['set']
            else:
                #the specified set was None (no set) or False (any set),
                kwargs['set'] = False #deferred until next if block
            if doc and self.set and self.set in doc.alias_set:
                self.set = doc.alias_set[self.set]
        if 'set' not in kwargs or kwargs['set'] is False and annotationtype is not None:
            #no, set explicitly specified; check declarations (both with and without provenance) for a default set
            try:
                defaultset = doc.defaultset(annotationtype)
            except NoSuchAnnotation:
                #no such annotation is declared, that's fine and very common, it just means we don't have a default set and continue with set = None (i.e. a setless annotation)
                defaultset = False
            if defaultset is not False: #caution: None is a valid set so we check explicitly!
                self.set = defaultset
            elif Attrib.CLASS in supported:
                if doc.FOLIA1:
                    self.set ="undefined" #FoLiA <2.0 allowed a 'default' undefined set, FoLiA 2.0 doesn't
                    if not doc.keepversion: #convert to the new default sets
                        if isinstance(self, TextContent):
                            self.set = DEFAULT_TEXT_SET
                        if isinstance(self, PhonContent):
                            self.set = DEFAULT_PHON_SET
                else:
                    self.set = None
        if Attrib.CLASS in required and not self.set:
            raise ValueError("Set is required for " + self.__class__.__name__)

        if 'set' in kwargs:
            del kwargs['set']

        if not self.set:
            #We define a default set for TextContent and PhonContent in FoLiA v2
            if isinstance(self, TextContent):
                self.set = DEFAULT_TEXT_SET
            if isinstance(self, PhonContent):
                self.set = DEFAULT_PHON_SET

        self.checkdeclaration()

        if 'class' in kwargs:
            if not Attrib.CLASS in supported:
                raise ValueError("Class is not supported for " + self.__class__.__name__)
            self.cls = kwargs['class']
            del kwargs['class']
        elif 'cls' in kwargs:
            if not Attrib.CLASS in supported:
                raise ValueError("Class is not supported on " + self.__class__.__name__)
            self.cls = kwargs['cls']
            del kwargs['cls']
        elif Attrib.CLASS in required:
            raise ValueError("Class is required for " + self.__class__.__name__)

        if self.cls and self.set is False:
            #we have a class but no set!
            if doc and doc.autodeclare:
                #If autodeclare is enabled and it is an old FoLiA v1 document,
                #then we can automatically declare the 'undefined' set or new-style default text/phon sets
                if doc.FOLIA1:
                    if annotationtype == AnnotationType.TEXT:
                        if (annotationtype, DEFAULT_TEXT_SET) not in doc.annotations: #prevent duplicates
                            if doc.debug >= 1: print("[FoLiA DEBUG] Auto-declaring text with default set for FoLiA v1 document", file=stderr)
                            doc.annotations.append( (annotationtype, DEFAULT_TEXT_SET) )
                            doc.annotationdefaults[annotationtype] = {DEFAULT_TEXT_SET: {} }
                        self.set = DEFAULT_TEXT_SET
                    elif annotationtype == AnnotationType.PHON:
                        if (annotationtype, DEFAULT_PHON_SET) not in doc.annotations: #prevent duplicates
                            if doc.debug >= 1: print("[FoLiA DEBUG] Auto-declaring phon with default set for FoLiA v1 document", file=stderr)
                            doc.annotations.append( (annotationtype, DEFAULT_PHON_SET) )
                            doc.annotationdefaults[annotationtype] = {DEFAULT_PHON_SET: {} }
                        self.set = DEFAULT_PHON_SET
                    else:
                        if (annotationtype, 'undefined') not in doc.annotations: #prevent duplicates
                            if doc.debug >= 1: print("[FoLiA DEBUG] Auto-declaring undefined set for FoLiA v1 document", file=stderr)
                            doc.annotations.append( (annotationtype, 'undefined') )
                            doc.annotationdefaults[annotationtype] = {'undefined': {} }
                        self.set = 'undefined'
            else:
                raise DeclarationError("Set is required for " + self.__class__.__name__ + " <"+self.__class__.XMLTAG+"> . Class '" + self.cls + "' assigned without set and no default set found in declaration.")


        if 'processor' in kwargs:
            if Attrib.ANNOTATOR not in supported:   #(ANNOTATOR attribute also subsumes Processor)
                raise ValueError("Processor is not supported for " + self.__class__.__name__)
            self.setprocessor(kwargs['processor']) #this also takes care of adding an annotator to the declarations
            #Both processor and annotator are specified! This is valid only if the annotator equals the processor name!
            if 'annotator' in kwargs and kwargs.annotator:
                if kwargs['annotator'] != self.processor.name:
                    raise ValueError("Annotator attribute " + kwargs['annotator'] + " does not equal processor name (" + self.processor.name + ")")
            if 'annotatortype' in kwargs and kwargs.annotator:
                if kwargs['annotatortype'] != self.processor.type:
                    raise ValueError("Annotatortype attribute " + kwargs['annotatortype'] + " does not equal processor type (" + self.processor.type + ")")
            del kwargs['processor']
        elif doc and annotationtype in doc.annotators and self.set in doc.annotators[annotationtype] and doc.annotators[annotationtype][self.set] and Attrib.ANNOTATOR in supported:
            try:
                self.processor = doc.getdefaultprocessor(annotationtype,self.set)
            except NoDefaultError as e:
                if doc.fixunassignedprocessor:
                    for processor in doc.getprocessors(annotationtype, self.set): #iterate over all
                        self.processor = processor #assign the first one
                        break
                else:
                    raise e

        if self.processor is None:
            #old behavour without provenance (FoLiA <= 1.5), still valid in FoLiA v2 as well
            if 'annotator' in kwargs:
                if Attrib.ANNOTATOR not in supported:
                    raise ValueError("Annotator is not supported for " + self.__class__.__name__)
                self.annotator = kwargs['annotator']
                del kwargs['annotator']
            elif doc and annotationtype in doc.annotationdefaults and self.set in doc.annotationdefaults[annotationtype] and 'annotator' in doc.annotationdefaults[annotationtype][self.set]:
                self.annotator = doc.annotationdefaults[annotationtype][self.set]['annotator']
            elif Attrib.ANNOTATOR in required:
                raise ValueError("Annotator is required for " + self.__class__.__name__)


            if 'annotatortype' in kwargs:
                if not Attrib.ANNOTATOR in supported:
                    raise ValueError("Annotatortype is not supported for " + self.__class__.__name__)
                if kwargs['annotatortype'] == AnnotatorType.AUTO:
                    self.annotatortype = AnnotatorType.AUTO
                elif kwargs['annotatortype']  == AnnotatorType.MANUAL:
                    self.annotatortype = AnnotatorType.MANUAL
                else:
                    raise ValueError("annotatortype must be 'auto' or 'manual', got "  + repr(kwargs['annotatortype']))
                del kwargs['annotatortype']
            elif doc and annotationtype in doc.annotationdefaults and self.set in doc.annotationdefaults[annotationtype] and 'annotatortype' in doc.annotationdefaults[annotationtype][self.set]:
                self.annotatortype = doc.annotationdefaults[annotationtype][self.set]['annotatortype']
            elif Attrib.ANNOTATOR in required:
                raise ValueError("Annotatortype is required for " + self.__class__.__name__)
        else:
            if 'annotator' in kwargs:
                if kwargs['annotator'] != self.processor.name:
                    if doc and doc.autodeclare:
                        self.annotator2processor(kwargs['annotator'], kwargs.get('annotatortype', AnnotatorType.AUTO))
                    else:
                        raise DeclarationError("Autodeclarations are disabled but an annotator (" + str(kwargs['annotator']) + ") was specified that differs from the one in the declared processor for this annoation type: " + repr(self))
                del kwargs['annotator']
            if 'annotatortype' in kwargs:
                del kwargs['annotatortype']

        if 'confidence' in kwargs:
            if not Attrib.CONFIDENCE in supported:
                raise ValueError("Confidence is not supported")
            if kwargs['confidence'] is not None:
                try:
                    self.confidence = float(kwargs['confidence'])
                    assert self.confidence >= 0.0 and self.confidence <= 1.0
                except:
                    raise ValueError("Confidence must be a floating point number between 0 and 1, got " + repr(kwargs['confidence']) )
            del kwargs['confidence']
        elif Attrib.CONFIDENCE in required:
            raise ValueError("Confidence is required for " + self.__class__.__name__)



        if 'n' in kwargs:
            if not Attrib.N in supported:
                raise ValueError("N is not supported for " + self.__class__.__name__)
            self.n = kwargs['n']
            del kwargs['n']
        elif Attrib.N in required:
            raise ValueError("N is required for " + self.__class__.__name__)

        if kwargs.get('datetime'):
            if not Attrib.DATETIME in supported:
                raise ValueError("Datetime is not supported")
            if isinstance(kwargs['datetime'], datetime):
                self.datetime = kwargs['datetime']
            else:

                #try:
                self.datetime = parse_datetime(kwargs['datetime'])
                #except:
                #    raise ValueError("Unable to parse datetime: " + str(repr(kwargs['datetime'])))
            del kwargs['datetime']
        elif Attrib.DATETIME in supported and doc and annotationtype in doc.annotationdefaults and self.set in doc.annotationdefaults[annotationtype] and 'datetime' in doc.annotationdefaults[annotationtype][self.set]:
            self.datetime = doc.annotationdefaults[annotationtype][self.set]['datetime']
        elif Attrib.DATETIME in required:
            raise ValueError("Datetime is required for " + self.__class__.__name__)

        if 'src' in kwargs:
            if not Attrib.SRC in supported:
                raise ValueError("Source is not supported for " + self.__class__.__name__)
            self.src = kwargs['src']
            del kwargs['src']
        elif Attrib.SRC in required:
            raise ValueError("Source is required for " + self.__class__.__name__)

        if 'begintime' in kwargs:
            if not Attrib.BEGINTIME in supported:
                raise ValueError("Begintime is not supported for " + self.__class__.__name__)
            self.begintime = parsetime(kwargs['begintime'])
            del kwargs['begintime']
        elif Attrib.BEGINTIME in required:
            raise ValueError("Begintime is required for " + self.__class__.__name__)

        if 'endtime' in kwargs:
            if not Attrib.ENDTIME in supported:
                raise ValueError("Endtime is not supported for " + self.__class__.__name__)
            self.endtime = parsetime(kwargs['endtime'])
            del kwargs['endtime']
        elif Attrib.ENDTIME in required:
            raise ValueError("Endtime is required for " + self.__class__.__name__)


        if 'speaker' in kwargs:
            if not Attrib.SPEAKER in supported:
                raise ValueError("Speaker is not supported for " + self.__class__.__name__)
            self.speaker = kwargs['speaker']
            del kwargs['speaker']
        elif Attrib.SPEAKER in required:
            raise ValueError("Speaker is required for " + self.__class__.__name__)

        if 'auth' in kwargs:
            if kwargs['auth'] in ('no','false'):
                self.auth = False
            else:
                self.auth = bool(kwargs['auth'])
            del kwargs['auth']
        else:
            self.auth = self.__class__.AUTH

        if 'textclass' in kwargs:
            if 'text' in kwargs:
                #we are editing a text and providing a  textclass,
                #then what we want is settextclass rather than textclass
                #(which is for provenance). This may be needed for the FQL library:
                kwargs['settextclass'] = kwargs['textclass']
            elif not Attrib.TEXTCLASS in supported:
                raise ValueError("Textclass is not supported for " + self.__class__.__name__)
            else:
                self.textclass = kwargs['textclass']
            del kwargs['textclass']
        else:
            if Attrib.TEXTCLASS in supported:
                self.textclass = "current"

        if 'text' in kwargs:
            if kwargs['text']:
                if 'settextclass' in kwargs:
                    self.settext(kwargs['text'], kwargs['settextclass'])
                    del kwargs['settextclass']
                else:
                    self.settext(kwargs['text'])
            del kwargs['text']

        if 'phon' in kwargs:
            if kwargs['phon']:
                self.setphon(kwargs['phon'])
            del kwargs['phon']


        if 'tag' in kwargs:
            if kwargs['tag']:
                self.tags = kwargs['tag'].split(" ")
            del kwargs['tag']

        if Attrib.SPACE in supported:
            self.space = True #use spacing as determined by textdelimiter
            if 'space' in kwargs:
                if kwargs['space'] == "no" or not kwargs['space']:
                    self.space = False
                elif kwargs['space'] == "yes" or kwargs['space'] is True:
                    self.space = True
                else:
                    raise ValueError("Invalid value for space attribute: " + self.space)
                del kwargs['space']

        if 'metadata' in kwargs:
            if not Attrib.METADATA in supported:
                raise ValueError("Metadata is not supported for " + self.__class__.__name__)
            self.metadata = kwargs['metadata']
            if doc:
                try:
                    doc.submetadata[kwargs['metadata']]
                except KeyError:
                    raise KeyError("No such metadata defined: " + kwargs['metadata'])
            del kwargs['metadata']

        if self.XLINK:
            if 'href' in kwargs:
                self.href =kwargs['href']
                del kwargs['href']
            if 'xlinktype' in kwargs:
                self.xlinktype = kwargs['xlinktype']
                del kwargs['xlinktype']
            if 'xlinkrole' in kwargs:
                self.xlinkrole = kwargs['xlinkrole']
                del kwargs['xlinkrole']
            if 'xlinklabel' in kwargs:
                self.xlinklabel = kwargs['xlinklabel']
                del kwargs['xlinklabel']
            if 'xlinkshow' in kwargs:
                self.xlinkshow = kwargs['xlinkshow']
                del kwargs['xlinklabel']
            if 'xlinktitle' in kwargs:
                self.xlinktitle = kwargs['xlinktitle']
                del kwargs['xlinktitle']

        if 'preservespace' in kwargs:
            self.preservespace = kwargs['preservespace']
            del kwargs['preservespace']

        if doc and doc.debug >= 2:
            print("   @id           = ", repr(self.id),file=stderr)
            print("   @set          = ", repr(self.set),file=stderr)
            print("   @class        = ", repr(self.cls),file=stderr)
            print("   @processor    = ", repr(self.processor),file=stderr)
            print("   @annotator    = ", repr(self.annotator),file=stderr)
            print("   @annotatortype= ", repr(self.annotatortype),file=stderr)
            print("   @confidence   = ", repr(self.confidence),file=stderr)
            print("   @n            = ", repr(self.n),file=stderr)
            print("   @datetime     = ", repr(self.datetime),file=stderr)
            print("   @href         = ", repr(self.href),file=stderr)
            print("   @preservespace= ", repr(self.preservespace),file=stderr)


        #set index
        if self.id and doc:
            if self.id in doc.index:
                if doc.debug >= 1: print("[FoLiA DEBUG] Duplicate ID not permitted:" + self.id,file=stderr)
                raise DuplicateIDError("Duplicate ID not permitted: " + self.id)
            else:
                if doc.debug >= 1: print("[FoLiA DEBUG] Adding to index: " + self.id,file=stderr)
                doc.index[self.id] = self

        #Parse feature attributes (shortcut for feature specification for some elements)
        for c in self.ACCEPTED_DATA:
            if issubclass(c, Feature):
                if c.SUBSET in kwargs:
                    if kwargs[c.SUBSET]:
                        self.append(c,cls=kwargs[c.SUBSET])
                    del kwargs[c.SUBSET]

        return kwargs

    def setprocessor(self,processor):
        """Sets the processor for this element, taking care of adding an annotator in the declarations"""
        if isinstance(processor,str) and self.doc:
            processor = self.doc.provenance[processor]
        assert isinstance(processor, Processor)
        if self.ANNOTATIONTYPE is None:
            raise ValueError("Unable to set processor on " + self.__class__.__name__ + ". AnnotationType is None!")
        self.processor = processor
        if not any( annotator.processor_id == processor.id for annotator in self.doc.getannotators(self.ANNOTATIONTYPE, self.set)):
            if self.doc.autodeclare:
                self.doc.annotators[self.ANNOTATIONTYPE][self.set].append(Annotator(processor, self.doc))
            else:
                raise DeclarationError("Processor " + processor.id + " is used for annotationtype " + annotationtype2str(self.ANNOTATIONTYPE) + ", set " + str(self.set) + ", but has no corresponding <annotator> referring to it from the annotations declaration block!")


    def annotator2processor(self, annotator=None, annotatortype=None, parentprocessor=None):
        """Converts annotator information to processor information (FoLiA v2). Can be called with arguments to override defaults."""
        #get current values if not overriden
        if annotator is None: annotator = self.annotator
        if annotatortype is None: annotatortype = self.annotatortype if self.annotatortype else AnnotatorType.AUTO
        if not parentprocessor:
            if self.doc.processor:
                parentprocessor = self.doc.processor
            else:
                #no parent processor, we will append directly to the provenance chain then
                parentprocessor = self.doc.provenance

        annkey = (annotator, annotatortype)
        if annkey in self.doc.annotator2processor_map:
            #we're in our cache, easy:
            self.setprocessor(self.doc.annotator2processor_map[annkey])
        else:
            foundprocessor = None
            #do any processors already exist with the same name?
            for processor in self.doc.getprocessors(self.ANNOTATIONTYPE, self.set):
                if annotator == processor.name and annotatortype == processor.type:
                    foundprocessor = processor
            if foundprocessor:
                #one of the processors has the same name so we will reuse that one
                self.setprocessor(foundprocessor)
            else:
                #we need to create a new processor
                newprocessor = Processor(annotator, type=annotatortype)
                self.setprocessor(newprocessor)
                #add the new processor to the provenance chain (assuming parentprocessor is already added!)
                parentprocessor.append(newprocessor)
                foundprocessor = newprocessor
            #add to cache so we can be quicker next time
            self.doc.annotator2processor_map[annkey] = foundprocessor

        #delete the old attributes (setting them to None isn't good enough, we really need to get
        # rid of them so the library automatically looks up the processor attribute when they are accessed next time)
        try:
            del self.annotator
        except AttributeError: #already gone, ok
            pass
        try:
            del self.annotatortype
        except AttributeError:
            pass

    def checkdeclaration(self):
        """Internal method (usually no need to call this) that checks whether the element's annotation type is properly declared, raises an exception if not so, or auto-declares the annotation type if need be."""
        annotationtype = self.ANNOTATIONTYPE
        if self.doc and annotationtype is not None: #we can only do this check if we have a document, we'll be overly permissive for documentless elements (so caution adviced for those)
            FOLIA2 = self.doc.FOLIA2
            if not isinstance(self, (Text,Speech, AbstractCorrectionChild)): #Body is an undeclared element
                #Check if an element is declared (FoLiA v2+ only), this is a much stricter check than older FoLiA versions
                #for FoLiA <2 we only check if we have a set
                if annotationtype in self.doc.alias_set and self.set in self.doc.alias_set[annotationtype]:
                    foliaset = self.doc.alias_set[annotationtype][self.set]
                else:
                    foliaset = self.set
                if self.doc and (annotationtype, foliaset) not in self.doc.annotations:
                    if foliaset is False:
                        #set may be False in case of annotation layers, where it will be set later after appending children, we ignore that case (things like auto-declare are deferred until an actual span annotation appears)
                        pass
                    elif self.doc.autodeclare:
                        #autodeclare is enabled (default for FoLiA v2)
                        if isinstance(self, TextContent): #FoLiA v2.0, autodeclare text
                            if FOLIA2 or (self.doc.FOLIA1 and not self.doc.keepversion):
                                if self.doc.debug >= 1: print("[FoLiA DEBUG] Auto-declaring Text Annotation",file=stderr)
                                self.doc.declare(AnnotationType.TEXT, DEFAULT_TEXT_SET)
                        elif isinstance(self, PhonContent): #FoLiA v2.0
                            if FOLIA2 or (self.doc.FOLIA1 and not self.doc.keepversion):
                                if self.doc.debug >= 1: print("[FoLiA DEBUG] Auto-declaring Phonetic Annotation",file=stderr)
                                self.doc.declare(AnnotationType.PHON, DEFAULT_PHON_SET)
                        elif foliaset:
                            if self.doc.debug >= 1: print("[FoLiA DEBUG] Auto-declaring " + self.__class__.__name__ + " with set " + str(foliaset),file=stderr)
                            self.doc.declare(annotationtype, foliaset)
                        else:
                            if self.doc.debug >= 1: print("[FoLiA DEBUG] Auto-declaring " + self.__class__.__name__ + " (no set)", file=stderr)
                            self.doc.declare(annotationtype)
                    elif foliaset:
                        if self.doc.FOLIA1 and foliaset == "undefined":
                            #undefined sets could have been left undeclared in FoLiA v1
                            #this only works if there are already other sets declared
                            for atype, aset in self.doc.annotations:
                                if atype == annotationtype and aset and aset != "undefined":
                                    raise DeclarationError("Set '" + str(foliaset) + "' is used for " + self.__class__.__name__ + " <" + self.__class__.XMLTAG + ">, but there are already defined sets, such as " + aset)
                        else:
                            raise DeclarationError("Set '" + str(foliaset) + "' is used for " + self.__class__.__name__ + " <" + self.__class__.XMLTAG + ">, but has no declaration!")
                    elif FOLIA2:
                        raise DeclarationError("Encountered an instance without proper declaration: " + self.__class__.__name__ + " <" + self.__class__.XMLTAG + ">!")


    def description(self):
        """Obtain the description associated with the element.

        Raises:
            :class:`NoSuchAnnotation` if there is no associated description."""
        for e in self:
            if isinstance(e, Description):
                return e.value
        raise NoSuchAnnotation

    def textcontent(self, cls='current', correctionhandling=CorrectionHandling.CURRENT, hidden=False):
        """Get the text content explicitly associated with this element (of the specified class).

        Unlike :meth:`text`, this method does not recurse into child elements (with the sole exception of the Correction/New element), and it returns the :class:`TextContent` instance rather than the actual text!

        Parameters:
            cls (str): The class of the text content to obtain, defaults to ``current``.
            correctionhandling: Specifies what content to retrieve when corrections are encountered. The default is ``CorrectionHandling.CURRENT``, which will retrieve the corrected/current content. You can set this to ``CorrectionHandling.ORIGINAL`` if you want the content prior to correction, and ``CorrectionHandling.EITHER`` if you don't care.
            hidden (bool): Include hidden elements, defaults to ``False``.

        Returns:
            The phonetic content (:class:`TextContent`)

        Raises:
            :class:`NoSuchText` if there is no text content for the element

        See also:
            :meth:`text`
            :meth:`phoncontent`
            :meth:`phon`
        """
        if not self.PRINTABLE or (self.HIDDEN and not hidden): #only printable elements can hold text and hidden elements don't have text unless explicitly asked for
            raise NoSuchText


        #Find explicit text content (same class)
        for e in self:
            if isinstance(e, TextContent):
                if cls is None or e.cls == cls:
                    return e
            elif isinstance(e, Correction):
                try:
                    return e.textcontent(cls, correctionhandling, hidden)
                except NoSuchText:
                    pass
        raise NoSuchText



    def stricttext(self, cls='current'):
        """Alias for :meth:`text` with ``strict=True``"""
        return self.text(cls,strict=True)

    def findcorrectionhandling(self, cls):
        """Find the proper correctionhandling given a textclass by looking in the underlying corrections where it is reused"""
        if cls == "current":
            return CorrectionHandling.CURRENT
        elif cls == "original":
            return CorrectionHandling.ORIGINAL #backward compatibility
        else:
            correctionhandling = None
            #but any other class may be anything
            #Do we have corrections at all? otherwise no need to bother
            for correction in self.select(Correction):
                #yes, in which branch is the text class found?
                found = False
                hastext = False
                if correction.hasnew():
                    found = True
                    doublecorrection = correction.new().count(Correction) > 0
                    if doublecorrection: return None #skipping text validation, correction is too complex (nested) to handle for now
                    for t in  correction.new().select(TextContent):
                        hastext = True
                        if t.cls == cls:
                            if correctionhandling is not None and correctionhandling != CorrectionHandling.CURRENT:
                                return None #inconsistent
                            else:
                                correctionhandling = CorrectionHandling.CURRENT
                            break
                elif correction.hascurrent():
                    found = True
                    doublecorrection = correction.current().count(Correction) > 0
                    if doublecorrection: return None #skipping text validation, correction is too complex (nested) to handle for now
                    for t in  correction.current().select(TextContent):
                        hastext = True
                        if t.cls == cls:
                            if correctionhandling is not None and correctionhandling != CorrectionHandling.CURRENT:
                                return None #inconsistent
                            else:
                                correctionhandling = CorrectionHandling.CURRENT
                            break
                if correction.hasoriginal():
                    found = True
                    doublecorrection = correction.original().count(Correction) > 0
                    if doublecorrection: return None #skipping text validation, correction is too complex (nested) to handle for now
                    for t in  correction.original().select(TextContent):
                        hastext = True
                        if t.cls == cls:
                            if correctionhandling is not None and correctionhandling != CorrectionHandling.ORIGINAL:
                                return None #inconsistent
                            else:
                                correctionhandling = CorrectionHandling.ORIGINAL
                            break
            if correctionhandling is None:
                #well, we couldn't find our textclass in any correction, just fall back to current and let text validation fail if needed
                return CorrectionHandling.CURRENT
            return correctionhandling


    def textvalidation(self, warnonly=None, trim_spaces=True):
        """Run text validation on this element. Checks whether any text redundancy is consistent and whether offsets are valid.

        Parameters:
            warnonly (bool): Warn only (True) or raise exceptions (False). If set to None then this value will be determined based on the document's FoLiA version (Warn only before FoLiA v1.5)

        Returns:
            bool
        """

        #note: hidden text (i.e. in Hidden words) is never considered in text validation

        if warnonly is None and self.doc and self.doc.version:
            warnonly = (checkversion(self.doc.version, '1.5.0') < 0) #warn only for documents older than FoLiA v1.5

        pre241 = (checkversion(self.doc.version, '2.4.1') < 0)
        valid = True
        for cls in self.doc.textclasses:
            if self.hastext(cls, strict=True) and not isinstance(self, (Linebreak, Whitespace)):
                if self.doc and self.doc.debug: print("[FoLiA DEBUG] Text validation on " + repr(self),file=stderr)
                correctionhandling = self.findcorrectionhandling(cls)
                if correctionhandling is None:
                    #skipping text validation, correction is too complex (nested) to handle for now; just assume valid (benefit of the doubt)
                    if self.doc and self.doc.debug: print("[FoLiA DEBUG] SKIPPING Text validation on " + repr(self) + ", too complex to handle (nested corrections or inconsistent use)",file=stderr)
                    return True #just assume it's valid then

                strictnormtext = self.text(cls,retaintokenisation=False,strict=True, normalize_spaces=True, hidden=False, trim_spaces=trim_spaces, correctionhandling=correctionhandling)
                try:
                    deepnormtext = self.text(cls,retaintokenisation=False,strict=False, normalize_spaces=True, hidden=False, trim_spaces=trim_spaces, correctionhandling=correctionhandling)
                except NoSuchText:
                    deepnormtext = ""
                    if self.doc and self.doc.debug: print("[FoLiA DEBUG] deepnormtext on " + repr(self) + " is empty! (NoSuchText)",file=stderr)
                if strictnormtext != deepnormtext:
                    valid = False
                    deviation = 0
                    for i, (c1,c2) in enumerate(zip(strictnormtext,deepnormtext)):
                        if c1 != c2:
                            deviation = i
                            break
                    msg = "Text for " + repr(self) + ", is inconsistent: EXPECTED (deep text after normalization) *****>\n" + deepnormtext + "\n****> BUT FOUND (strict text after normalization) ****>\n" + strictnormtext + "\n******* DEVIATION POINT: " + strictnormtext[max(0,deviation-10):deviation] + "<*HERE*>" + strictnormtext[deviation:deviation+10]

                    if trim_spaces:
                        #prior to FoLiA v2.4.1, we didn't strip leading/trailing whitespace
                        #see issue https://github.com/proycon/folia/issues/88
                        #This means it is possible for older FoLiA to be invalid since
                        #v2.4.1. We don't want a hard failure in that case as older
                        #documents must continue to be valid.

                        #Since v2.5.0, the trim behaviour is even stricter/more consistent
                        #and more in line with what TEI also does

                        #Test if the element is valid according to the old rules
                        try:
                            self.textvalidation(None, trim_spaces=False)
                            warnonly = True
                            msg += "\nHowever, according to the older rules (<v2.4.1) the text is consistent. So we are treating this as a warning rather than an error. We do recommend fixing this if this is a document you intend to publish."
                        except InconsistentText as e:
                            msg += "\n(also checked against older rules prior to FoLiA v2.4.1)"
                            pass

                    if warnonly:
                        print("TEXT VALIDATION ERROR: " + msg + "\n",file=sys.stderr)
                    else:
                        raise InconsistentText(msg)

                #validate offsets
                tc = self.textcontent(cls)
                if tc.offset is not None:
                    #we can't validate the reference of this element yet since it may point to higher level elements still being created!! we store it in a buffer that will
                    #be processed by pendingvalidation() after parsing and prior to serialisation
                    if self.doc and self.doc.debug: print("[FoLiA DEBUG] Queing element for later offset validation: " + repr(self),file=stderr)
                    self.doc.offsetvalidationbuffer.append( (self, cls) )
        return valid

    def resolveoffsets(self, begin, end, retaintokenisation=True, strictend=True, cls='current'):
        """Resolves supplied character offset information and returns tokens (non-token structures like linebreaks etc are ignored!). Note: offsets are zero-indexed and the end is non-inclusive!"""
        offset = 0
        words = []
        for word in self.select(Word):
            text = word.text(cls)
            delimiter = word.gettextdelimiter(retaintokenisation)
            if offset == begin:
                if offset+len(text) == end:
                    #exact match
                    return [word]
                elif offset+len(text) > end:
                    #overshot
                    if strictend:
                        return []
                    else:
                        return [word]
                else:
                    words.append(word)
            elif words:
                if offset+len(text) == end:
                    #good, we're at the end
                    return words + [word]
                elif offset+len(text) > end:
                    #overshot
                    if strictend:
                        return words
                    else:
                        return words + [word]
                else:
                    words.append(word)
            offset += len(text) + len(delimiter)
        if words and not strictend:
            return words
        raise InconsistentText("Supplied offset range (" + str(begin) + "," + str(end) + ") is not consistent with the tokens in " + repr(self) + ": \"" + self.text(cls,retaintokenisation=retaintokenisation) + "\"; buffer: " + repr(words) + "; offset: " + str(offset))

    def toktext(self,cls='current'):
        """Alias for :meth:`text` with ``retaintokenisation=True``"""
        return self.text(cls,retaintokenisation=True)

    def text(self, cls='current', retaintokenisation=False, previousdelimiter="",strict=False, correctionhandling=CorrectionHandling.CURRENT, normalize_spaces=False, hidden=False, trim_spaces=True):
        """Get the text associated with this element (of the specified class)

        The text will be constructed from child-elements whereever possible, as they are more specific.
        If no text can be obtained from the children and the element has itself text associated with
        it, then that will be used.

        Parameters:
            cls (str): The class of the text content to obtain, defaults to ``current``.
            retaintokenisation (bool): If set, the space attribute on words will be ignored, otherwise it will be adhered to and text will be detokenised as much as possible. Defaults to ``False``.
            previousdelimiter (str): Can be set to a delimiter that was last outputed, useful when chaining calls to :meth:`text`. Defaults to an empty string.
            strict (bool):  Set this if you are strictly interested in the text explicitly associated with the element, without recursing into children. Defaults to ``False``.
            correctionhandling: Specifies what text to retrieve when corrections are encountered. The default is ``CorrectionHandling.CURRENT``, which will retrieve the corrected/current text. You can set this to ``CorrectionHandling.ORIGINAL`` if you want the text prior to correction, and ``CorrectionHandling.EITHER`` if you don't care.
            normalize_spaces (bool): Return the text with multiple spaces, linebreaks, tabs normalized to single spaces
            trim_spaces (bool): Trim leading and trailing spaces, this is default behaviour since FoLiA v2.4.1 and should only be set to False for compatibility with older documents
            hidden (bool): Include hidden elements, defaults to ``False``.

        Example::

            word.text()

        Returns:
            The text of the element (``unicode`` instance in Python 2, ``str`` in Python 3)

        Raises:
            :class:`NoSuchText`: if no text is found at all.
        """

        if strict:
            return self.textcontent(cls, correctionhandling,hidden=hidden).text(normalize_spaces=normalize_spaces, trim_spaces=trim_spaces)

        if self.TEXTCONTAINER:
            s = ""
            pendingspace = False
            for e in self:
                if isstring(e):
                    if pendingspace: #flush the pendingspace buffer
                        s += " "
                        pendingspace = False
                    if trim_spaces:
                        #This implements https://github.com/proycon/folia/issues/88
                        #FoLiA >= v2.5 behaviour (introduced earlier in v2.4.1 but modified thereafter)
                        l = len(s)
                        for j, line in enumerate(e.split("\n")):
                            if self.preservespace:
                                s2 = unicodedata.normalize('NFC', line.strip("\r")) #strip only artefacts of DOS-style line endings, leave all intact
                            else:
                                s2 = unicodedata.normalize('NFC', norm_spaces(line.strip(" \r"))) #strips leading and trailing whitespace per line (proycon/folia#88)
                                                                    #norm_spaces strips multi-spaces in the middle
                                                                    #also strips artefacts of DOS-style line-endings
                            if j > 0 and s2 and len(s) != l:
                                #insert spaces between lines that used to be newline separated, except if there already is space
                                s += " "
                            elif s2 and line and (line[0] != "\n" and is_space(line[0])) and not self.preservespace:
                                #we have leading indentation we may need to collapse or ignore entirely
                                #we can't be sure yet what to do so we add a temporary placeholder \0
                                #this will later be handled in postprocess_spaces() (converts to a space only if no space preceeds it)
                                s += "\0"
                            s += s2

                        if e and is_space(e[-1]) and s and not is_space(s[-1]) and not self.preservespace:
                            #this item has trailing spaces but we stripped them
                            #this may be premature so
                            #we reserve to output them later in case there is a next item
                            pendingspace = True
                    else:
                        #old FoLiA <= v2.4.1 behaviour, we don't trim anything
                        s += e
                elif e.PRINTABLE:
                    if pendingspace:
                        if not e.IMPLICITSPACE:
                            s += " "
                        pendingspace = False
                    if s:
                        s += e.gettextdelimiter() #for AbstractMarkup, will usually be "" (but we need it still for <br/>)
                    s += e.text(trim_spaces=trim_spaces) #(no need to propagate normalize_spaces because we handle it on a macro-level below)

            if normalize_spaces:
                return norm_spaces(postprocess_spaces(s))
            elif trim_spaces and (not self.preservespace or normalize_spaces):
                return postprocess_spaces(s)
            else:
                return s

        elif not self.PRINTABLE or (self.HIDDEN and not hidden): #only printable elements can hold text and hidden elements don't contain text unless explicitly queried
            raise NoSuchText
        else:
            #Get text from children first
            delimiter = ""
            s = ""
            for e in self:
                #was: e.PRINTABLE and not isinstance(e, TextContent) and not isinstance(e, String):
                if isinstance(e, (AbstractStructureElement, Correction, AbstractSpanAnnotation)):   #AbstractSpanAnnotation is needed when requesting text() on nested span annotations
                    try:
                        s += e.text(cls,retaintokenisation, delimiter,False,correctionhandling=correctionhandling, hidden=hidden)

                        #delimiter will be buffered and only printed upon next iteration, this prevents the delimiter being outputted at the end of a sequence and to be compounded with other delimiters
                        delimiter = e.gettextdelimiter(retaintokenisation)
                    except NoSuchText:
                        #No text, that's okay, just continue
                        continue

            if not s and self.hastext(cls, correctionhandling, hidden=hidden):
                s = self.textcontent(cls, correctionhandling, hidden=hidden).text()

            if s and previousdelimiter:
                s = previousdelimiter + s
            if s:
                if normalize_spaces:
                    return norm_spaces(s)
                else:
                    return s
            else:
                #No text found at all :`(
                raise NoSuchText

    def phoncontent(self, cls='current', correctionhandling=CorrectionHandling.CURRENT, hidden=False):
        """Get the phonetic content explicitly associated with this element (of the specified class).

        Unlike :meth:`phon`, this method does not recurse into child elements (with the sole exception of the Correction/New element), and it returns the PhonContent instance rather than the actual text!

        Parameters:
            cls (str): The class of the phonetic content to obtain, defaults to ``current``.
            correctionhandling: Specifies what content to retrieve when corrections are encountered. The default is ``CorrectionHandling.CURRENT``, which will retrieve the corrected/current content. You can set this to ``CorrectionHandling.ORIGINAL`` if you want the content prior to correction, and ``CorrectionHandling.EITHER`` if you don't care.

        Returns:
            The phonetic content (:class:`PhonContent`)

        Raises:
            :class:`NoSuchPhon` if there is no phonetic content for the element

        See also:
            :meth:`phon`
            :meth:`textcontent`
            :meth:`text`
        """
        if not self.SPEAKABLE or (self.HIDDEN and not hidden): #only printable elements can hold text
            raise NoSuchPhon


        #Find explicit text content (same class)
        for e in self:
            if isinstance(e, PhonContent):
                if cls is None or e.cls == cls:
                    return e
            elif isinstance(e, Correction):
                try:
                    return e.phoncontent(cls, correctionhandling=correctionhandling, hidden=hidden)
                except NoSuchPhon:
                    pass
        raise NoSuchPhon


    def speech_src(self):
        """Retrieves the URL/filename of the audio or video file associated with the element.

        The source is inherited from ancestor elements if none is specified. For this reason, always use this method rather than access the ``src`` attribute directly.

        Returns:
            str or None if not found
        """
        if self.src:
            return self.src
        elif self.parent:
            return self.parent.speech_src()
        else:
            return None

    def speech_speaker(self):
        """Retrieves the speaker of the audio or video file associated with the element.

        The source is inherited from ancestor elements if none is specified. For this reason, always use this method rather than access the ``src`` attribute directly.

        Returns:
            str or None if not found
        """
        if self.speaker:
            return self.speaker
        elif self.parent:
            return self.parent.speech_speaker()
        else:
            return None



    def phon(self, cls='current', previousdelimiter="", strict=False,correctionhandling=CorrectionHandling.CURRENT, hidden=False):
        """Get the phonetic representation associated with this element (of the specified class)

        The phonetic content will be constructed from child-elements whereever possible, as they are more specific.
        If no phonetic content can be obtained from the children and the element has itself phonetic content associated with
        it, then that will be used.

        Parameters:
            cls (str): The class of the phonetic content to obtain, defaults to ``current``.
            retaintokenisation (bool): If set, the space attribute on words will be ignored, otherwise it will be adhered to and phonetic content will be detokenised as much as possible. Defaults to ``False``.
            previousdelimiter (str): Can be set to a delimiter that was last outputed, useful when chaining calls to :meth:`phon`. Defaults to an empty string.
            strict (bool):  Set this if you are strictly interested in the phonetic content explicitly associated with the element, without recursing into children. Defaults to ``False``.
            correctionhandling: Specifies what phonetic content to retrieve when corrections are encountered. The default is ``CorrectionHandling.CURRENT``, which will retrieve the corrected/current phonetic content. You can set this to ``CorrectionHandling.ORIGINAL`` if you want the phonetic content prior to correction, and ``CorrectionHandling.EITHER`` if you don't care.
            hidden (bool): Include hidden elements, defaults to ``False``.

        Example::

            word.phon()

        Returns:
            The phonetic content of the element (``unicode`` instance in Python 2, ``str`` in Python 3)

        Raises:
            :class:`NoSuchPhon`: if no phonetic conent is found at all.

        See also:
            :meth:`phoncontent`: Retrieves the phonetic content as an element rather than a string
            :meth:`text`
            :meth:`textcontent`
        """

        if strict:
            return self.phoncontent(cls,correctionhandling,hidden=hidden).phon()

        if self.PHONCONTAINER:
            s = ""
            for e in self:
                if isstring(e):
                    s += e
                else:
                    try:
                        if s: s += e.TEXTDELIMITER #We use TEXTDELIMITER for phon too
                    except AttributeError:
                        pass
                    s += e.phon()
            return s
        elif not self.SPEAKABLE: #only readable elements can hold phonetic content
            raise NoSuchPhon
        else:
            #Get text from children first
            delimiter = ""
            s = ""
            for e in self:
                if e.SPEAKABLE and not isinstance(e, PhonContent) and not isinstance(e,String):
                    try:
                        s += e.phon(cls, delimiter,False,correctionhandling,hidden=hidden)

                        #delimiter will be buffered and only printed upon next iteration, this prevents the delimiter being outputted at the end of a sequence and to be compounded with other delimiters
                        delimiter = e.gettextdelimiter() #We use TEXTDELIMITER for phon too
                    except NoSuchPhon:
                        #No text, that's okay, just continue
                        continue

            if not s and self.hasphon(cls,correctionhandling, hidden=hidden):
                s = self.phoncontent(cls,correctionhandling,hidden=hidden).phon()

            if s and previousdelimiter:
                return previousdelimiter + s
            elif s:
                return s
            else:
                #No text found at all :`(
                raise NoSuchPhon

    def originaltext(self,cls='original'):
        """Alias for retrieving the original uncorrect text.

        A call to :meth:`text` with ``correctionhandling=CorrectionHandling.ORIGINAL``"""
        return self.text(cls,correctionhandling=CorrectionHandling.ORIGINAL)


    def gettextdelimiter(self, retaintokenisation=False):
        """Return the text delimiter for this class.

        Uses the ``TEXTDELIMITER`` attribute but may return a customised one instead."""
        if self.TEXTDELIMITER is None:
            #no text delimiter of itself, recurse into children to inherit delimiter
            for child in reversed(self):
                if isinstance(child, AbstractElement):
                    return child.gettextdelimiter(retaintokenisation)
            return ""
        elif Attrib.SPACE in self.OPTIONAL_ATTRIBS: #(we use the assumption it's never a required attribute to speed up things)
            if self.space or retaintokenisation:
                return self.TEXTDELIMITER
            else:
                return ''
        else:
            return self.TEXTDELIMITER

    def feat(self,subset):
        """Obtain the feature class value of the specific subset.

        If a feature occurs multiple times, the values will be returned in a list.

        Example::

            sense = word.annotation(folia.Sense)
            synset = sense.feat('synset')

        Returns:
            str or list
        """
        r = None
        for f in self:
            if isinstance(f, Feature) and f.subset == subset:
                if r: #support for multiclass features
                    if isinstance(r,list):
                        r.append(f.cls)
                    else:
                        r = [r, f.cls]
                else:
                    r = f.cls
        if r is None:
            raise NoSuchAnnotation
        else:
            return r

    def __ne__(self, other):
        return not (self == other)

    def __eq__(self, other): #pylint: disable=too-many-return-statements
        """Equality method, tests whether two elements are equal.
        Elements are equal if all their attributes and children are equal."""
        if self is other: return True #pythonic equality (object address)

        if self.doc and self.doc.debug: print("[FoLiA DEBUG] AbstractElement Equality Check - " + repr(self) + " vs " + repr(other),file=stderr)

        #Check if we are of the same time
        if type(self) != type(other): #pylint: disable=unidiomatic-typecheck
            if self.doc and self.doc.debug: print("[FoLiA DEBUG] AbstractElement Equality Check - Type mismatch: " + str(type(self)) + " vs " + str(type(other)),file=stderr)
            return False

        #Check FoLiA attributes
        if self.id != other.id:
            if self.doc and self.doc.debug: print("[FoLiA DEBUG] AbstractElement Equality Check - ID mismatch: " + str(self.id) + " vs " + str(other.id),file=stderr)
            return False
        if self.set != other.set and not (self.set is None and other.set == "undefined"): #the latter condition gives us some lenience in comparisons with pre 2.0 documents
            if self.doc and self.doc.debug: print("[FoLiA DEBUG] AbstractElement Equality Check - Set mismatch: " + str(self.set) + " vs " + str(other.set),file=stderr)
            return False
        if self.cls != other.cls:
            if self.doc and self.doc.debug: print("[FoLiA DEBUG] AbstractElement Equality Check - Class mismatch: " + repr(self.cls) + " vs " + repr(other.cls),file=stderr)
            return False
        if self.annotator != other.annotator:
            if self.doc and self.doc.debug: print("[FoLiA DEBUG] AbstractElement Equality Check - Annotator mismatch: " + repr(self.annotator) + " vs " + repr(other.annotator),file=stderr)
            return False
        if self.annotatortype != other.annotatortype:
            if self.doc and self.doc.debug: print("[FoLiA DEBUG] AbstractElement Equality Check - Annotator mismatch: " + repr(self.annotatortype) + " vs " + repr(other.annotatortype),file=stderr)
            return False

        #Check if we have same amount of children:
        mychildren = list(self)
        yourchildren = list(other)
        if len(mychildren) != len(yourchildren):
            if self.doc and self.doc.debug: print("[FoLiA DEBUG] AbstractElement Equality Check - Unequal amount of children",file=stderr)
            return False

        #Now check equality of children
        for mychild, yourchild in zip(mychildren, yourchildren):
            if self.doc and self.doc.debug: print("[FoLiA DEBUG] AbstractElement Equality Check - Descending into children of " + repr(self) + " and " + repr(other),file=stderr)
            if mychild != yourchild:
                if self.doc and self.doc.debug: print("[FoLiA DEBUG] AbstractElement Equality Check - Child mismatch: " + repr(mychild) + " vs " + repr(yourchild) + " (in " + repr(self) + ", id: " + str(self.id) + ")",file=stderr)
                return False

        #looks like we made it! \o/
        return True

    def __repr__(self):
        return "<" + self.__class__.__name__ + " at " + str(id(self)) + " id=" + str(self.id) + " set="+ str(self.set) + " class="+ str(self.cls) + ">"

    def __len__(self):
        """Returns the number of child elements under the current element."""
        return len(self.data)

    def __nonzero__(self): #Python 2.x
        return True

    def __bool__(self):
        return True

    def __hash__(self):
        if self.id:
            return hash(self.id)
        else:
            return hash(id(self)) #use the memory address

    def __iter__(self):
        """Iterate over all children of this element.

        Example::

            for annotation in word:
                ...
        """
        return iter(self.data)


    def __contains__(self, element):
        """Tests if the specified element is part of the children of the element"""
        return element in self.data

    def __getitem__(self, key):
        try:
            return self.data[key]
        except KeyError:
            raise

    def __unicode__(self): #Python 2 only
        """Alias for :meth:`text`. Python 2 only."""
        return self.text()

    def __str__(self):
        """Alias for :meth:`text`"""
        return self.text()

    def move(self, newdoc, idsuffix=""):
        """Move elements of one document to another

        Parameters:
            newdoc (:class:`Document`): The document the copy should be associated with.
            idsuffix (str or bool): If set to a string, the ID of the copy will be append with this (prevents duplicate IDs when making copies for the same document). If set to ``True``, a random suffix will be generated.

        Returns:
            a copy of the element
        """
        if idsuffix is True: idsuffix = ".copy." + "%08x" % random.getrandbits(32) #random 32-bit hash for each copy, same one will be reused for all children
        self.setdoc(newdoc, idsuffix)
        return self

    def copy(self, newdoc=None, idsuffix=""):
        """Make a deep copy of this element and all its children.

        Parameters:
            newdoc (:class:`Document`): The document the copy should be associated with.
            idsuffix (str or bool): If set to a string, the ID of the copy will be append with this (prevents duplicate IDs when making copies for the same document). If set to ``True``, a random suffix will be generated.

        Returns:
            a copy of the element
        """
        if idsuffix is True: idsuffix = ".copy." + "%08x" % random.getrandbits(32) #random 32-bit hash for each copy, same one will be reused for all children
        c = deepcopy(self)
        c.setdoc(newdoc, idsuffix)
        return c

    def copychildren(self, newdoc=None, idsuffix=""):
        """Generator creating a deep copy of the children of this element.

        Invokes :meth:`copy` on all children, parameters are the same.
        """
        if idsuffix is True: idsuffix = ".copy." + "%08x" % random.getrandbits(32) #random 32-bit hash for each copy, same one will be reused for all children
        for c in self:
            if isinstance(c, AbstractElement):
                yield c.copy(newdoc,idsuffix)


    def addidsuffix(self, idsuffix, recursive = True):
        """Appends a suffix to this element's ID, and optionally to all child IDs as well. There is sually no need to call this directly, invoked implicitly by :meth:`copy`"""
        if self.id: self.id += idsuffix
        if recursive:
            for e in self:
                try:
                    e.addidsuffix(idsuffix, recursive)
                except Exception:
                    pass

    def setparents(self):
        """Correct all parent relations for elements within the scop. There is sually no need to call this directly, invoked implicitly by :meth:`copy`"""
        for c in self:
            if isinstance(c, AbstractElement):
                c.parent = self
                c.setparents()

    def setdoc(self,newdoc, idsuffix=""):
        """Set a different document and handles setting an id suffix. Usually no need to call this directly, invoked implicitly by :meth:`copy`"""
        if self.id and idsuffix: self.id += idsuffix
        self.doc = newdoc
        if self.doc and self.id:
            self.doc.index[self.id] = self
        for c in self:
            if isinstance(c, AbstractElement):
                c.parent = self
                c.setdoc(newdoc, idsuffix)


    def hastext(self,cls='current',strict=True, correctionhandling=CorrectionHandling.CURRENT, hidden=False): #pylint: disable=too-many-return-statements
        """Does this element have text (of the specified class)

        By default, and unlike :meth:`text`, this checks strictly, i.e. the element itself must have the text and it is not inherited from its children.

        Parameters:
            cls (str): The class of the text content to obtain, defaults to ``current``.
            strict (bool):  Set this if you are strictly interested in the text explicitly associated with the element, without recursing into children. Defaults to ``True``.
            correctionhandling: Specifies what text to check for when corrections are encountered. The default is ``CorrectionHandling.CURRENT``, which will retrieve the corrected/current text. You can set this to ``CorrectionHandling.ORIGINAL`` if you want the text prior to correction, and ``CorrectionHandling.EITHER`` if you don't care.

        Returns:
            bool
        """
        if not self.PRINTABLE or (self.HIDDEN and not hidden): #only printable elements can hold text and hidden elements only have text if explicitly asked for
            return False
        elif self.TEXTCONTAINER:
            return True
        else:
            try:
                if strict:
                    self.textcontent(cls, correctionhandling, hidden) #will raise NoSuchTextException when not found
                    return True
                else:
                    #Check children
                    for e in self:
                        if e.PRINTABLE and not isinstance(e, TextContent):
                            if e.hastext(cls, strict, correctionhandling, hidden):
                                return True

                    self.textcontent(cls, correctionhandling, hidden)  #will raise NoSuchTextException when not found
                    return True
            except NoSuchText:
                return False

    def hasphon(self,cls='current',strict=True,correctionhandling=CorrectionHandling.CURRENT, hidden=False): #pylint: disable=too-many-return-statements
        """Does this element have phonetic content (of the specified class)

        By default, and unlike :meth:`phon`, this checks strictly, i.e. the element itself must have the phonetic content and it is not inherited from its children.

        Parameters:
            cls (str): The class of the phonetic content to obtain, defaults to ``current``.
            strict (bool):  Set this if you are strictly interested in the phonetic content explicitly associated with the element, without recursing into children. Defaults to ``True``.
            correctionhandling: Specifies what phonetic content to check for when corrections are encountered. The default is ``CorrectionHandling.CURRENT``, which will retrieve the corrected/current phonetic content. You can set this to ``CorrectionHandling.ORIGINAL`` if you want the phonetic content prior to correction, and ``CorrectionHandling.EITHER`` if you don't care.

        Returns:
            bool
        """
        if not self.SPEAKABLE or (self.HIDDEN and not hidden): #only speakable elements can hold phoentics and hidden elements only have phonetics if explicitly asked for
            return False
        elif self.PHONCONTAINER:
            return True
        else:
            try:
                if strict:
                    self.phoncontent(cls, correctionhandling, hidden)
                    return True
                else:
                    #Check children
                    for e in self:
                        if e.SPEAKABLE and not isinstance(e, PhonContent):
                            if e.hasphon(cls, strict, correctionhandling,hidden):
                                return True

                    self.phoncontent(cls, hidden=hidden)  #will raise NoSuchTextException when not found
                    return True
            except NoSuchPhon:
                return False

    def settext(self, text, cls='current'):
        """Set the text for this element.

        Arguments:
            text (str): The text
            cls (str): The class of the text, defaults to ``current`` (leave this unless you know what you are doing). There may be only one text content element of each class associated with the element.
        """
        self.replace(TextContent, value=text, cls=cls)

    def setdocument(self, doc):
        """Associate a document with this element.

        Arguments:
            doc (:class:`Document`): A document

        Each element must be associated with a FoLiA document.
        """
        assert isinstance(doc, Document)

        if not self.doc:
            self.doc = doc
            if self.id:
                if self.id in doc:
                    raise DuplicateIDError(self.id)
                else:
                    self.doc.index[id] = self

        for e in self: #recursive for all children
            if isinstance(e,AbstractElement): e.setdocument(doc)

    @classmethod
    def accepts(Parentclass, Class, raiseexceptions=True, parentinstance=None):
        if Class in Parentclass.ACCEPTED_DATA:
            return True
        else:
            #Class is not in accepted data, but perhaps any of its ancestors is?
            for c in Class.__mro__: #iterate over all base/super methods (automatically recurses)
                if c is not Class and c in Parentclass.ACCEPTED_DATA:
                    return True
            if raiseexceptions:
                extra = ""
                if parentinstance and parentinstance.id:
                    extra = ' (id=' + parentinstance.id + ')'
                raise ValueError("Unable to add object of type " + Class.__name__ + " to " + Parentclass.__name__ + " " + extra + ". Type not allowed as child.")
            else:
                return False


    @classmethod
    def addable(Class, parent, set=False, raiseexceptions=True):
        """Tests whether a new element of this class can be added to the parent.

        This method is mostly for internal use.
        This will use the ``OCCURRENCES`` property, but may be overidden by subclasses for more customised behaviour.

        Parameters:
            parent (:class:`AbstractElement`): The element that is being added to
            set (str,None, or False): The set
            raiseexceptions (bool): Raise an exception if the element can't be added?

        Returns:
            bool

        Raises:
            ValueError
         """


        if not parent.__class__.accepts(Class, raiseexceptions, parent):
            return False

        if Class.OCCURRENCES > 0:
            #check if the parent doesn't have too many already
            count = parent.count(Class,None,True,[True, AbstractStructureElement]) #never descend into embedded structure annotatioton
            if count >= Class.OCCURRENCES:
                if raiseexceptions:
                    if parent.id:
                        extra = ' (id=' + parent.id + ')'
                    else:
                        extra = ''
                    raise DuplicateAnnotationError("Unable to add another object of type " + Class.__name__ + " to " + parent.__class__.__name__ + " " + extra + ". There are already " + str(count) + " instances of this class, which is the maximum.")
                else:
                    return False

        if Class.OCCURRENCES_PER_SET > 0 and set and Class.REQUIRED_ATTRIBS and Attrib.CLASS in Class.REQUIRED_ATTRIBS:
            count = parent.count(Class,set,True, [True, AbstractStructureElement])
            if count >= Class.OCCURRENCES_PER_SET:
                if raiseexceptions:
                    if parent.id:
                        extra = ' (id=' + parent.id + ')'
                    else:
                        extra = ''
                    raise DuplicateAnnotationError("Unable to add another object of set " + set + " and type " + Class.__name__ + " to " + parent.__class__.__name__ + " " + extra + ". There are already " + str(count) + " instances of this class, which is the maximum for the set.")
                else:
                    return False



        return True


    def postappend(self):
        """This method will be called after an element is added to another and does some checks.

        It can do extra checks and if necessary raise exceptions to prevent addition. By default makes sure the right document is associated.

        This method is mostly for internal use.
        """

        #If the element was not associated with a document yet, do so now (and for all unassociated children:
        if not self.doc and self.parent.doc:
            self.setdocument(self.parent.doc)

        #Inherit xml:space attribute per XML-specification
        if (not hasattr(self,'preservespace') or self.preservespace is None) and hasattr(self.parent,'preservespace'):
            self.preservespace = self.parent.preservespace

        if self.doc and self.doc.deepvalidation:
            self.deepvalidation()

    def addtoindex(self,norecurse=[]):
        """Makes sure this element (and all subelements), are properly added to the index.

        Mostly for internal use."""
        if self.id:
            self.doc.index[self.id] = self
        for e in self.data:
            if all([not isinstance(e, C) for C in norecurse]):
                try:
                    e.addtoindex(norecurse)
                except AttributeError:
                    pass

    def deepvalidation(self):
        """Perform deep validation of this element.

        Raises:
            :class:`DeepValidationError`
        """
        if self.doc and self.doc.deepvalidation and self.set and self.set[0] != '_':
            try:
                self.doc.setdefinitions[self.set].testclass(self.cls)
                self.doc.setdefinitions[self.set].testconstraints(self.cls, { f.subset: f.cls for f in self.select(Feature,recursive=False) }, self.doc.debug)
            except KeyError:
                if self.cls and not self.doc.allowadhocsets:
                    raise DeepValidationError("Set definition " + self.set + " for " + self.XMLTAG + " not loaded (document " + self.doc.id+ ", " + str(self.doc.filename) + ")")
            except DeepValidationError as e:
                errormsg =  str(e) + " (in set " + self.set+" for " + self.XMLTAG
                if self.id:
                    errormsg += " with ID " + self.id
                errormsg += ")"
                raise DeepValidationError(errormsg)

    def append(self, child, *args, **kwargs):
        """Append a child element.

        Arguments:
            child (instance or class): 1) The instance to add (usually an instance derived from  :class:`AbstractElement`. or 2) a class subclassed from :class:`AbstractElement`.

        Keyword Arguments:
        {generic_attribs}

        If an *instance* is passed as first argument, it will be appended
        If a *class* derived from :class:`AbstractElement` is passed as first argument, an instance will first be created and then appended.

        Keyword arguments:
            alternative (bool): If set to True, the element will be made into an alternative. (default to False)

        Generic example, passing a pre-generated instance::

            word.append( folia.LemmaAnnotation(doc,  cls="house", annotator="proycon", annotatortype=folia.AnnotatorType.MANUAL ) )

        Generic example, passing a class to be generated::

            word.append( folia.LemmaAnnotation, cls="house", annotator="proycon", annotatortype=folia.AnnotatorType.MANUAL )

        Generic example, setting text with a class:

            word.append( "house", cls='original' )

        Returns:
            the added element

        Raises:
            ValueError: The element is not valid in this context
            :class:`DuplicateAnnotationError`: There is already such an annotation

        See also:
            :meth:`add`
            :meth:`insert`
            :meth:`replace`
        """.format(generic_attribs=DOCSTRING_GENERIC_ATTRIBS)



        #obtain the set (if available, necessary for checking addability)
        if 'set' in kwargs:
            set = kwargs['set']
        else:
            try:
                set = child.set
            except AttributeError:
                set = None

        #Check if a Class rather than an instance was passed
        Class = None #do not set to child.__class__
        if inspect.isclass(child):
            Class = child
            if Class.addable(self, set):
                if 'id' not in kwargs and 'generate_id_in' not in kwargs and ((Class.REQUIRED_ATTRIBS and (Attrib.ID in Class.REQUIRED_ATTRIBS)) or Class.AUTO_GENERATE_ID):
                    kwargs['generate_id_in'] = self
                child = Class(self.doc, *args, **kwargs)
        elif args:
            raise Exception("Too many arguments specified. Only possible when first argument is a class and not an instance")


        dopostappend = True

        #Do the actual appending
        if not Class and isstring(child):
            if self.TEXTCONTAINER or self.PHONCONTAINER:
                #element is a text/phon container and directly allows strings as content, add the string as such:
                self.data.append(u(child))
                dopostappend = False
            elif TextContent in self.ACCEPTED_DATA:
                #you can pass strings directly (just for convenience), will be made into textcontent automatically.
                child = TextContent(self.doc, child )
                self.data.append(child)
                child.parent = self
            elif PhonContent in self.ACCEPTED_DATA:
                #you can pass strings directly (just for convenience), will be made into phoncontent automatically (note that textcontent always takes precedence, so you most likely will have to do it explicitly)
                child = PhonContent(self.doc, child )
                self.data.append(child)
                child.parent = self
            else:
                raise ValueError("Unable to append object of type " + child.__class__.__name__ + " to " + self.__class__.__name__ + ". Type not allowed as child.")
        elif Class or (isinstance(child, AbstractElement) and child.__class__.addable(self, set)): #(prevents calling addable again if already done above)
            if 'alternative' in kwargs and kwargs['alternative']:
                child = Alternative(self.doc, child, generate_id_in=self)
            self.data.append(child)
            child.parent = self
        else:
            raise ValueError("Unable to append object of type " + child.__class__.__name__ + " to " + self.__class__.__name__ + ". Type not allowed as child.")

        if dopostappend:
            try:
                child.postappend()
            except Exception as e:
                self.data.remove(child)
                raise e
        return child

    def insert(self, index, child, *args, **kwargs):
        """Insert a child element at specified index. Returns the added element

        If an *instance* is passed as first argument, it will be appended
        If a *class* derived from AbstractElement is passed as first argument, an instance will first be created and then appended.

        Arguments:
            index (int): The position where to insert the child element
            child: Instance or class

        Keyword arguments:
            alternative (bool):  If set to True, the element will be made into an alternative.
            corrected (bool): Used only when passing strings to be made into TextContent elements.
        {generic_attribs}

        Generic example, passing a pre-generated instance::

            word.insert( 3, folia.LemmaAnnotation(doc,  cls="house", annotator="proycon", annotatortype=folia.AnnotatorType.MANUAL ) )

        Generic example, passing a class to be generated::

            word.insert( 3, folia.LemmaAnnotation, cls="house", annotator="proycon", annotatortype=folia.AnnotatorType.MANUAL )

        Generic example, setting text::

            word.insert( 3, "house" )

        Returns:
            the added element

        Raises:
            ValueError: The element is not valid in this context
            :class:`DuplicateAnnotationError`: There is already such an annotation

        See also:
            :meth:`append`
            :meth:`replace`
        """.format(generic_attribs=DOCSTRING_GENERIC_ATTRIBS)

        #obtain the set (if available, necessary for checking addability)
        if 'set' in kwargs:
            set = kwargs['set']
        else:
            try:
                set = child.set
            except AttributeError:
                set = None

        #Check if a Class rather than an instance was passed
        Class = None #do not set to child.__class__
        if inspect.isclass(child):
            Class = child
            if Class.addable(self, set):
                if 'id' not in kwargs and 'generate_id_in' not in kwargs and ((Class.REQUIRED_ATTRIBS and Attrib.ID in Class.REQUIRED_ATTRIBS) or (Class.OPTIONAL_ATTRIBS and Attrib.ID in Class.OPTIONAL_ATTRIBS)):
                    kwargs['generate_id_in'] = self
                child = Class(self.doc, *args, **kwargs)
        elif args:
            raise Exception("Too many arguments specified. Only possible when first argument is a class and not an instance")

        #Do the actual appending
        if not Class and isinstance(child,str) and TextContent in self.ACCEPTED_DATA:
            #you can pass strings directly (just for convenience), will be made into textcontent automatically.
            child = TextContent(self.doc, child )
            self.data.insert(index, child)
            child.parent = self
        elif Class or (isinstance(child, AbstractElement) and child.__class__.addable(self, set)): #(prevents calling addable again if already done above)
            if 'alternative' in kwargs and kwargs['alternative']:
                child = Alternative(self.doc, child, generate_id_in=self)
            self.data.insert(index, child)
            child.parent = self
        else:
            raise ValueError("Unable to append object of type " + child.__class__.__name__ + " to " + self.__class__.__name__ + ". Type not allowed as child.")

        try:
            child.postappend()
        except Exception as e:
            self.data.remove(child)
            raise e
        return child

    def add(self, child, *args, **kwargs):
        """Add a child element.

        This is a higher level function that adds (appends) an annotation to an element, it will simply call :meth:`AbstractElement.append` for inline annotation elements that fit within the scope. For span annotation, it will create and find or create the proper annotation layer and insert the element there.

        Arguments:
            child (instance or class): 1) The instance to add (usually an instance derived from  :class:`AbstractElement`. or 2) a class subclassed from :class:`AbstractElement`.

        If an *instance* is passed as first argument, it will be appended
        If a *class* derived from :class:`AbstractElement` is passed as first argument, an instance will first be created and then appended.

        Keyword arguments:
            alternative (bool): If set to True, the element will be made into an alternative. (default to False)
        {generic_attribs}

        Generic example, passing a pre-generated instance::
            word.add( folia.LemmaAnnotation(doc,  cls="house", annotator="proycon", annotatortype=folia.AnnotatorType.MANUAL ) )

        Generic example, passing a class to be generated::

            word.add( folia.LemmaAnnotation, cls="house", annotator="proycon", annotatortype=folia.AnnotatorType.MANUAL )

        Generic example, setting text with a class::

            word.add( "house", cls='original' )

        Returns:
            the added element

        Raises:
            ValueError: The element is not valid in this context
            :class:`DuplicateAnnotationError`: There is already such an annotation

        See also:
            :meth:`add`
            :meth:`insert`
            :meth:`replace`
        """.format(generic_attribs=DOCSTRING_GENERIC_ATTRIBS)

        addspanfromspanned = False #add a span annotation element from that which is spanned (i.e. a Word, Morpheme)
        addspanfromstructure = False #add a span annotation elements from a structural parent which holds the span layers? (e.g. a Sentence, Paragraph)
        if (inspect.isclass(child) and issubclass(child, AbstractSpanAnnotation)) or (not inspect.isclass(child) and isinstance(child, AbstractSpanAnnotation)):
            layerclass = ANNOTATIONTYPE2LAYERCLASS[child.ANNOTATIONTYPE]
            if isinstance(self, wrefables):
                addspanfromspanned = True
            elif isinstance(self,AbstractStructureElement): #add a span
                addspanfromstructure = True

        if addspanfromspanned or addspanfromstructure:
            #get the set
            if 'set' in kwargs:
                set = kwargs['set']
            else:
                set = self.doc.defaultset(layerclass)
                if set is False:
                    raise Exception("No set defined when adding span annotation and none could be inferred")

        if addspanfromspanned: #pylint: disable=too-many-nested-blocks
            #collect ancestors of the current element,
            allowedparents = [self] + list(self.ancestors(AbstractStructureElement))
            #find common ancestors of structure elements in the arguments, and check whether it has the required annotation layer, create one if necessary
            for e in commonancestors(AbstractStructureElement,  *[ x for x in args if isinstance(x, AbstractStructureElement)] ):
                if e in allowedparents: #is the element in the list of allowed parents according to this element?
                    if AbstractAnnotationLayer in e.ACCEPTED_DATA or layerclass in e.ACCEPTED_DATA:
                        try:
                            layer = next(e.select(layerclass,set,True))
                        except StopIteration:
                            layer = e.append(layerclass)
                        if 'emptyspan' in kwargs and kwargs['emptyspan']:
                            del kwargs['emptyspan']
                            return layer.append(child,*[],**kwargs)
                        else:
                            return layer.append(child,*args,**kwargs)

            raise Exception("Unable to find suitable common ancestor to create annotation layer")
        elif addspanfromstructure:
            layer = None
            for layer in self.layers(child.ANNOTATIONTYPE, set):
                pass #last one (only one actually) should be available in outer context
            if layer is None:
                layer = self.append(layerclass)
            return layer.append(child,*args,**kwargs)
        else:
            #normal behaviour, append
            return self.append(child,*args,**kwargs)




    @classmethod
    def findreplaceables(Class, parent, set=False,**kwargs):
        """Internal method to find replaceable elements. Auxiliary function used by :meth:`AbstractElement.replace`. Can be overriden for more fine-grained control."""
        return list(parent.select(Class,set,False))



    def updatetext(self):
        """Recompute textual value based on the text content of the children. Only supported on elements that are a ``TEXTCONTAINER``"""
        if self.TEXTCONTAINER:
            s = ""
            for child in self:
                if isinstance(child, AbstractElement):
                    child.updatetext()
                    s += child.text()
                elif isstring(child):
                    s += child
            self.data = [s]

    def replace(self, child, *args, **kwargs):
        """Appends a child element like ``append()``, but replaces any existing child element of the same type and set. If no such child element exists, this will act the same as append()

        Keyword arguments:
            alternative (bool): If set to True, the *replaced* element will be made into an alternative. Simply use :meth:`AbstractElement.append` if you want the added element
            to be an alternative.

        See :meth:`AbstractElement.append` for more information and all parameters.
        """

        if 'set' in kwargs:
            set = kwargs['set']
            del kwargs['set']
        else:
            try:
                set = child.set
            except AttributeError:
                set = False

        if inspect.isclass(child):
            Class = child
            replace = Class.findreplaceables(self, set, **kwargs)
        elif (self.TEXTCONTAINER or self.PHONCONTAINER) and isstring(child):
            #replace will replace ALL text content, removing text markup along the way!
            self.data = []
            return self.append(child, *args,**kwargs)
        else:
            Class = child.__class__
            kwargs['instance'] = child
            replace = Class.findreplaceables(self,set,**kwargs)
            del kwargs['instance']

        kwargs['set'] = set #was deleted temporarily for findreplaceables

        if len(replace) == 0:
            #nothing to replace, simply call append
            if 'alternative' in kwargs:
                del kwargs['alternative'] #has other meaning in append()
            return self.append(child, *args, **kwargs)
        elif len(replace) > 1:
            raise Exception("Unable to replace. Multiple candidates found, unable to choose.")
        elif len(replace) == 1:
            if 'alternative' in kwargs and kwargs['alternative']:
                #old version becomes alternative
                if replace[0] in self.data:
                    self.data.remove(replace[0])
                alt = self.append(Alternative)
                alt.append(replace[0])
                del kwargs['alternative'] #has other meaning in append()
            else:
                #remove old version competely
                self.remove(replace[0])
            e = self.append(child, *args, **kwargs)
            self.updatetext()
            return e

    def substitute(self, oldchild, newchild, *args, **kwargs):
        """Substitutes a particular child element with another. The child element can be specified like with ``append()``. Unlike the ``replace()`` function, here you specify explicitly the old child elements, and it can be any child element.

        Arguments:
            oldchild: The child instance to replace

        See :meth:`AbstractElement.append` for more information and all parameters.
        """
        index = self.getindex(oldchild)
        self.data[index] = None #temporarily clear the entry so it doesn't interfere in any checks

        if inspect.isclass(newchild):
            newchild = newchild(self.doc, *args, **kwargs)

        if isinstance(oldchild, AbstractElement):
            oldchild.parent = None
            if oldchild.id and oldchild.id in self.doc.index:
                del self.doc.index[oldchild.id]

        if isinstance(newchild,str) and TextContent in self.ACCEPTED_DATA:
            newchild = TextContent(self.doc, newchild)


        if isinstance(newchild, AbstractElement) and newchild.__class__.addable(self, newchild.set):
            self.data[index] = newchild
        elif isinstance(newchild, str) and (self.TEXTCONTAINER or self.PHONCONTAINER):
            self.data[index] = newchild
        else:
            raise ValueError("Unable to substitute to an object of type " + newchild.__class__.__name__ + " in " + self.__class__.__name__ + ". Type not allowed as child.")

        try:
            newchild.postappend()
        except Exception as e:
            self.data.remove(newchild)
            raise e

    def ancestors(self, Class=None):
        """Generator yielding all ancestors of this element, effectively back-tracing its path to the root element. A tuple of multiple classes may be specified.

        Arguments:
            *Class: The class or (tuple of) classes (:class:`AbstractElement` or subclasses). Not instances!

        Yields:
            elements (instances derived from :class:`AbstractElement`)
        """
        e = self
        while e:
            if e.parent:
                e = e.parent
                if not Class or isinstance(e,Class):
                    yield e
                elif isinstance(Class, tuple):
                    for C in Class:
                        if isinstance(e,C):
                            yield e
            else:
                break

    def ancestor(self, *Classes):
        """Find the most immediate ancestor of the specified type, multiple classes may be specified. Raise a NoSuchAnnotation exception if not found.

        Arguments:
            * Classes: The possible classes (:class:`AbstractElement` or subclasses) to select from. Not instances!

        Example::

            paragraph = word.ancestor(folia.Paragraph)
        """
        for e in self.ancestors(tuple(Classes)):
            return e
        raise NoSuchAnnotation


    def xml(self, attribs = None,elements = None, skipchildren = False, form = Form.NORMAL):
        """Serialises the FoLiA element and all its contents to XML.

        Arguments are mostly for internal use.

        Returns:
            an lxml.etree.Element

        See also:
            :meth:`AbstractElement.xmlstring` - for direct string output
        """
        if self.doc:
            FOLIA1 = self.doc.FOLIA1
        else:
            FOLIA1 = False

        if not attribs: attribs = {}
        if not elements: elements = []

        if self.id:
            attribs['{http://www.w3.org/XML/1998/namespace}id'] = self.id

        #output xml:space (value is typically None, meaning it doesn't get ouputted)
        if self.preservespace is True:
            attribs['{http://www.w3.org/XML/1998/namespace}space'] = "preserve"
        elif self.preservespace is False:
            attribs['{http://www.w3.org/XML/1998/namespace}space'] = "default"

        if form == Form.EXPLICIT:
            if isinstance(self, AbstractStructureElement):
                attribs['typegroup'] = "structure"
            elif isinstance(self, AbstractInlineAnnotation):
                attribs['typegroup'] = "inline"
            elif isinstance(self, AbstractHigherOrderAnnotation):
                attribs['typegroup'] = "higherorder"
            elif isinstance(self, AbstractSpanRole):
                attribs['typegroup'] = "spanrole"
            elif isinstance(self, AbstractSpanAnnotation):
                attribs['typegroup'] = "span"
            elif isinstance(self, AbstractTextMarkup):
                attribs['typegroup'] = "textmarkup"
            elif isinstance(self, AbstractContentAnnotation):
                attribs['typegroup'] = "content"
            elif isinstance(self, AbstractAnnotationLayer):
                attribs['typegroup'] = "layer"
            elif isinstance(self, AbstractSubtokenAnnotation):
                attribs['typegroup'] = "subtoken"
            elif isinstance(self, AbstractCorrectionChild):
                attribs['typegroup'] = "correctionchild"
            elif isinstance(self, Feature):
                attribs['typegroup'] = "feature"

        #The set attribute is only added on elements that can take classes
        takes_class = (self.REQUIRED_ATTRIBS and Attrib.CLASS in self.REQUIRED_ATTRIBS) or (self.OPTIONAL_ATTRIBS and Attrib.CLASS in self.OPTIONAL_ATTRIBS)
        if takes_class and not isinstance(self, AbstractAnnotationLayer):
            if self.set and 'set' not in attribs: #do not override if overloaded function already set it
                if self.doc:
                    #Is there a default set? If so, we need not serialise the set attribute (except in explicit form)
                    try:
                        defaultset = self.doc.defaultset(self.ANNOTATIONTYPE)
                    except NoSuchAnnotation:
                        if not FOLIA1: #This may happen for FoLiA v1 as not everything is declared there, for FoLiA v2 we can be strict though
                            raise
                        defaultset = False
                    if self.set != defaultset or form == Form.EXPLICIT:
                        if form != Form.EXPLICIT and self.ANNOTATIONTYPE in self.doc.set_alias and self.set in self.doc.set_alias[self.ANNOTATIONTYPE]:
                            attribs['set'] = self.doc.set_alias[self.ANNOTATIONTYPE][self.set] #use alias instead
                        elif FOLIA1 and self.doc.keepversion and self.set == "undefined":
                            pass #we don't output the 'undefined' set in FoLiA v1, it is the implicit default
                        else:
                            attribs['set'] = self.set
                else:
                    #no document so no declarations, serialise everything
                    attribs['set'] = self.set

        if 'class' not in attribs: #do not override if caller already set it
            if self.cls:
                attribs['class'] = self.cls

        if 'processor' not in attribs: #do not override if caller already set it
            if self.ANNOTATIONTYPE in self.doc.annotators and self.set in self.doc.annotators[self.ANNOTATIONTYPE] and self.doc.annotators[self.ANNOTATIONTYPE][self.set] and ((self.OPTIONAL_ATTRIBS is not None and Attrib.ANNOTATOR in self.OPTIONAL_ATTRIBS) or (self.REQUIRED_ATTRIBS is not None and Attrib.ANNOTATOR in self.REQUIRED_ATTRIBS)):
                #there are new-style (FoLiA v2) annotators (pointing to processors in provenance data)
                try:
                    defaultprocessor = self.doc.getdefaultprocessor(self.ANNOTATIONTYPE, self.set)
                    if form == Form.EXPLICIT:
                        attribs['processor'] = defaultprocessor.id
                except NoDefaultError:
                    if not (FOLIA1 and self.doc.keepversion) and self.processor:
                        attribs['processor'] = self.processor.id


        if 'annotator' not in attribs and not self.processor: #do not override if caller already set it
            if self.annotator and (self.ANNOTATIONTYPE not in self.doc.annotationdefaults or self.set not in self.doc.annotationdefaults[self.ANNOTATIONTYPE] or 'annotator' not in self.doc.annotationdefaults[self.ANNOTATIONTYPE][self.set] or self.annotator != self.doc.annotationdefaults[self.ANNOTATIONTYPE][self.set]['annotator']):
                attribs['annotator'] = self.annotator
            if self.annotatortype and (self.ANNOTATIONTYPE not in self.doc.annotationdefaults or self.set not in self.doc.annotationdefaults[self.ANNOTATIONTYPE] or 'annotatortype' not in self.doc.annotationdefaults[self.ANNOTATIONTYPE][self.set] or self.annotatortype != self.doc.annotationdefaults[self.ANNOTATIONTYPE][self.set]['annotatortype']):
                if self.annotatortype == AnnotatorType.AUTO:
                    attribs['annotatortype'] = 'auto'
                elif self.annotatortype == AnnotatorType.MANUAL:
                    attribs['annotatortype'] = 'manual'

        if 'confidence' not in attribs: #do not override if caller already set it
            if self.confidence is not None:
                attribs['confidence'] = str(self.confidence)

        if 'n' not in attribs: #do not override if caller already set it
            if self.n is not None:
                attribs['n'] = str(self.n)

        if 'auth' not in attribs: #do not override if caller already set it
            try:
                if not self.AUTH or not self.auth: #(former is static, latter isn't)
                    attribs['auth'] = 'no'
            except AttributeError:
                pass

        if 'datetime' not in attribs: #do not override if caller already set it
            if self.datetime and (self.ANNOTATIONTYPE not in self.doc.annotationdefaults or self.set not in self.doc.annotationdefaults[self.ANNOTATIONTYPE] or 'datetime' not in self.doc.annotationdefaults[self.ANNOTATIONTYPE][self.set] or self.datetime != self.doc.annotationdefaults[self.ANNOTATIONTYPE][self.set]['datetime']):
                attribs['datetime'] = self.datetime.strftime("%Y-%m-%dT%H:%M:%S")

        if 'src' not in attribs: #do not override if caller already set it
            if self.src:
                attribs['src'] = self.src

        if 'speaker' not in attribs: #do not override if caller already set it
            if self.speaker:
                attribs['speaker'] = self.speaker

        if 'begintime' not in attribs: #do not override if caller already set it
            if self.begintime:
                attribs['begintime'] = "%02d:%02d:%02d.%03d" % self.begintime

        if 'endtime' not in attribs: #do not override if caller already set it
            if self.endtime:
                attribs['endtime'] = "%02d:%02d:%02d.%03d" % self.endtime

        if 'textclass' not in attribs: #do not override if caller already set it
            if self.textclass and (self.textclass != "current" or form == Form.EXPLICIT):
                attribs['textclass'] = self.textclass

        if self.OPTIONAL_ATTRIBS and Attrib.SPACE in self.OPTIONAL_ATTRIBS and not self.space:
            attribs['space'] = 'no'

        if 'metadata' not in attribs: #do not override if caller already set it
            if self.metadata and self.metadata in self.doc.submetadata:
                attribs['metadata'] = self.metadata


        if self.XLINK:
            if self.href:
                attribs['{http://www.w3.org/1999/xlink}href'] = self.href
                if not self.xlinktype:
                    attribs['{http://www.w3.org/1999/xlink}type'] = "simple"
            if self.xlinktype:
                attribs['{http://www.w3.org/1999/xlink}type'] = self.xlinktype
            if self.xlinklabel:
                attribs['{http://www.w3.org/1999/xlink}label'] = self.xlinklabel
            if self.xlinkrole:
                attribs['{http://www.w3.org/1999/xlink}role'] = self.xlinkrole
            if self.xlinkshow:
                attribs['{http://www.w3.org/1999/xlink}show'] = self.xlinkshow
            if self.xlinktitle:
                attribs['{http://www.w3.org/1999/xlink}title'] = self.xlinktitle

        omitchildren =  []

        #Are there predetermined Features in ACCEPTED_DATA?
        if form == Form.NORMAL:
            for c in self.ACCEPTED_DATA:
                if issubclass(c, Feature) and c.SUBSET:
                    #Do we have any of those?
                    for c2 in self.data:
                        if c2.__class__ is c and c.SUBSET == c2.SUBSET and c2.cls:
                            #Yes, serialize them as attributes
                            attribs[c2.SUBSET] = c2.cls
                            omitchildren.append(c2) #and skip them as elements
                            break #only one

        tag = self.XMLTAG
        if self.doc and FOLIA1 and self.doc.keepversion and tag in OLDTAGS_REVERSE and tag != "item":
            tag = OLDTAGS_REVERSE[tag]
        e = E(tag,**attribs)

        if self.tags:
            #we have to add this after the creating because ElementMaker treats 'tag' as a reserved keyword parameter
            e.attrib['tag'] = " ".join(self.tags) #XML property uses singular, API plural


        if not skipchildren and self.data:
            #append children,
            # we want make sure that text elements are in the right order, 'current' class first
            # so we first put them in  a list
            textelements = []
            otherelements = []
            for child in self:
                if isinstance(child, TextContent):
                    if child.cls == 'current':
                        textelements.insert(0, child)
                    else:
                        textelements.append(child)
                elif not child in omitchildren:
                    otherelements.append(child)
            for child in textelements+otherelements:
                if (self.TEXTCONTAINER or self.PHONCONTAINER) and isstring(child):
                    if len(e) == 0:
                        if e.text:
                            e.text += child
                        else:
                            e.text = child
                    else:
                        #add to tail of last child
                        if e[-1].tail:
                            e[-1].tail += child
                        else:
                            e[-1].tail = child

                else:
                    xml = child.xml(form=form) #may return None in rare occassions, meaning we want to skip
                    if not xml is None:
                        e.append(xml)

        if elements: #extra elements
            for e2 in elements:
                if isinstance(e2, str):
                    if e.text is None:
                        e.text = e2
                    else:
                        e.text += e2
                else:
                    e.append(e2)
        return e


    def json(self, attribs=None, recurse=True, ignorelist=False):
        """Serialises the FoLiA element and all its contents to a Python dictionary suitable for serialisation to JSON.

        Example::

            import json
            json.dumps(word.json())

        Returns:
            dict
        """
        jsonnode = {}

        jsonnode['type'] = self.XMLTAG
        if self.id:
            jsonnode['id'] = self.id
        if self.set:
            jsonnode['set'] = self.set
        if self.cls:
            jsonnode['class'] = self.cls
        if self.processor:
            jsonnode['processor'] = self.processor.id
        else:
            if self.annotator:
                jsonnode['annotator'] = self.annotator
            if self.annotatortype:
                if self.annotatortype == AnnotatorType.AUTO:
                    jsonnode['annotatortype'] = "auto"
                elif self.annotatortype == AnnotatorType.MANUAL:
                    jsonnode['annotatortype'] = "manual"
        if self.confidence is not None:
            jsonnode['confidence'] = self.confidence
        if self.n:
            jsonnode['n'] = self.n
        if self.auth:
            jsonnode['auth'] = self.auth
        if self.datetime:
            jsonnode['datetime'] = self.datetime.strftime("%Y-%m-%dT%H:%M:%S")
        if self.OPTIONAL_ATTRIBS and Attrib.SPACE in self.OPTIONAL_ATTRIBS and not self.space:
            jsonnode['space'] = "no"

        if self.XLINK:
            if self.href:
                jsonnode['href'] = self.href

        if recurse: #pylint: disable=too-many-nested-blocks
            jsonnode['children'] = []
            if self.TEXTCONTAINER:
                jsonnode['text'] = self.text()
            if self.PHONCONTAINER:
                jsonnode['phon'] = self.phon()
            for child in self:
                if self.TEXTCONTAINER and isstring(child):
                    jsonnode['children'].append(child)
                elif not self.PHONCONTAINER:
                    #check ignore list
                    ignore = False
                    if ignorelist:
                        for e in ignorelist:
                            if isinstance(child,e):
                                ignore = True
                                break
                    if not ignore:
                        jsonnode['children'].append(child.json(attribs,recurse,ignorelist))

        if attribs:
            for key, value in attribs.items():
                jsonnode[key] = value

        return jsonnode



    def xmlstring(self, pretty_print=False, form= Form.NORMAL):
        """Serialises this FoLiA element and all its contents to XML.

        Returns:
            str: a string with XML representation for this element and all its children"""
        return str(ElementTree.tostring(self.xml(form=form), xml_declaration=False, pretty_print=pretty_print, encoding='utf-8'),'utf-8')


    def select(self, Class, set=False, recursive=True,  ignore=True, node=None): #pylint: disable=bad-classmethod-argument,redefined-builtin
        """Select child elements of the specified class.

        A further restriction can be made based on set.

        Arguments:
            Class (class): The class to select; any python class (not instance) subclassed off :class:`AbstractElement`
            Set (str): The set to match against, only elements pertaining to this set will be returned. If set to False (default), all elements regardless of set will be returned.
            recursive (bool): Select recursively? Descending into child elements? Defaults to ``True``.
            ignore: A list of Classes to ignore, if set to ``True`` instead of a list, all non-authoritative elements will be skipped (this is the default behaviour and corresponds to the following elements: :class:`Alternative`, :class:`AlternativeLayers`, :class:`Suggestion`, and :class:`folia.Original`. These elements and those contained within are never *authorative*. You may also include the boolean True as a member of a list, if you want to skip additional tags along the predefined non-authoritative ones.
            * ``node``: Reserved for internal usage, used in recursion.

        Yields:
            Elements (instances derived from :class:`AbstractElement`)

        Example::

            for sense in text.select(folia.Sense, 'cornetto', True, [folia.Original, folia.Suggestion, folia.Alternative] ):
                ..

        """

        #if ignorelist is True:
        #    ignorelist = default_ignore

        if not node:
            node = self
        for e in self.data: #pylint: disable=too-many-nested-blocks
            if e is None: continue #may sometimes occur as a temporary placeholder
            if (not self.TEXTCONTAINER and not self.PHONCONTAINER) or isinstance(e, AbstractElement):
                if ignore is True:
                    try:
                        if not e.auth:
                            continue
                    except AttributeError:
                        #not all elements have auth attribute..
                        pass
                elif ignore: #list
                    doignore = False
                    for c in ignore:
                        if c is True:
                            try:
                                if not e.auth:
                                    doignore =True
                                    break
                            except AttributeError:
                                #not all elements have auth attribute..
                                pass
                        elif c == e.__class__ or issubclass(e.__class__,c):
                            doignore = True
                            break
                    if doignore:
                        continue

                if isinstance(e, Class):
                    if set is not False:
                        try:
                            if e.set != set:
                                continue
                        except AttributeError:
                            continue
                    yield e
                if recursive:
                    for e2 in e.select(Class, set, recursive, ignore, e):
                        if set is not False:
                            try:
                                if e2.set != set:
                                    continue
                            except AttributeError:
                                continue
                        yield e2

    def count(self, Class, set=False, recursive=True,  ignore=True, node=None):
        """Like :meth:`AbstractElement.select`, but instead of returning the elements, it merely counts them.

        Returns:
            int
        """
        return sum(1 for i in self.select(Class,set,recursive,ignore,node) )

    def items(self, founditems=None): #pylint: disable=dangerous-default-value
        """Returns a depth-first flat list of *all* items below this element (not limited to AbstractElement)"""
        if founditems is None: founditems = set()
        l = []
        for e in self.data:
            if id(e) not in founditems: #prevent going in recursive loops
                founditems.add(id(e))
                l.append(e)
                if isinstance(e, AbstractElement):
                    l += e.items(l, founditems)
        return l

    def elements(self, founditems=None): #pylint: disable=dangerous-default-value
        """Returns a depth-first flat list of *all* elements below this element"""
        if founditems is None: founditems = set()
        l = []
        for e in self.data:
            if id(e) not in founditems: #prevent going in recursive loops
                if isinstance(e, AbstractElement):
                    founditems.add(id(e))
                    l.append(e)
                    l += e.elements(founditems)
        return l

    def getmetadata(self, key=None):
        """Get the metadata that applies to this element, automatically inherited from parent elements"""
        if self.metadata:
            d =  self.doc.submetadata[self.metadata]
        elif self.parent:
            d =  self.parent.getmetadata()
        elif self.doc:
            d =  self.doc.metadata
        else:
            return None
        if key:
            return d[key]
        else:
            return d



    def getindex(self, child, recursive=True, ignore=True):
        """Get the index at which an element occurs, recursive by default!

        Returns:
            int
        """

        #breadth first search
        for i, c in enumerate(self.data):
            if c is child:
                return i
        if recursive:  #pylint: disable=too-many-nested-blocks
            for i, c in enumerate(self.data):
                if ignore is True:
                    try:
                        if not c.auth:
                            continue
                    except AttributeError:
                        #not all elements have auth attribute..
                        pass
                elif ignore: #list
                    doignore = False
                    for e in ignore:
                        if e is True:
                            try:
                                if not c.auth:
                                    doignore =True
                                    break
                            except AttributeError:
                                #not all elements have auth attribute..
                                pass
                        elif e == c.__class__ or issubclass(c.__class__,e):
                            doignore = True
                            break
                    if doignore:
                        continue
                if isinstance(c, AbstractElement):
                    j = c.getindex(child, recursive)
                    if j != -1:
                        return i #yes, i ... not j!
        return -1

    def precedes(self, other):
        """Returns a boolean indicating whether this element precedes the other element"""
        if not self.parent:
            raise NoCommonAncestor("Element " + repr(self) + " has no parent!")
        elif not other.parent:
            raise NoCommonAncestor("Other element " + repr(other) + " has no parent!")
        try:
            ancestor = next(commonancestors(AbstractElement, self, other))
        except StopIteration:
            raise NoCommonAncestor("Elements share no common ancestor")
        #now we just do a depth first search and see who comes first
        def callback(e):
            if e is self:
                return True
            elif e is other:
                return False
            return None
        result = ancestor.depthfirstsearch(callback)
        if result is None:
            raise Exception("Unable to find relation between elements! (shouldn't happen)")
        return result


    def depthfirstsearch(self, function):
        """Generic depth first search algorithm using a callback function, continues as long as the callback function returns None"""
        result = function(self)
        if result is not None:
            return result
        for e in self:
            if isinstance(e, AbstractElement):
                result = e.depthfirstsearch(function)
                if result is not None:
                    return result
        return None

    def next(self, Class=True, scope=True, reverse=False):
        """Returns the next element, if it is of the specified type and if it does not cross the boundary of the defined scope. Returns None if no next element is found. Non-authoritative elements are never returned.

        Arguments:
            * ``Class``: The class to select; any python class subclassed off `'AbstractElement``, may also be a tuple of multiple classes. Set to ``True`` to constrain to the same class as that of the current instance, set to ``None`` to not constrain at all
            * ``scope``: A list of classes which are never crossed looking for a next element. Set to ``True`` to constrain to a default list of structure elements (Sentence,Paragraph,Division,Event, ListItem,Caption), set to ``None`` to not constrain at all.

        """
        if Class is True: Class = self.__class__
        if scope is True: scope = STRUCTURESCOPE

        if isinstance(Class, (tuple,list)):
            structural = any(issubclass(C,AbstractStructureElement) for C in Class)
        else:
            structural = Class is not None and issubclass(Class,AbstractStructureElement)

        if reverse:
            order = reversed
            descendindex = -1
        else:
            order = lambda x: x
            descendindex = 0

        child = self
        parent = self.parent
        while parent: #pylint: disable=too-many-nested-blocks
            if len(parent) > 1:
                returnnext = False
                for e in order(parent):
                    if e is child:
                        #we found the current item, next item will be the one to return
                        returnnext = True
                    elif returnnext and isinstance(e, AbstractElement) and e.auth and not isinstance(e,AbstractAnnotationLayer) and (not structural or (structural and (not isinstance(e,(AbstractInlineAnnotation,TextContent)) ) )):
                        if structural and isinstance(e,Correction):
                            if not list(e.select(AbstractStructureElement)): #skip-over non-structural correction
                                continue

                        if Class is None or (isinstance(Class,tuple) and (any(isinstance(e,C) for C in Class))) or isinstance(e,Class):
                            return e
                        else:
                            #this is not yet the element of the type we are looking for, we are going to descend again in the very leftmost (rightmost if reversed) branch only
                            while e.data:
                                e = e.data[descendindex]
                                if not isinstance(e, AbstractElement):
                                    return None #we've gone too far
                                if e.auth and not isinstance(e,AbstractAnnotationLayer):
                                    if Class is None or (isinstance(Class,tuple) and (any(isinstance(e,C) for C in Class))) or isinstance(e,Class):
                                        return e
                                    else:
                                        #descend deeper
                                        continue
                        return None

            #generational iteration
            child = parent
            if scope is not None and child.__class__ in scope:
                #you shall not pass!
                break
            parent = parent.parent

        return None



    def previous(self, Class=True, scope=True):
        """Returns the previous element, if it is of the specified type and if it does not cross the boundary of the defined scope. Returns None if no next element is found. Non-authoritative elements are never returned.

        Arguments:
            * ``Class``: The class to select; any python class subclassed off `'AbstractElement``, may also be a tuple of multiple classes. Set to ``True`` to constrain to the same class as that of the current instance, set to ``None`` to not constrain at all
            * ``scope``: A list of classes which are never crossed looking for a next element. Set to ``True`` to constrain to a default list of structure elements (Sentence,Paragraph,Division,Event, ListItem,Caption), set to ``None`` to not constrain at all.

        """
        return self.next(Class,scope, True)

    def leftcontext(self, size, placeholder=None, scope=None):
        """Returns the left context for an element, as a list. This method crosses sentence/paragraph boundaries by default, which can be restricted by setting scope"""

        if size == 0: return [] #for efficiency

        context = []
        e = self
        while len(context) < size:
            e = e.previous(True,scope)
            if not e: break
            context.append(e)

        if placeholder:
            while len(context) < size:
                context.append(placeholder)

        context.reverse()
        return context


    def rightcontext(self, size, placeholder=None, scope=None):
        """Returns the right context for an element, as a list. This method crosses sentence/paragraph boundaries by default, which can be restricted by setting scope"""

        if size == 0: return [] #for efficiency

        context = []
        e = self
        while len(context) < size:
            e = e.next(True,scope)
            if not e: break
            context.append(e)

        if placeholder:
            while len(context) < size:
                context.append(placeholder)

        return context

    def context(self, size, placeholder=None, scope=None):
        """Returns this word in context, {size} words to the left, the current word, and {size} words to the right"""
        return self.leftcontext(size, placeholder,scope) + [self] + self.rightcontext(size, placeholder,scope)

    @classmethod
    def relaxng(cls, includechildren=True,extraattribs = None, extraelements=None, origclass = None):
        """Returns a RelaxNG definition for this element (as an XML element (lxml.etree) rather than a string)"""


        if origclass: cls = origclass

        preamble = []
        try:
            if cls.__doc__:
                E2 = ElementMaker(namespace="http://relaxng.org/ns/annotation/0.9", nsmap={'a':'http://relaxng.org/ns/annotation/0.9'} )
                preamble.append(E2.documentation(cls.__doc__))
        except AttributeError:
            pass

        if cls.REQUIRED_ATTRIBS is None: cls.REQUIRED_ATTRIBS = () #bit hacky
        if cls.OPTIONAL_ATTRIBS is None: cls.OPTIONAL_ATTRIBS = () #bit hacky


        attribs = [ ]
        if cls.REQUIRED_ATTRIBS and Attrib.ID in cls.REQUIRED_ATTRIBS:
            attribs.append( RXE.attribute(RXE.data(type='ID',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'),name='id', ns="http://www.w3.org/XML/1998/namespace") )
        elif Attrib.ID in cls.OPTIONAL_ATTRIBS:
            attribs.append( RXE.optional( RXE.attribute(RXE.data(type='ID',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='id', ns="http://www.w3.org/XML/1998/namespace") ) )
        if Attrib.CLASS in cls.REQUIRED_ATTRIBS:
            attribs.append( RXE.attribute(RXE.data(type='string',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'),name='class') )
            attribs.append( RXE.optional( RXE.attribute( RXE.data(type='string',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'),name='set' ) ) )
        elif Attrib.CLASS in cls.OPTIONAL_ATTRIBS:
            attribs.append( RXE.optional( RXE.attribute(RXE.data(type='string',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'),name='class') ) )
            attribs.append( RXE.optional( RXE.attribute(RXE.data(type='string',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='set' ) ) )
        if Attrib.ANNOTATOR in cls.REQUIRED_ATTRIBS or Attrib.ANNOTATOR in cls.OPTIONAL_ATTRIBS:
            #FoLiA without provenance
            attribs.append( RXE.optional( RXE.attribute(RXE.data(type='string',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='annotator') ) )
            attribs.append( RXE.optional( RXE.attribute(name='annotatortype') ) )
            #FoLiA >2.0 provenance
            attribs.append( RXE.optional( RXE.attribute(RXE.data(type='IDREF',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='processor') ) )
        if Attrib.CONFIDENCE in cls.REQUIRED_ATTRIBS:
            attribs.append(  RXE.attribute(RXE.data(type='double',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='confidence') )
        elif Attrib.CONFIDENCE in cls.OPTIONAL_ATTRIBS:
            attribs.append(  RXE.optional( RXE.attribute(RXE.data(type='double',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='confidence') ) )
        if Attrib.N in cls.REQUIRED_ATTRIBS:
            attribs.append( RXE.attribute( RXE.data(type='string',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'),name='n') )
        elif Attrib.N in cls.OPTIONAL_ATTRIBS:
            attribs.append( RXE.optional( RXE.attribute( RXE.data(type='string',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'),name='n') ) )
        if Attrib.DATETIME in cls.REQUIRED_ATTRIBS:
            attribs.append( RXE.attribute(RXE.data(type='dateTime',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='datetime') )
        elif Attrib.DATETIME in cls.OPTIONAL_ATTRIBS:
            attribs.append( RXE.optional( RXE.attribute( RXE.data(type='dateTime',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'),  name='datetime') ) )
        if Attrib.BEGINTIME in cls.REQUIRED_ATTRIBS:
            attribs.append(RXE.attribute(name='begintime') )
        elif Attrib.BEGINTIME in cls.OPTIONAL_ATTRIBS:
            attribs.append( RXE.optional( RXE.attribute(name='begintime') ) )
        if Attrib.ENDTIME in cls.REQUIRED_ATTRIBS:
            attribs.append(RXE.attribute(name='endtime') )
        elif Attrib.ENDTIME in cls.OPTIONAL_ATTRIBS:
            attribs.append( RXE.optional( RXE.attribute(name='endtime') ) )
        if Attrib.SRC in cls.REQUIRED_ATTRIBS:
            attribs.append(RXE.attribute(RXE.data(type='anyURI',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'),name='src') )
        elif Attrib.SRC in cls.OPTIONAL_ATTRIBS:
            attribs.append( RXE.optional( RXE.attribute(RXE.data(type='anyURI',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'),name='src') ) )
        if Attrib.SPEAKER in cls.REQUIRED_ATTRIBS:
            attribs.append(RXE.attribute(RXE.data(type='string',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='speaker') )
        elif Attrib.SPEAKER in cls.OPTIONAL_ATTRIBS:
            attribs.append( RXE.optional( RXE.attribute(RXE.data(type='string',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'),name='speaker') ) )
        if Attrib.TEXTCLASS in cls.REQUIRED_ATTRIBS:
            attribs.append(RXE.attribute(name='textclass') )
        elif Attrib.TEXTCLASS in cls.OPTIONAL_ATTRIBS:
            attribs.append( RXE.optional( RXE.attribute(name='textclass') ) )
        if Attrib.METADATA in cls.REQUIRED_ATTRIBS:
            attribs.append(RXE.attribute(name='metadata') )
        elif Attrib.METADATA in cls.OPTIONAL_ATTRIBS:
            attribs.append( RXE.optional( RXE.attribute(name='metadata') ) )
        if Attrib.SPACE in cls.REQUIRED_ATTRIBS:
            attribs.append(RXE.attribute(name='space') )
        elif Attrib.SPACE in cls.OPTIONAL_ATTRIBS:
            attribs.append( RXE.optional( RXE.attribute(name='space') ) )
        if Attrib.TAG in cls.OPTIONAL_ATTRIBS:
            attribs.append( RXE.optional( RXE.attribute(name='tag') ) )
        attribs.append( RXE.optional( RXE.attribute(name='typegroup') ) )  #used in explicit form only
        attribs.append( RXE.optional(RXE.attribute(RXE.data(type='string',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'),name='space', ns="http://www.w3.org/XML/1998/namespace")) )  #xml:space attribute

        if cls.XLINK:
            attribs += [ #loose interpretation of specs, not checking whether xlink combinations are valid
                    RXE.optional(RXE.attribute(name='href',ns="http://www.w3.org/1999/xlink"),RXE.attribute(name='type',ns="http://www.w3.org/1999/xlink") ),
                    RXE.optional(RXE.attribute(name='role',ns="http://www.w3.org/1999/xlink")),
                    RXE.optional(RXE.attribute(name='title',ns="http://www.w3.org/1999/xlink")),
                    RXE.optional(RXE.attribute(name='label',ns="http://www.w3.org/1999/xlink")),
                    RXE.optional(RXE.attribute(name='show',ns="http://www.w3.org/1999/xlink")),
            ]

        attribs.append( RXE.optional( RXE.attribute( name='auth' ) ) )



        if extraattribs:
            for e in extraattribs:
                attribs.append(e) #s

        attribs.append( RXE.ref(name="allow_foreign_attributes") )


        elements = [] #(including attributes)
        if cls.TEXTCONTAINER or cls.PHONCONTAINER:
            elements.append( RXE.text())
            #We actually want to require non-empty text (RXE.text() is not sufficient)
            #but this is not solved yet, see https://github.com/proycon/folia/issues/19
            #elements.append( RXE.data(RXE.param(r".+",name="pattern"),type='string'))
            #elements.append( RXE.data(RXE.param(r"(.|\n|\r)*\S+(.|\n|\r)*",name="pattern"),type='string'))
        done = {}
        if includechildren and cls.ACCEPTED_DATA: #pylint: disable=too-many-nested-blocks
            for c in cls.ACCEPTED_DATA:
                if c.__name__[:8] == 'Abstract' and inspect.isclass(c):
                    for c2 in globals().values():
                        try:
                            if inspect.isclass(c2) and issubclass(c2, c):
                                try:
                                    if c2.XMLTAG and c2.XMLTAG not in done:
                                        if c2.OCCURRENCES == 1:
                                            elements.append( RXE.optional( RXE.ref(name=c2.XMLTAG) ) )
                                        else:
                                            elements.append( RXE.zeroOrMore( RXE.ref(name=c2.XMLTAG) ) )
                                            elements += list(c2.relaxng_backwards())
                                        done[c2.XMLTAG] = True
                                except AttributeError:
                                    continue
                        except TypeError:
                            pass
                elif issubclass(c, Feature) and c.SUBSET:
                    attribs.append( RXE.optional( RXE.attribute(name=c.SUBSET)))  #features as attributes
                else:
                    try:
                        if c.XMLTAG and c.XMLTAG not in done:
                            if cls.REQUIRED_DATA and c in cls.REQUIRED_DATA:
                                if c.OCCURRENCES == 1:
                                    elements.append( RXE.ref(name=c.XMLTAG) )
                                else:
                                    elements.append( RXE.oneOrMore( RXE.ref(name=c.XMLTAG) ) )
                            elif c.OCCURRENCES == 1:
                                elements.append( RXE.optional( RXE.ref(name=c.XMLTAG) ) )
                            else:
                                elements.append( RXE.zeroOrMore( RXE.ref(name=c.XMLTAG) ) )
                                elements += list(c.relaxng_backwards())

                            done[c.XMLTAG] = True
                    except AttributeError:
                        continue

        if extraelements:
            for e in extraelements:
                elements.append( e )

        if elements:
            if len(elements) > 1:
                attribs.append( RXE.interleave(*elements) )
            else:
                attribs.append( *elements )

        if not attribs:
            attribs.append( RXE.empty() )

        if cls.XMLTAG in ('desc','comment'):
            return RXE.define( RXE.element(RXE.text(), *(preamble + attribs), **{'name': cls.XMLTAG}), name=cls.XMLTAG, ns=NSFOLIA)
        else:
            return RXE.define( RXE.element(*(preamble + attribs), **{'name': cls.XMLTAG}), name=cls.XMLTAG, ns=NSFOLIA)

    @classmethod
    def relaxng_backwards(cls):
        """internal helper function for backward compatibility"""
        if cls.XMLTAG in OLDTAGS_REVERSE:
            yield RXE.zeroOrMore( RXE.ref(name=OLDTAGS_REVERSE[cls.XMLTAG]))



    @classmethod
    def parsexml(Class, node, doc, **kwargs): #pylint: disable=bad-classmethod-argument
        """Internal class method used for turning an XML element into an instance of the Class.

        Args:
            * ``node`` - XML Element
            * ``doc`` - Document

        Returns:
            An instance of the current Class.
        """

        assert issubclass(Class, AbstractElement)

        if doc.preparsexmlcallback:
            result = doc.preparsexmlcallback(node)
            if not result:
                return None
            if isinstance(result, AbstractElement):
                return result



        args = []
        if not kwargs: kwargs = {}
        if node.text:
            if Class.TEXTCONTAINER or Class.PHONCONTAINER:
                args.append(node.text)
            elif node.text.strip()  != "" and Class not in (Comment, Description, TextContent, PhonContent, Content):
                raise ParseError("Found extra text '" + node.text.strip() + "' in handling of  <" + node.tag[len(NSFOLIA)+2:] + "> @ line " + str(node.sourceline))


        for subnode in node: #pylint: disable=too-many-nested-blocks
            #don't trip over comments
            if isinstance(subnode, ElementTree._Comment): #pylint: disable=protected-access
                if (Class.TEXTCONTAINER or Class.PHONCONTAINER) and subnode.tail:
                    args.append(subnode.tail)
            elif isinstance(subnode, ElementTree._ProcessingInstruction): #pylint: disable=protected-access
                #ignore processing instructions
                pass
            else:
                if subnode.tag.startswith('{' + NSFOLIA + '}'):
                    if doc.debug >= 1: print("[FoLiA DEBUG] Processing subnode " + subnode.tag[nslen:],file=stderr)
                    try:
                        e = doc.parsexml(subnode, Class)
                    except ParseError as e:
                        raise #just re-raise deepest parseError
                    except Exception as e:
                        #Python 3 will preserve full original traceback, Python 2 does not, original cause is explicitly passed to ParseError anyway:
                        raise ParseError("FoLiA exception in handling of <" + subnode.tag[len(NSFOLIA)+2:] + "> @ line " + str(subnode.sourceline) + " (in parent <" + node.tag[len(NSFOLIA)+2:]+"> @ parent line " + str(node.sourceline) + ") : [" + e.__class__.__name__ + "] " + str(e), cause=e)
                    if e is not None:
                        args.append(e)
                    if subnode.tail:
                        if Class.TEXTCONTAINER or Class.PHONCONTAINER:
                            args.append(subnode.tail)
                        elif subnode.tail.strip() != "" and Class not in (Comment, Description, TextContent, PhonContent, Content):
                            raise ParseError("Found extra trailing text '" + subnode.tail.strip() + "' in handling of <" + node.tag[len(NSFOLIA)+2:] + "> @ line " + str(subnode.sourceline))
                elif doc.debug >= 1:
                    print("[FoLiA DEBUG] Ignoring subnode outside of FoLiA namespace: " + subnode.tag,file=stderr)



        for key, value in node.attrib.items():
            if key[0] == '{':
                if key == '{http://www.w3.org/XML/1998/namespace}id':
                    key = 'id'
                elif key == '{http://www.w3.org/XML/1998/namespace}space':
                    key = 'preservespace'
                    if value == "preserve":
                        value = True
                    else:
                        value = False
                elif key.startswith( '{' + NSFOLIA + '}'):
                    key = key[nslen:]
                    if key == 'id':
                        #ID in FoLiA namespace is always a reference, passed in kwargs as follows:
                        key = 'idref'
                elif Class.XLINK and key.startswith('{http://www.w3.org/1999/xlink}'):
                    key = key[30:]
                    if key != 'href':
                        key = 'xlink' + key #xlinktype, xlinkrole, xlinklabel, xlinkshow, etc..


            if key != "typegroup": #typegroup is for explicit form only, we can safely ignore it during parsing
                kwargs[key] = value


        if doc.debug >= 1: print("[FoLiA DEBUG] Found " + node.tag[nslen:],file=stderr)
        instance = Class(doc, *args, **kwargs)
        #if id:
        #    if doc.debug >= 1: print >>stderr, "[FoLiA DEBUG] Adding to index: " + id
        #    doc.index[id] = instance

        if doc.parsexmlcallback:
            result = doc.parsexmlcallback(instance)
            if not result:
                return None
            if isinstance(result, AbstractElement):
                return result

        return instance

    def resolveword(self, id):
        return None

    def remove(self, child):
        """Removes the child element"""
        if not isinstance(child, AbstractElement):
            raise ValueError("Expected AbstractElement, got " + str(type(child)))
        if child.parent == self:
            child.parent = None
        self.data.remove(child)
        #delete from index
        if child.id and self.doc and child.id in self.doc.index:
            del self.doc.index[child.id]

    def incorrection(self):
        """Is this element part of a correction? If it is, it returns the Correction element (evaluating to True), otherwise it returns None"""
        e = self.parent

        while e:
            if isinstance(e, Correction):
                return e
            if isinstance(e, AbstractStructureElement):
                break
            e = e.parent
        return None

    def tag(self, tag):
        """Add a processing tag"""
        if ' ' in tag:
            raise ValueError("Processing tags may not contain spaces")
        if self.tags:
            self.tags.append(tag)
        else:
            self.tags = [tag]

    def hastag(self, tag):
        """Check whether a processing tag is present"""
        return tag in self.tags

    def untag(self, tag):
        """Remove a processing tag"""
        if tag in self.tags:
            self.tags.remove(tag)
            return True
        else:
            return False

class AbstractHigherOrderAnnotation(AbstractElement):
    pass

class Description(AbstractHigherOrderAnnotation):
    """Description is an element that can be used to associate a description with almost any other FoLiA element"""

    def __init__(self,doc, *args, **kwargs):
        """Required keyword arguments:
                * ``value=``: The text content for the description (``str`` or ``unicode``)
        """
        if 'value' in kwargs:
            if kwargs['value'] is None:
                self.value = ""
            elif isstring(kwargs['value']):
                self.value = u(kwargs['value'])
            else:
                raise Exception("value= parameter must be str instance, got " + str(type(kwargs['value'])))
            del kwargs['value']
        else:
            raise Exception("Description expects value= parameter")
        super(Description,self).__init__(doc, *args, **kwargs)

    def __nonzero__(self): #Python 2.x
        return bool(self.value)

    def __bool__(self):
        return bool(self.value)

    def __unicode__(self):
        return self.value

    def __str__(self):
        return self.value


    def xml(self, attribs = None,elements = None, skipchildren = False, form = Form.NORMAL):
        return super(Description, self).xml(attribs, [self.value],skipchildren, form)

    def json(self,attribs =None, recurse=True, ignorelist=False):
        jsonnode = {'type': self.XMLTAG, 'value': self.value}
        if attribs:
            for attrib in attribs:
                jsonnode[attrib] = attrib
        return jsonnode

    @classmethod
    def parsexml(Class, node, doc, **kwargs):
        if not kwargs: kwargs = {}
        kwargs['value'] = node.text
        return super(Description,Class).parsexml(node, doc, **kwargs)


class Comment(AbstractHigherOrderAnnotation):
    """Comment is an element that can be used to associate a comment with almost any other FoLiA element"""

    def __init__(self,doc, *args, **kwargs):
        """Required keyword arguments:
                * ``value=``: The text content for the comment (``str`` or ``unicode``)
        """
        if 'value' in kwargs:
            if kwargs['value'] is None:
                self.value = ""
            elif isstring(kwargs['value']):
                self.value = u(kwargs['value'])
            else:
                raise Exception("value= parameter must be str instance, got " + str(type(kwargs['value'])))
            del kwargs['value']
        else:
            raise Exception("Comment expects value= parameter")
        super(Comment,self).__init__(doc, *args, **kwargs)

    def __nonzero__(self): #Python 2.x
        return bool(self.value)

    def __bool__(self):
        return bool(self.value)

    def __unicode__(self):
        return self.value

    def __str__(self):
        return self.value


    def xml(self, attribs = None,elements = None, skipchildren = False, form = Form.NORMAL):
        return super(Comment, self).xml(attribs, [self.value],skipchildren, form)

    def json(self,attribs =None, recurse=True, ignorelist=False):
        jsonnode = {'type': self.XMLTAG, 'value': self.value}
        if attribs:
            for attrib in attribs:
                jsonnode[attrib] = attrib
        return jsonnode

    @classmethod
    def parsexml(Class, node, doc, **kwargs):
        if not kwargs: kwargs = {}
        kwargs['value'] = node.text
        return super(Comment,Class).parsexml(node, doc, **kwargs)


class AllowCorrections(object):
    def correct(self, **kwargs):
        """Apply a correction (TODO: documentation to be written still)"""

        if 'insertindex_offset' in kwargs:
            del kwargs['insertindex_offset'] #dealt with in an earlier stage

        if 'confidence' in kwargs and kwargs['confidence'] is None:
            del kwargs['confidence']

        if 'reuse' in kwargs:
            #reuse an existing correction instead of making a new one
            if isinstance(kwargs['reuse'], Correction):
                c = kwargs['reuse']
            else: #assume it's an index
                try:
                    c = self.doc.index[kwargs['reuse']]
                    assert isinstance(c, Correction)
                except:
                    raise ValueError("reuse= must point to an existing correction (id or instance)! Got " + str(kwargs['reuse']))

            suggestionsonly = (not c.hasnew(True) and not c.hasoriginal(True) and c.hassuggestions(True))

            if 'new' in kwargs and c.hascurrent():
                #can't add new if there's current, so first set original to current, and then delete current

                if 'current' in kwargs:
                    raise Exception("Can't set both new= and current= !")
                if 'original' not in kwargs:
                    kwargs['original'] = c.current()

                c.remove(c.current())
        else:
            if 'id' not in kwargs and 'generate_id_in' not in kwargs:
                kwargs['generate_id_in'] = self
            kwargs2 = copy(kwargs)
            for x in ['new','original','suggestion', 'suggestions','current', 'insertindex','nooriginal']:
                if x in kwargs2:
                    del kwargs2[x]
            c = Correction(self.doc, **kwargs2)

        addnew = False
        if 'insertindex' in kwargs:
            insertindex = int(kwargs['insertindex'])
            del kwargs['insertindex']
        else:
            insertindex = -1 #append

        if 'nooriginal' in kwargs and kwargs['nooriginal']:
            nooriginal = True
            del kwargs['nooriginal']
        else:
            nooriginal = False

        if 'current' in kwargs:
            if 'original' in kwargs or 'new' in kwargs: raise Exception("When setting current=, original= and new= can not be set!")
            if not isinstance(kwargs['current'], list) and not isinstance(kwargs['current'], tuple): kwargs['current'] = [kwargs['current']] #support both lists (for multiple elements at once), as well as single element
            c.replace(Current(self.doc, *kwargs['current']))
            for o in kwargs['current']: #delete current from current element
                if o in self and isinstance(o, AbstractElement): #pylint: disable=unsupported-membership-test
                    if insertindex == -1: insertindex = self.data.index(o)
                    self.remove(o)
            del kwargs['current']
        if 'new' in kwargs:
            if not isinstance(kwargs['new'], list) and not isinstance(kwargs['new'], tuple): kwargs['new'] = [kwargs['new']] #support both lists (for multiple elements at once), as well as single element
            addnew = New(self.doc, *kwargs['new'])
            c.replace(addnew)
            for current in c.select(Current): #delete current if present
                c.remove(current)
            del kwargs['new']
        if 'original' in kwargs and kwargs['original']:
            if not isinstance(kwargs['original'], list) and not isinstance(kwargs['original'], tuple): kwargs['original'] = [kwargs['original']] #support both lists (for multiple elements at once), as well as single element
            c.replace(Original(self.doc, *kwargs['original']))
            for o in kwargs['original']: #delete original from current element
                if o in self and isinstance(o, AbstractElement): #pylint: disable=unsupported-membership-test
                    if insertindex == -1: insertindex = self.data.index(o)
                    self.remove(o)
            for o in kwargs['original']: #make sure IDs are still properly set after removal
                o.addtoindex()
            for current in c.select(Current):  #delete current if present
                c.remove(current)
            del kwargs['original']
        elif addnew and not nooriginal:
            #original not specified, find automagically:
            original = []
            for new in addnew:
                kwargs2 = {}
                if isinstance(new, TextContent):
                    kwargs2['cls'] = new.cls
                try:
                    set = new.set
                except AttributeError:
                    set = None
                #print("DEBUG: Finding replaceables within " + str(repr(self)) + " for ", str(repr(new)), " set " ,set , " args " ,repr(kwargs2),file=sys.stderr)
                replaceables = new.__class__.findreplaceables(self, set, **kwargs2)
                #print("DEBUG: " , len(replaceables) , " found",file=sys.stderr)
                original += replaceables
            if not original:
                #print("DEBUG: ", self.xmlstring(),file=sys.stderr)
                raise Exception("No original= specified and unable to automatically infer on " + str(repr(self)) + " for " + str(repr(new)) + " with set " + set)
            else:
                c.replace( Original(self.doc, *original))
                for current in c.select(Current):  #delete current if present
                    c.remove(current)

        if addnew and not nooriginal:
            for original in c.original():
                if original in self: #pylint: disable=unsupported-membership-test
                    self.remove(original)

        if 'suggestion' in kwargs:
            kwargs['suggestions'] = [kwargs['suggestion']]
            del kwargs['suggestion']
        if 'suggestions' in kwargs:
            for suggestion in kwargs['suggestions']:
                if isinstance(suggestion, Suggestion):
                    c.append(suggestion)
                elif isinstance(suggestion, list) or isinstance(suggestion, tuple):
                    c.append(Suggestion(self.doc, *suggestion))
                else:
                    c.append(Suggestion(self.doc, suggestion))
            del kwargs['suggestions']




        if 'reuse' in kwargs:
            if addnew and suggestionsonly:
                #What was previously only a suggestion, now becomes a real correction
                #If annotator, annotatortypes
                #are associated with the correction as a whole, move it to the suggestions
                #correction-wide annotator, annotatortypes might be overwritten
                for suggestion in c.suggestions():
                    if c.annotator and not suggestion.annotator:
                        suggestion.annotator = c.annotator
                    if c.annotatortype and not suggestion.annotatortype:
                        suggestion.annotatortype = c.annotatortype

            if 'annotator' in kwargs:
                c.annotator = kwargs['annotator'] #pylint: disable=attribute-defined-outside-init
            if 'annotatortype' in kwargs:
                c.annotatortype = kwargs['annotatortype'] #pylint: disable=attribute-defined-outside-init
            if 'confidence' in kwargs:
                c.confidence = float(kwargs['confidence']) #pylint: disable=attribute-defined-outside-init
            c.addtoindex()
            del kwargs['reuse']
        else:
            c.addtoindex()
            if insertindex == -1:
                self.append(c)
            else:
                self.insert(insertindex, c)
        return c



class AllowInlineAnnotation(AllowCorrections):
    """Elements that allow inline annotation (including extended annotation) must inherit from this class"""


    def annotations(self,Class,set=False):
        """Obtain child elements (annotations) of the specified class.

        A further restriction can be made based on set.

        Arguments:
            Class (class): The class to select; any python class (not instance) subclassed off :class:`AbstractElement`
            Set (str): The set to match against, only elements pertaining to this set will be returned. If set to False (default), all elements regardless of set will be returned.

        Yields:
            Elements (instances derived from :class:`AbstractElement`)

        Example::

            for sense in text.annotations(folia.Sense, 'http://some/path/cornetto'):
                ..

        See also:
            :meth:`AbstractElement.select`

        Raises:
            :meth:`AllowInlineAnnotation.annotations`
            :class:`NoSuchAnnotation` if no such annotation exists
        """
        found = False
        for e in self.select(Class,set,True,default_ignore_annotations):
            found = True
            yield e
        if not found:
            raise NoSuchAnnotation()

    def hasannotation(self,Class,set=False):
        """Returns an integer indicating whether such as annotation exists, and if so, how many.

        See :meth:`AllowInlineAnnotation.annotations`` for a description of the parameters."""
        return sum( 1 for _ in self.select(Class,set,True,default_ignore_annotations))

    def annotation(self, type, set=False):
        """Obtain a single annotation element.

        A further restriction can be made based on set.

        Arguments:
            Class (class): The class to select; any python class (not instance) subclassed off :class:`AbstractElement`
            Set (str): The set to match against, only elements pertaining to this set will be returned. If set to False (default), all elements regardless of set will be returned.

        Returns:
            An element (instance derived from :class:`AbstractElement`)

        Example::

            sense = word.annotation(folia.Sense, 'http://some/path/cornetto').cls

        See also:
            :meth:`AllowInlineAnnotation.annotations`
            :meth:`AbstractElement.select`

        Raises:
            :class:`NoSuchAnnotation` if no such annotation exists
        """
        """Will return a **single** annotation (even if there are multiple). Raises a ``NoSuchAnnotation`` exception if none was found"""
        for e in self.select(type,set,True,default_ignore_annotations):
            return e
        raise NoSuchAnnotation()

    def alternatives(self, Class=None, set=False, returnelements=False):
        """Generator over alternatives, either all or only of a specific annotation type, and possibly restrained also by set.

        Arguments:
            Class (class): The python Class you want to retrieve (e.g. PosAnnotation). Or set to ``None`` to select all alternatives regardless of what type they are.
            set (str): The set you want to retrieve (defaults to ``None``, which selects irregardless of set)
            returnelements: Return the actual matches within the alternatives, will return two-tuples where the first is an instance of Alternative and the second an instance of Class.

        Yields:
            :class:`Alternative` elements
        """

        for e in self.select(Alternative,False, True, []): #pylint: disable=too-many-nested-blocks
            if Class is None:
                yield e
            elif len(e) >= 1: #child elements?
                for e2 in e:
                    try:
                        if isinstance(e2, Class):
                            try:
                                if set is False or e2.set == set:
                                    if returnelements:
                                        yield e, e2
                                    else:
                                        yield e
                                    break #yield an alternative only once (in case there are multiple matches)
                            except AttributeError:
                                continue
                    except AttributeError:
                        continue

class AbstractWord: #interface grouping elements that act like words
    """Interface class that is inherited by word-like (wrefable) elements (Word, Hiddenword, Morpheme)"""

    def sentence(self):
        """Obtain the sentence this word is a part of, otherwise return None"""
        return self.ancestor(Sentence)


    def paragraph(self):
        """Obtain the paragraph this word is a part of, otherwise return None"""
        return self.ancestor(Paragraph)

    def division(self):
        """Obtain the deepest division this word is a part of, otherwise return None"""
        return self.ancestor(Division)

    def pos(self,set=False):
        """Shortcut: returns the FoLiA class of the PoS annotation (will return only one if there are multiple!)"""
        return self.annotation(PosAnnotation,set).cls

    def lemma(self, set=False):
        """Shortcut: returns the FoLiA class of the lemma annotation (will return only one if there are multiple!)"""
        return self.annotation(LemmaAnnotation,set).cls

    def sense(self,set=False):
        """Shortcut: returns the FoLiA class of the sense annotation (will return only one if there are multiple!)"""
        return self.annotation(SenseAnnotation,set).cls

    def etymology(self,set=False):
        """Shortcut: returns the FoLiA class of the etymology annotation (will return only one if there are multiple!)"""
        return self.annotation(EtymologyAnnotation,set).cls

    def domain(self,set=False):
        """Shortcut: returns the FoLiA class of the domain annotation (will return only one if there are multiple!)"""
        return self.annotation(DomainAnnotation,set).cls

    def morphemes(self,set=False):
        """Generator yielding all morphemes (in a particular set if specified). For retrieving one specific morpheme by index, use morpheme() instead"""
        for layer in self.select(MorphologyLayer):
            for m in layer.select(Morpheme, set):
                yield m

    def phonemes(self,set=False):
        """Generator yielding all phonemes (in a particular set if specified). For retrieving one specific morpheme by index, use morpheme() instead"""
        for layer in self.select(PhonologyLayer):
            for p in layer.select(Phoneme, set):
                yield p

    def morpheme(self,index, set=False):
        """Returns a specific morpheme, the n'th morpheme (given the particular set if specified)."""
        for layer in self.select(MorphologyLayer):
            for i, m in enumerate(layer.select(Morpheme, set)):
                if index == i:
                    return m
        raise NoSuchAnnotation


    def phoneme(self,index, set=False):
        """Returns a specific phoneme, the n'th morpheme (given the particular set if specified)."""
        for layer in self.select(PhonologyLayer):
            for i, p in enumerate(layer.select(Phoneme, set)):
                if index == i:
                    return p
        raise NoSuchAnnotation

    def getcorrection(self,set=False,cls=None):
        try:
            return self.getcorrections(set,cls)[0]
        except:
            raise NoSuchAnnotation

    def getcorrections(self, set=False,cls=None):
        try:
            l = []
            for correction in self.annotations(Correction):
                if ((not set or correction.set == set) and (not cls or correction.cls == cls)):
                    l.append(correction)
            return l
        except NoSuchAnnotation:
            raise

    def findspans(self, type,set=False, alternatives=False, returnlayers=False):
        """Yields span annotation elements of the specified type that include this word.

        Arguments:
            type: The annotation type, can be passed as using any of the :class:`AnnotationType` member, or by passing the relevant :class:`AbstractSpanAnnotation` or :class:`AbstractAnnotationLayer` class.
            set (str/None/False): Constrain by set. Set to False to return regardless of set.
            alternatives: Find alternatives only (i.e. if set, this returns only alternatives and not the authoritative annotations, if unset, it does the oppose and returns only the authoritative annotations and no alternatives)
            returnlayers: Return the layers in additions to the actual span annotation elements

        Example::

            for chunk in word.findspans(folia.Chunk):
                print(" Chunk class=", chunk.cls, " words=")
                for word2 in chunk.wrefs(): #print all words in the chunk (of which the word is a part)
                    print(word2, end="")
                print()

        Yields:
            Matching span annotation instances (derived from :class:`AbstractSpanAnnotation`)
            If returnlayers is set, it returns a tuple (:class:`AbstractSpanAnnotation`, :class:`AbstractAnnotationLayer`)
        """

        if issubclass(type, AbstractAnnotationLayer):
            layerclass = type
        else:
            layerclass = ANNOTATIONTYPE2LAYERCLASS[type.ANNOTATIONTYPE]

        if alternatives:
            extraselector = lambda x: x.select(AlternativeLayers, set, False, ignore=False)
        else:
            extraselector = lambda x: [x]
        e = self
        while True:
            if not e.parent: break
            e = e.parent
            for extra in extraselector(e): #simply returns only e unless alternatives are enabled
                for layer in extra.select(layerclass,set,False):
                    if type is layerclass:
                        for e2 in layer.select(AbstractSpanAnnotation,set,recursive=True, ignore=ignore_wrefables):
                            if not isinstance(e2, AbstractSpanRole) and self in e2.wrefs():
                                if returnlayers:
                                    yield e2, layer
                                else:
                                    yield e2
                    else:
                        for e2 in layer.select(type,set,recursive=True, ignore=ignore_wrefables):
                            if not isinstance(e2, AbstractSpanRole) and self in e2.wrefs():
                                if returnlayers:
                                    yield e2, layer
                                else:
                                    yield e2

                #for e2 in layer:
                #    if (type is layerclass and isinstance(e2, AbstractSpanAnnotation)) or (type is not layerclass and isinstance(e2, type)):
                #        if self in e2.wrefs():
                #            yield e2

    def alternativelayers(self, type, set=False, returnelements=False):
        """Generator over alternative layers, either all or only of a specific annotation type, and possibly restrained also by folia set.

        Arguments:
            type: The annotation type, can be passed as using any of the :class:`AnnotationType` member, or by passing the relevant :class:`AbstractSpanAnnotation` or :class:`AbstractAnnotationLayer` class.
            set (str): The set you want to retrieve (defaults to ``None``, which selects irregardless of set)
            returnelements: Return the actual matches within the alternatives, will return two-tuples

        Yields:
            :class:`AlternativeLayers` elements
        """
        found = {}
        for element, layer in self.findspans(type,foliaset, alternatives=True, returnlayers=True):
            assert isinstance(layer.parent, AlternativeLayers)
            if returnelements or layer.parent not in found:
                found[layer.parent] = True
                if returnelements:
                    yield element, layer.parent
                else:
                    yield layer.parent


class AllowGenerateID(object):
    """Classes inherited from this class allow for automatic ID generation, using the convention of adding a period, the name of the element , another period, and a sequence number"""

    def _getmaxid(self, xmltag):
        try:
            if xmltag in self.maxid:
                return self.maxid[xmltag]
            else:
                return 0
        except AttributeError:
            return 0


    def _setmaxid(self, child):
        #print "set maxid on " + repr(self) + " for " + repr(child)
        try:
            self.maxid
        except AttributeError:
            self.maxid = {}#pylint: disable=attribute-defined-outside-init
        try:
            if child.id and child.XMLTAG:
                fields = child.id.split(self.doc.IDSEPARATOR)
                if len(fields) > 1 and fields[-1].isdigit():
                    if not child.XMLTAG in self.maxid:
                        self.maxid[child.XMLTAG] = int(fields[-1])
                        #print "set maxid on " + repr(self) + ", " + child.XMLTAG + " to " + fields[-1]
                    else:
                        if self.maxid[child.XMLTAG] < int(fields[-1]):
                            self.maxid[child.XMLTAG] = int(fields[-1])
                            #print "set maxid on " + repr(self) + ", " + child.XMLTAG + " to " + fields[-1]

        except AttributeError:
            pass



    def generate_id(self, cls):
        if isinstance(cls,str):
            xmltag = cls
        else:
            try:
                xmltag = cls.XMLTAG
            except:
                raise GenerateIDException("Unable to generate ID, expected a class such as Alternative, Correction, etc...")


        maxid = self._getmaxid(xmltag)

        id = None
        if self.id:
            id = self.id
        else:
            #this element has no ID, fall back to closest parent ID:
            e = self
            while e.parent:
                if e.id:
                    id = e.id
                    break
                e = e.parent

            if id is None:
                raise GenerateIDException("Unable to generate ID, no parent ID could be found")

        origid = id

        while True:
            maxid += 1
            id = origid + '.' + xmltag + '.' + str(maxid)
            if not self.doc or id not in self.doc.index: #extra check
                break

        try:
            self.maxid
        except AttributeError:
            self.maxid = {}#pylint: disable=attribute-defined-outside-init
        self.maxid[xmltag] = maxid #Set MAX ID
        return id


class AbstractStructureElement(AbstractElement, AllowInlineAnnotation, AllowGenerateID):
    """Abstract element, all structure elements inherit from this class. Never instantiated directly."""



    def __init__(self, doc, *args, **kwargs):
        super(AbstractStructureElement,self).__init__(doc, *args, **kwargs)

    def resolveword(self, id):
        for child in self:
            r =  child.resolveword(id)
            if r:
                return r
        return None

    def append(self, child, *args, **kwargs):
        """See ``AbstractElement.append()``"""
        e = super(AbstractStructureElement,self).append(child, *args, **kwargs)
        self._setmaxid(e)
        return e


    def postappend(self):
        super(AbstractStructureElement,self).postappend()
        if self.doc and self.doc.textvalidation:
            self.doc.textvalidationerrors += int(not self.textvalidation())

    def __hash__(self):
        if self.id:
            return hash(self.id)
        else:
            return hash(id(self)) #use the memory address

    def words(self, index = None):
        """Returns a generator of Word elements found (recursively) under this element.

        Arguments:
            * ``index``: If set to an integer, will retrieve and return the n'th element (starting at 0) instead of returning the list of all
        """
        if index is None:
            return self.select(Word,False,True,default_ignore_structure)
        else:
            if index < 0:
                index = self.count(Word,False,True,default_ignore_structure) + index
            for i, e in enumerate(self.select(Word,False,True,default_ignore_structure)):
                if i == index:
                    return e
            raise IndexError


    def paragraphs(self, index = None):
        """Returns a generator of Paragraph elements found (recursively) under this element.

        Arguments:
            index (int or None): If set to an integer, will retrieve and return the n'th element (starting at 0) instead of returning the generator of all
        """
        if index is None:
            return self.select(Paragraph,False,True,default_ignore_structure)
        else:
            if index < 0:
                index = self.count(Paragraph,False,True,default_ignore_structure) + index
            for i,e in enumerate(self.select(Paragraph,False,True,default_ignore_structure)):
                if i == index:
                    return e
            raise IndexError

    def sentences(self, index = None):
        """Returns a generator of Sentence elements found (recursively) under this element

        Arguments:
            index (int or None): If set to an integer, will retrieve and return the n'th element (starting at 0) instead of returning a generator of all
        """
        if index is None:
            return self.select(Sentence,False,True,default_ignore_structure)
        else:
            if index < 0:
                index = self.count(Sentence,False,True,default_ignore_structure) + index
            for i,e in enumerate(self.select(Sentence,False,True,default_ignore_structure)):
                if i == index:
                    return e
            raise IndexError

    def layers(self, annotationtype=None,set=False):
        """Returns a list of annotation layers found *directly* under this element, does not include alternative layers"""
        if inspect.isclass(annotationtype): annotationtype = annotationtype.ANNOTATIONTYPE
        return [ x for x in self.select(AbstractAnnotationLayer,set,False,True) if annotationtype is None or x.ANNOTATIONTYPE == annotationtype ]

    def hasannotationlayer(self, annotationtype=None,set=False):
        """Does the specified annotation layer exist?"""
        l = self.layers(annotationtype, set)
        return (len(l) > 0)

    def __eq__(self, other):
        return super(AbstractStructureElement, self).__eq__(other)


class AbstractInlineAnnotation(AbstractElement, AllowGenerateID):
    """Abstract element, all inline annotation elements are derived from this class"""


    def append(self, child, *args, **kwargs):
        """See ``AbstractElement.append()``"""
        e = super(AbstractInlineAnnotation,self).append(child, *args, **kwargs)
        self._setmaxid(e)
        return e



class AbstractTextMarkup(AbstractElement):
    """Abstract class for text markup elements, elements that appear with the :class:`TextContent` (``t``) element.

    Markup elements pertain primarily to styling, but also have other roles.

    Iterating over the element of a
    :class:`TextContent` element will first and foremost produce strings, but also
    uncover these markup elements when present.
    """

    def __init__(self, doc, *args, **kwargs):
        """See :meth:`AbstractElement.__init__`, text is passed as a string in ``*args``."""

        if 'idref' in kwargs:
            self.idref = kwargs['idref']
            del kwargs['idref']
        elif not hasattr(self, 'idref'): #if not already set by a subclass
            self.idref = None

        if 'value' in kwargs:
            #for backward compatibility
            kwargs['text'] = kwargs['value']
            del kwargs['value']

        super(AbstractTextMarkup,self).__init__(doc, *args, **kwargs)

        #if self.value and (self.value != self.value.translate(ILLEGAL_UNICODE_CONTROL_CHARACTERS)):
        #    raise ValueError("There are illegal unicode control characters present in Text Markup Content: " + repr(self.value))

    def settext(self, text):
        """Sets the text content of the markup element.

        Arguments:
            text (str)
        """
        self.data = [text]
        if not self.data:
            raise ValueError("Empty text content elements are not allowed")

    def resolve(self):
        if self.idref:
            return self.doc[self.idref]
        else:
            return self

    def xml(self, attribs = None,elements = None, skipchildren = False, form = Form.NORMAL):
        """See :meth:`AbstractElement.xml`"""
        if not attribs: attribs = {}
        if self.idref:
            attribs['id'] = self.idref
        return super(AbstractTextMarkup,self).xml(attribs,elements, skipchildren, form)

    def json(self,attribs =None, recurse=True, ignorelist=False):
        """See :meth:`AbstractElement.json`"""
        if not attribs: attribs = {}
        if self.idref:
            attribs['id'] = self.idref
        return super(AbstractTextMarkup,self).json(attribs,recurse, ignorelist)

    @classmethod
    def parsexml(Class, node, doc, **kwargs):
        if not kwargs: kwargs ={}
        if 'id' in node.attrib:
            kwargs['idref'] = node.attrib['id']
            del node.attrib['id']
        return super(AbstractTextMarkup,Class).parsexml(node, doc, **kwargs)

    @classmethod
    def relaxng(cls, includechildren=True,extraattribs = None, extraelements=None):
        if not extraattribs: extraattribs = []
        extraattribs.append( RXE.optional(RXE.attribute(name='id' ))) #id reference
        return super(AbstractTextMarkup, cls).relaxng(includechildren, extraattribs, extraelements)


class TextMarkupString(AbstractTextMarkup):
    """Markup element to mark arbitrary substrings in text content (:class:`TextContent`)"""

class TextMarkupReference(AbstractTextMarkup):
    """Markup element placing an explicit reference to another structural element, used for instance to refer to footnotes from untokenised text. Used in text content (:class:`TextContent`)

    Only consider this element for references in spans of untokenised text. The use of structural element :class:`Reference` is preferred.
    """

    def __init__(self, doc, *args, **kwargs):
        if 'idref' in kwargs:
            self.idref = kwargs['idref']
            del kwargs['idref']
        else:
            self.idref = None
        if 'type' in kwargs:
            self.type = kwargs['type']
            del kwargs['type']
        else:
            self.type = None
        if 'format' in kwargs:
            self.format = kwargs['format']
            del kwargs['format']
        else:
            self.format = "text/folia+xml"
        super().__init__(doc, *args, **kwargs)

    def xml(self, attribs = None,elements = None, skipchildren = False, form = Form.NORMAL):
        if not attribs: attribs = {}
        if self.idref:
            attribs['id'] = self.idref
        if self.type:
            attribs['type'] = self.type
        if self.format and self.format != "text/folia+xml":
            attribs['format'] = self.format
        return super().xml(attribs,elements, skipchildren, form)

    def json(self, attribs=None, recurse=True, ignorelist=False):
        if attribs is None: attribs = {}
        if self.idref:
            attribs['idref'] = self.idref
        if self.type:
            attribs['type'] = self.type
        if self.format:
            attribs['format'] = self.format
        return super().json(attribs,recurse,ignorelist)

    def resolve(self):
        if self.idref:
            return self.doc[self.idref]
        else:
            return self

    @classmethod
    def parsexml(Class, node, doc, **kwargs):#pylint: disable=bad-classmethod-argument
        if not kwargs: kwargs = {}
        if 'id' in node.attrib:
            kwargs['idref'] = node.attrib['id']
            del node.attrib['id']
        if 'type' in node.attrib:
            kwargs['type'] = node.attrib['type']
            del node.attrib['type']
        if 'format' in node.attrib:
            kwargs['format'] = node.attrib['format']
            del node.attrib['format']
        return super().parsexml(node, doc, **kwargs)


    @classmethod
    def relaxng(cls, includechildren=True,extraattribs = None, extraelements=None):
        if not extraattribs: extraattribs = []
        extraattribs.append( RXE.optional(RXE.attribute(name='type' )))
        extraattribs.append( RXE.optional(RXE.attribute(name='format' )))
        return super().relaxng(includechildren, extraattribs, extraelements)

class TextMarkupGap(AbstractTextMarkup):
    """Markup element to mark gaps in text content (:class:`TextContent`)

    Only consider this element for gaps in spans of untokenised text. The use of structural element :class:`Gap` is preferred.
    """

class TextMarkupCorrection(AbstractTextMarkup):
    """Markup element to mark corrections in text content (:class:`TextContent`).

    Only consider this element for corrections on untokenised text. The use of :class:`Correction` is preferred.
    """

    def __init__(self, doc, *args, **kwargs):
        if 'original' in kwargs:
            self.original = kwargs['original']
            del kwargs['original']
        else:
            self.original = None
        super(TextMarkupCorrection,self).__init__(doc, *args, **kwargs)

    def xml(self, attribs = None,elements = None, skipchildren = False, form = Form.NORMAL):
        if not attribs: attribs = {}
        if self.original:
            attribs['original'] = self.original
        return super(TextMarkupCorrection,self).xml(attribs,elements, skipchildren, form)

    def json(self,attribs =None, recurse=True, ignorelist=False):
        if not attribs: attribs = {}
        if self.original:
            attribs['original'] = self.original
        return super(TextMarkupCorrection,self).json(attribs,recurse,ignorelist)

    @classmethod
    def parsexml(Class, node, doc, **kwargs):
        if not kwargs: kwargs = {}
        if 'original' in node.attrib:
            kwargs['original'] = node.attrib['original']
            del node.attrib['original']
        return super(TextMarkupCorrection,Class).parsexml(node, doc, **kwargs)

    @classmethod
    def relaxng(cls, includechildren=True,extraattribs = None, extraelements=None):
        if not extraattribs: extraattribs = []
        extraattribs.append( RXE.optional(RXE.attribute(name='original' )))
        return super(TextMarkupCorrection, cls).relaxng(includechildren, extraattribs, extraelements)


class TextMarkupError(AbstractTextMarkup):
    """Markup element to mark gaps in text content (:class:`TextContent`)

    Only consider this element for gaps in spans of untokenised text. The use of structural element :class:`ErrorDetection` is preferred.
    """

class TextMarkupStyle(AbstractTextMarkup):
    """Markup element to style text content (:class:`TextContent`), e.g. make text bold, italics, underlined, coloured, etc.."""

class TextMarkupWhitespace(AbstractTextMarkup):
    """Whitespace element, signals a vertical whitespace"""

    def text(self, cls='current', retaintokenisation=False, previousdelimiter="", strict=False, correctionhandling=None, normalize_spaces=False, hidden=False, trim_spaces=True):
        if normalize_spaces:
            return " "
        else:
            return previousdelimiter.strip(' ') + "\n\n"

class TextMarkupHSpace(AbstractTextMarkup):
    """Whitespace element, signals a horizontal whitespace"""

    def text(self, cls='current', retaintokenisation=False, previousdelimiter="", strict=False, correctionhandling=None, normalize_spaces=False, hidden=False, trim_spaces=True):
        if normalize_spaces:
            return " "
        else:
            return previousdelimiter.strip(' ') + " "

class TextMarkupLanguage(AbstractTextMarkup):
    """Language annotation as markup"""


class AbstractContentAnnotation(AbstractElement):
    """Abstract element for content annotation (TextContent and PhonContent)"""
    pass

class TextContent(AbstractContentAnnotation):
    """Text content element (``t``), holds text to be associated with whatever element the text content element is a child of.

    Text content elements
    on structure elements like :class:`Paragraph` and :class:`Sentence` are by definition untokenised. Only on :class:`Word`` level and deeper they are by definition tokenised.

    Text content elements can specify offset that refer to text at a higher parent level. Use the following keyword arguments:

        * ``ref=``: The instance to point to, this points to the element holding the text content element, not the text content element itself.
        * ``offset=``: The offset where this text is found, offsets start at 0
    """


    def __init__(self, doc, *args, **kwargs):
        """

        Example::

                text = folia.TextContent(doc, 'test')
                text = folia.TextContent(doc, 'test',cls='original')

        """

        #for backward compatibility:
        if 'value' in kwargs:
            kwargs['text'] = kwargs['value']
            del kwargs['value']


        if 'offset' in kwargs: #offset
            self.offset = int(kwargs['offset'])
            del kwargs['offset']
        else:
            self.offset = None


        #If no class is specified, it defaults to 'current'. (FoLiA uncharacteristically predefines two classes for t: current and original)
        if 'cls' not in kwargs and 'class' not in kwargs:
            kwargs['cls'] = 'current'

        if 'ref' in kwargs: #reference to offset
            if isinstance(kwargs['ref'], AbstractElement):
                if kwargs['ref'].id is None:
                    raise ValueError("Reference for text content must have an ID or can't act as reference!")
                self.ref = kwargs['ref'].id
            else:
                #a string (ID) is passed, we can't resolve it yet cause it may not exist at construction time, use getreference() to resolve when needed
                self.ref = kwargs['ref']
            del kwargs['ref']
        else:
            self.ref = None #no explicit reference; if the reference is implicit, getreference() will still work


        super(TextContent,self).__init__(doc, *args, **kwargs)

        doc.textclasses.add(self.cls)

        if not self.data:
            raise ValueError("Empty text content elements are not allowed")
        #if isstring(self.data[0]) and (self.data[0] != self.data[0].translate(ILLEGAL_UNICODE_CONTROL_CHARACTERS)):
        #    raise ValueError("There are illegal unicode control characters present in TextContent: " + repr(self.data[0]))


    def text(self, normalize_spaces=False, trim_spaces=True):
        """Obtain the text (unicode instance)"""
        return super(TextContent,self).text(normalize_spaces=normalize_spaces, trim_spaces=trim_spaces) #AbstractElement will handle it now, merely overridden to get rid of parameters that dont make sense in this context

    def settext(self, text, cls=None):
        self.data = [text]
        if cls is not None: self.cls = cls
        if not self.data:
            raise ValueError("Empty text content elements are not allowed")
        #if isstring(self.data[0]) and (self.data[0] != self.data[0].translate(ILLEGAL_UNICODE_CONTROL_CHARACTERS)):
        #    raise ValueError("There are illegal unicode control characters present in TextContent: " + repr(self.data[0]))


    def getreference(self, validate=True, trim_spaces=True):
        """Returns and validates the Text Content's reference. Raises UnresolvableTextContent when invalid"""

        if self.offset is None: return None #nothing to test
        if self.ref:
            ref = self.doc[self.ref]
        else:
            ref = self.finddefaultreference()

        if not ref:
            raise UnresolvableTextContent("Default reference for textcontent not found!")
        elif not ref.hastext(self.cls):
            raise UnresolvableTextContent("Reference (ID " + str(ref.id) + ") has no such text (class=" + self.cls+")")
        elif validate and self.text() != ref.textcontent(self.cls).text(trim_spaces=trim_spaces)[self.offset:self.offset+len(self.data[0])]:
            raise UnresolvableTextContent("Reference (ID " + str(ref.id) + ", class=" + self.cls+") found but no text match at specified offset ("+str(self.offset)+")! Expected '" + self.text() + "', got '" + ref.textcontent(self.cls).text(trim_spaces=trim_spaces)[self.offset:self.offset+len(self.data[0])] +"', full text: '" + ref.textcontent(self.cls).text(trim_spaces=trim_spaces) + '"')
        else:
            #finally, we made it!
            return ref


    def deepvalidation(self):
        return True


    def __unicode__(self):
        return self.text()

    def __str__(self):
        return self.text()

    def __eq__(self, other):
        if isinstance(other, TextContent):
            return self.text() == other.text()
        elif isstring(other):
            return self.text() == u(other)
        else:
            return False



    def finddefaultreference(self):
        """Find the default reference for text offsets:
          The parent of the current textcontent's parent (counting only Structure Elements and Subtoken Annotation Elements)

          Note: This returns not a TextContent element, but its parent. Whether the textcontent actually exists is checked later/elsewhere
        """

        depth = 0
        e = self
        while True:
            if e.parent:
                e = e.parent
            else:
                #no parent, breaking
                return False

            if isinstance(e, (AbstractStructureElement, AbstractSubtokenAnnotation, String)):
                depth += 1
                if depth == 2:
                    return e


        return False

    #Change in behaviour (FoLiA 0.10), iter() no longer iterates over the text itself!!


    #Change in behaviour (FoLiA 0.10), len() no longer return the length of the text!!


    @classmethod
    def findreplaceables(Class, parent, set, **kwargs):
        """(Method for internal usage, see AbstractElement)"""
        #some extra behaviour for text content elements, replace also based on the 'corrected' attribute:
        if 'cls' not in kwargs:
            kwargs['cls'] = 'current'
        replace = super(TextContent, Class).findreplaceables(parent, set, **kwargs)
        replace = [ x for x in replace if x.cls == kwargs['cls']]
        del kwargs['cls'] #always delete what we processed
        return replace


    @classmethod
    def parsexml(Class, node, doc, **kwargs):
        """(Method for internal usage, see AbstractElement)"""
        if not kwargs: kwargs = {}
        if 'offset' in node.attrib:
            kwargs['offset'] = int(node.attrib['offset'])
        if 'ref' in node.attrib:
            kwargs['ref'] = node.attrib['ref']
        return super(TextContent,Class).parsexml(node,doc, **kwargs)



    def xml(self, attribs = None,elements = None, skipchildren = False, form = Form.NORMAL):
        """See :meth:`AbstractElement.xml`"""
        attribs = {}
        if not self.offset is None:
            attribs['offset'] = str(self.offset)
        if self.parent and self.ref:
            attribs['ref'] = self.ref


        e = super(TextContent,self).xml(attribs,elements,skipchildren, form)
        if 'class' in e.attrib and e.attrib['class'] == "current":
            #delete 'class=current' unless we are in explicit form
            if form != Form.EXPLICIT:
                del e.attrib['class']
        if 'set' in e.attrib and e.attrib['set'] == "undefined" and self.doc and self.doc.FOLIA1:
            del e.attrib['set']

        return e

    def json(self, attribs =None, recurse =True,ignorelist=False):
        """See :meth:`AbstractElement.json`"""
        attribs = {}
        if not self.offset is None:
            attribs['offset'] = self.offset
        if self.parent and self.ref:
            attribs['ref'] = self.ref
        return super(TextContent,self).json(attribs, recurse,ignorelist)


    @classmethod
    def relaxng(cls, includechildren=True,extraattribs = None, extraelements=None):
        if not extraattribs: extraattribs = []
        extraattribs.append( RXE.optional(RXE.attribute(name='offset' )))
        extraattribs.append( RXE.optional(RXE.attribute(name='ref' )))
        return super(TextContent, cls).relaxng(includechildren, extraattribs, extraelements)


    def postappend(self):
        super(TextContent,self).postappend()
        found = set()
        for c in self.parent:
            if isinstance(c,TextContent):
                if c.cls in found:
                    raise DuplicateAnnotationError("Can not add multiple text content elements with the same class (" + cls + ") to the same structural element!")
                else:
                    found.add(c.cls)


class PhonContent(AbstractContentAnnotation):
    """Phonetic content element (``ph``), holds a phonetic representation to be associated with whatever element the phonetic content element is a child of.

    Phonetic content elements behave much like text content elements.

    Phonetic content elements can specify offset that refer to phonetic content at a higher parent level. Use the following keyword arguments:

        * ``ref=``: The instance to point to, this points to the element holding the text content element, not the text content element itself.
        * ``offset=``: The offset where this text is found, offsets start at 0
    """

    def __init__(self, doc, *args, **kwargs):
        """

        Example::

                phon = folia.PhonContent(doc, 'hɛˈləʊ̯')
                phon = folia.PhonContent(doc, 'hɛˈləʊ̯', cls="original")

        """

        if 'offset' in kwargs: #offset
            self.offset = int(kwargs['offset'])
            del kwargs['offset']
        else:
            self.offset = None



        #If no class is specified, it defaults to 'current'. (FoLiA uncharacteristically predefines two classes for phon: current and original)
        if 'cls' not in kwargs and 'class' not in kwargs:
            kwargs['cls'] = 'current'

        if 'ref' in kwargs: #reference to offset
            if isinstance(kwargs['ref'], AbstractElement):
                if kwargs['ref'].id is None:
                    raise ValueError("Reference for phonetic content must have an ID or can't act as reference!")
                self.ref = kwargs['ref'].id
            else:
                #a string (ID) is passed, we can't resolve it yet cause it may not exist at construction time, use getreference() to resolve when needed
                self.ref = kwargs['ref']
            del kwargs['ref']
        else:
            self.ref = None #no explicit reference; if the reference is implicit, getreference() will still work

        super(PhonContent,self).__init__(doc, *args, **kwargs)

        if not self.data:
            raise ValueError("Empty phonetic content elements are not allowed")
        #if isstring(self.data[0]) and (self.data[0] != self.data[0].translate(ILLEGAL_UNICODE_CONTROL_CHARACTERS)):
        #    raise ValueError("There are illegal unicode control characters present in TextContent: " + repr(self.data[0]))



    def phon(self):
        """Obtain the actual phonetic representation (unicode/str instance)"""
        return super(PhonContent,self).phon() #AbstractElement will handle it now, merely overridden to get rid of parameters that dont make sense in this context

    def setphon(self, phon):
        """Set the representation for the phonetic content (unicode instance), called whenever phon= is passed as a keyword argument to an element constructor  """
        self.data = [phon]
        if not self.data:
            raise ValueError("Empty phonetic content elements are not allowed")
        #if isstring(self.data[0]) and (self.data[0] != self.data[0].translate(ILLEGAL_UNICODE_CONTROL_CHARACTERS)):
        #    raise ValueError("There are illegal unicode control characters present in TextContent: " + repr(self.data[0]))


    def getreference(self, validate=True):
        """Return and validate the Phonetic Content's reference. Raises UnresolvableTextContent when invalid"""

        if self.offset is None: return None #nothing to test
        if self.ref:
            ref = self.doc[self.ref]
        else:
            ref = self.finddefaultreference()

        if not ref:
            raise UnresolvableTextContent("Default reference for phonetic content not found!")
        elif not ref.hasphon(self.cls):
            raise UnresolvableTextContent("Reference has no such phonetic content (class=" + self.cls+")")
        elif validate and self.phon() != ref.textcontent(self.cls).phon()[self.offset:self.offset+len(self.data[0])]:
            raise UnresolvableTextContent("Reference (class=" + self.cls+") found but no phonetic match at specified offset ("+str(self.offset)+")! Expected '" + self.text() + "', got '" + ref.textcontent(self.cls).text()[self.offset:self.offset+len(self.data[0])] +"'")
        else:
            #finally, we made it!
            return ref

    def deepvalidation(self):
        return True


    def __unicode__(self):
        return self.phon()

    def __str__(self):
        return self.phon()

    def __eq__(self, other):
        if isinstance(other, PhonContent):
            return self.phon() == other.phon()
        elif isstring(other):
            return self.phon() == u(other)
        else:
            return False

    #append is implemented, the default suffices

    def postappend(self):
        super(PhonContent,self).postappend()
        found = set()
        invalid = set()
        for c in self.parent:
            if isinstance(c,PhonContent):
                if c.cls in found:
                    raise DuplicateAnnotationError("Can not add multiple phonetic content elements with the same class (" + cls + ") to the same structural element!")
                else:
                    found.add(c.cls)

    def finddefaultreference(self):
        """Find the default reference for text offsets:
          The parent of the current textcontent's parent (counting only Structure Elements and Subtoken Annotation Elements)

          Note: This returns not a TextContent element, but its parent. Whether the textcontent actually exists is checked later/elsewhere
        """

        depth = 0
        e = self
        while True:
            if e.parent:
                e = e.parent
            else:
                #no parent, breaking
                return False

            if isinstance(e,AbstractStructureElement) or isinstance(e,AbstractSubtokenAnnotation):
                depth += 1
                if depth == 2:
                    return e


        return False

    #Change in behaviour (FoLiA 0.10), iter() no longer iterates over the text itself!!


    #Change in behaviour (FoLiA 0.10), len() no longer return the length of the text!!


    @classmethod
    def findreplaceables(Class, parent, set, **kwargs):#pylint: disable=bad-classmethod-argument
        """(Method for internal usage, see AbstractElement)"""
        #some extra behaviour for text content elements, replace also based on the 'corrected' attribute:
        if 'cls' not in kwargs:
            kwargs['cls'] = 'current'
        replace = super(PhonContent, Class).findreplaceables(parent, set, **kwargs)
        replace = [ x for x in replace if x.cls == kwargs['cls']]
        del kwargs['cls'] #always delete what we processed
        return replace


    @classmethod
    def parsexml(Class, node, doc, **kwargs):#pylint: disable=bad-classmethod-argument
        """(Method for internal usage, see AbstractElement)"""
        if not kwargs: kwargs = {}
        if 'offset' in node.attrib:
            kwargs['offset'] = int(node.attrib['offset'])
        if 'ref' in node.attrib:
            kwargs['ref'] = node.attrib['ref']
        return super(PhonContent,Class).parsexml(node,doc, **kwargs)



    def xml(self, attribs = None,elements = None, skipchildren = False, form = Form.NORMAL):
        attribs = {}
        if not self.offset is None:
            attribs['offset'] = str(self.offset)
        if self.parent and self.ref:
            attribs['ref'] = self.ref


        e = super(PhonContent,self).xml(attribs,elements,skipchildren, form)
        if 'class' in e.attrib and e.attrib['class'] == "current":
            #delete 'class=current' unless we are in explicit form
            if form != Form.EXPLICIT:
                del e.attrib['class']
        if 'set' in e.attrib and e.attrib['set'] == "undefined" and self.doc and self.doc.FOLIA1:
            del e.attrib['set']

        return e

    def json(self, attribs =None, recurse =True,ignorelist=False):
        attribs = {}
        if not self.offset is None:
            attribs['offset'] = self.offset
        if self.parent and self.ref:
            attribs['ref'] = self.ref
        return super(PhonContent,self).json(attribs, recurse, ignorelist)


    @classmethod
    def relaxng(cls, includechildren=True,extraattribs = None, extraelements=None):
        if not extraattribs: extraattribs = []
        extraattribs.append( RXE.optional(RXE.attribute(name='offset' )))
        extraattribs.append( RXE.optional(RXE.attribute(name='ref' )))
        return super(PhonContent, cls).relaxng(includechildren, extraattribs, extraelements)

class Content(AbstractHigherOrderAnnotation):     #used for raw content, subelement for Gap
    """A container element that takes raw content, used by :class:`Gap`"""

    def __init__(self,doc, *args, **kwargs):
        if 'value' in kwargs:
            if isstring(kwargs['value']):
                self.value = u(kwargs['value'])
            elif kwargs['value'] is None:
                self.value = ""
            else:
                raise Exception("value= parameter must be unicode or str instance")
            del kwargs['value']
        else:
            raise Exception("Content expects value= parameter")
        super(Content,self).__init__(doc, *args, **kwargs)

    def __nonzero__(self):
        return bool(self.value)

    def __bool__(self):
        return bool(self.value)

    def __unicode__(self):
        return self.value

    def __str__(self):
        return self.value

    def xml(self, attribs = None,elements = None, skipchildren = False, form = Form.NORMAL):

        if not attribs:
            attribs = {}

        return E.content(self.value, **attribs)

    def json(self,attribs =None, recurse=True, ignorelist=False):
        jsonnode = {'type': self.XMLTAG, 'value': self.value}
        if attribs:
            for attrib in attribs:
                jsonnode[attrib] = attrib
        return jsonnode


    @classmethod
    def relaxng(cls, includechildren=True,extraattribs = None, extraelements=None):
        return RXE.define( RXE.element(RXE.text(), name=cls.XMLTAG), name=cls.XMLTAG, ns=NSFOLIA)

    @classmethod
    def parsexml(Class, node, doc, **kwargs):#pylint: disable=bad-classmethod-argument
        if not kwargs: kwargs = {}
        kwargs['value'] = node.text
        return Content(doc, **kwargs)

class Part(AbstractStructureElement):
    """Generic structure element used to mark a part inside another block.

    Do **not** use this for morphology, use :class:`Morpheme` instead.
    """


class Gap(AbstractElement):
    """Gap element, represents skipped portions of the text.

    Usually contains :class:`Content` and possibly also a :class:`Description` element"""

    def __init__(self, doc, *args, **kwargs):
        if 'content' in kwargs:
            self.value = kwargs['content']
            del kwargs['content']
        elif 'description' in kwargs:
            self.description = kwargs['description']
            del kwargs['description']
        super(Gap,self).__init__(doc, *args, **kwargs)

    def content(self):
        for e in self:
            if isinstance(e, Content):
                return e.value
        return ""


class Linebreak(AbstractStructureElement, AbstractTextMarkup): #this element has a double role!!
    """Line break element, signals a line break.

    This element acts both as a structure element as well as a text markup element.
    """

    def __init__(self, doc, *args, **kwargs):
        if 'linenr' in kwargs:
            self.linenr = kwargs['linenr']
            del kwargs['linenr']
        else:
            self.linenr = None
        if 'pagenr' in kwargs:
            self.pagenr = kwargs['pagenr']
            del kwargs['pagenr']
        else:
            self.pagenr = None
        if 'newpage' in kwargs and kwargs['newpage']:
            self.newpage = True
            del kwargs['newpage']
        else:
            self.newpage = False
        super(Linebreak, self).__init__(doc, *args, **kwargs)


    def text(self, cls='current', retaintokenisation=False, previousdelimiter="", strict=False, correctionhandling=None, normalize_spaces=False, hidden=False, trim_spaces=True):
        if normalize_spaces:
            return " "
        else:
            return previousdelimiter.strip(' ') + "\n"

    @classmethod
    def parsexml(Class, node, doc):#pylint: disable=bad-classmethod-argument
        kwargs = {}
        if 'linenr' in node.attrib:
            kwargs['linenr'] = node.attrib['linenr']
        if 'pagenr' in node.attrib:
            kwargs['pagenr'] = node.attrib['pagenr']
        if 'newpage' in node.attrib and node.attrib['newpage'] == 'yes':
            kwargs['newpage'] = True
        return super(Linebreak,Class).parsexml(node, doc, **kwargs)

    def xml(self, attribs = None,elements = None, skipchildren = False, form = Form.NORMAL):
        if attribs is None: attribs = {}
        if self.linenr is not None:
            attribs['linenr'] = str(self.linenr)
        if self.pagenr is not None:
            attribs['pagenr'] = str(self.pagenr)
        if self.newpage:
            attribs['newpage'] = "yes"
        return super(Linebreak, self).xml(attribs,elements,skipchildren, form)

    @classmethod
    def relaxng(cls, includechildren=True,extraattribs = None, extraelements=None):
        attribs = []
        attribs.append(RXE.optional(RXE.attribute(name='pagenr')))
        attribs.append(RXE.optional(RXE.attribute(name='linenr')))
        attribs.append(RXE.optional(RXE.attribute(name='newpage')))
        return super(Linebreak,cls).relaxng(includechildren,attribs,extraelements)

class Hyphbreak(AbstractTextMarkup):
    """Hyphenation break element, signals a hyphenised linebreak in a word"""

    def __init__(self, doc, *args, **kwargs):
        if 'linenr' in kwargs:
            self.linenr = kwargs['linenr']
            del kwargs['linenr']
        else:
            self.linenr = None
        if 'pagenr' in kwargs:
            self.pagenr = kwargs['pagenr']
            del kwargs['pagenr']
        else:
            self.pagenr = None
        if 'newpage' in kwargs and kwargs['newpage']:
            self.newpage = True
            del kwargs['newpage']
        else:
            self.newpage = False
        super(Hyphbreak, self).__init__(doc, *args, **kwargs)

    def text(self, cls='current', retaintokenisation=False, previousdelimiter="", strict=False, correctionhandling=None, normalize_spaces=False, hidden=False, trim_spaces=True):
        return ""

    @classmethod
    def parsexml(Class, node, doc):#pylint: disable=bad-classmethod-argument
        kwargs = {}
        if 'linenr' in node.attrib:
            kwargs['linenr'] = node.attrib['linenr']
        if 'pagenr' in node.attrib:
            kwargs['pagenr'] = node.attrib['pagenr']
        if 'newpage' in node.attrib and node.attrib['newpage'] == 'yes':
            kwargs['newpage'] = True
        return super(Hyphbreak,Class).parsexml(node, doc, **kwargs)

    def xml(self, attribs = None,elements = None, skipchildren = False, form = Form.NORMAL):
        if attribs is None: attribs = {}
        if self.linenr is not None:
            attribs['linenr'] = str(self.linenr)
        if self.pagenr is not None:
            attribs['pagenr'] = str(self.pagenr)
        if self.newpage:
            attribs['newpage'] = "yes"
        return super(Hyphbreak, self).xml(attribs,elements,skipchildren, form)

    @classmethod
    def relaxng(cls, includechildren=True,extraattribs = None, extraelements=None):
        attribs = []
        attribs.append(RXE.optional(RXE.attribute(name='pagenr')))
        attribs.append(RXE.optional(RXE.attribute(name='linenr')))
        attribs.append(RXE.optional(RXE.attribute(name='newpage')))
        return super(Hyphbreak,cls).relaxng(includechildren,attribs,extraelements)

class Whitespace(AbstractStructureElement):
    """Whitespace element, signals a vertical whitespace"""

    def text(self, cls='current', retaintokenisation=False, previousdelimiter="", strict=False, correctionhandling=None, normalize_spaces=False, hidden=False):
        if normalize_spaces:
            return " "
        else:
            return previousdelimiter.strip(' ') + "\n\n"



class Word(AbstractStructureElement, AbstractWord, AllowCorrections):
    """Word (aka token) element. Holds a word/token and all its related inline annotations."""

    def __init__(self, doc, *args, **kwargs):
        """Constructor for words.

        See :class:`AbstractElement.__init__` for all inherited keyword arguments and parameters.

        Keyword arguments:

        * space (bool): Indicates whether this token is followed by a space (defaults to True)

        Example::

            sentence.append( folia.Word, 'This')
            sentence.append( folia.Word, 'is')
            sentence.append( folia.Word, 'a')
            sentence.append( folia.Word, 'test', space=False)
            sentence.append( folia.Word, '.')

        See also:
            :class:`AbstractElement.__init__`
        """
        super(Word,self).__init__(doc, *args, **kwargs)

    def resolveword(self, id):
        if id == self.id:
            return self
        else:
            return None

    def split(self, *newwords, **kwargs):
        self.sentence().splitword(self, *newwords, **kwargs)

class Hiddenword(AbstractStructureElement, AbstractWord, AllowCorrections):
    """Hidden word (aka token) element. Holds a word/token and all its related inline annotations, but the word is ignored for most intents and purposes. It may act as a dummy for e.g. syntactic movement annotation."""
    pass


class Feature(AbstractElement):
    """Feature elements can be used to associate subsets and subclasses with almost any
    annotation element"""


    def __init__(self,doc, *args, **kwargs): #pylint: disable=super-init-not-called
        """Constructor.

        Keyword Arguments:
            subset (str): the subset
            cls (str): the class
        """

        self.id = None
        self.set = None
        self.data = []
        if not isinstance(doc, Document) and not (doc is None):
            raise Exception("First argument of Feature constructor must be a Document instance, not " + str(type(doc)))
        self.doc = doc
        self.auth = True


        if self.SUBSET:
            self.subset = self.SUBSET
        elif 'subset' in kwargs:
            self.subset = kwargs['subset']
        else:
            raise Exception("No subset specified for " + self.__class__.__name__)
        if 'cls' in kwargs:
            self.cls = kwargs['cls']
        elif 'class' in kwargs:
            self.cls = kwargs['class']
        else:
            raise Exception("No class specified for " + self.__class__.__name__)

        if isinstance(self.cls, datetime):
            self.cls = self.cls.strftime("%Y-%m-%dT%H:%M:%S")

    def xml(self, attribs = None, elements = None, skipchildren = False, form = Form.NORMAL):
        attribs = {}
        if self.subset != self.SUBSET or form == Form.EXPLICIT:
            attribs['subset'] = self.subset
        attribs['class'] =  self.cls
        return getattr(E, Feature.XMLTAG)(**attribs)

    def json(self,attribs=None, recurse=True, ignorelist=False):
        jsonnode= {'type': Feature.XMLTAG}
        jsonnode['subset'] = self.subset
        jsonnode['class'] = self.cls
        return jsonnode

    @classmethod
    def relaxng(cls, includechildren=True, extraattribs = None, extraelements=None):
        return RXE.define( RXE.element(RXE.attribute(name='subset'), RXE.attribute(name='class'),name=cls.XMLTAG), name=cls.XMLTAG,ns=NSFOLIA)

    def deepvalidation(self):
        """Perform deep validation of this element.

        Raises:
            :class:`DeepValidationError`
        """
        if self.doc and self.doc.deepvalidation and self.parent.set and self.parent.set[0] != '_':
            try:
                self.doc.setdefinitions[self.parent.set].testsubclass(self.parent.cls, self.subset, self.cls)
            except KeyError as e:
                if self.parent.cls and not self.doc.allowadhocsets:
                    raise DeepValidationError("Set definition " + self.parent.set + " for " + self.parent.XMLTAG + " not loaded (feature validation failed)!")
            except DeepValidationError as e:
                errormsg =  str(e) + " (in set " + self.parent.set+" for " + self.parent.XMLTAG
                if self.parent.id:
                    errormsg += " with ID " + self.parent.id
                errormsg +=  ")"
                raise DeepValidationError(errormsg)


class ValueFeature(Feature):
    """Value feature, to be used within :class:`Metric`"""
    pass

class Metric(AbstractHigherOrderAnnotation):
    """Metric elements provide a key/value pair to allow the annotation of any kind of metric with any kind of annotation element.

    It is used for example for statistical measures to be added to elements as annotation."""
    pass

class AbstractSubtokenAnnotation(AbstractStructureElement, AllowGenerateID):
    """Abstract element, all subtoken annotation elements are derived from this class"""
    pass

class AbstractSpanAnnotation(AbstractElement, AllowGenerateID, AllowCorrections):
    """Abstract element, all span annotation elements are derived from this class"""

    def xml(self, attribs = None,elements = None, skipchildren = False, form = Form.NORMAL):
        """See :meth:`AbstractElement.xml`"""
        if not attribs: attribs = {}
        e = super(AbstractSpanAnnotation,self).xml(attribs, elements, True, form)
        for child in self:
            if isinstance(child, wrefables):
                #Include REFERENCES to word items instead of word items themselves
                attribs['id'] = child.id
                if child.PRINTABLE and child.hastext(self.textclass):
                    attribs['t'] = child.text(self.textclass)
                e.append( E.wref(**attribs) )
            elif not (isinstance(child, Feature) and child.SUBSET and form != Form.EXPLICIT): #Don't add pre-defined features, they are already added as attributes, except in explicit form
                e.append( child.xml(form=form) )
        return e

    @classmethod
    def accepts(Parentclass, Class, raiseexceptions=True, parentinstance=None):
        #constrain inline annotations under span annotations (requires groupannotation="yes" in declaration, may be autodeclared here)
        if issubclass(Class, AbstractInlineAnnotation):
            if parentinstance is not None and parentinstance.doc:
                if parentinstance.doc.autodeclare:
                    parentinstance.doc.groupannotations[parentinstance.ANNOTATIONTYPE][parentinstance.set] = True
                    return True
                else:
                    return parentinstance.doc.groupannotations[parentinstance.ANNOTATIONTYPE][parentinstance.set]
        return super(AbstractSpanAnnotation,Parentclass).accepts(Class, raiseexceptions, parentinstance)

    def append(self, child, *args, **kwargs):
        """See :meth:`AbstractElement.append`"""
        if isinstance(child, AbstractElement) and child.WREFABLE and WordReference in self.ACCEPTED_DATA:
            #We don't really append but do an insertion so all references are in proper order
            insertionpoint = len(self.data)
            needsort = False
            for i, sibling in enumerate(self.data):
                if isinstance(sibling, AbstractElement) and sibling.WREFABLE:
                    wref = child
                elif isinstance(sibling, AbstractSpanAnnotation):
                    try:
                        wref = sibling.wrefs(0)
                    except IndexError:
                        needsort = True
                else:
                    wref = None
                if wref:
                    try:
                        if not sibling.precedes(wref):
                            insertionpoint = i
                            break
                    except NoCommonAncestor: #happens if we can't determine common ancestors
                        needsort = True

            self.data.insert(insertionpoint, child)
            try:
                child.postappend()
            except Exception as e:
                self.data.remove(child)
                raise e
            if needsort and self.doc and self.doc.doneparsing:
                try:
                    self.doc.layersortbuffer.append(self.layer())
                except:
                    #no such ancestor
                    pass
            return child
        else:
            return super(AbstractSpanAnnotation,self).append(child, *args, **kwargs)

    def setspan(self, *args):
        """Sets the span of the span element anew, erases all data inside.

        Arguments:
            *args: Instances of :class:`Word`, :class:`Morpheme` or :class:`Phoneme`
        """
        self.data = [ x for x in self.data if not isinstance(x, wrefables) ]
        for child in args:
            self.append(child)

    def add(self, child, *args, **kwargs): #alias for append
        return self.append(child, *args, **kwargs)

    def hasannotation(self,Class,set=False):
        """Returns an integer indicating whether such as annotation exists, and if so, how many. See ``annotations()`` for a description of the parameters."""
        return self.count(Class,set,True,default_ignore_annotations)

    def annotation(self, type, set=False):
        """Will return a **single** annotation (even if there are multiple). Raises a ``NoSuchAnnotation`` exception if none was found"""
        l = list(self.select(type,set,True,default_ignore_annotations))
        if len(l) >= 1:
            return l[0]
        else:
            raise NoSuchAnnotation()

    def annotations(self,Class,set=False):
        """Obtain annotations. Very similar to ``select()`` but raises an error if the annotation was not found.

        Arguments:
            * ``Class`` - The Class you want to retrieve (e.g. PosAnnotation)
            * ``set``   - The set you want to retrieve (defaults to None, which selects irregardless of set)

        Yields:
            elements

        Raises:
            ``NoSuchAnnotation`` if the specified annotation does not exist.
        """
        found = False
        for e in self.select(Class,set,True,default_ignore_annotations):
            found = True
            yield e
        if not found:
            raise NoSuchAnnotation()

    def _helper_wrefs(self, targets, recurse=True):
        """Internal helper function"""
        for c in self:
            if isinstance(c, wrefables):
                targets.append(c)
            elif isinstance(c,WordReference):
                try:
                    targets.append(self.doc[c.id]) #try to resolve
                except KeyError:
                    targets.append(c) #add unresolved
            elif isinstance(c, AbstractSpanAnnotation) and recurse:
                #recursion
                c._helper_wrefs(targets) #pylint: disable=protected-access
            elif isinstance(c, Correction) and c.auth: #recurse into corrections
                for e in c:
                    if isinstance(e, AbstractCorrectionChild) and e.auth:
                        for e2 in e:
                            if isinstance(e2, AbstractSpanAnnotation):
                                #recursion
                                e2._helper_wrefs(targets) #pylint: disable=protected-access

    def wrefs(self, index = None, recurse=True):
        """Returns a list of word references, these can be Words but also Morphemes or Phonemes.

        Arguments:
            index (int or None): If set to an integer, will retrieve and return the n'th element (starting at 0) instead of returning the list of all
        """
        targets =[]
        self._helper_wrefs(targets, recurse)
        if index is None:
            return targets
        else:
            return targets[index]

    def addtoindex(self,norecurse=None):
        """Makes sure this element (and all subelements), are properly added to the index"""
        if not norecurse: norecurse = wrefables
        if self.id:
            self.doc.index[self.id] = self
        for e in self.data:
            if all([not isinstance(e, C) for C in norecurse]):
                try:
                    e.addtoindex(norecurse)
                except AttributeError:
                    pass


    def copychildren(self, newdoc=None, idsuffix=""):
        """Generator creating a deep copy of the children of this element. If idsuffix is a string, if set to True, a random idsuffix will be generated including a random 32-bit hash"""
        if idsuffix is True: idsuffix = ".copy." + "%08x" % random.getrandbits(32) #random 32-bit hash for each copy, same one will be reused for all children
        for c in self:
            if isinstance(c, Word):
                yield WordReference(newdoc, id=c.id)
            else:
                yield c.copy(newdoc,idsuffix)

    def postappend(self):
        super(AbstractSpanAnnotation,self).postappend()

        if self.doc and self.doc.doneparsing:
            try:
                layer = self.layer()
                if self not in self.doc.layersortbuffer:
                    self.doc.layersortbuffer.append(layer)
            except NoSuchAnnotation:
                pass

    def layer(self):
        """Return the annotation layer this annotation pertains to"""
        return self.ancestor(AbstractAnnotationLayer)

    def sort(self, force=False):
        """Sort children (wrefs and child spans) in order of appearance. Returns True if sort is successful (or not needed), False if sort could not be performed at this stage"""
        if self.doc and self.doc.debug >= 2: print("CALLED SORT ON", type(self), self.id,file=sys.stderr)
        nonrefdata = [] #data that has no wrefs
        refdata = [] #data that has wrefs
        missingparents = False
        duplicates = set() #set of potential duplicate wrefs in parent and children
        for e in self.data:
            missingparents = not e.parent or missingparents
            #is this element a word reference?
            reference = True #falsify
            if isinstance(e, AbstractSpanAnnotation):
                if self.doc and self.doc.debug >= 2: print("RECURSION",file=sys.stderr)
                e.sort()
                if self.doc and self.doc.debug >= 2: print("RETURNED FROM RECURSION, ",type(self), self.id,file=sys.stderr)
                try:
                    w = e.wrefs(0, recurse=True)
                except IndexError:
                    #empty span
                    if self.doc and self.doc.debug >= 2: print("EMPTY SPAN ", (type(e), self.id),file=sys.stderr)
                    reference = False

                #If a child span contains references that the parent span also contains, they will be removed from the parent, as they are already implicit through recursion.
                for childwref in e.wrefs(recurse=True):
                    if childwref in self.data:
                        duplicates.add(childwref)

            elif not isinstance(e, wrefables):
                reference = False
            if not reference:
                nonrefdata.append(e)
            else:
                refdata.append(e)

        refdata = [ w for w in refdata if w not in duplicates ]
        self.data = nonrefdata + refdata #everything that is a non-reference will precede everything that is a reference

        if missingparents:
            #unable to sort if not all elements have parents yet, defer to later stage (e.g. serialisation)
            if self.doc and self.doc.debug >= 2: print(" MISSING PARENTS INSIDE ", (type(self), self.id),file=sys.stderr)
            return False

        if len(refdata) <= 1:
            return True #by definition in proper order


        cache = set() #contains (w1,w2) word tuples indicating w1 precedes w2 (to prevent recomputation)

        if self.doc and self.doc.debug >= 2: print(" SORTING ", (type(self), self.id),file=sys.stderr)
        if self.doc and self.doc.debug >= 2: print("  SORT BEFORE: ", [(type(e), e.id) for e in self.data] ,file=sys.stderr)
        #now make sure everything that is a reference is in proper order
        #using a simple bubble sort
        inorder = False
        while not inorder: #as long as elements are not in proper order
            inorder = True #falsify this
            for i in range(len(nonrefdata),len(self.data) - 1):
                e1 = self.data[i]
                e2 = self.data[i+1]

                if isinstance(e1, wrefables):
                    e1_word = e1
                elif isinstance(e1, AbstractSpanAnnotation):
                    e1_word = e1.wrefs(0, recurse=True)
                else: #TODO: corrections
                    e1_word = None
                if isinstance(e2, wrefables):
                    e2_word = e2
                elif isinstance(e2, AbstractSpanAnnotation):
                    e2_word = e2.wrefs(0, recurse=True)
                else: #TODO: corrections
                    e2_word = None

                if self.doc and self.doc.debug >= 2: print("     TESTING: ",  type(e1),e1.id , " vs ", type(e2),e2.id,file=sys.stderr)
                if e1_word and e2_word:
                    if self.doc and self.doc.debug >= 2: print("       CHECKING: ",  e1_word.id , " vs ", e2_word.id ,file=sys.stderr)
                    try:
                        if not e1_word.precedes(e2_word):
                            if self.doc and self.doc.debug >= 2: print("       SWAPPING!",file=sys.stderr)
                            #swap places
                            self.data[i] = e2
                            self.data[i+1] = e1
                            #cache.add((e2_word,e1_word))
                            inorder = False
                        else:
                            if self.doc and self.doc.debug >= 2: print("       OK!",file=sys.stderr)
                            #cache.add((e1_word,e2_word))
                    except NoCommonAncestor:
                            if self.doc and self.doc.debug >= 2: print("       No common ancestor",file=sys.stderr)
                else:
                    if self.doc and self.doc.debug >= 2: print("       NO REFERENCE WORDS", file=sys.stderr)

            if self.doc and self.doc.debug >= 2: print("  SORT AFTER: ", [(type(e), e.id) for e in self.data] ,file=sys.stderr)
        return True

class AbstractAnnotationLayer(AbstractElement, AllowGenerateID, AllowCorrections):
    """Annotation layers for Span Annotation are derived from this abstract base class"""

    def __init__(self, doc, *args, **kwargs):
        self.set = False # This is the initial default and we retain this value to indicate we don't know the set yet, but it will be assigned as soon as elements are appended
        if 'set' in kwargs:
            self.set = kwargs['set']
        elif doc:
            try:
                defaultset = doc.defaultset(self.ANNOTATIONTYPE)
            except NoSuchAnnotation:
                defaultset = False
            if defaultset is not False:
                self.set = defaultset
        super(AbstractAnnotationLayer,self).__init__(doc, *args, **kwargs)


    def xml(self, attribs = None,elements = None, skipchildren = False, form = Form.NORMAL):
        """See :meth:`AbstractElement.xml`"""
        if self.set is False:
            if len(self.data) == 0: #just skip the entire layer if there are no children at all
                return None
            else:
                #this should have been prevented by the AbstractAnnotationLayer.append() method which will assign a set
                #we just keep it set to False
                #raise ValueError("No set specified or derivable for annotation layer " + self.__class__.__name__) #too strict at this point, leads to problems
                pass
        return super(AbstractAnnotationLayer, self).xml(attribs, elements, skipchildren, form)

    def append(self, child, *args, **kwargs):
        """See :meth:`AbstractElement.append`"""
        #if no set is associated with the layer yet, we learn it from span annotation elements that are added
        if self.set is False:
            if inspect.isclass(child) and child.ANNOTATIONTYPE == self.ANNOTATIONTYPE:
                if issubclass(child,(AbstractSpanAnnotation,AbstractSubtokenAnnotation)):
                    if 'set' in kwargs:
                        self.set = kwargs['set']
            elif isinstance(child, (AbstractSpanAnnotation,AbstractSubtokenAnnotation)) and child.ANNOTATIONTYPE == self.ANNOTATIONTYPE:
                if child.set is not False:
                    self.set = child.set
            elif isinstance(child, Correction):
                #descend into corrections to find the proper set for this layer (derived from span annotation elements)
                for e in itertools.chain( child.new(), child.original(), child.suggestions() ):
                    if isinstance(e, (AbstractSpanAnnotation, AbstractSubtokenAnnotation)) and e.set is not False and child.ANNOTATIONTYPE == self.ANNOTATIONTYPE:
                        self.set = e.set
                        break
            if self.set is not False and self.doc and self.doc.debug >= 1:
                print("[FoLiA DEBUG] Derived set " + repr(self.set) + " for " + self.__class__.__name__,file=stderr)

        return super(AbstractAnnotationLayer, self).append(child, *args, **kwargs)

    def postappend(self):
        super(AbstractAnnotationLayer, self).postappend()
        if self.doc:
            self.doc.layersortbuffer.append(self)  #will hold instances derived off AbstractAnnotationLayer (i.e. all span annotation layers), so the the span annotations within can be sorted after all parsing is done

    def add(self, child, *args, **kwargs): #alias for append
        return self.append(child, *args, **kwargs)

    def annotations(self,Class,set=False):
        """Obtain annotations. Very similar to ``select()`` but raises an error if the annotation was not found.

        Arguments:
            * ``Class`` - The Class you want to retrieve (e.g. PosAnnotation)
            * ``set``   - The set you want to retrieve (defaults to False, which selects irregardless of set)

        Yields:
            elements

        Raises:
            ``NoSuchAnnotation`` if the specified annotation does not exist.
        """
        found = False
        for e in self.select(Class,set,True,default_ignore_annotations):
            found = True
            yield e
        if not found:
            raise NoSuchAnnotation()

    def hasannotation(self,Class,set=False):
        """Returns an integer indicating whether such as annotation exists, and if so, how many. See ``annotations()`` for a description of the parameters."""
        return self.count(Class,set,True,default_ignore_annotations)

    def annotation(self, type, set=False):
        """Will return a **single** annotation (even if there are multiple). Raises a ``NoSuchAnnotation`` exception if none was found"""
        for e in self.select(type,set,True,default_ignore_annotations):
            return e
        raise NoSuchAnnotation()

    def findspan(self, *words):
        """Returns the span element which spans over the specified words or morphemes.

        See also:
            :meth:`Word.findspans`
        """

        for span in self.select(AbstractSpanAnnotation,False,True):
            if tuple(span.wrefs()) == words:
                return span
        raise NoSuchAnnotation

    @classmethod
    def relaxng(cls, includechildren=True,extraattribs = None, extraelements=None, origclass = None):
        """Returns a RelaxNG definition for this element (as an XML element (lxml.etree) rather than a string)"""
        if not extraattribs:
            extraattribs = []
        extraattribs.append(RXE.optional(RXE.attribute(RXE.text(), name='set')) )
        return AbstractElement.relaxng(includechildren, extraattribs, extraelements, cls)

    def deepvalidation(self):
        return True

    def sort(self):
        for e in self:
            if isinstance(e, AbstractSpanAnnotation):
                e.sort()

# class AbstractSubtokenAnnotationLayer(AbstractElement, AllowGenerateID):
    # """Annotation layers for Subtoken Annotation are derived from this abstract base class"""
    # OPTIONAL_ATTRIBS = ()
    # PRINTABLE = False

    # def __init__(self, doc, *args, **kwargs):
        # if 'set' in kwargs:
            # self.set = kwargs['set']
            # del kwargs['set']
        # super(AbstractSubtokenAnnotationLayer,self).__init__(doc, *args, **kwargs)



class String(AbstractElement, AllowInlineAnnotation):
    """String"""

    def postappend(self):
        if self.doc and self.doc.textvalidation:
            self.doc.textvalidationerrors += int(not self.textvalidation())

class AbstractCorrectionChild(AbstractElement):
    def generate_id(self, cls):
        #Delegate ID generation to parent
        return self.parent.generate_id(cls)

    def deepvalidation(self):
        return True

class Reference(AbstractStructureElement):
    """A structural element that denotes a reference, internal or external. Examples are references to footnotes, bibliographies, hyperlinks."""

    def __init__(self, doc, *args, **kwargs):
        if 'idref' in kwargs:
            self.idref = kwargs['idref']
            del kwargs['idref']
        else:
            self.idref = None
        if 'type' in kwargs:
            self.type = kwargs['type']
            del kwargs['type']
        else:
            self.type = None
        if 'format' in kwargs:
            self.format = kwargs['format']
            del kwargs['format']
        else:
            self.format = "text/folia+xml"
        super(Reference,self).__init__(doc, *args, **kwargs)

    def xml(self, attribs = None,elements = None, skipchildren = False, form = Form.NORMAL):
        if not attribs: attribs = {}
        if self.idref:
            attribs['id'] = self.idref
        if self.type:
            attribs['type'] = self.type
        if self.format and self.format != "text/folia+xml":
            attribs['format'] = self.format
        return super(Reference,self).xml(attribs,elements, skipchildren, form)

    def json(self, attribs=None, recurse=True, ignorelist=False):
        if attribs is None: attribs = {}
        if self.idref:
            attribs['idref'] = self.idref
        if self.type:
            attribs['type'] = self.type
        if self.format:
            attribs['format'] = self.format
        return super(Reference,self).json(attribs,recurse,ignorelist)

    def resolve(self):
        if self.idref:
            return self.doc[self.idref]
        else:
            return self

    @classmethod
    def parsexml(Class, node, doc, **kwargs):#pylint: disable=bad-classmethod-argument
        if not kwargs: kwargs = {}
        if 'id' in node.attrib:
            kwargs['idref'] = node.attrib['id']
            del node.attrib['id']
        if 'type' in node.attrib:
            kwargs['type'] = node.attrib['type']
            del node.attrib['type']
        if 'format' in node.attrib:
            kwargs['format'] = node.attrib['format']
            del node.attrib['format']
        return super(Reference,Class).parsexml(node, doc, **kwargs)


    @classmethod
    def relaxng(cls, includechildren=True,extraattribs = None, extraelements=None):
        if not extraattribs: extraattribs = []
        extraattribs.append( RXE.optional(RXE.attribute(name='id'))) #id reference
        extraattribs.append( RXE.optional(RXE.attribute(name='type' )))
        extraattribs.append( RXE.optional(RXE.attribute(name='format' )))
        return super(Reference, cls).relaxng(includechildren, extraattribs, extraelements)

class LinkReference(AbstractElement):
    """The LinkReference element is used to point to specific elements inside the aligned source.

    It is used with :class:`Relation` which is responsible for pointing to the external resource."""

    def __init__(self, doc, *args, **kwargs): #pylint: disable=super-init-not-called
        #Special constructor, not calling super constructor
        if 'id' not in kwargs:
            raise Exception("ID required for LinkReference")
        if 'type' in kwargs:
            if isinstance(kwargs['type'], AbstractElement) or inspect.isclass(kwargs['type']):
                self.type = kwargs['type'].XMLTAG
            else:
                self.type = kwargs['type']
        else:
            self.type = None
        if 't' in kwargs:
            self.t = kwargs['t']
        else:
            self.t = None
        assert(isinstance(doc,Document))
        self.doc = doc
        self.id = kwargs['id']
        self.auth = False
        self.set = None
        self.data = []



    @classmethod
    def parsexml(Class, node, doc, **kwargs):#pylint: disable=bad-classmethod-argument
        assert Class is LinkReference or issubclass(Class, LinkReference)

        #special handling for word references
        if not kwargs: kwargs = {}
        kwargs['id'] = node.attrib['id']
        if 't' in node.attrib:
            kwargs['t'] = node.attrib['t']
        if 'type' in node.attrib:
            kwargs['type'] = node.attrib['type']
        return LinkReference(doc,**kwargs)

    @classmethod
    def relaxng(cls, includechildren=True,extraattribs = None, extraelements=None):
        return RXE.define( RXE.element(RXE.attribute(RXE.text(), name='id'), RXE.optional(RXE.attribute(RXE.text(), name='t')), RXE.optional(RXE.attribute(RXE.text(), name='type')), name=cls.XMLTAG), name=cls.XMLTAG, ns=NSFOLIA)

    def resolve(self, context=None, documents={}):
        if not context or not hasattr(context, 'href') or not context.href:
            #no target document, same document
            return self.doc[self.id]
        else:
            #other document
            if context.href in documents:
                return documents[context.href][self.id]
            else:
                raise DocumentNotLoaded()

    def xml(self, attribs = None,elements = None, skipchildren = False, form = Form.NORMAL):
        if self.doc:
            FOLIA1 = self.doc.FOLIA1
        else:
            FOLIA1 = False
        if not attribs:
            attribs = {}
        attribs['id'] = self.id
        if self.type:
            attribs['type'] = self.type
        if self.t: attribs['t'] = self.t

        if FOLIA1 and self.doc and self.doc.keepversion:
            return E.aref( **attribs)
        else:
            return E.xref( **attribs)

    def json(self, attribs=None, recurse=True, ignorelist=False):
        jsonnode = {}
        jsonnode['type'] = self.XMLTAG
        jsonnode['idref'] = self.id
        if self.type:
            jsonnode['linktype'] = self.type
        if self.t:
            jsonnode['t'] = self.t
        return jsonnode

AlignReference = LinkReference #backward compatibility for FoLiA < 2


class Relation(AbstractElement):
    """
    The Relation element is a form of higher-order annotation that is used to point to an external resource.

    It concerns references as annotation rather than references which are
    explicitly part of the text, such as hyperlinks and :class:`Reference`.

    Inside the Relation element, the :class:`LinkReference` element may be used to point to specific elements (multiple denotes a span).
    """

    def __init__(self, doc, *args, **kwargs):
        if 'format' in kwargs:
            self.format = kwargs['format']
            del kwargs['format']
        else:
            self.format = "text/folia+xml"
        super(Relation,self).__init__(doc, *args, **kwargs)

    @classmethod
    def parsexml(Class, node, doc, **kwargs):#pylint: disable=bad-classmethod-argument
        if 'format' in node.attrib:
            kwargs['format'] = node.attrib['format']
            del node.attrib['format']
        return super(Relation,Class).parsexml(node, doc, **kwargs)

    def xml(self, attribs = None,elements = None, skipchildren = False, form = Form.NORMAL):
        if not attribs: attribs = {}
        if self.format and self.format != "text/folia+xml":
            attribs['format'] = self.format
        return super(Relation,self).xml(attribs,elements, skipchildren, form)

    def json(self, attribs =None, recurse=True, ignorelist=False):
        if not attribs: attribs = {}
        if self.format and self.format != "text/folia+xml":
            attribs['format'] = self.format
        return super(Relation,self).json(attribs,recurse, ignorelist)

    def resolve(self, documents=None):
        """Resolves the targets to which this relation refers, returns a generator"""
        if documents is None: documents = {}
        #documents is a dictionary of urls to document instances, to aid in resolving cross-document alignments
        targets = []
        for x in self.select(LinkReference,False,True,False):
            yield x.resolve(self, documents)

    def targets(self, documents=None): #alias
        """Returns the targets to which this relation refers, as a list"""
        return list(self.resolve(documents))

    @classmethod
    def relaxng(cls, includechildren=True,extraattribs = None, extraelements=None):
        if extraattribs is None: extraattribs = []
        extraattribs.append(RXE.optional(RXE.attribute(name="format")))
        return super(Relation,cls).relaxng(includechildren, extraattribs, extraelements)

Alignment = Relation #backward compatibility for FoLiA < 2


class ErrorDetection(AbstractInlineAnnotation):
    """The ErrorDetection element is used to signal the presence of errors in a structural element."""
    pass



class Suggestion(AbstractCorrectionChild):
    """Suggestions are used in the context of :class:`Correction`, but rather than provide an authoritative correction, it instead offers a suggestion for correction."""

    def __init__(self,  doc, *args, **kwargs):
        if 'split' in kwargs:
            self.split = kwargs['split']
            del kwargs['split']
        else:
            self.split = None
        if 'merge' in kwargs:
            self.merge = kwargs['merge']
            del kwargs['merge']
        else:
            self.merge = None
        super(Suggestion,self).__init__(doc, *args, **kwargs)

    @classmethod
    def parsexml(Class, node, doc, **kwargs): #pylint: disable=bad-classmethod-argument
        if not kwargs: kwargs = {}
        if 'split' in node.attrib:
            kwargs['split'] = node.attrib['split']
        if 'merge' in node.attrib:
            kwargs['merge'] = node.attrib['merge']
        if 'annotator' in node.attrib:
            print("WARNING: Usage of annotator attribute on <suggestion> element is deprecated in FoLiA v2! Ignoring value '" + node.attrib['annotator'] + "'",file=sys.stderr)
            del kwargs['annotator']
        if 'annotatortype' in node.attrib:
            print("WARNING: Usage of annotatortype attribute on <suggestion> element is deprecated in FoLiA v2! Ignoring value '" + node.attrib['annotatortype'] + "'",file=sys.stderr)
            del kwargs['annotatortype']
        return super(Suggestion,Class).parsexml(node, doc, **kwargs)

    def xml(self, attribs = None,elements = None, skipchildren = False, form = Form.NORMAL):
        if not attribs: attribs= {}

        if self.split: attribs['split']  = self.split
        if self.merge: attribs['merge']  = self.merge

        return super(Suggestion, self).xml(attribs, elements, skipchildren, form )

    @classmethod
    def relaxng(cls, includechildren=True,extraattribs = None, extraelements=None):
        if not extraattribs: extraattribs = []
        extraattribs.append( RXE.optional(RXE.attribute(name='split' )))
        extraattribs.append( RXE.optional(RXE.attribute(name='merge' )))
        return super(Suggestion, cls).relaxng(includechildren, extraattribs, extraelements)

    def json(self, attribs = None, recurse=True,ignorelist=False):
        if self.split:
            if not attribs: attribs = {}
            attribs['split'] = self.split
        if self.merge:
            if not attribs: attribs = {}
            attribs['merge'] = self.merge
        return super(Suggestion, self).json(attribs, recurse, ignorelist)

class New(AbstractCorrectionChild):

    @classmethod
    def addable(Class, parent, set=False, raiseexceptions=True):#pylint: disable=bad-classmethod-argument
        if not super(New,Class).addable(parent,set,raiseexceptions): return False
        if any( ( isinstance(c, Current) for c in parent ) ):
            if raiseexceptions:
                raise ValueError("Can't add New element to Correction if there is a Current item")
            else:
                return False
        return True

    def correct(self, **kwargs):
        return self.parent.correct(**kwargs)

class Original(AbstractCorrectionChild):
    """Used in the context of :class:`Correction` to encapsulate the original annotations *prior* to correction."""

    @classmethod
    def addable(Class, parent, set=False, raiseexceptions=True):#pylint: disable=bad-classmethod-argument
        if not super(Original,Class).addable(parent,set,raiseexceptions): return False
        if any( ( isinstance(c, Current)  for c in parent ) ):
            if raiseexceptions:
                raise Exception("Can't add Original item to Correction if there is a Current item")
            else:
                return False
        return True


class Current(AbstractCorrectionChild):
    """Used in the context of :class:`Correction` to encapsulate the currently authoritative annotations.

    Needed only when suggestions for correction are proposed (:class:`Suggestion`) for structural elements.
    """

    @classmethod
    def addable(Class, parent, set=False, raiseexceptions=True):
        if not super(Current,Class).addable(parent,set,raiseexceptions): return False
        if any( ( isinstance(c, New) or isinstance(c, Original) for c in parent ) ):
            if raiseexceptions:
                raise Exception("Can't add Current element to Correction if there is a New or Original element")
            else:
                return False
        return True

    def correct(self, **kwargs):
        return self.parent.correct(**kwargs)

class Correction(AbstractHigherOrderAnnotation, AllowGenerateID):
    """
    Corrections are one of the most complex annotation types in FoLiA. Corrections
    can be applied not just over text, but over any type of structure annotation,
    inline annotation or span annotation. Corrections explicitly preserve the
    original, and recursively so if corrections are done over other corrections.

    Despite their complexity, the library treats correction transparently. Whenever
    you query for a particular element, and it is part of a correction, you get the
    corrected version rather than the original. The original is always *non-authoritative*
    and normal selection methods will ignore it.

    This class takes four classes as children, that in turn encapsulate the actual annotations:
        * :class:`New` - Encapsulates the newly corrected annotation(s)
        * :class:`Original` - Encapsulated the old original annotation(s)
        * :class:`Current` - Encapsulates the current authoritative annotation(s)
        * :class:`Suggestions` - Encapsulates the annotation(s) that are a non-authoritative suggestion for correction
    """

    def append(self, child, *args, **kwargs):
        """See ``AbstractElement.append()``"""
        e = super(Correction,self).append(child, *args, **kwargs)
        self._setmaxid(e)
        return e

    def hasnew(self,allowempty=False):
        """Does the correction define new corrected annotations?"""
        for e in  self.select(New,False,False, False):
            if not allowempty and len(e) == 0: continue
            return True
        return False

    def hasoriginal(self,allowempty=False):
        """Does the correction record the old annotations prior to correction?"""
        for e in self.select(Original,False,False, False):
            if not allowempty and len(e) == 0: continue
            return True
        return False

    def hascurrent(self, allowempty=False):
        """Does the correction record the current authoritative annotation (needed only in a structural context when suggestions are proposed)"""
        for e in self.select(Current,False,False, False):
            if not allowempty and len(e) == 0: continue
            return True
        return False

    def hassuggestions(self,allowempty=False):
        """Does the correction propose suggestions for correction?"""
        for e in self.select(Suggestion,False,False, False):
            if not allowempty and len(e) == 0: continue
            return True
        return False

    def textcontent(self, cls='current', correctionhandling=CorrectionHandling.CURRENT, hidden=False):
        """See :meth:`AbstractElement.textcontent`"""
        if cls == 'original': correctionhandling = CorrectionHandling.ORIGINAL #backward compatibility
        if correctionhandling in (CorrectionHandling.CURRENT, CorrectionHandling.EITHER):
            for e in self:
                if isinstance(e, New) or isinstance(e, Current):
                    return e.textcontent(cls,correctionhandling, hidden)
        if correctionhandling in (CorrectionHandling.ORIGINAL, CorrectionHandling.EITHER):
            for e in self:
                if isinstance(e, Original):
                    return e.textcontent(cls,correctionhandling, hidden)
        raise NoSuchText


    def phoncontent(self, cls='current', correctionhandling=CorrectionHandling.CURRENT):
        """See :meth:`AbstractElement.phoncontent`"""
        if cls == 'original': correctionhandling = CorrectionHandling.ORIGINAL #backward compatibility
        if correctionhandling in (CorrectionHandling.CURRENT, CorrectionHandling.EITHER):
            for e in self:
                if isinstance(e, New) or isinstance(e, Current):
                    return e.phoncontent(cls, correctionhandling)
        if correctionhandling in (CorrectionHandling.ORIGINAL, CorrectionHandling.EITHER):
            for e in self:
                if isinstance(e, Original):
                    return e.phoncontent(cls, correctionhandling)
        raise NoSuchPhon


    def hastext(self, cls='current',strict=True, correctionhandling=CorrectionHandling.CURRENT):
        """See :meth:`AbstractElement.hastext`"""
        if cls == 'original': correctionhandling = CorrectionHandling.ORIGINAL #backward compatibility
        if correctionhandling in (CorrectionHandling.CURRENT, CorrectionHandling.EITHER):
            for e in self:
                if isinstance(e, New) or isinstance(e, Current):
                    return e.hastext(cls,strict, correctionhandling)
        if correctionhandling in (CorrectionHandling.ORIGINAL, CorrectionHandling.EITHER):
            for e in self:
                if isinstance(e, Original):
                    return e.hastext(cls,strict, correctionhandling)
        return False

    def text(self, cls = 'current', retaintokenisation=False, previousdelimiter="",strict=False, correctionhandling=CorrectionHandling.CURRENT, normalize_spaces=False, hidden=False, trim_spaces=True):
        """See :meth:`AbstractElement.text`"""
        if cls == 'original': correctionhandling = CorrectionHandling.ORIGINAL #backward compatibility
        if correctionhandling in (CorrectionHandling.CURRENT, CorrectionHandling.EITHER):
            for e in self:
                if isinstance(e, New) or isinstance(e, Current):
                    s = previousdelimiter + e.text(cls, retaintokenisation,"", strict, correctionhandling, trim_spaces=trim_spaces)
                    if normalize_spaces:
                        return norm_spaces(s)
                    else:
                        return s
        if correctionhandling in (CorrectionHandling.ORIGINAL, CorrectionHandling.EITHER):
            for e in self:
                if isinstance(e, Original):
                    s =  previousdelimiter + e.text(cls, retaintokenisation,"", strict, correctionhandling, trim_spaces=trim_spaces)
                    if normalize_spaces:
                        return norm_spaces(s)
                    else:
                        return s
        raise NoSuchText

    def hasphon(self, cls='current',strict=True, correctionhandling=CorrectionHandling.CURRENT):
        """See :meth:`AbstractElement.hasphon`"""
        if cls == 'original': correctionhandling = CorrectionHandling.ORIGINAL #backward compatibility
        if correctionhandling in (CorrectionHandling.CURRENT, CorrectionHandling.EITHER):
            for e in self:
                if isinstance(e, New) or isinstance(e, Current):
                    return e.hasphon(cls,strict, correctionhandling)
        if correctionhandling in (CorrectionHandling.ORIGINAL, CorrectionHandling.EITHER):
            for e in self:
                if isinstance(e, Original):
                    return e.hasphon(cls,strict, correctionhandling)
        return False

    def phon(self, cls = 'current', previousdelimiter="",strict=False, correctionhandling=CorrectionHandling.CURRENT):
        """See :meth:`AbstractElement.phon`"""
        if cls == 'original': correctionhandling = CorrectionHandling.ORIGINAL #backward compatibility
        if correctionhandling in (CorrectionHandling.CURRENT, CorrectionHandling.EITHER):
            for e in self:
                if isinstance(e, New) or isinstance(e, Current):
                    return previousdelimiter + e.phon(cls, "", strict, correctionhandling)
        if correctionhandling in (CorrectionHandling.ORIGINAL, CorrectionHandling.EITHER):
            for e in self:
                if isinstance(e, Original):
                    return previousdelimiter + e.phon(cls, "", correctionhandling)
        raise NoSuchPhon

    def gettextdelimiter(self, retaintokenisation=False):
        """See :meth:`AbstractElement.gettextdelimiter`"""
        for e in self:
            if isinstance(e, New) or isinstance(e, Current):
                return e.gettextdelimiter(retaintokenisation)
        return ""


    def new(self,index = None):
        """Get the new corrected annotation.

        This returns only one annotation if multiple exist, use `index` to select another in the sequence.

        Returns:
            an annotation element (:class:`AbstractElement`)

        Raises:
            :class:`NoSuchAnnotation`
        """

        if index is None:
            try:
                return next(self.select(New,False,False))
            except StopIteration:
                raise NoSuchAnnotation
        else:
            for e in self.select(New,False,False):
                return e[index]
            raise NoSuchAnnotation

    def original(self,index=None):
        """Get the old annotation prior to correction.

        This returns only one annotation if multiple exist, use `index` to select another in the sequence.

        Returns:
            an annotation element (:class:`AbstractElement`)

        Raises:
            :class:`NoSuchAnnotation`
        """
        if index is None:
            try:
                return next(self.select(Original,False,False, False))
            except StopIteration:
                raise NoSuchAnnotation
        else:
            for e in self.select(Original,False,False, False):
                return e[index]
            raise NoSuchAnnotation

    def current(self,index=None):
        """Get the current authoritative annotation (used with suggestions in a structural context)

        This returns only one annotation if multiple exist, use `index` to select another in the sequence.

        Returns:
            an annotation element (:class:`AbstractElement`)

        Raises:
            :class:`NoSuchAnnotation`
        """
        if index is None:
            try:
                return next(self.select(Current,False,False))
            except StopIteration:
                raise NoSuchAnnotation
        else:
            for e in self.select(Current,False,False):
                return e[index]
            raise NoSuchAnnotation

    def suggestions(self,index=None):
        """Get suggestions for correction.

        Yields:
            :class:`Suggestion` element that encapsulate the suggested annotations (if index is ``None``, default)

        Returns:
            a :class:`Suggestion` element that encapsulate the suggested annotations (if index is set)

        Raises:
            :class:`IndexError`
        """
        if index is None:
            return self.select(Suggestion,False,False, False)
        else:
            for i, e in enumerate(self.select(Suggestion,False,False, False)):
                if index == i:
                    return e
            raise IndexError


    def __unicode__(self):
        return str(self)

    def __str__(self):
        return self.text(self, 'current', False, "",False, CorrectionHandling.EITHER)

    def correct(self, **kwargs):
        if 'new' in kwargs:
            if 'nooriginal' not in kwargs: #if not an insertion
                kwargs['original'] = self
        elif 'current' in kwargs:
            kwargs['current'] = self

        if 'insertindex' in kwargs:
            #recompute insertindex
            index = self.parent.getindex(self)
            if index != -1:
                kwargs['insertindex'] = index
                if 'insertindex_offset' in kwargs:
                    kwargs['insertindex'] += kwargs['insertindex_offset']
                    del kwargs['insetindex_offset']
            else:
                raise Exception("Can't find insertion point for higher-order correction")
        return self.parent.correct(**kwargs)

    #obsolete
    #def select(self, cls, set=None, recursive=True,  ignorelist=[], node=None):
    #    """Select on Correction only descends in either "NEW" or "CURRENT" branch"""
    #    if ignorelist is False:
    #        #to override and go into all branches, set ignorelist explictly to False
    #        return super(Correction,self).select(cls,set,recursive, ignorelist, node)
    #    else:
    #        if ignorelist is True:
    #            ignorelist = copy(default_ignore)
    #        else:
    #            ignorelist = copy(ignorelist) #we don't want to alter a passed ignorelist (by ref)
    #        ignorelist.append(Original)
    #        ignorelist.append(Suggestion)
    #        return super(Correction,self).select(cls,set,recursive, ignorelist, node)





class Alternative(AbstractHigherOrderAnnotation, AllowInlineAnnotation, AllowGenerateID):
    """Element grouping alternative inline annotation(s).

    Multiple alternative elements may occur, each denoting a different alternative. Elements grouped inside an alternative block are considered dependent.

    A key feature of FoLiA is its ability to make explicit alternative
    annotations, for inline annotations, this class is used to this end.
    Alternative annotations are embedded in this structure. This implies the
    annotation is *not authoritative*, but is merely an alternative to the
    actual annotation (if any). Alternatives may typically occur in larger
    numbers, representing a distribution each with a confidence value (not
    mandatory). Each alternative is wrapped in its an instance of this class,
    as multiple elements inside a single alternative are considered dependent
    and part of the same alternative. Combining multiple annotation in one
    alternative makes sense for mixed annotation types, where for instance a
    pos tag alternative is tied to a particular lemma.
    """

    def __init__(self, doc, *args, **kwargs):
        """See :meth:`AbstractElement.__init__`"""
        if 'exclusive' in kwargs and kwargs['exclusive'] in (True,'yes','true',1):
            #for backward compatibility
            self.exclusive = True
            del kwargs['exclusive']
        super(Alternative,self).__init__(doc, *args, **kwargs)

    def xml(self, attribs = None,elements = None, skipchildren = False, form = Form.NORMAL):
        """See :meth:`AbstractElement.xml`"""
        if not attribs: attribs = {}
        if self.exclusive:
            attribs['exclusive'] = "yes"
        return super(Alternative,self).xml(attribs,elements, skipchildren, form)

    def json(self,attribs =None, recurse=True, ignorelist=False):
        """See :meth:`AbstractElement.json`"""
        if not attribs: attribs = {}
        if self.exclusive:
            attribs['exclusive'] = True
        return super(Alternative,self).json(attribs,recurse, ignorelist)

    @classmethod
    def parsexml(Class, node, doc, **kwargs):
        if not kwargs: kwargs ={}
        if 'exclsuive' in node.attrib:
            kwargs['exclusive'] = node.attrib['exclusive']
            del node.attrib['exclusive']
        return super(Alternative,Class).parsexml(node, doc, **kwargs)

    @classmethod
    def relaxng(cls, includechildren=True,extraattribs = None, extraelements=None):
        if not extraattribs: extraattribs = []
        extraattribs.append( RXE.optional(RXE.attribute(name='exclusive' ))) #id reference
        return super(Alternative, cls).relaxng(includechildren, extraattribs, extraelements)

    def deepvalidation(self):
        return True



class AlternativeLayers(AbstractHigherOrderAnnotation):
    """Element grouping alternative span or subtoken annotation(s). Multiple altlayers elements may occur, each denoting a different alternative. Elements grouped inside an alternative block are considered dependent."""

    def __init__(self, doc, *args, **kwargs):
        """See :meth:`AbstractElement.__init__`"""
        if 'exclusive' in kwargs and kwargs['exclusive'] in (True,'yes','true',1):
            #for backward compatibility
            self.exclusive = True
            del kwargs['exclusive']
        super(AlternativeLayers,self).__init__(doc, *args, **kwargs)

    def xml(self, attribs = None,elements = None, skipchildren = False, form = Form.NORMAL):
        """See :meth:`AbstractElement.xml`"""
        if not attribs: attribs = {}
        if self.exclusive:
            attribs['exclusive'] = "yes"
        return super(AlternativeLayers,self).xml(attribs,elements, skipchildren, form)

    def json(self,attribs =None, recurse=True, ignorelist=False):
        """See :meth:`AbstractElement.json`"""
        if not attribs: attribs = {}
        if self.exclusive:
            attribs['exclusive'] = True
        return super(AlternativeLayers,self).json(attribs,recurse, ignorelist)

    @classmethod
    def parsexml(Class, node, doc, **kwargs):
        if not kwargs: kwargs ={}
        if 'exclsuive' in node.attrib:
            kwargs['exclusive'] = node.attrib['exclusive']
            del node.attrib['exclusive']
        return super(AlternativeLayers,Class).parsexml(node, doc, **kwargs)

    @classmethod
    def relaxng(cls, includechildren=True,extraattribs = None, extraelements=None):
        if not extraattribs: extraattribs = []
        extraattribs.append( RXE.optional(RXE.attribute(name='exclusive' ))) #id reference
        return super(AlternativeLayers, cls).relaxng(includechildren, extraattribs, extraelements)

    def deepvalidation(self):
        return True



class External(AbstractHigherOrderAnnotation):
    """External annotation makes a reference to an external FoLiA document whose structure is inserted at the exact place the external element occurs."""


class WordReference(AbstractElement):
    """Word reference. Used to refer to words or morphemes from span annotation elements. The Python class will only be used when word reference can not be resolved, if they can, Word or Morpheme objects will be used"""

    def __init__(self, doc, *args, **kwargs): #pylint: disable=super-init-not-called
        #Special constructor, not calling super constructor
        if 'idref' not in kwargs and 'id' not in kwargs:
            raise Exception("ID required for WordReference")
        assert isinstance(doc,Document)
        self.doc = doc
        if 'idref' in kwargs:
            self.id = kwargs['idref']
        else:
            self.id = kwargs['id']
        self.data = []
        self.auth = True

    @classmethod
    def parsexml(Class, node, doc, **kwargs):#pylint: disable=bad-classmethod-argument
        assert Class is WordReference or issubclass(Class, WordReference)
        #special handling for word references
        id = node.attrib['id']
        if doc.debug >= 1: print("[FoLiA DEBUG] Found word reference",file=stderr)
        try:
            return doc[id]
        except KeyError:
            if doc.debug >= 1: print("[FoLiA DEBUG] ...Unresolvable!",file=stderr)
            if doc.checkreferences:
                raise InvalidReference(id)
            else:
                return WordReference(doc, id=id)

    @classmethod
    def relaxng(cls, includechildren=True,extraattribs = None, extraelements=None):
        return RXE.define( RXE.element(RXE.attribute(RXE.text(), name='id'), RXE.optional(RXE.attribute(RXE.text(), name='t')), name=cls.XMLTAG), name=cls.XMLTAG, ns=NSFOLIA)


    def xml(self, attribs = None,elements = None, skipchildren = False, form = Form.NORMAL):
        """Serialises the FoLiA element to XML, by returning an XML Element (in lxml.etree) for this element and all its children. For string output, consider the xmlstring() method instead."""

        if not attribs: attribs = {}
        if not elements: elements = []

        if self.id:
            attribs['id'] = self.id
            try:
                w = self.doc[self.id]
                try:
                    attribs['t'] = w.text()
                except NoSuchText:
                    pass
                orphan = True
                for a in w.ancestors():
                    if isinstance(a, (Text, Speech)):
                        orphan = False
                if orphan:
                    assert KeyError
            except KeyError:
                if self.doc.fixinvalidreferences:
                    return ElementTree.Comment("Reference to non-existant " + self.id + " removed at this point")

        return getattr(E, self.XMLTAG)(**attribs)

class SyntacticUnit(AbstractSpanAnnotation):
    """Syntactic Unit, span annotation element to be used in :class:`SyntaxLayer`"""
    pass


class Chunk(AbstractSpanAnnotation):
    """Chunk element, span annotation element to be used in :class:`ChunkingLayer`"""
    pass

class Entity(AbstractSpanAnnotation):
    """Entity element, for entities such as named entities, multi-word expressions, temporal entities. This is a span annotation element to be used in :class:`EntitiesLayer`"""
    pass

class AbstractSpanRole(AbstractSpanAnnotation):
    #TODO: span roles don't take classes, derived off spanannotation allows too much
    pass

class Headspan(AbstractSpanRole): #generic head element
    """The headspan role is used to mark the head of a span annotation.

    It can be used in various contexts, for instance to mark the head of a :class:`Dependency`.
    It is allowed by most span annotations.
    """


DependencyHead = Headspan #alias, backwards compatibility with FoLiA 0.8


class DependencyDependent(AbstractSpanRole):
    """Span role element that marks the dependent in a dependency relation. Used in :class:`Dependency`.

    :class:`Headspan` in turn is used to mark the head of a dependency relation."""
    pass

class Source(AbstractSpanRole):
    """The source span role is used to mark the source in a :class:`Modality` or :class:`Statement` """

class Target(AbstractSpanRole):
    """The target span role is used to mark the target in a :class:`Modality`"""

class Scope(AbstractSpanRole):
    """The scope span role is used to mark the scope of a :class:`Modality`"""

class Cue(AbstractSpanRole):
    """The cue span role is used to mark the cue/trigger of a :class:`Modality`"""

class StatementRelation(AbstractSpanRole):
    """The relation span role is used to mark the relation between the content of a statement and its source in a :class:`Statement`"""

class Dependency(AbstractSpanAnnotation):
    """Span annotation element to encode dependency relations"""

    def head(self):
        """Returns the head of the dependency relation. Instance of :class:`Headspan`"""
        return next(self.select(Headspan))

    def dependent(self):
        """Returns the dependent of the dependency relation. Instance of :class:`DependencyDependent`"""
        return next(self.select(DependencyDependent))

class Modality(AbstractSpanAnnotation):
    """Span annotation element to encode modality (e.g. sentiment, negation, truthfulness, doubt)"""

class ModalityFeature(Feature):
    """Modality feature, to be used with coreferences"""

class TimeFeature(Feature):
    """Time feature, to be used with coreferences"""

class LevelFeature(Feature):
    """Level feature, to be used with coreferences"""

class CoreferenceLink(AbstractSpanRole):
    """Coreference link. Used in :class:`CoreferenceChain`"""

class CoreferenceChain(AbstractSpanAnnotation):
    """Coreference chain. Holds :class:`CoreferenceLink` instances."""

class SemanticRole(AbstractSpanAnnotation):
    """Semantic Role"""

class Predicate(AbstractSpanAnnotation):
    """Predicate, used within :class:`SemanticRolesLayer`, takes :class:`SemanticRole` annotations as children, but has its own annotation type and separate declaration"""

class Sentiment(AbstractSpanAnnotation):
    """Sentiment. Takes span roles :class:`Headspan`, :class:`Source` and :class:`Target` as children"""

class Statement(AbstractSpanAnnotation):
    """Statement. Takes span roles :class:`Headspan`, :class:`Source` and :class:`Relation` as children"""

class Observation(AbstractSpanAnnotation):
    """Observation."""

class SpanRelation(AbstractHigherOrderAnnotation):
    """Span Relation"""

    #same as for AbstractSpanAnnotation, which this technically is not (hence copy)
    def hasannotation(self,Class,set=False):
        """Returns an integer indicating whether such as annotation exists, and if so, how many. See ``annotations()`` for a description of the parameters."""
        return self.count(Class,set,True,default_ignore_annotations)

    #same as for AbstractSpanAnnotation, which this technically is not (hence copy)
    def annotation(self, type, set=False):
        """Will return a **single** annotation (even if there are multiple). Raises a ``NoSuchAnnotation`` exception if none was found"""
        l = self.count(type,set,True,default_ignore_annotations)
        if len(l) >= 1:
            return l[0]
        else:
            raise NoSuchAnnotation()

class FunctionFeature(Feature):
    """Function feature, to be used with :class:`Morpheme`"""

class Morpheme(AbstractSubtokenAnnotation, AbstractWord):
    """Morpheme element, represents one morpheme in morphological analysis, subtoken annotation element to be used in :class:`MorphologyLayer`"""


    def textvalidation(self, warnonly=None): #warnonly will change at some point in the future to be stricter
        return True


class Phoneme(AbstractSubtokenAnnotation, AbstractWord):
    """Phone element, represents one phone in phonetic analysis, subtoken annotation element to be used in :class:`PhonologyLayer`"""
    pass

#class Subentity(AbstractSubtokenAnnotation):
#    """Subentity element, for named entities within a single token, subtoken annotation element to be used in SubentitiesLayer"""
#    ACCEPTED_DATA = (Feature,TextContent, Metric)
#    ANNOTATIONTYPE = AnnotationType.SUBENTITY
#    XMLTAG = 'subentity'




class SyntaxLayer(AbstractAnnotationLayer):
    """Syntax Layer: Annotation layer for :class:`SyntacticUnit` span annotation elements"""

class ChunkingLayer(AbstractAnnotationLayer):
    """Chunking Layer: Annotation layer for :class:`Chunk` span annotation elements"""

class EntitiesLayer(AbstractAnnotationLayer):
    """Entities Layer: Annotation layer for :class:`Entity` span annotation elements. For named entities."""

class DependenciesLayer(AbstractAnnotationLayer):
    """Dependencies Layer: Annotation layer for :class:`Dependency` span annotation elements. For dependency entities."""

class ModalitiesLayer(AbstractAnnotationLayer):
    """ModalitiesLayer Layer: Annotation layer for :class:`Modality` span annotation elements."""

class MorphologyLayer(AbstractAnnotationLayer):
    """Morphology Layer: Annotation layer for :class:`Morpheme` subtoken annotation elements. For morphological analysis."""

class PhonologyLayer(AbstractAnnotationLayer):
    """Phonology Layer: Annotation layer for :class:`Phoneme` subtoken annotation elements. For phonetic analysis."""

class CoreferenceLayer(AbstractAnnotationLayer):
    """Syntax Layer: Annotation layer for :class:`SyntacticUnit` span annotation elements"""

class SemanticRolesLayer(AbstractAnnotationLayer):
    """Syntax Layer: Annotation layer for :class:`SemanticRole` span annotation elements"""

class StatementLayer(AbstractAnnotationLayer):
    """Statement Layer: Annotation layer for :class:`Statement` span annotation elements, used for attribution annotation."""

class SentimentLayer(AbstractAnnotationLayer):
    """Sentiment Layer: Annotation layer for :class:`Sentiment` span annotation elements, used for sentiment analysis."""

class ObservationLayer(AbstractAnnotationLayer):
    """Observation Layer: Annotation layer for :class:`Observation` span annotation elements."""

class SpanRelationLayer(AbstractAnnotationLayer):
    """Span Relation Layer: Annotation layer for :class:`SpanRelation`"""


class HeadFeature(Feature):
    """Head feature, to be used within :class:`PosAnnotation`"""

class PosAnnotation(AbstractInlineAnnotation):
    """Part-of-Speech annotation:  an inline annotation element"""

class LemmaAnnotation(AbstractInlineAnnotation):
    """Lemma annotation:  an inline annotation element"""

class LangAnnotation(AbstractInlineAnnotation):
    """Language annotation:  an extended inline annotation element"""

#class PhonAnnotation(AbstractInlineAnnotation): #DEPRECATED in v0.9
#    """Phonetic annotation:  a token annotation element"""
#    ANNOTATIONTYPE = AnnotationType.PHON
#    ACCEPTED_DATA = (Feature,Description, Metric)
#    XMLTAG = 'phon'


class DomainAnnotation(AbstractInlineAnnotation):
    """Domain annotation:  an inline annotation element"""

class SynsetFeature(Feature):
    """Synset feature, to be used within :class:`Sense`"""

class ActorFeature(Feature):
    """Actor feature, to be used within :class:`Event`"""

class PolarityFeature(Feature):
    """Polarity feature, to be used within :class:`Sentiment`"""

class StrengthFeature(Feature):
    """Strength feature, to be used within :class:`Sentiment`"""

class BegindatetimeFeature(Feature):
    """Begindatetime feature, to be used within :class:`Event`"""

class EnddatetimeFeature(Feature):
    """Enddatetime feature, to be used within :class:`Event`"""

class StyleFeature(Feature):
    pass

class FontFeature(Feature):
    """Font feature, to be used within :class:`TextMarkupStyle`"""

class SizeFeature(Feature):
    """Size feature, to be used within :class:`TextMarkupStyle`"""

class Note(AbstractStructureElement):
    """Element used for notes, such as footnotes or warnings or notice blocks."""

class Definition(AbstractStructureElement):
    """Element used in :class:`Entry` for the portion that provides a definition for the entry."""

class Term(AbstractStructureElement):
    """A term, often used in contect of :class:`Entry`"""

class Example(AbstractStructureElement):
    """Element that provides an example. Used for instance in the context of :class:`Entry`"""

class Entry(AbstractStructureElement):
    """Represents an entry in a glossary/lexicon/dictionary."""


class TimeSegment(AbstractSpanAnnotation):
    """A time segment"""

TimedEvent = TimeSegment #alias for FoLiA 0.8 compatibility

class TimingLayer(AbstractAnnotationLayer):
    """Timing layer: Annotation layer for :class:`TimeSegment` span annotation elements. """


class SenseAnnotation(AbstractInlineAnnotation):
    """Sense annotation: an inline annotation element"""

class EtymologyAnnotation(AbstractInlineAnnotation):
    """Etymology Annotation allows to relate a word/morpheme to its historic origin (often in some kind of etymological database)"""

class SubjectivityAnnotation(AbstractInlineAnnotation):
    """Subjectivity annotation/Sentiment analysis: an inline annotation element"""


class Quote(AbstractStructureElement):
    """Quote: a structure element. For quotes/citations. May hold :class:`Word`, :class:`Sentence` or :class:`Paragraph` data."""

    def __init__(self,  doc, *args, **kwargs):
        super(Quote,self).__init__(doc, *args, **kwargs)


    def resolveword(self, id):
        for child in self:
            r =  child.resolveword(id)
            if r:
                return r
        return None

    def append(self, child, *args, **kwargs):
        #Quotes have some more complex ACCEPTED_DATA behaviour depending on what lever they are used on

        #Note that Sentences under quotes may occur if the parent of the quote is a sentence already
        insentence = len(list(self.ancestors(Sentence))) > 0
        inparagraph = len(list(self.ancestors(Paragraph))) > 0
        if inspect.isclass(child):
            if (insentence or inparagraph) and (child is Paragraph or child is Division):
                raise Exception("Can't add paragraphs or divisions to a quote when the quote is in a sentence or paragraph!")
        else:
            if (insentence or inparagraph) and (isinstance(child, Paragraph) or isinstance(child, Division)):
                raise Exception("Can't add paragraphs or divisions to a quote when the quote is in a sentence or paragraph!")

        return super(Quote, self).append(child, *args, **kwargs)

    def gettextdelimiter(self, retaintokenisation=False):
        #no text delimiter of itself, recurse into children to inherit delimiter
        for child in reversed(self):
            if isinstance(child, Sentence):
                return "" #if a quote ends in a sentence, we don't want any delimiter
            else:
                return child.gettextdelimiter(retaintokenisation)
        return self.TEXTDELIMITER


class Sentence(AbstractStructureElement):
    """Sentence element. A structure element. Represents a sentence and holds all its words (:class:`Word`), and possibly other structure such as :class:`LineBreak`, :class:`Whitespace` and :class:`Quote`"""

    def __init__(self,  doc, *args, **kwargs):
        """
        Example::

            sentence = paragraph.append( folia.Sentence)

            sentence.append( folia.Word, 'This')
            sentence.append( folia.Word, 'is')
            sentence.append( folia.Word, 'a')
            sentence.append( folia.Word, 'test', space=False)
            sentence.append( folia.Word, '.')

        Example::

            sentence = folia.Sentence( doc, folia.Word(doc, 'This'),  folia.Word(doc, 'is'),  folia.Word(doc, 'a'),  folia.Word(doc, 'test', space=False),  folia.Word(doc, '.') )
            paragraph.append(sentence)


        See also:
            :meth:`AbstractElement.__init__`
        """
        super(Sentence,self).__init__(doc, *args, **kwargs)


    def resolveword(self, id):
        for child in self:
            r =  child.resolveword(id)
            if r:
                return r
        return None

    def corrections(self):
        """Are there corrections in this sentence?

        Returns:
            bool
        """
        return bool(self.select(Correction))

    def paragraph(self):
        """Obtain the paragraph this sentence is a part of (None otherwise). Shortcut for :meth:`AbstractElement.ancestor`"""
        return self.ancestor(Paragraph)

    def division(self):
        """Obtain the division this sentence is a part of (None otherwise). Shortcut for :meth:`AbstractElement.ancestor`"""
        return self.ancestor(Division)


    def correctwords(self, originalwords, newwords, **kwargs):
        """Generic correction method for words. You most likely want to use the helper functions
           :meth:`Sentence.splitword` , :meth:`Sentence.mergewords`, :meth:`deleteword`, :meth:`insertword` instead"""
        for w in originalwords:
            if not isinstance(w, Word):
                raise Exception("Original word is not a Word instance: " + str(type(w)))
            elif w.sentence() != self:
                raise Exception("Original not found as member of sentence!")
        for w in newwords:
            if not isinstance(w, Word):
                raise Exception("New word is not a Word instance: " + str(type(w)))
        if 'suggest' in kwargs and kwargs['suggest']:
            del kwargs['suggest']
            return self.correct(suggestion=newwords,current=originalwords, **kwargs)
        else:
            return self.correct(original=originalwords, new=newwords, **kwargs)



    def splitword(self, originalword, *newwords, **kwargs):
        """TODO: Write documentation"""
        if isstring(originalword):
            originalword = self.doc[u(originalword)]
        return self.correctwords([originalword], newwords, **kwargs)



    def mergewords(self, newword, *originalwords, **kwargs):
        """TODO: Write documentation"""
        return self.correctwords(originalwords, [newword], **kwargs)

    def deleteword(self, word, **kwargs):
        """TODO: Write documentation"""
        if isstring(word):
            word = self.doc[u(word)]
        return self.correctwords([word], [], **kwargs)


    def insertword(self, newword, prevword, **kwargs):
        """Inserts a word **as a correction** after an existing word.

        This method automatically computes the index of insertion
        and calls :meth:`AbstractElement.insert`

        Arguments:
            newword (:class:`Word`): The new word to insert
            prevword (:class:`Word`): The word to insert after

        Keyword Arguments:
            suggest (bool): Do a suggestion for correction rather than the default authoritive correction

        See also:
            :meth:`AbstractElement.insert` and :meth:`AbstractElement.getindex` If you do not want to do corrections
        """
        if prevword:
            if isstring(prevword):
                prevword = self.doc[u(prevword)]
            if not prevword in self or not isinstance(prevword, Word):
                raise Exception("Previous word not found or not instance of Word!")
            if isinstance(newword, list) or isinstance(newword, tuple):
                if not all([ isinstance(x, Word) for x in newword ]):
                    raise Exception("New word (iterable) constains non-Word instances!")
            elif not isinstance(newword, Word):
                raise Exception("New word no instance of Word!")

            kwargs['insertindex'] = self.getindex(prevword) + 1
        else:
            kwargs['insertindex'] = 0
        kwargs['nooriginal'] = True
        if isinstance(newword, list) or isinstance(newword, tuple):
            return self.correctwords([], newword, **kwargs)
        else:
            return self.correctwords([], [newword], **kwargs)


    def insertwordleft(self, newword, nextword, **kwargs):
        """Inserts a word **as a correction** before an existing word.

        Reverse of :meth:`Sentence.insertword`.
        """
        if nextword:
            if isstring(nextword):
                nextword = self.doc[u(nextword)]
            if not nextword in self or not isinstance(nextword, Word):
                raise Exception("Next word not found or not instance of Word!")
            if isinstance(newword, list) or isinstance(newword, tuple):
                if not all([ isinstance(x, Word) for x in newword ]):
                    raise Exception("New word (iterable) constains non-Word instances!")
            elif not isinstance(newword, Word):
                raise Exception("New word no instance of Word!")

            kwargs['insertindex'] = self.getindex(nextword)
        else:
            kwargs['insertindex'] = 0
        kwargs['nooriginal'] = True
        if isinstance(newword, list) or isinstance(newword, tuple):
            return self.correctwords([], newword, **kwargs)
        else:
            return self.correctwords([], [newword], **kwargs)


    def gettextdelimiter(self, retaintokenisation=False):
        #no text delimiter of itself, recurse into children to inherit delimiter
        for child in reversed(self):
            if isinstance(child, (Linebreak, Whitespace)):
                return "" #if a sentence ends in a linebreak, we don't want any delimiter
            elif isinstance(child, Word) and not child.space:
                return "" #if a sentence ends in a word with space=no, then we don't delimit either
            elif isinstance(child, AbstractStructureElement):
                #recurse? if the child is hidden in another element (part for instance?)
                return child.gettextdelimiter(retaintokenisation) #if a sentence ends in a word with space=no, then we don't delimit either
            #TODO: what about corrections?
            elif isinstance(child, (AbstractAnnotationLayer, AbstractInlineAnnotation) ):
                continue #this never counts as the last element (issue #41), continue...
            else:
                break
        return self.TEXTDELIMITER

class Utterance(AbstractStructureElement):
    """Utterance element. A structure element for speech annotation."""

class Event(AbstractStructureElement):
    """Structural element representing events, often used in new media contexts for things such as tweets,chat messages and forum posts."""

class Caption(AbstractStructureElement):
    """Element used for captions for :class:`Figure` or :class:`Table`"""


class Label(AbstractStructureElement):
    """Element used for labels. Mostly in within list item. Contains words."""


class ListItem(AbstractStructureElement):
    """Single element in a List. Structure element. Contained within :class:`List` element."""

class List(AbstractStructureElement):
    """Element for enumeration/itemisation. Structure element. Contains :class:`ListItem` elements."""


class Figure(AbstractStructureElement):
    """Element for the representation of a graphical figure. Structure element."""

    def json(self, attribs = None, recurse=True,ignorelist=False):
        if self.src:
            if not attribs: attribs = {}
            attribs['src'] = self.src
        return super(Figure, self).json(attribs, recurse, ignorelist)

    def caption(self):
        try:
            caption = next(self.select(Caption))
            return caption.text()
        except:
            raise NoSuchText





class Head(AbstractStructureElement):
    """Head element; a structure element that acts as the header/title of a :class:`Division`.

    There may be only one per division. Often contains sentences (:class:`Sentence`) or Words (:class:`Word`)."""

class Paragraph(AbstractStructureElement):
    """Paragraph element. A structure element. Represents a paragraph and holds all its sentences (and possibly other structure Whitespace and Quotes)."""


class Cell(AbstractStructureElement):
    """A cell in a :class:`Row` in a :class:`Table`"""

    def text(self, cls='current', retaintokenisation=False, previousdelimiter="",strict=False, correctionhandling=CorrectionHandling.CURRENT, normalize_spaces=False, hidden=False, trim_spaces=True):
        if self.hastext(cls, strict, correctionhandling, hidden):
            return super(AbstractStructureElement, self).text(cls,retaintokenisation, previousdelimiter,strict, correctionhandling, normalize_spaces, hidden, trim_spaces)
        else:
            return previousdelimiter #force output of previous delimiter, needed for empty cells

class Row(AbstractStructureElement):
    """A row in a :class:`Table`"""

    def text(self, cls='current', retaintokenisation=False, previousdelimiter="",strict=False, correctionhandling=CorrectionHandling.CURRENT, normalize_spaces=False, hidden=False, trim_spaces=True):
        if self.hastext(cls, strict, correctionhandling, hidden):
            return super(AbstractStructureElement, self).text(cls,retaintokenisation, previousdelimiter,strict, correctionhandling, normalize_spaces, hidden, trim_spaces)
        else:
            s = previousdelimiter
            count = self.count(Cell) #needed for edge case with all empty cells
            if count > 1:
                s += Cell.TEXTDELIMITER * (count - 1)
            return s


class TableHead(AbstractStructureElement):
    """Encapsulated the header of a table, contains :class:`Cell` elements"""

    def text(self, cls='current', retaintokenisation=False, previousdelimiter="",strict=False, correctionhandling=CorrectionHandling.CURRENT, normalize_spaces=False, hidden=False, trim_spaces=True):
        if self.hastext(cls, strict, correctionhandling, hidden):
            return super(AbstractStructureElement, self).text(cls,retaintokenisation, previousdelimiter,strict, correctionhandling, normalize_spaces, hidden, trim_spaces)
        else:
            s = previousdelimiter
            count = self.count(Cell) #needed for edge case with all empty cells
            if count > 1:
                s += Cell.TEXTDELIMITER * (count - 1)
            return s


class Table(AbstractStructureElement):
    """A table consisting of :class:`Row` elements that in turn consist of :class:`Cell` elements"""
    pass


class Division(AbstractStructureElement):
    """Structure element representing some kind of division. Divisions may be nested at will, and may include almost all kinds of other structure elements."""

    def head(self):
        for e in self.data:
            if isinstance(e, Head):
                return e
        raise NoSuchAnnotation()


class Speech(AbstractStructureElement):
    """A full speech. This is a high-level element. This element may contain :class:`Division`,:class:`Paragraph`, class:`Sentence`, etc.."""
    # (both SPEAKABLE and PRINTABLE)

class Text(AbstractStructureElement):
    """A full text. This is a high-level element (not to be confused with TextContent!). This element may contain :class:`Division`,:class:`Paragraph`, class:`Sentence`, etc.."""
    # (both SPEAKABLE and PRINTABLE)


class ForeignData(AbstractHigherOrderAnnotation):
    """The ForeignData element encapsulated data that is not in FoLiA but in a different format.

    Such data must use a different XML namespace and will be preserved as-is, that is the ``lxml.etree.Element`` instance is retained unmodified. No further interpretation takes place.
    """

    def __init__(self, doc, *args, **kwargs): #pylint: disable=super-init-not-called
        self.data = []
        if 'node' not in kwargs:
            raise ValueError("Expected a node= keyword argument for foreign-data")
        if not isinstance(kwargs['node'],ElementTree._Element):
            raise ValueError("foreign-data node should be ElementTree.Element instance, got " + str(type(kwargs['node'])))
        self.node = kwargs['node']
        for subnode in self.node:
            self._checknamespace(subnode)
        self.doc = doc
        self.id = None
        self.auth = True
        self.next = None #chains foreigndata
        #do not call superconstructor

    def _checknamespace(self, node):
        #namespace must be foreign
        for subnode in node:
            if node.tag and node.tag.startswith('{'+NSFOLIA+'}'):
                raise ValueError("foreign-data may not include elements in the FoLiA namespace, a foreign XML namespace is mandatory")
            self._checknamespace(subnode)

    @classmethod
    def parsexml(Class, node, doc, **kwargs):
        return ForeignData(doc, node=node)

    def select(self, Class, set=False, recursive=True,  ignore=True, node=None): #pylint: disable=bad-classmethod-argument,redefined-builtin
        """This is a dummy method that returns an empty generator, select() does not work on ForeignData"""
        #select can never descend into ForeignData, empty generator:
        return
        yield

    def xml(self, attribs = None,elements = None, skipchildren = False, form = Form.NORMAL):
        """Returns the XML node (an lxml.etree.Element) that holds the foreign data"""
        return self.node

    @classmethod
    def relaxng(cls, includechildren=True,extraattribs = None, extraelements=None):
        return RXE.define( RXE.element(RXE.ref(name="any_content"), name=cls.XMLTAG), name=cls.XMLTAG, ns=NSFOLIA)




#===================================================================================================================


class Query(object):
    """An XPath query on one or more FoLiA documents"""
    def __init__(self, files, expression):
        if isstring(files):
            self.files = [u(files)]
        else:
            assert hasattr(files,'__iter__')
            self.files = files
        self.expression = expression

    def __iter__(self):
        for filename in self.files:
            doc = Document(file=filename, mode=Mode.XPATH)
            for result in doc.xpath(self.expression):
                yield result

class RegExp(object):
    def __init__(self, regexp):
        self.regexp = re.compile(regexp)

    def __eq__(self, value):
        return self.regexp.match(value)


class Pattern(object):
    """
    This class describes a pattern over words to be searched for. The
:meth:`Document.findwords` method can subsequently be called with this pattern,
and it will return all the words that match. An example will best illustrate
this, first a trivial example of searching for one word::

        for match in doc.findwords( folia.Pattern('house') ):
            for word in match:
                print word.id
            print "----"

    The same can be done for a sequence::

        for match in doc.findwords( folia.Pattern('a','big', 'house') ):
            for word in match:
                print word.id
            print "----"

    The boolean value ``True`` acts as a wildcard, matching any word::

        for match in doc.findwords( folia.Pattern('a',True,'house') ):
            for word in match:
                print word.id, word.text()
            print "----"

    Alternatively, and more constraning, you may also specify a tuple of alternatives::


        for match in doc.findwords( folia.Pattern('a',('big','small'),'house') ):
            for word in match:
                print word.id, word.text()
            print "----"

    Or even a regular expression using the ``folia.RegExp`` class::


        for match in doc.findwords( folia.Pattern('a', folia.RegExp('b?g'),'house') ):
            for word in match:
                print word.id, word.text()
            print "----"


    Rather than searching on the text content of the words, you can search on the
    classes of any kind of inline annotation using the keyword argument
    ``matchannotation=``::

        for match in doc.findwords( folia.Pattern('det','adj','noun',matchannotation=folia.PosAnnotation ) ):
            for word in match:
                print word.id, word.text()
            print "----"

    The set can be restricted by adding the additional keyword argument
    ``matchannotationset=``. Case sensitivity, by default disabled, can be enabled by setting ``casesensitive=True``.

    Things become even more interesting when different Patterns are combined. A
    match will have to satisfy all patterns::

        for match in doc.findwords( folia.Pattern('a', True, 'house'), folia.Pattern('det','adj','noun',matchannotation=folia.PosAnnotation ) ):
            for word in match:
                print word.id, word.text()
            print "----"


    The ``findwords()`` method can be instructed to also return left and/or right context for any match. This is done using the ``leftcontext=`` and ``rightcontext=`` keyword arguments, their values being an integer number of the number of context words to include in each match. For instance, we can look for the word house and return its immediate neighbours as follows::

        for match in doc.findwords( folia.Pattern('house') , leftcontext=1, rightcontext=1):
            for word in match:
                print word.id
            print "----"

    A match here would thus always consist of three words instead of just one.

    Last, ``Pattern`` also has support for variable-width gaps, the asterisk symbol
    has special meaning to this end::


        for match in doc.findwords( folia.Pattern('a','*','house') ):
            for word in match:
                print word.id
            print "----"

    Unlike the pattern ``('a',True,'house')``, which by definition is a pattern of
    three words, the pattern in the example above will match gaps of any length (up
    to a certain built-in maximum), so this might include matches such as *a very
    nice house*.

    Some remarks on these methods of querying are in order. These searches are
    pretty exhaustive and are done by simply iterating over all the words in the
    document. The entire document is loaded in memory and no special indices are involved.
    For single documents this is okay, but when iterating over a corpus of
    thousands of documents, this method is too slow, especially for real-time
    applications. For huge corpora, clever indexing and database management systems
    will be required. This however is beyond the scope of this library.

    """


    def __init__(self, *args, **kwargs):
        if not all( ( (x is True or isinstance(x,RegExp) or isstring(x) or isinstance(x, list) or isinstance(x, tuple)) for x in args )):
            raise TypeError
        self.sequence = args

        if 'matchannotation' in kwargs:
            self.matchannotation = kwargs['matchannotation']
            del kwargs['matchannotation']
        else:
            self.matchannotation = None
        if 'matchannotationset' in kwargs:
            self.matchannotationset = kwargs['matchannotationset']
            del kwargs['matchannotationset']
        else:
            self.matchannotationset = None
        if 'casesensitive' in kwargs:
            self.casesensitive = bool(kwargs['casesensitive'])
            del kwargs['casesensitive']
        else:
            self.casesensitive = False
        for key in kwargs.keys():
            raise Exception("Unknown keyword parameter: " + key)

        if not self.casesensitive:
            if all( ( isstring(x) for x in self.sequence) ):
                self.sequence = [ u(x).lower() for x in self.sequence ]

    def __nonzero__(self): #Python 2.x
        return True

    def __bool__(self):
        return True

    def __len__(self):
        return len(self.sequence)

    def __getitem__(self, index):
        return self.sequence[index]

    def __getslice__(self, begin,end):
        return self.sequence[begin:end]

    def variablesize(self):
        return ('*' in self.sequence)

    def variablewildcards(self):
        wildcards = []
        for i,x in enumerate(self.sequence):
            if x == '*':
                wildcards.append(i)
        return wildcards


    def __repr__(self):
        return repr(self.sequence)


    def resolve(self,size, distribution):
        """Resolve a variable sized pattern to all patterns of a certain fixed size"""
        if not self.variablesize():
            raise Exception("Can only resize patterns with * wildcards")

        nrofwildcards = 0
        for x in self.sequence:
            if x == '*':
                nrofwildcards += 1

        assert (len(distribution) == nrofwildcards)

        wildcardnr = 0
        newsequence = []
        for x in self.sequence:
            if x == '*':
                newsequence += [True] * distribution[wildcardnr]
                wildcardnr += 1
            else:
                newsequence.append(x)
        d = { 'matchannotation':self.matchannotation, 'matchannotationset':self.matchannotationset, 'casesensitive':self.casesensitive }
        yield Pattern(*newsequence, **d )

class ExternalMetaData(object):
    def __init__(self, url):
        self.url = url
        self.next = None #reserved for chaining, not used yet

class NativeMetaData(object):
    def __init__(self, *args, **kwargs):
        self.data = {}
        self.order = []
        self.next = None #Foreign data
        for key, value in kwargs.items():
            self[key] = value

    def __setitem__(self, key, value):
        exists = key in self.data
        self.data[key] = str(value)
        if not exists: self.order.append(key)

    def __iter__(self):
        for x in self.order:
            yield x

    def __contains__(self, x):
        return x in self.data

    def items(self):
        for key in self.order:
            yield key, self.data[key]

    def __len__(self):
        return len(self.data)

    def __getitem__(self, key):
        return self.data[key]

    def __delitem__(self,key):
        del self.data[key]
        self.order.remove(key)


class Document(object):
    """This is the FoLiA Document and holds all its data in memory.

    All FoLiA elements have to be associated with a FoLiA document.
    Besides holding elements, the document may hold metadata including declarations, and an index of all IDs."""

    IDSEPARATOR = '.'

    def __init__(self, *args, **kwargs):
        """Start/load a FoLiA document:

        There are four sources of input for loading a FoLiA document::

        1) Create a new document by specifying an *ID*::

            doc = folia.Document(id='test')

        2) Load a document from FoLiA or D-Coi XML file::

            doc = folia.Document(file='/path/to/doc.xml')

        3) Load a document from an XML string::

            doc = folia.Document(string='<FoLiA>....</FoLiA>')

        4) Load a document by passing a parse xml tree (lxml.etree)::

            doc = folia.Document(tree=xmltree)

        You will often want to associate a :class:`Processor` when you instantiate a document, the processor encapsulates information regarding the tool that is processing a document (i.e. your script), and adds this to the document's provenance chain. Any new annotations you add to this document will be automatically related to the processor::

            doc = folia.Document(id="example", processor=Processor.create(name="my-tool", version="0.1"))


        Keyword Arguments:

            setdefinition (dict):  A dictionary of set definitions, the key corresponds to the set name, the value is a SetDefinition instance
            loadsetdefinitions (bool):  download and load set definitions (default: False)
            deepvalidation (bool): Do deep validation of the document (default: False), implies ``loadsetdefinitions``
            textvalidation (bool): Do validation of text consistency (default: False), this value is always forced to True to FoLiA v1.5 and above``
            preparsexmlcallback (function):  Callback for a function taking one argument (``node``, an lxml node). Will be called whenever an XML element is parsed into FoLiA. The function should return an instance inherited from folia.AbstractElement, or None to abort parsing this element (and all its children)
            parsexmlcallback (function):  Callback for a function taking one argument (``element``, a FoLiA element). Will be called whenever an XML element is parsed into FoLiA. The function should return an instance inherited from folia.AbstractElement, or None to abort adding this element (and all its children)
            keepversion (bool): attempt to keep the FoLiA version (use with caution)
            version (str): force a particular FoLiA version when creating a new document (use with caution)
            declare (list): Declare the specifies annotation types. Consists of a list or tuple of annotationtypes or (annotation,set) tuples or (annotationtype,set,processor) tuples
            processor (Processor): Register the current processor in the provenance data and use this processor in all subsequent declarations.
            reprocessor (Processor): As above, but will take pro-active ownership of any declarations already present but not tied to a processor yet.
            debug (bool): Boolean to enable/disable debug
            autodeclare (bool): Automatically declare annotation types and annotators whenever possible (enabled by default for FoLiA v2)
            mode: The mode for loading a document, is either ``folia.Mode.MEMORY``,  in which the entire FoLiA Document will be loaded into memory. This is the default mode and the only mode in which documents can be manipulated and saved againor ``folia.Mode.XPATH``, in which the full XML tree will still be loaded into memory, but conversion to FoLiA classes occurs only when queried. This mode can be used when the full power of XPath is required.
            checkreferences (bool): Check whether references are valid upon loading (default: True)
            fixunassignedprocessor (bool): If set, fixes invalid FoLiA that does not explicitly assign a processor to an annotation when multiple processors are possible (and there is therefore no default). The last processor will be used in this case. (default: False)
            fixinvalidereferences (bool): Do not serialise an invalid reference, remove the reference and output a comment instead. (default: False)
        """


        self.version = kwargs.get('version', FOLIAVERSION)
        self.FOLIA2 = checkversion(self.version, "2.0.0") >= 0
        self.FOLIA1 = checkversion(self.version, "2.0.0") < 0 #also includes FoLiA v0.*
        self.keepversion = 'version' in kwargs or ('keepversion' in kwargs and kwargs['keepversion'])
        self.document_version = None

        self.data = [] #will hold all texts (usually only one)

        self.annotationdefaults = {}
        self.annotations = [] #Ordered list of (AnnotationType, set (str))
        self.annotators = {} #AnnotationType => set => Annotator    (leaf value resolves to Processor when called)
        self.groupannotations = {} #AnnotationType -> set -> bool  (used to store whether inline annotations are allowed in certain span annotations)
        self.setdefinitionformat = {} #AnnotationType -> set -> str (mime type)  (used to store the format of the set definitions)
        self.annotator2processor_map = {} #maps (annotator, annotatortype) to a Processor instance, used in automatic upgrades


        self.index = {} #all IDs go here
        self.declareprocessed = False # Will be set to True when declarations have been processed

        self.checkreferences = kwargs.get('checkreferences', True) #check whether wrefs point to valid elements, this is good practice but needs to be disabled for streaming readers and <external> (proycon/folia#41).

        self.metadata = NativeMetaData() #will point to XML Element holding native metadata
        self.metadatatype = "native"
        self.provenance = Provenance()
        self.processor = None
        if 'reprocessor' in kwargs and kwargs['reprocessor']:
            assert isinstance(kwargs['reprocessor'], Processor)
            self.processor = kwargs['reprocessor']

        self.submetadata = OrderedDict()
        self.submetadatatype = {}

        self.alias_set = {} #alias to set map (via annotationtype => first)
        self.set_alias = {} #set to alias map (via annotationtype => first)

        self.textclasses = set() #will contain the text classes found

        self.autodeclare = None #Automatic declarations in case of undeclared elements, will be set later
                                # False for FoLiA < 2.0
                                # True for FoLiA >= 2.0
        self.fixunassignedprocessor = kwargs.get('fixunassignedprocessor',False) #Fixes invalid FoLiA that does not explicitly assign a processor and when multiple options are possible (so not defaults)
        self.fixinvalidreferences = kwargs.get('fixinvalidreferences',False) #Fixes invalid wrefs by simply omitting them from serialisation (if this is not enabled, references will be saved without checking, meaning there is a chance a document may not be load if loaded with the default checkreferences=True)
        self.filename = ""

        if 'setdefinitions' in kwargs:
            self.setdefinitions = kwargs['setdefinitions'] #to re-use a shared store
        else:
            self.setdefinitions = {} #key: set name, value: SetDefinition instance (only used when deepvalidation=True)
        self.failedsetdefinitions = [] #will contain list of sets that failed to load (in case allowadhocsets=True)

        #The metadata fields FoLiA is directly aware of:
        self._title = self._date = self._publisher = self._license = self._language = None


        if 'debug' in kwargs:
            self.debug = kwargs['debug']
        else:
            self.debug = False

        if 'verbose' in kwargs:
            self.verbose = kwargs['verbose']
        else:
            self.verbose = False

        if 'mode' in kwargs:
            self.mode = int(kwargs['mode'])
        else:
            self.mode = Mode.MEMORY #Load all in memory


        if 'parentdoc' in kwargs:  #for subdocuments
            assert isinstance(kwargs['parentdoc'], Document)
            self.parentdoc = kwargs['parentdoc']
        else:
            self.parentdoc = None

        self.subdocs = {} #will hold all subdocs (sourcestring => document) , needed so the index can resolve IDs in subdocs
        self.standoffdocs = {} #will hold all standoffdocs (type => set => sourcestring => document)

        if 'external' in kwargs:
            self.external = kwargs['external']
        else:
            self.external = False

        if self.external and not self.parentdoc:
            raise DeepValidationError("Document is marked as external and should not be loaded independently. However, no parentdoc= has been specified!")


        if 'loadsetdefinitions' in kwargs:
            self.loadsetdefinitions = bool(kwargs['loadsetdefinitions'])
        else:
            self.loadsetdefinitions = False

        if 'deepvalidation' in kwargs:
            self.deepvalidation = bool(kwargs['deepvalidation'])
        else:
            self.deepvalidation = False

        if self.deepvalidation:
            self.loadsetdefinitions = True


        if 'textvalidation' in kwargs:
            self.textvalidation = bool(kwargs['textvalidation'])
        else:
            self.textvalidation = False
        self.textvalidationerrors = 0 #will count the number of text validation errors
        self.offsetvalidationbuffer = [] #will hold (AbstractStructureElement, textclass pairs) that need to be validated still (if textvalidation == True), validation will be done when all parsing is complete and/or prior to serialisation
        self.layersortbuffer = [] #will hold instances derived off AbstractAnnotationLayer (i.e. all span annotation layers), so the the span annotations within can be sorted after all parsing is done

        if 'allowadhocsets' in kwargs:
            self.allowadhocsets = bool(kwargs['allowadhocsets'])
        else:
            if self.deepvalidation:
                self.allowadhocsets = False
            else:
                self.allowadhocsets = True

        if 'autodeclare' in kwargs:
            self.autodeclare = kwargs['autodeclare']

        if 'bypassleak' in kwargs:
            self.bypassleak = False #obsolete now

        if 'preparsexmlcallback' in kwargs:
            self.preparsexmlcallback = kwargs['parsexmlcallback']
        else:
            self.preparsexmlcallback = None

        if 'parsexmlcallback' in kwargs:
            self.parsexmlcallback = kwargs['parsexmlcallback']
        else:
            self.parsexmlcallback = None

        if 'id' in kwargs:
            isncname(kwargs['id'])
            self.id = kwargs['id']
            if self.autodeclare is None:
                self.autodeclare = True
        elif 'file' in kwargs:
            self.filename = kwargs['file']
            if self.filename[-4:].lower() == '.bz2':
                f = bz2.BZ2File(self.filename)
                contents = f.read()
                f.close()
                self.tree = xmltreefromstring(contents)
                del contents
                self.parsexml(self.tree.getroot())
            elif self.filename[-3:].lower() == '.gz':
                f = gzip.GzipFile(self.filename)
                contents = f.read()
                f.close()
                self.tree = xmltreefromstring(contents)
                del contents
                self.parsexml(self.tree.getroot())
            else:
                self.load(self.filename)
        elif 'string' in kwargs:
            self.tree = xmltreefromstring(kwargs['string'])
            del kwargs['string']
            self.parsexml(self.tree.getroot())
            if self.mode != Mode.XPATH:
                #XML Tree is now obsolete (only needed when partially loaded for xpath queries)
                self.tree = None
        elif 'tree' in kwargs:
            self.parsexml(kwargs['tree'])
        else:
            raise Exception("No ID, filename or tree specified. Or the argument name is wrong.")

        self.doneparsing = True #indicates that the document is done parsing

        #### POST-READING

        if self.mode != Mode.XPATH:
            #XML Tree is now obsolete (only needed when partially loaded for xpath queries), free memory
            self.tree = None

        if 'processor' in kwargs and kwargs['processor']:
            assert isinstance(kwargs['processor'], Processor)
            self.processor = kwargs['processor']

        if self.processor:
            #Add the processor to the provenance chain
            self.provenance.append( self.processor )

        if 'declare' in kwargs:
            for item in kwargs['declare']:
                if isinstance(item, (list,tuple)):
                    self.declare(item[0], item[1], *item[2:])
                else:
                    self.declare(item)
        else:
            #declare text by default (set declare=[] if you don't want this)
            if all( t != AnnotationType.TEXT for t, s in self.annotations ):
                self.declare(AnnotationType.TEXT, DEFAULT_TEXT_SET)

    #def __del__(self):
    #    del self.index
    #    for child in self.data:
    #        del child
    #    del self.data

    def load(self, filename):
        """Load a FoLiA XML file.

        Argument:
            filename (str): The file to load
        """
        self.tree = xmltreefromfile(filename)
        self.parsexml(self.tree.getroot())
        if self.mode != Mode.XPATH:
            #XML Tree is now obsolete (only needed when partially loaded for xpath queries)
            self.tree = None

    def items(self):
        """Returns a depth-first flat list of all items in the document"""
        l = []
        for e in self.data:
            l += e.items()
        return l

    def elements(self):
        """Returns a depth-first flat list of all elements in the document"""
        l = []
        for e in self.data:
            l += e.elements()
        return l

    def xpath(self, query):
        """Run Xpath expression and parse the resulting elements. Don't forget to use the FoLiA namesapace in your expressions, using folia: or the short form f: """
        for result in self.tree.xpath(query,namespaces={'f': 'http://ilk.uvt.nl/folia','folia': 'http://ilk.uvt.nl/folia' }):
            yield self.parsexml(result)


    def alias(self, annotationtype, set, fallback=False):
        """Return the alias for a set (if applicable, returns the unaltered set otherwise iff fallback is enabled)"""
        if inspect.isclass(annotationtype): annotationtype = annotationtype.ANNOTATIONTYPE
        if annotationtype in self.set_alias and set in self.set_alias[annotationtype]:
            return self.set_alias[annotationtype][set]
        elif fallback:
            return set
        else:
            raise KeyError("No alias for set " + set)


    def unalias(self, annotationtype, alias):
        """Return the set for an alias (if applicable, raises an exception otherwise)"""
        if inspect.isclass(annotationtype): annotationtype = annotationtype.ANNOTATIONTYPE
        return self.alias_set[annotationtype][alias]

    def findwords(self, *args, **kwargs):
        for x in findwords(self,self.words,*args,**kwargs):
            yield x

    def save(self, filename=None, form = Form.NORMAL):
        """Save the document to file.

        Arguments:
            * filename (str): The filename to save to. If not set (``None``, default), saves to the same file as loaded from.
        """
        if not filename:
            filename = self.filename
        if not filename:
            raise Exception("No filename specified")
        if filename[-4:].lower() == '.bz2':
            f = bz2.BZ2File(filename,'wb')
        elif filename[-3:].lower() == '.gz':
            f = gzip.GzipFile(filename,'wb')
        else:
            f = open(filename,'wb')
        f.write(ElementTree.tostring(self.xml(form=form), xml_declaration=True, pretty_print=True, encoding='utf-8'))
        f.close()



    def __len__(self):
        return len(self.data)

    def __nonzero__(self): #Python 2.x
        return True

    def __bool__(self):
        return True

    def __iter__(self):
        for text in self.data:
            yield text


    def __contains__(self, key):
        """Tests if the specified element ID is in the document index"""
        if key in self.index:
            return True
        elif self.subdocs:
            for subdoc in self.subdocs.values():
                if key in subdoc:
                    return True
            return False
        else:
            return False

    def __getitem__(self, key):
        """Obtain an element by ID from the document index.

        Example::

            word = doc['example.p.4.s.10.w.3']
        """
        if isinstance(key, int):
            return self.data[key]
        else:
            try:
                return self.index[key]
            except KeyError:
                if self.subdocs: #perhaps the key is in one of our subdocs?
                    for subdoc in self.subdocs.values():
                        try:
                            return subdoc[key]
                        except KeyError:
                            pass
                else:
                    raise KeyError("No such key: " + key)


    def append(self,text):
        """Add a text (or speech) to the document:

        Example 1::

            doc.append(folia.Text)

        Example 2::
            doc.append( folia.Text(doc, id='example.text') )

        Example 3::

            doc.append(folia.Speech)

        """
        if text is Text:
            text = Text(self, id=self.id + '.text.' + str(len(self.data)+1) )
        elif text is Speech:
            text = Speech(self, id=self.id + '.speech.' + str(len(self.data)+1) )
        else:
            assert isinstance(text, Text) or isinstance(text, Speech)
        self.data.append(text)
        return text

    def add(self,text):
        """Alias for :meth:`Document.append`"""
        return self.append(text)

    def create(self, Class, *args, **kwargs):
        """Create an element associated with this Document. This method may be obsolete and removed later."""
        return Class(self, *args, **kwargs)

    def xmldeclarations(self):
        """Internal method to generate XML nodes for all declarations"""
        l = []

        for annotationtype, set in self.annotations:
            #Find the 'label' for the declarations dynamically (aka: AnnotationType --> String)
            label = annotationtype2str(annotationtype)

            if self.FOLIA1 and self.keepversion and annotationtype in ( AnnotationType.TEXT, AnnotationType.PHON) and set in ('undefined', DEFAULT_TEXT_SET, DEFAULT_PHON_SET):
                #this is the implicit TextContent or PhonContent declaration for FoLiA v1 output, no need to output it explicitly
                continue


            attribs = {}
            if set and (set != 'undefined' or self.FOLIA2): #'undefined' sets for FoLiA v1 can be left out and are implicit, but not so for FoLiA v2
                attribs['set'] = set

            if annotationtype in self.setdefinitionformat and set in self.setdefinitionformat[annotationtype]:
                attribs['format'] = self.setdefinitionformat[annotationtype][set]

            if annotationtype in self.set_alias and set in self.set_alias[annotationtype]:
                attribs['alias'] = self.set_alias[annotationtype][set]

            if not self.hasprocessors(annotationtype, set) and self.hasdefaults(annotationtype, set):
                #there are no new-style processors associated with this declaration, but there are old-style defaults, fall back to those:
                for key, value in self.annotationdefaults[annotationtype][set].items():
                    if key == 'annotatortype':
                        if value == AnnotatorType.MANUAL:
                            attribs[key] = 'manual'
                        elif value == AnnotatorType.AUTO:
                            attribs[key] = 'auto'
                    elif key == 'datetime':
                        attribs[key] = value.strftime("%Y-%m-%dT%H:%M:%S") #proper iso-formatting
                    elif value:
                        attribs[key] = value


            annotators = []
            if not (self.FOLIA1 and self.keepversion):
                if annotationtypeisspan(annotationtype):
                    if self.groupannotations[annotationtype][set]:
                        attribs["groupannotations"] = "yes"
                if annotationtype in self.annotators and set in self.annotators[annotationtype]:
                    for annotator in self.annotators[annotationtype][set]:
                        annotators.append( getattr(E, 'annotator')(processor=annotator.processor_id) )
            if label:
                label = label.lower()
                if self.FOLIA1 and self.keepversion and label in OLDTAGS_REVERSE and label != "item":
                    #for FoLiA v1 serialisation
                    label = OLDTAGS_REVERSE[label]
                l.append( getattr(E,'{' + NSFOLIA + '}' + label + '-annotation')(*annotators, **attribs) )
            else:
                raise Exception("Invalid annotation type")
        return l

    def jsondeclarations(self):
        """Return all declarations in a form ready to be serialised to JSON.

        Returns:
            list of dict
        """
        l = []
        for annotationtype, set in self.annotations:
            #Find the 'label' for the declarations dynamically (aka: AnnotationType --> String)
            label = annotationtype2str(annotationtype)

            if self.FOLIA1 and self.keepversion and annotationtype in ( AnnotationType.TEXT, AnnotationType.PHON) and set in ('undefined', DEFAULT_TEXT_SET, DEFAULT_PHON_SET):
                #this is the implicit TextContent or PhonContent declaration for FoLiA v1 output, no need to output it explicitly
                continue

            jsonnode = {'annotationtype': label.lower()}
            if set and (set != 'undefined' or self.FOLIA2):
                jsonnode['set'] = set


            if not self.hasprocessors(annotationtype, set) and self.hasdefaults(annotationtype, set):
                #there are no new-style processors associated with this declaration, but there are old-style defaults, fall back to those:
                for key, value in self.annotationdefaults[annotationtype][set].items():
                    if key == 'annotatortype':
                        if value == AnnotatorType.MANUAL:
                            jsonnode[key] = 'manual'
                        elif value == AnnotatorType.AUTO:
                            jsonnode[key] = 'auto'
                    elif key == 'datetime':
                        jsonnode[key] = value.strftime("%Y-%m-%dT%H:%M:%S") #proper iso-formatting
                    elif value:
                        jsonnode[key] = value
            jsonnode["annotators"] = []
            if not (self.FOLIA1 and self.keepversion):
                if annotationtypeisspan(annotationtype):
                    if self.groupannotations[annotationtype][set]:
                        jsonnode["groupannotations"] = True
                if annotationtype in self.annotators and set in self.annotators[annotationtype]:
                    for annotator in self.annotators[annotationtype][set]:
                        jsonnode["annotators"].append(annotator.processor_id)
            if label:
                l.append( jsonnode  )
            else:
                raise Exception("Invalid annotation type")
        return l

    def done(self):
        """Signal that you are done editing the document, this will perform any pending post-processing operation"""
        self.pendingvalidation()
        self.pendingsort()


    def xml(self, form = Form.NORMAL):
        """Serialise the document to XML.

        Returns:
            lxml.etree.Element

        See also:
            :meth:`Document.xmlstring`
        """

        self.done()


        attribs = {}
        attribs['{http://www.w3.org/XML/1998/namespace}id'] = self.id

        if self.keepversion:
            attribs['version'] = self.version
        else:
            attribs['version'] = FOLIAVERSION

        attribs['generator'] = 'foliapy-v' + LIBVERSION

        if form == Form.EXPLICIT:
            attribs['form'] = "explicit"

        metadataattribs = {}
        metadataattribs['type'] = self.metadatatype

        if isinstance(self.metadata, ExternalMetaData):
            metadataattribs['src'] = self.metadata.url


        e = E.FoLiA(**attribs)
        e.append(
            E.metadata(
                E.annotations(
                    *self.xmldeclarations()
                ),
                *self.xmlprovenance(),
                *self.xmlmetadata(),
                **metadataattribs
            )
        )
        for text in self.data:
            e.append(text.xml(form=form))
        return e

    def json(self):
        """Serialise the document to a ``dict`` ready for serialisation to JSON.

        Example::

            import json
            jsondoc = json.dumps(doc.json())
        """
        self.pendingvalidation()
        self.pendingsort()

        jsondoc = {'id': self.id, 'children': [], 'declarations': self.jsondeclarations(), 'provenance': self.jsonprovenance()}
        if self.keepversion:
            jsondoc['version'] = self.version
        else:
            jsondoc['version'] = FOLIAVERSION
        jsondoc['generator'] = 'foliapy-v' + LIBVERSION

        for text in self.data:
            jsondoc['children'].append(text.json())
        return jsondoc

    def xmlprovenance(self):
        """Internal method to serialize provenance data to XML"""
        if self.keepversion and self.FOLIA1:
            return []
        elif self.provenance:
            return [ self.provenance.xml() ]
        else:
            return []


    def jsonprovenance(self):
        """Internal method to serialize provenance data to JSON"""
        if self.keepversion and self.FOLIA1:
            return {}
        elif self.provenance:
            return self.provenance.json()
        else:
            return {}

    def xmlmetadata(self):
        """Internal method to serialize metadata to XML"""
        elements = []
        if not isinstance(self.metadata, ExternalMetaData):
            #in-document
            m = self.metadata
            while m is not None:
                if isinstance(m, NativeMetaData):
                    for key, value in self.metadata.items():
                        elements.append(E.meta(value,id=key) )
                else:
                    #ForeignData
                    elements.append(m.xml())
                m = m.next
        for metadata_id, submetadata in self.submetadata.items():
            subelements = []
            attribs = {
                "{http://www.w3.org/XML/1998/namespace}id": metadata_id,
                "type": self.submetadatatype.get(metadata_id,"native") }
            m = submetadata
            while m is not None:
                if isinstance(m, NativeMetaData):
                    for key, value in m.items():
                        subelements.append(E.meta(value,id=key) )
                elif isinstance(m, ExternalMetaData):
                    attribs['src'] = m.url
                elif isinstance(m, ForeignData):
                    #ForeignData
                    subelements.append(m.xml())
                m = m.next
            elements.append( E.submetadata(*subelements, **attribs))
        return elements




    def parsexmldeclarations(self, node):
        """Internal method to parse XML declarations"""
        if self.debug >= 1:
            print("[FoLiA DEBUG] Processing Annotation Declarations",file=stderr)
        self.declareprocessed = True
        for subnode in node: #pylint: disable=too-many-nested-blocks
            if not isinstance(subnode.tag, str): continue
            if node.text and node.text.strip():
                raise ParseError("Found extra leading text '" + node.text.strip() + "' in handling of <" + node.tag + "> @ line " + str(node.sourceline))
            if isinstance(subnode, ElementTree._Comment): continue #don't trip over comments #pylint: disable=protected-access
            if subnode.tag[:25] == '{' + NSFOLIA + '}' and subnode.tag[-11:] == '-annotation':
                prefix = subnode.tag[25:][:-11]
                type = None
                if prefix in OLDTAGS:
                    prefix = OLDTAGS[prefix]
                if prefix.upper() in vars(AnnotationType):
                    type = vars(AnnotationType)[prefix.upper()]
                else:
                    raise Exception("Unknown declaration: " + subnode.tag)

                if 'set' in subnode.attrib and subnode.attrib['set']:
                    set = subnode.attrib['set']
                    del subnode.attrib['set']
                else:
                    set = None

                if type is AnnotationType.TEXT and set is None and (checkversion(self.version, "2.0.0") >= 0 or not self.keepversion) :
                    set = DEFAULT_TEXT_SET
                elif type is AnnotationType.PHON and set is None and (checkversion(self.version, "2.0.0") >= 0 or not self.keepversion) :
                    set = DEFAULT_PHON_SET

                if type not in self.annotators:
                    self.annotators[type] = OrderedDict()
                if set not in self.annotators[type]:
                    self.annotators[type][set] = []

                for annotatornode in subnode:
                    if not isinstance(annotatornode, ElementTree._Comment): #don't trip over comments #pylint: disable=protected-access
                        if annotatornode.tag == '{' + NSFOLIA + '}annotator':
                             self.annotators[type][set].append(Annotator(annotatornode.attrib['processor'], self))
                        else:
                            raise ParseError("Expected <annotator>, got " + annotatornode.tag)

                self.declare(type, set, **subnode.attrib)
            elif subnode.tail and subnode.tail.strip():
                raise ParseError("Found extra trailing text '" + subnode.tail.strip() + "' in handling of <annotations> @ line " + str(subnode.sourceline))






    def declare(self, annotationtype, set=None, *args, **kwargs):
        """Declare new annotation types, sets or annotators to be used in the document.

           This typically done by associating an annotationtype and set with a processor, the processor
           contains annotator information and will be recorded in the provenance data.

        Arguments:
            annotationtype: The type of annotation, this is conveyed by passing the corresponding annotation class (such as :class:`PosAnnotation` for example), or a member of :class:`AnnotationType`, such as ``AnnotationType.POS``.
            set (str): the set, should formally be a URL pointing to the set definition

        Positional Arguments:
            processor (Processor or str): A processor to declare, can be a processor instance or an ID of an existing processor. The processor encapsulates all information of an annotator. If you specify multiple processors then they are parsed as a hierarchy, the first one being the root and the others subprocessors.

        Keyword Arguments:
            alias (str): Defines alias that may be used in set attribute of elements instead of the full set name
            generator (bool): Automatically append a subprocessor with generator information on the FoLiA library used? (default: True)

        Keyword Arguments (<= FoLiA 1.5 behaviour, i.e. without provenance data):
            annotator (str): Sets a default annotator old-style, i.e. without full provenance
            annotatortype: Old-style, should be either ``AnnotatorType.MANUAL`` or ``AnnotatorType.AUTO``, indicating whether the annotation was performed manually or by an automated process. Please use processor= instead.
            datetime (datetime.datetime): Sets the default datetime

        Example 1 (with provenance)::

            doc.declare(folia.PosAnnotation, 'http://some/path/brown-tag-set', Processor(name="mytagger") )

        Example 2 (with provenance; nested processors)::

            main_processor = Processor(name="myNLPtool", version="2.2")
            doc.declare(folia.PosAnnotation, 'http://some/path/brown-tag-set', main_processor, Processor(name="mytagger"))
            doc.declare(folia.LemmaAnnotation, 'http://some/set', main_processor, Processor(name="mylemmatiser"))

        Example 2b (with provenance; nested processors, same as above but setting main processor on Document instantiation instead)::

            doc = folia.Document(id="mydoc", processor=Processor(name="myNLPtool", version="2.2"))
            doc.declare(folia.PosAnnotation, 'http://some/path/brown-tag-set', Processor(name="mytagger"))
            doc.declare(folia.LemmaAnnotation, 'http://some/set', Processor(name="mylemmatiser"))

        Example 3 (with provenance; nested processors)::

            main_processor = Processor(name="myEditor", version="1.2")
            doc.declare(folia.PosAnnotation, 'http://some/path/brown-tag-set', main_processor, Processor(name="alice", type=AnnotatorType.MANUAL))
            doc.declare(folia.PosAnnotation, 'http://some/path/brown-tag-set', main_processor, Processor(name="bob", type=AnnotatorType.MANUAL))
            doc.declare(folia.PosAnnotation, 'http://some/path/brown-tag-set', main_processor, Processor(name="john", type=AnnotatorType.MANUAL))

        Example 4 (without provenance, for backward compatibility, the use of proper provenance is always preferred!)::

            doc.declare(folia.PosAnnotation, 'http://some/path/brown-tag-set', annotator="mytagger", annotatortype=folia.AnnotatorType.AUTO)

        Returns::
            Processor instance of the last processor added (or None if no provenance is used)


        """
        if inspect.isclass(annotationtype):
            annotationtype = annotationtype.ANNOTATIONTYPE
        if set is None: #empty set or unspecified set
            #We assume default sets for TEXT and PHON (if not explicitly declared otherwise)
            if annotationtype == AnnotationType.TEXT:
                set = DEFAULT_TEXT_SET
                if self.debug >= 1: print("[FoLiA DEBUG] No set specified for text, auto-declaring default text set", file=stderr)
            elif annotationtype == AnnotationType.PHON:
                set = DEFAULT_PHON_SET
                if self.debug >= 1: print("[FoLiA DEBUG] No set specified for phon, auto-declaring default phon set", file=stderr)
            elif self.FOLIA1:
                set = "undefined" #only for FoLiA < v2
                if self.debug >= 1: print("[FoLiA DEBUG] No set specified for " + annotationtype2str(annotationtype) + " in FoLiA v1 document; auto-declaring undefined", file=stderr)
            #else we maintain the value None
        if annotationtype in (AnnotationType.TEXT, AnnotationType.PHON) and annotationtype in self.annotationdefaults and 'undefined' in self.annotationdefaults[annotationtype]:
            #override any 'undefined' declarations (for FoLiA <2), so
            #we don't end up with two declarations
            del self.annotationdefaults[annotationtype]['undefined']
        if set is not None  and not isinstance(set,str):
            raise ValueError("Set parameter for declare() must be a string, None (no set)")

        if annotationtype in self.alias_set and set in self.alias_set[annotationtype]:
            raise ValueError("Set " + set + " conflicts with alias, may not be equal!")
        if (annotationtype, set) not in self.annotations:
            self.annotations.append( (annotationtype,set) )
            if set and self.loadsetdefinitions and set not in self.setdefinitions:
                if set[:7] == "http://" or set[:8] == "https://" or set[:6] == "ftp://":
                    try:
                        self.setdefinitions[set] = SetDefinition(set,verbose=self.verbose) #will raise exception on error
                    except DeepValidationError as e:
                        self.failedsetdefinitions.append(set)
                        print("WARNING: ",str(e),file=sys.stderr)
                        if not self.allowadhocsets:
                            raise e
        if annotationtype not in self.annotationdefaults:
            self.annotationdefaults[annotationtype] = {}
        if annotationtype not in self.annotators:
            self.annotators[annotationtype] = OrderedDict()
        if annotationtype not in self.groupannotations:
            self.groupannotations[annotationtype] = {}
        if set not in self.annotators[annotationtype]:
            self.annotators[annotationtype][set] = []
        if annotationtypeisspan( annotationtype): #for span annotation only
            if set not in self.groupannotations[annotationtype]:
                self.groupannotations[annotationtype][set] = False #default
            if 'groupannotations' in kwargs and kwargs['groupannotations'] in ("yes","true",True,1):
                self.groupannotations[annotationtype][set] = True
        if 'alias' in kwargs:
            if annotationtype in self.set_alias and set in self.set_alias[annotationtype] and self.set_alias[annotationtype][set] != kwargs['alias']:
                raise ValueError("Redeclaring set " + set + " with another alias ('"+kwargs['alias']+"') is not allowed!")
            if annotationtype in self.alias_set and kwargs['alias'] in self.alias_set[annotationtype] and self.alias_set[annotationtype][kwargs['alias']] != set:
                raise ValueError("Redeclaring alias " + kwargs['alias'] + " with another set ('"+set+"') is not allowed!")
            if annotationtype in self.set_alias and kwargs['alias'] in self.set_alias[annotationtype]:
                raise ValueError("Alias " + kwargs['alias'] + " conflicts with set name, may not be equal!")
            if annotationtype not in self.alias_set:
                self.alias_set[annotationtype] = {}
            if annotationtype not in self.set_alias:
                self.set_alias[annotationtype] = {}
            self.alias_set[annotationtype][kwargs['alias']] = set
            self.set_alias[annotationtype][set] = kwargs['alias']


        if 'format' in kwargs and set:
            if annotationtype not in self.setdefinitionformat:
                self.setdefinitionformat[annotationtype] = {}
            self.setdefinitionformat[annotationtype][set] = kwargs['format']


        if self.debug >= 1:
            print("[FoLiA DEBUG] Declaring " + annotationtype2str(annotationtype) + ", set " + str(set), file=stderr)

        #add the document main processor
        if self.processor and (not args or args[0] != self.processor):
            if isinstance(args, tuple):
                args = list(args)
            args.insert(0, self.processor)


        if 'processor' in kwargs:
            if isinstance(args, tuple):
                args = list(args)
            #just some flexibility in case the user used processor= instead of a direct positional argument
            args.append(kwargs['processor'])
            del kwargs['processor']

        context = None
        for i, processor in enumerate(args):
            if isinstance(processor, Processor):
                #check if processor is new
                processor_new = processor not in self.provenance
                if not processor_new:
                    processor = self.provenance[processor]
                elif self.debug >= 1:
                    print("[FoLiA DEBUG] Processor",processor.id,"is new",file=sys.stderr)
            else:
                #assume we got passed a processor ID of an already existing processor, resolve it
                processor = self.provenance[processor]
                processor_new = False

            leaf = i == len(args) - 1
            if leaf:
                #An annotator is a reference to a processor, make the reference only if it is not already there
                annotator_new = all( a.processor_id != processor.id for a in self.annotators[annotationtype][set] )
                if annotator_new:
                    if self.debug >= 1:
                        print("[FoLiA DEBUG] Adding annotator for " + annotationtype2str(annotationtype) + " to processor  " + processor.name + ", ID " + processor.id, file=stderr)
                    self.annotators[annotationtype][set].append(Annotator(processor.id, self))

            if processor_new:
                if 'generator' not in kwargs or not kwargs['generator']:
                    try:
                        #ensure the subprocessor doesn't already exist
                        processor[processor.id+'.generator']
                    except KeyError: #good, this is what we want:
                        #Add a subprocessor with generator information about this FoLiA library
                        processor.append(Processor(id=processor.id+'.generator', name="foliapy", type=ProcessorType.GENERATOR, version=LIBVERSION, folia_version=FOLIAVERSION))
                if context:
                    #add processor to existing context in provenance chain
                    if self.debug >= 1:
                        print("[FoLiA DEBUG] Adding new processor " + processor.name + ", ID " + processor.id + " as child of existing processor " + context.id, file=stderr)
                    context.append(processor)
                else:
                    #add processor to provenance chain
                    if self.debug >= 1:
                        print("[FoLiA DEBUG] Adding new processor " + processor.name + ", ID " + processor.id, file=stderr)
                    self.provenance.append(processor)
            context = processor

        if 'external' in kwargs:
            self.attachexternal(type,set,**kwargs)

        #Set defaults
        if args:
            #no defaults
            self.annotationdefaults[annotationtype][set] = {}
            #return last processor
            return processor
        elif not args:
            #No processors, old-style behaviour with annotator/annotatortype attributes for defaults
            if 'datetime' in kwargs:
                kwargs['datetime'] = parse_datetime(kwargs['datetime'])
            elif 'annotator' in kwargs and 'annotatortype' not in kwargs:
                kwargs['annotatortype'] = AnnotatorType.AUTO
            self.annotationdefaults[annotationtype][set] = kwargs
        else:
            #no defaults
            self.annotationdefaults[annotationtype][set] = {}


    def erase(self, Class, annotationset=False):
        """Erases all annotations of a particular type and annotation set (unless set is False in which case it applies to all elements regardless of set). Also removed the declarations (i.e. the opposite of declare()) """
        annotationtype = Class.ANNOTATIONTYPE
        count = 0
        ismarkup = issubclass(Class, AbstractTextMarkup)
        #loop over the entire document recursively and collect all matches (fairly time consuming)
        matches = []
        for element in self.select(Class,annotationset,recursive=True, ignore=False):
            matches.append(element)


        #delete all matches
        for element in matches:
            if not ismarkup:
                element.parent.remove(element)
            else:
                i = element.parent.getindex(element)
                if i == -1: raise Exception("Can't find child from parent, this should not happen")
                element.parent.data[i] = element.text()
            count += 1

        if annotationset is False:
            #for any set!

            #remove declaration
            self.annotations = [ (t,s) for t,s in self.annotations if t != annotationtype ]
            #remove annotator references from declarations (new style)
            if annotationtype in self.annotators:
                del self.annotators[annotationtype]
            #remove old style annotation defaults
            if annotationtype in self.annotationdefaults:
                del self.annotationdefaults[annotationtype]
        else:
            #for a specific set

            #remove declaration
            if (annotationtype, annotationset) in self.annotations:
                self.annotations.remove((annotationtype, annotationset))
            #remove annotator references from declarations
            if annotationtype in self.annotators and annotationset in self.annotators[annotationtype]:
                del self.annotators[annotationtype][annotationset]
            #remove old style annotation defaults
            if annotationtype in self.annotationdefaults and annotationset in self.annotationdefaults[annotationtype]:
                del self.annotationdefaults[annotationtype][annotationset]

        return count




    def attachexternal(self, type, set, **kwargs):
        if self.debug >= 1:
            print("[FoLiA DEBUG] Loading external document: " + subnode.attrib['external'],file=stderr)
        if not type in self.standoffdocs:
            self.standoffdocs[type] = {}
        self.standoffdocs[type][set] = {}

        #check if it is already loaded, if multiple references are made to the same doc we reuse the instance
        standoffdoc = None
        for t in self.standoffdocs:
            for s in self.standoffdocs[t]:
                for source in self.standoffdocs[t][s]:
                    if source == subnode.attrib['external']:
                        standoffdoc = self.standoffdocs[t][s]
                        break
                if standoffdoc: break
            if standoffdoc: break

        if not standoffdoc:
            if subnode.attrib['external'][:7] == 'http://' or subnode.attrib['external'][:8] == 'https://':
                #document is remote, download (in memory)
                try:
                    f = urlopen(subnode.attrib['external'])
                except:
                    raise DeepValidationError("Unable to download standoff document: " + subnode.attrib['external'])
                try:
                    content = u(f.read())
                except IOError:
                    raise DeepValidationError("Unable to download standoff document: " + subnode.attrib['external'])
                f.close()
                standoffdoc = Document(string=content, parentdoc=self, setdefinitions=self.setdefinitions)
            elif os.path.exists(subnode.attrib['external']):
                #document is on disk:
                standoffdoc = Document(file=subnode.attrib['external'], parentdoc=self, setdefinitions=self.setdefinitions)
            else:
                #document not found
                raise DeepValidationError("Unable to find standoff document: " + subnode.attrib['external'])

        self.standoffdocs[type][set][subnode.attrib['external']] = standoffdoc
        standoffdoc.parentdoc = self




    def declared(self, annotationtype, set=False):
        """Checks if the annotation type is present (i.e. declared) in the document.

        Arguments:
            annotationtype: The type of annotation, this is conveyed by passing the corresponding annototion class (such as :class:`PosAnnotation` for example), or a member of :class:`AnnotationType`, such as ``AnnotationType.POS``.
            set (str/None/False): the set, should formally be a URL pointing to the set definition (aliases are also supported). If set to False, checks regardless of set (i.e. matching any set). If set to None, there is no associated set.

        Example::

            if doc.declared(folia.PosAnnotation, 'http://some/path/brown-tag-set'):
                ..

        Returns:
            bool
        """
        if inspect.isclass(annotationtype): annotationtype = annotationtype.ANNOTATIONTYPE
        if set is False:
            for atype,_  in self.annotations:
                if annotationtype == atype:
                    return True
            return False
        else:
            return ( (annotationtype,set) in self.annotations) or (set in self.alias_set and self.alias_set[set] and (annotationtype, self.alias_set[set]) in self.annotations )


    def defaultset(self, annotationtype):
        """Obtain the default set for the specified annotation type.

        Arguments:
            annotationtype: The type of annotation, this is conveyed by passing the corresponding annototion class (such as :class:`PosAnnotation` for example), or a member of :class:`AnnotationType`, such as ``AnnotationType.POS``.

        Returns:
            the set (str or None), or False if there is no default set. Take care to explicitly distinguish between False and None!

        Raises:
            :class:`NoSuchAnnotation` if the annotation type does not exist or if there is ambiguity (multiple sets for the same type). Or returns False instead if raiseexception = False
        """

        if inspect.isclass(annotationtype):
            annotationtype = annotationtype.ANNOTATIONTYPE
        elif isinstance(annotationtype,AbstractElement):
            annotationtype = annotationtype.__class__.ANNOTATIONTYPE
        if annotationtype is None:
            return False

        #new style
        matches = [ (atype, aset) for atype, aset in self.annotations if atype == annotationtype ]
        if matches:
            l = len(matches)
            if l == 1:
                return matches[0][1]
            elif l > 1:
                return False

        #if that failes try old style by considering defaults
        if annotationtype in self.annotationdefaults:
            l = len(self.annotationdefaults[annotationtype])
            if l == 1:
                return list(self.annotationdefaults[annotationtype].keys())[0]
            elif l > 1:
                return False

        raise NoSuchAnnotation("No declaration for annotation type " + annotationtype2str(annotationtype))

    def getannotators(self, annotationtype, annotationset):
        """Get all annotators for the given annotationtype and set. This is a generator that yields Annotator instances, these resolve to a Processor when called. See also `:meth:AbstractElement.getprocessors` to obtain processors directly, which is most likely what you want."""
        if inspect.isclass(annotationtype) or isinstance(annotationtype,AbstractElement): annotationtype = annotationtype.ANNOTATIONTYPE
        if annotationtype not in self.annotators: self.annotators[annotationtype] = {}
        if annotationset not in self.annotators[annotationtype]: self.annotators[annotationtype][annotationset] = []
        for annotator in self.annotators[annotationtype][annotationset]:
            yield annotator

    def getprocessors(self, annotationtype, annotationset):
        """Get all processors associated with  the given annotationtype and set, generator yielding Processor instances, see also `:meth:AbstractElement.getannotators`"""
        for annotator in self.getannotators(annotationtype, annotationset):
            yield annotator() #calling the annotator returns a Processor

    def hasprocessors(self, annotationtype, annotationset):
        """Does this annotationtype and set have associated processors/annotators? (FoLiA v2 provenance data)"""
        return annotationtype in self.annotators and annotationset in self.annotators[annotationtype] and len(self.annotators[annotationtype][annotationset]) > 0

    def hasannotators(self, annotationtype, annotationset):
        """Alias for :meth:`Document.hasprocessors`: Does this annotationtype and set have associated processors/annotators? (FoLiA v2 provenance data)"""
        return self.hasprocessors(annotationtype, annotationset)

    def hasdefaults(self, annotationtype, annotationset):
        """Does this annotationtype and set have associated defaults? (old style FoLiA v1 without provenance data)"""
        return annotationtype in self.annotationdefaults and annotationset in self.annotationdefaults[annotationtype] and len(self.annotationdefaults[annotationtype][annotationset]) > 0

    def hasdefaultprocessor(self, annotationtype, annotationset):
        """Does this annotationtype and set have defaults? (new style FoLiA v2 with provenance data)"""
        return len(self.annotators[annotationtype][annotationset]) == 1

    def getdefaultprocessor(self, annotationtype, annotationset):
        l = len(self.annotators[annotationtype][annotationset])
        if l == 1:
            for processor in self.getprocessors(annotationtype, annotationset): #should only iterate over one!
                return processor
        elif l > 1:
            raise NoDefaultError("No processor specified for <" + ANNOTATIONTYPE2XML[annotationtype] +  ">, but the presence of multiple declarations prevents assigning a default")

    def defaultannotator(self, annotationtype, set=False):
        """Obtain the default annotator for the specified annotation type and set.

        Arguments:
            annotationtype: The type of annotation, this is conveyed by passing the corresponding annototion class (such as :class:`PosAnnotation` for example), or a member of :class:`AnnotationType`, such as ``AnnotationType.POS``.
            set (str/None/False): the set, should formally be a URL pointing to the set definition or None for setless annotations. If set to False, the default set will be inferred automatically, but an exception will occur if there is none!

        Returns:
            the set (str)

        Raises:
            :class:`NoDefaultError` if the annotation type does not exist or if there is ambiguity (multiple sets for the same type)
        """

        if inspect.isclass(annotationtype) or isinstance(annotationtype,AbstractElement): annotationtype = annotationtype.ANNOTATIONTYPE
        try:
            if set is False: set = self.defaultset(annotationtype)
            return self.annotationdefaults[annotationtype][set]['annotator']
        except (NoSuchAnnotation, KeyError):
            raise NoDefaultError

    def defaultannotatortype(self, annotationtype,set=False):
        """Obtain the default annotator type for the specified annotation type and set.

        Arguments:
            annotationtype: The type of annotation, this is conveyed by passing the corresponding annototion class (such as :class:`PosAnnotation` for example), or a member of :class:`AnnotationType`, such as ``AnnotationType.POS``.
            set (str/None/False): the set, should formally be a URL pointing to the set definition or None for setless annotations. If set to False, the default set will be inferred automatically, but an exception will occur if there is none!

        Returns:
            ``AnnotatorType.AUTO`` or ``AnnotatorType.MANUAL``

        Raises:
            :class:`NoDefaultError` if the annotation type does not exist or if there is ambiguity (multiple sets for the same type)
        """
        if inspect.isclass(annotationtype) or isinstance(annotationtype,AbstractElement): annotationtype = annotationtype.ANNOTATIONTYPE
        try:
            if set is False: set = self.defaultset(annotationtype)
            return self.annotationdefaults[annotationtype][set]['annotatortype']
        except (NoSuchAnnotation, KeyError):
            raise NoDefaultError


    def defaultdatetime(self, annotationtype,set=False):
        """Obtain the default datetime for the specified annotation type and set.

        Arguments:
            annotationtype: The type of annotation, this is conveyed by passing the corresponding annototion class (such as :class:`PosAnnotation` for example), or a member of :class:`AnnotationType`, such as ``AnnotationType.POS``.
            set (str/None/False): the set, should formally be a URL pointing to the set definition or None for setless annotations. If set to False, the default set will be inferred automatically, but an exception will occur if there is none!

        Returns:
            the set (str)

        Raises:
            :class:`NoDefaultError` if the annotation type does not exist or if there is ambiguity (multiple sets for the same type)
        """
        if inspect.isclass(annotationtype) or isinstance(annotationtype,AbstractElement): annotationtype = annotationtype.ANNOTATIONTYPE
        try:
            if set is False: set = self.defaultset(annotationtype)
            return self.annotationdefaults[annotationtype][set]['datetime']
        except (NoSuchAnnotation, KeyError):
            raise NoDefaultError





    def title(self, value=None):
        """Get or set the document's title from/in the metadata

           No arguments: Get the document's title from metadata
           Argument: Set the document's title in metadata
        """
        if not (value is None):
            if (self.metadatatype == "native"):
                self.metadata['title'] = value
            else:
                self._title = value
        if (self.metadatatype == "native"):
            if 'title' in self.metadata:
                return self.metadata['title']
            else:
                return None
        else:
            return self._title

    def date(self, value=None):
        """Get or set the document's date from/in the metadata.

           No arguments: Get the document's date from metadata
           Argument: Set the document's date in metadata
        """
        if not (value is None):
            if (self.metadatatype == "native"):
                self.metadata['date'] = value
            else:
                self._date = value
        if (self.metadatatype == "native"):
            if 'date' in self.metadata:
                return self.metadata['date']
            else:
                return None
        else:
            return self._date

    def publisher(self, value=None):
        """No arguments: Get the document's publisher from metadata
           Argument: Set the document's publisher in metadata
        """
        if not (value is None):
            if (self.metadatatype == "native"):
                self.metadata['publisher'] = value
            else:
                self._publisher = value
        if (self.metadatatype == "native"):
            if 'publisher' in self.metadata:
                return self.metadata['publisher']
            else:
                return None
        else:
            return self._publisher

    def license(self, value=None):
        """No arguments: Get the document's license from metadata
           Argument: Set the document's license in metadata
        """
        if not (value is None):
            if (self.metadatatype == "native"):
                self.metadata['license'] = value
            else:
                self._license = value
        if (self.metadatatype == "native"):
            if 'license' in self.metadata:
                return self.metadata['license']
            else:
                return None
        else:
            return self._license

    def language(self, value=None):
        """No arguments: Get the document's language (ISO-639-3) from metadata
           Argument: Set the document's language (ISO-639-3) in metadata
        """
        if not (value is None):
            if (self.metadatatype == "native"):
                self.metadata['language'] = value
            else:
                self._language = value
        if self.metadatatype == "native":
            if 'language' in self.metadata:
                return self.metadata['language']
            else:
                return None
        else:
            return self._language

    def parsemetadata(self, node):
        """Internal method to parse metadata"""

        if 'type' in node.attrib:
            self.metadatatype = node.attrib['type']
        else:
            #no type specified, default to native
            self.metadatatype = "native"

        externalmetadata = False
        if 'src' in node.attrib:
            self.metadata = ExternalMetaData(node.attrib['src'])
            externalmetadata = True
        elif self.metadatatype == "native":
            self.metadata = NativeMetaData()
        else:
            self.metadata = None #may be set below to ForeignData


        declarations = None
        for subnode in node:
            if subnode.tag == '{' + NSFOLIA + '}annotations':
                #we defer parsing to the end of this function, as we may need to have parsed provenance first
                declarations = subnode
            elif subnode.tag == '{' + NSFOLIA + '}provenance':
                self.parsexmlprovenance(subnode)
            elif subnode.tag == '{' + NSFOLIA + '}meta':
                if not externalmetadata:
                    if self.metadata is None: self.metadata = NativeMetaData()
                    if subnode.text:
                        self.metadata[subnode.attrib['id']] = subnode.text
                else:
                    raise MetaDataError("Encountered a meta element but metadata is external!")
            elif subnode.tag == '{' + NSFOLIA + '}foreign-data':
                if externalmetadata:
                    raise MetaDataError("Encountered a foreign-data element but metadata is external!")
                elif self.metadata is not None:
                    #multiple foreign-data elementss, chain, also works with NativeMetaData:
                    e = self.metadata
                    while e.next is not None:
                        e = e.next
                    e.next = ForeignData(self, node=subnode)
                else:
                    self.metadata = ForeignData(self, node=subnode)
            elif subnode.tag == '{' + NSFOLIA + '}submetadata':
                self.parsesubmetadata(subnode)
            elif subnode.tag == '{http://www.mpi.nl/IMDI/Schema/IMDI}METATRANSCRIPT': #backward-compatibility for old IMDI without foreign-key
                self.metadatatype = "imdi"
                self.metadata = ForeignData(self, node=subnode)
            if subnode.tail and subnode.tail.strip():
                raise ParseError("Found extra trailing text '" + subnode.tail.strip() + "' in handling of <metadata> @ line " + str(subnode.sourceline))

        self.parsexmldeclarations(declarations)

    def parsexmlprovenance(self, node):
        if node.text and node.text.strip():
            raise ParseError("Found extra leading text '" + node.text.strip() + "' in handling of <" + node.tag + "> @ line " + str(node.sourceline))
        for subnode in node:
            if subnode.text and subnode.text.strip():
                raise ParseError("Found extra leading text '" + subnode.text.strip() + "' in handling of <" + subnode.tag + "> @ line " + str(node.sourceline))
            elif subnode.tag == '{' + NSFOLIA + '}processor':
                processor = Processor.parsexml(subnode)
                self.provenance.append(processor)
            if subnode.tail and subnode.tail.strip():
                raise ParseError("Found extra trailing text '" + subnode.tail.strip() + "' in handling of <provenance> @ line " + str(subnode.sourceline))



    def parsesubmetadata(self, node):
        if '{http://www.w3.org/XML/1998/namespace}id' not in node.attrib:
            raise MetaDataError("Encountered a submetadata element without xml:id!")
        else:
            id = node.attrib['{http://www.w3.org/XML/1998/namespace}id']


        if 'type' in node.attrib:
            self.submetadatatype[id] = node.attrib['type']
        else:
            self.submetadatatype[id] = "native"

        if 'src' in node.attrib:
            self.submetadata[id] = ExternalMetaData(node.attrib['src'])
        elif self.submetadatatype[id] == "native":
            self.submetadata[id] = NativeMetaData()
        else:
            self.submetadata[id] = None

        for subnode in node:
            if subnode.tag == '{' + NSFOLIA + '}meta':
                if self.submetadatatype[id] == "native":
                    if subnode.text:
                        self.submetadata[id][subnode.attrib['id']] = subnode.text
                else:
                    raise MetaDataError("Encountered a meta element but metadata type is not native!")
            elif subnode.tag == '{' + NSFOLIA + '}foreign-data':
                if self.submetadatatype[id] == "native":
                    raise MetaDataError("Encountered a foreign-data element but metadata type is native!")
                elif self.submetadata[id] is not None:
                    #multiple foreign-data elements, chain:
                    e = self.submetadata[id]
                    while e.next is not None:
                        e = e.next
                    e.next = ForeignData(self, node=subnode)
                else:
                    self.submetadata[id] = ForeignData(self, node=subnode)
            elif subnode.tail and subnode.tail.strip():
                raise ParseError("Found extra trailing text '" + subnode.tail.strip() + "' in handling of <" + node.tag + "> @ line " + str(subnode.sourceline))

    def parsexml(self, node, ParentClass = None):
        """Internal method.

        This is the main XML parser, will invoke class-specific XML parsers."""
        if isinstance(node,ElementTree._ElementTree): #pylint: disable=protected-access
            node = node.getroot()
        elif isstring(node):
            node = xmltreefromstring(node).getroot()

        self.doneparsing = False #indicates that the document is still parsing

        if node.tag.startswith('{' + NSFOLIA + '}'):
            foliatag = node.tag[nslen:]
            if foliatag == "FoLiA":
                if self.debug >= 1: print("[FoLiA DEBUG] Found FoLiA document",file=stderr)
                try:
                    self.id = node.attrib['{http://www.w3.org/XML/1998/namespace}id']
                except KeyError:
                    raise Exception("FoLiA Document has no ID!")
                if 'version' in node.attrib:
                    self.version = node.attrib['version']
                else:
                    print("WARNING: FoLiA Document has no version! Assuming an old version (<1.0)",file=sys.stderr)
                    self.version = "0.12"
                if self.debug >= 1: print("[FoLiA DEBUG] FoLiA version:", self.version,file=stderr)
                if checkversion(self.version) > 0:
                    print("WARNING!!! Document uses a newer version of FoLiA than this library! (" + self.version + " vs " + FOLIAVERSION + "). Any possible subsequent failures in parsing or processing may probably be attributed to this. Upgrade foliapy to remedy this.",file=sys.stderr)
                self.FOLIA2 = checkversion(self.version, "2.0.0") >= 0
                self.FOLIA1 = checkversion(self.version, "2.0.0") < 0 #also includes FoLiA v0.*
                if checkversion(self.version,'1.5.0') >= 0:
                    self.textvalidation = True
                if self.FOLIA1:
                    #older FoLiA, add implicit declarations:
                    if self.autodeclare is None: self.autodeclare = False

                    if self.keepversion:
                        #Add implicit declaration for TextContent (FoLiA < 2)
                        self.annotations.append( (AnnotationType.TEXT,'undefined') )
                        self.annotationdefaults[AnnotationType.TEXT] = {'undefined': {} }
                        #Add implicit declaration for PhonContent (FoLiA < 2)
                        self.annotations.append( (AnnotationType.PHON,'undefined') )
                        self.annotationdefaults[AnnotationType.PHON] = {'undefined': {} }
                    else:
                        #use the new default sets
                        self.annotations.append( (AnnotationType.TEXT,DEFAULT_TEXT_SET) )
                        self.annotationdefaults[AnnotationType.TEXT] = {DEFAULT_TEXT_SET: {} }
                        self.annotations.append( (AnnotationType.PHON,DEFAULT_PHON_SET) )
                        self.annotationdefaults[AnnotationType.PHON] = {DEFAULT_PHON_SET: {} }
                else:
                    if self.autodeclare is None: self.autodeclare = True
                if 'document_version' in node.attrib:
                    self.document_version = node.attrib['document_version']

                if 'external' in node.attrib:
                    self.external = (node.attrib['external'] == 'yes')

                    if self.external and not self.parentdoc:
                        raise DeepValidationError("Document is marked as external and should not be loaded independently. However, no parentdoc= has been specified!")

                if node.text and node.text.strip():
                    raise ParseError("Found extra leading text '" + node.text.strip() + "' in handling of <FoLiA> @ line " + str(node.sourceline))

                for subnode in node:
                    # don't trip over comments
                    if isinstance(subnode, ElementTree._Comment):
                        continue
                    if subnode.text and subnode.text.strip():
                        raise ParseError("Found extra leading text '" + subnode.text.strip() + "' in handling of <"+ subnode.tag+"> @ line " + str(node.sourceline))
                    if subnode.tag == '{' + NSFOLIA + '}metadata':
                        self.parsemetadata(subnode)
                    elif (subnode.tag == '{' + NSFOLIA + '}text' or subnode.tag == '{' + NSFOLIA + '}speech') and self.mode == Mode.MEMORY:
                        if self.debug >= 1: print("[FoLiA DEBUG] Found Text",file=stderr)
                        e = self.parsexml(subnode)
                        if e is not None:
                            self.data.append(e)
                    if subnode.tail and subnode.tail.strip():
                        raise ParseError("Found extra trailing text '" + subnode.tail.strip() + "' in handling of <FoLiA> @ line " + str(subnode.sourceline))
            else:
                #generic handling (FoLiA)
                if foliatag in OLDTAGS: #backward compatibility
                    foliatag = OLDTAGS[foliatag]
                elif foliatag == "relation" and self.FOLIA1: #this is a patch for backward compatibility because the span role 'relation' got renamed to 'rel' so alignments could be renamed to relations,
                    foliatag = "rel"
                if foliatag not in XML2CLASS:
                    raise Exception("Unknown FoLiA XML tag: " + foliatag)
                Class = XML2CLASS[foliatag]
                return Class.parsexml(node,self)
        else:
            raise Exception("Unknown FoLiA XML tag: " + node.tag)

        self.done()
        self.doneparsing = True #indicates that the document is still parsing


    def pendingsort(self, warnonly=None):
        """Perform any pending sorts on span annotation elements (per layer, in turn recurses into all span annotations)"""
        while self.layersortbuffer:
            layer = self.layersortbuffer.pop()
            layer.sort()


    def pendingvalidation(self, warnonly=None):
        """Perform any pending validations

        Parameters:
            warnonly (bool): Warn only (True) or raise exceptions (False). If set to None then this value will be determined based on the document's FoLiA version (Warn only before FoLiA v1.5)

        Returns:
            bool
        """
        if self.debug: print("[FoLiA DEBUG] Processing pending validations (if any)",file=stderr)

        if warnonly is None and self and self.version:
            warnonly = (checkversion(self.version, '1.5.0') < 0) #warn only for documents older than FoLiA v1.5
        if self.textvalidation:
            while self.offsetvalidationbuffer:
                structureelement, textclass = self.offsetvalidationbuffer.pop(0)

                if self.debug: print("[FoLiA DEBUG] Performing offset validation on " + repr(structureelement) + " textclass " + textclass,file=stderr)

                #validate offsets
                tc = structureelement.textcontent(textclass)
                if tc.offset is not None:
                    try:
                        tc.getreference(validate=True)
                    except UnresolvableTextContent as e:
                        msg = "Text for " + structureelement.__class__.__name__ + ", ID " + str(structureelement.id) + ", textclass " + textclass  + ", has incorrect offset " + str(tc.offset) + " or invalid reference: " + str(e)

                        warn_legacy = False
                        try:
                            tc.getreference(validate=True, trim_spaces=False)
                            msg += "\nHowever, according to the older rules (<v2.4.1) the offsets are accepted. So we are treating this as a warning rather than an error. We do recommend fixing this if this is a document you intend to publish."
                            warn_legacy = True
                        except UnresolvableTextContent as e2:
                            msg += "\n(also checked against older rules prior to FoLiA v2.4.1)"

                        if self.filename:
                            print( self.filename + ": TEXT VALIDATION ERROR: " + msg,file=sys.stderr)
                        else:
                            print("TEXT VALIDATION ERROR: " + msg,file=sys.stderr)
                        if not warnonly and not warn_legacy:
                            raise


    def select(self, Class, set=False, recursive=True,  ignore=True):
        """See :meth:`AbstractElement.select`"""
        if self.mode == Mode.MEMORY:
            for t in self.data:
                if Class.__name__ == 'Text':
                    yield t
                else:
                    for e in t.select(Class,set,recursive,ignore):
                        yield e

    def count(self, Class, set=False, recursive=True,ignore=True):
        """See :meth:`AbstractElement.count`"""
        if self.mode == Mode.MEMORY:
            s = 0
            for t in self.data:
                s += t.count(Class,set,recursive, ignore)
            return s

    def paragraphs(self, index = None):
        """Return a generator of all paragraphs found in the document.

        If an index is specified, return the n'th paragraph only (starting at 0)"""
        if index is None:
            return self.select(Paragraph)
        else:
            if index < 0:
                index = sum(t.count(Paragraph) for t in self.data) + index
            for t in self.data:
                for i,e in enumerate(t.select(Paragraph)) :
                    if i == index:
                        return e
            raise IndexError

    def sentences(self, index = None):
        """Return a generator of all sentence found in the document. Except for sentences in quotes.

        If an index is specified, return the n'th sentence only (starting at 0)"""
        if index is None:
            return self.select(Sentence,False,True,[Quote])
        else:
            if index < 0:
                index = sum(t.count(Sentence,False,True,[Quote]) for t in self.data) + index
            for t in self.data:
                for i,e in enumerate(t.select(Sentence,False,True,[Quote])) :
                    if i == index:
                        return e
            raise IndexError


    def words(self, index = None):
        """Return a generator of all active words found in the document. Does not descend into annotation layers, alternatives, originals, suggestions.

        If an index is specified, return the n'th word only (starting at 0)"""
        if index is None:
            return self.select(Word,False,True,default_ignore_structure)
        else:
            if index < 0:
                index = sum(t.count(Word,False,True,default_ignore_structure) for t in self.data)  + index
            for t in self.data:
                for i, e in enumerate(t.select(Word,False,True,default_ignore_structure)):
                    if i == index:
                        return e
            raise IndexError



    def text(self, cls='current', retaintokenisation=False, hidden=False, trim_spaces=True, correctionhandling=CorrectionHandling.CURRENT):
        """Returns the text of the entire document, returns a single string

        See also:
            :meth:`AbstractElement.text`
        """

        #backward compatibility, old versions didn't have cls as first argument, so if a boolean is passed first we interpret it as the 2nd:
        if cls is True or cls is False:
            retaintokenisation = cls
            cls = 'current'

        s = ""
        for c in self.data:
            if s: s += "\n\n\n"
            try:
                s += c.text(cls, retaintokenisation=retaintokenisation, hidden=hidden, trim_spaces=trim_spaces, correctionhandling=correctionhandling)
            except NoSuchText:
                continue
        return s

    def xmlstring(self, form = Form.NORMAL):
        """Return the XML representation of the document as a string."""
        return str(ElementTree.tostring(self.xml(form=form), xml_declaration=True, pretty_print=True, encoding='utf-8'),'utf-8')


    def __unicode__(self):
        """Returns the text of the entire document"""
        return self.text()

    def __str__(self):
        """Returns the text of the entire document"""
        return self.text()

    def __ne__(self, other):
        return not (self == other)

    def __eq__(self, other):
        if len(self.data) != len(other.data):
            if self.debug: print("[FoLiA DEBUG] Equality check - Documents have unequal amount of children",file=stderr)
            return False
        for e,e2 in zip(self.data,other.data):
            if e != e2:
                return False
        return True











#==============================================================================

class Corpus:
    """A corpus of various FoLiA documents. Yields a Document on each iteration. Suitable for sequential processing."""

    def __init__(self,corpusdir, extension = 'xml', restrict_to_collection = "", conditionf=lambda x: True, ignoreerrors=False, **kwargs):
        self.corpusdir = corpusdir
        self.extension = extension
        self.restrict_to_collection = restrict_to_collection
        self.conditionf = conditionf
        self.ignoreerrors = ignoreerrors
        self.kwargs = kwargs

    def __iter__(self):
        if not self.restrict_to_collection:
            for f in glob.glob(os.path.join(self.corpusdir,"*." + self.extension)):
                if self.conditionf(f):
                    try:
                        yield Document(file=f, **self.kwargs )
                    except Exception as e: #pylint: disable=broad-except
                        print("Error, unable to parse " + f + ": " + e.__class__.__name__  + " - " + str(e),file=stderr)
                        if not self.ignoreerrors:
                            raise
        for d in glob.glob(os.path.join(self.corpusdir,"*")):
            if (not self.restrict_to_collection or self.restrict_to_collection == os.path.basename(d)) and (os.path.isdir(d)):
                for f in glob.glob(os.path.join(d ,"*." + self.extension)):
                    if self.conditionf(f):
                        try:
                            yield Document(file=f, **self.kwargs)
                        except Exception as e: #pylint: disable=broad-except
                            print("Error, unable to parse " + f + ": " + e.__class__.__name__  + " - " + str(e),file=stderr)
                            if not self.ignoreerrors:
                                raise


class CorpusFiles(Corpus):
    """A corpus of various FoLiA documents. Yields the filenames on each iteration."""

    def __iter__(self):
        if not self.restrict_to_collection:
            for f in glob.glob(os.path.join(self.corpusdir,"*." + self.extension)):
                if self.conditionf(f):
                    try:
                        yield f
                    except Exception as e: #pylint: disable=broad-except
                        print("Error, unable to parse " + f+ ": " + e.__class__.__name__  + " - " + str(e),file=stderr)
                        if not self.ignoreerrors:
                            raise
        for d in glob.glob(os.path.join(self.corpusdir,"*")):
            if (not self.restrict_to_collection or self.restrict_to_collection == os.path.basename(d)) and (os.path.isdir(d)):
                for f in glob.glob(os.path.join(d, "*." + self.extension)):
                    if self.conditionf(f):
                        try:
                            yield f
                        except Exception as e: #pylint: disable=broad-except
                            print("Error, unable to parse " + f+ ": " + e.__class__.__name__  + " - " + str(e),file=stderr)
                            if not self.ignoreerrors:
                                raise





class CorpusProcessor(object):
    """Processes a corpus of various FoLiA documents using a parallel processing. Calls a user-defined function with the three-tuple (filename, args, kwargs) for each file in the corpus. The user-defined function is itself responsible for instantiating a FoLiA document! args and kwargs, as received by the custom function, are set through the run() method, which yields the result of the custom function on each iteration."""

    def __init__(self,corpusdir, function, threads = None, extension = 'xml', restrict_to_collection = "", conditionf=lambda x: True, maxtasksperchild=100, preindex = False, ordered=True, chunksize = 1):
        self.function = function
        self.threads = threads #If set to None, will use all available cores by default
        self.corpusdir = corpusdir
        self.extension = extension
        self.restrict_to_collection = restrict_to_collection
        self.conditionf = conditionf
        self.ignoreerrors = True
        self.maxtasksperchild = maxtasksperchild #This should never be set too high due to lxml leaking memory!!!
        self.preindex = preindex
        self.ordered = ordered
        self.chunksize = chunksize
        if preindex:
            self.index = list(CorpusFiles(self.corpusdir, self.extension, self.restrict_to_collection, self.conditionf, True))
            self.index.sort()


    def __len__(self):
        if self.preindex:
            return len(self.index)
        else:
            return ValueError("Can only retrieve length if instantiated with preindex=True")

    def execute(self):
        for _ in self.run():
            pass

    def run(self, *args, **kwargs):
        if not self.preindex:
            self.index = CorpusFiles(self.corpusdir, self.extension, self.restrict_to_collection, self.conditionf, True) #generator
        pool = multiprocessing.Pool(self.threads,None,None, self.maxtasksperchild)
        if self.ordered:
            return pool.imap( self.function,  ( (filename, args, kwargs) for filename in self.index), self.chunksize)
        else:
            return pool.imap_unordered( self.function,  ( (filename, args, kwargs) for filename in self.index), self.chunksize)
        #pool.close()



    def __iter__(self):
        return self.run()







def relaxng_declarations():
    for key in vars(AnnotationType).keys():
        if key[0] != '_':
            yield RXE.element(
                RXE.optional( RXE.attribute(RXE.data(type='string',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='set') ),
                RXE.optional( RXE.attribute(RXE.data(type='string',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='alias') ),
                RXE.optional( RXE.attribute(RXE.data(type='string',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='annotator') ), #pre-provenance, FoLiA <2.0
                RXE.optional( RXE.attribute(RXE.data(type='string',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='annotatortype') ), #pre-provenance, FoLiA <2.0
                RXE.optional( RXE.attribute(RXE.data(type='dateTime',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='datetime') ), #pre-provenance, FoLiA <2.0
                RXE.optional( RXE.attribute(RXE.data(type='string',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='groupannotations') ), #(this overstretches, only valid on span elements),
                RXE.optional( RXE.attribute(RXE.data(type='string',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='format') ),
                RXE.zeroOrMore(
                    RXE.element(RXE.attribute(RXE.data(type='IDREF',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name="processor"), name="annotator")
                )
                , name=key.lower() + '-annotation')
            #backward compatibility with FoLiA 1.5
            if key.lower() in OLDTAGS_REVERSE:
                yield RXE.element(
                    RXE.optional( RXE.attribute(RXE.data(type='string',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='set') ),
                    RXE.optional( RXE.attribute(RXE.data(type='string',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='alias') ),
                    RXE.optional( RXE.attribute(RXE.data(type='string',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='annotator') ), #pre-provenance, FoLiA <2.0
                    RXE.optional( RXE.attribute(RXE.data(type='string',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='annotatortype') ), #pre-provenance, FoLiA <2.0
                    RXE.optional( RXE.attribute(RXE.data(type='dateTime',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='datetime') ), #pre-provenance, FoLiA <2.0
                    RXE.optional( RXE.attribute(RXE.data(type='string',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='format') ),
                    RXE.zeroOrMore(
                        RXE.element(RXE.attribute(RXE.data(type='IDREF',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name="processor"), name="annotator")
                    )
                    , name=OLDTAGS_REVERSE[key.lower()] + '-annotation')

def relaxng(filename=None):
    """Generates a RelaxNG Schema for FoLiA. Optionally saves it to file.

    Args:
        filename (str): Save the schema to the following filename

    Returns:
        lxml.ElementTree: The schema
    """
    #TODO: Generate documentation INSIDE the RelaxNG (I did something similar for CLAM XML) (relates to #43)
    #TODO: Add data types #27
    grammar = RXE.grammar( RXE.start( RXE.element( #FoLiA
                RXE.attribute(name='id',ns="http://www.w3.org/XML/1998/namespace"),
                RXE.attribute(name='version'),
                RXE.optional( RXE.attribute(name='generator') ),
                RXE.optional( RXE.attribute(name='form') ),
                RXE.element( #metadata
                    RXE.optional(RXE.attribute(name='type')),
                    RXE.optional(RXE.attribute(name='src')),
                    RXE.element( RXE.zeroOrMore( RXE.choice( *relaxng_declarations() ) ) ,name='annotations'),
                    RXE.optional(RXE.element( RXE.zeroOrMore( RXE.ref(name="processor")) ,name='provenance')),
                    RXE.zeroOrMore(
                        RXE.element(RXE.attribute(name='id'), RXE.text(), name='meta'),
                    ),
                    RXE.zeroOrMore(
                        RXE.ref(name="foreign-data"),
                    ),
                    RXE.zeroOrMore(
                        RXE.element( #submetadata
                            RXE.attribute(name='id',ns="http://www.w3.org/XML/1998/namespace"),
                            RXE.optional(RXE.attribute(name='type')),
                            RXE.optional(RXE.attribute(name='src')),
                            RXE.zeroOrMore(
                                RXE.element(RXE.attribute(name='id'), RXE.text(), name='meta'),
                            ),
                            RXE.zeroOrMore(
                                RXE.ref(name="foreign-data"),
                            ),
                            name="submetadata"
                        )
                    ),
                    #RXE.optional(
                    #    RXE.ref(name='METATRANSCRIPT')
                    #),
                    name='metadata',
                    #ns=NSFOLIA,
                ),
                RXE.interleave(
                    RXE.zeroOrMore(
                        RXE.ref(name='text'),
                    ),
                    RXE.zeroOrMore(
                        RXE.ref(name='speech'),
                    ),
                ),
                name='FoLiA',
                ns = NSFOLIA
            ) ),
            #definitions needed for ForeignData (allow any content) - see http://www.microhowto.info/howto/match_arbitrary_content_using_relax_ng.html
            RXE.define( RXE.interleave(RXE.zeroOrMore(RXE.ref(name="any_element")),RXE.text()), name="any_content"),
            RXE.define( RXE.element(RXE.anyName(), RXE.zeroOrMore(RXE.ref(name="any_attribute")), RXE.zeroOrMore(RXE.ref(name="any_content"))), name="any_element"),
            RXE.define( RXE.attribute(RXE.anyName()), name="any_attribute"),
            #Definition for allowing alien-namespace attributes on any element
            RXE.define( RXE.zeroOrMore(RXE.attribute(RXE.anyName(getattr(RXE,'except')(RXE.nsName(),RXE.nsName(ns=""),RXE.nsName(ns="http://www.w3.org/XML/1998/namespace"),RXE.nsName(ns="http://www.w3.org/1999/xlink"))))), name="allow_foreign_attributes"),
            #Definition for processors (provenance)
            RXE.define(
                RXE.element(
                    RXE.attribute(RXE.data(type='ID',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='id',ns="http://www.w3.org/XML/1998/namespace"),
                    RXE.optional(RXE.attribute(RXE.data(type='string',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='name')),
                    RXE.optional(RXE.attribute(RXE.data(type='string',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='type')),
                    RXE.optional(RXE.attribute(RXE.data(type='string',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='version')),
                    RXE.optional(RXE.attribute(RXE.data(type='string',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='document_version')),
                    RXE.optional(RXE.attribute(RXE.data(type='string',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='command')),
                    RXE.optional(RXE.attribute(RXE.data(type='string',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='host')),
                    RXE.optional(RXE.attribute(RXE.data(type='string',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='user')),
                    RXE.optional(RXE.attribute(RXE.data(type='string',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='folia_version')),
                    RXE.optional(RXE.attribute(RXE.data(type='string',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='src')),
                    RXE.optional(RXE.attribute(RXE.data(type='string',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='format')),
                    RXE.optional(RXE.attribute(RXE.data(type='dateTime',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='begindatetime')),
                    RXE.optional(RXE.attribute(RXE.data(type='dateTime',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='enddatetime')),
                    RXE.interleave(
                        RXE.zeroOrMore(RXE.element(RXE.attribute(name='id'), RXE.text(), name='meta')),
                        RXE.zeroOrMore(RXE.ref(name="processor")),
                    )
                , name="processor")
            , name="processor", ns=NSFOLIA),
            #grammar keyword args:
            datatypeLibrary="http://www.w3.org/2001/XMLSchema-datatypes",
            ) #end grammar, rest will be appended dynamically below

    done = {}
    for c in globals().values():
        if 'relaxng' in dir(c):
            if c.relaxng and c.XMLTAG and not c.XMLTAG in done:
                done[c.XMLTAG] = True
                definition = c.relaxng()
                grammar.append( definition )
                if c.XMLTAG in OLDTAGS_REVERSE: #backward-compatibility hack to allow renamed elements
                    oldtag = OLDTAGS_REVERSE[c.XMLTAG]
                    definition_alias = c.relaxng()
                    definition_alias.set('name',oldtag)
                    definition_alias[0].set('name',oldtag)
                    grammar.append( definition_alias )

    #for e in relaxng_imdi():
    #    grammar.append(e)
    if filename:
        f = io.open(filename,'wb')
        f.write( ElementTree.tostring(relaxng(),pretty_print=True).replace(b"</define>",b"</define>\n\n") )
        f.close()

    return grammar



def findwords(doc, worditerator, *args, **kwargs):
    if 'leftcontext' in kwargs:
        leftcontext = int(kwargs['leftcontext'])
        del kwargs['leftcontext']
    else:
        leftcontext = 0
    if 'rightcontext' in kwargs:
        rightcontext =  int(kwargs['rightcontext'])
        del kwargs['rightcontext']
    else:
        rightcontext = 0
    if 'maxgapsize' in kwargs:
        maxgapsize = int(kwargs['maxgapsize'])
        del kwargs['maxgapsize']
    else:
        maxgapsize = 10
    for key in kwargs.keys():
        raise Exception("Unknown keyword parameter: " + key)

    matchcursor = 0

    #shortcut for when no Pattern is passed, make one on the fly
    if len(args) == 1 and not isinstance(args[0], Pattern):
        if not isinstance(args[0], list) and not isinstance(args[0], tuple):
            args[0] = [args[0]]
        args[0] = Pattern(*args[0])



    unsetwildcards = False
    variablewildcards = None
    prevsize = -1
    #sanity check
    for i, pattern in enumerate(args):
        if not isinstance(pattern, Pattern):
            raise TypeError("You must pass instances of Sequence to findwords")
        if prevsize > -1 and len(pattern) != prevsize:
            raise Exception("If multiple patterns are provided, they must all have the same length!")
        if pattern.variablesize():
            if not variablewildcards and i > 0:
                unsetwildcards = True
            else:
                if variablewildcards and pattern.variablewildcards() != variablewildcards:
                    raise Exception("If multiple patterns are provided with variable wildcards, then these wildcards must all be in the same positions!")
                variablewildcards = pattern.variablewildcards()
        elif variablewildcards:
            unsetwildcards = True
        prevsize = len(pattern)

    if unsetwildcards:
        #one pattern determines a fixed length whilst others are variable, rewrite all to fixed length
        #converting multi-span * wildcards into single-span 'True' wildcards
        for pattern in args:
            if pattern.variablesize():
                pattern.sequence = [ True if x == '*' else x for x in pattern.sequence ]

    if variablewildcards: #pylint: disable=too-many-nested-blocks
        #one or more items have a * wildcard, which may span multiple tokens. Resolve this to a wider range of simpler patterns

        #we're not commited to a particular size, expand to various ones
        for size in range(len(variablewildcards), maxgapsize+1):
            for distribution in sum_to_n(size, len(variablewildcards)): #gap distributions, (amount) of 'True' wildcards
                patterns = []
                for pattern in args:
                    if pattern.variablesize():
                        patterns += list(pattern.resolve(size,distribution))
                    else:
                        patterns.append( pattern )
                for match in findwords(doc, worditerator,*patterns, **{'leftcontext':leftcontext,'rightcontext':rightcontext}):
                    yield match

    else:
        patterns = args
        buffers = []

        for word in worditerator():
            buffers.append( [] ) #Add a new empty buffer for every word
            match = [None] * len(buffers)
            for pattern in patterns:
                #find value to match against
                if not pattern.matchannotation:
                    value = word.text()
                else:
                    if pattern.matchannotationset:
                        items = list(word.select(pattern.matchannotation, pattern.matchannotationset, True, [Original, Suggestion, Alternative]))
                    else:
                        try:
                            set = doc.defaultset(pattern.matchannotation.ANNOTATIONTYPE)
                            items = list(word.select(pattern.matchannotation, set, True, [Original, Suggestion, Alternative] ))
                        except (NoSuchAnnotation, KeyError):
                            continue
                    if len(items) == 1:
                        value = items[0].cls
                    else:
                        continue

                if not pattern.casesensitive:
                    value = value.lower()


                for i, buffer in enumerate(buffers):
                    if match[i] is False:
                        continue
                    matchcursor = len(buffer)
                    match[i] = (value == pattern.sequence[matchcursor] or pattern.sequence[matchcursor] is True or (isinstance(pattern.sequence[matchcursor], tuple) and value in pattern.sequence[matchcursor]))


            for buffer, matches in list(zip(buffers, match)):
                if matches:
                    buffer.append(word) #add the word
                    if len(buffer) == len(pattern.sequence):
                        yield buffer[0].leftcontext(leftcontext) + buffer + buffer[-1].rightcontext(rightcontext)
                        buffers.remove(buffer)
                else:
                    buffers.remove(buffer) #remove buffer

class Reader(object):
    """Streaming FoLiA reader.

    The reader allows you to read a FoLiA Document without holding the whole tree structure in memory. The document will be read and the elements you seek returned as they are found. If you are querying a corpus of large FoLiA documents for a specific structure, then it is strongly recommend to use the Reader rather than the standard Document!"""


    def __init__(self, filename, target, *args, **kwargs):
        """Read a FoLiA document in a streaming fashion. You select a specific target element and all occurrences of this element, including all  contents (so all elements within), will be returned.

        Arguments:

            * ``filename``: The filename of the document to read
            * ``target``: The FoLiA element(s) you want to read (with everything contained in its scope). Passed as a class. For example: ``folia.Sentence``, or a tuple of multiple element classes. Can also be set to ``None`` to return all elements, but that would load the full tree structure into memory.

        """

        self.target = target
        if not (isinstance(self.target, tuple) or isinstance(self.target, list) or issubclass(self.target, AbstractElement)):
            raise ValueError("Target must be subclass of FoLiA element")
        if 'bypassleak' in kwargs:
            self.bypassleak = False
        self.stream = io.open(filename,'rb')
        self.initdoc()
        if self.doc.FOLIA1:
            self.doc.declare(AnnotationType.PHON)
        if 'declare' in kwargs:
            for item in kwargs['declare']:
                if isinstance(item, (list,tuple)):
                    self.doc.declare(item[0], item[1])
                else:
                    self.doc.declare(item)
        else:
            #declare text by default (set declare=[] if you don't want this)
            self.doc.declare(AnnotationType.TEXT)


    def findwords(self, *args, **kwargs):
        self.target = Word
        for x in findwords(self.doc,self.__iter__,*args,**kwargs):
            yield x

    def initdoc(self):
        self.doc = None
        metadata = False
        for action, node in ElementTree.iterparse(self.stream, events=("start","end")):
            if action == "start" and node.tag == "{" + NSFOLIA + "}FoLiA":
                if '{http://www.w3.org/XML/1998/namespace}id' in node.attrib:
                    id = node.attrib['{http://www.w3.org/XML/1998/namespace}id']
                self.doc = Document(id=id)
                if 'version' in node.attrib:
                    self.doc.version = node.attrib['version']
            if action == "end" and node.tag == "{" + NSFOLIA + "}metadata":
                if not self.doc:
                    raise MalformedXMLError("Metadata found, but no document? Impossible")
                metadata = True
                self.doc.parsemetadata(node)
                break
        self.doc.checkreferences = False


        if not self.doc:
            raise MalformedXMLError("No FoLiA Document found!")
        elif not metadata:
            raise MalformedXMLError("No metadata found!")

        self.stream.seek(0)


    def __iter__(self):
        """Iterating over a Reader instance will cause the FoLiA document to be read. This is a generator yielding instances of the object you specified"""

        if not isinstance(self.target, tuple) or isinstance(self.target,list):
            target = "{" + NSFOLIA + "}" + self.target.XMLTAG
            Class = self.target
            multitargets = False
        else:
            multitargets = True

        for action, node in ElementTree.iterparse(self.stream, events=("end",), tag=target):
            if not multitargets or (multitargets and node.tag.startswith('{' + NSFOLIA + '}')):
                if not multitargets: Class = XML2CLASS[node.tag[nslen:]]
                if not multitargets or (multitargets and Class in self.targets):
                    element = Class.parsexml(node, self.doc)
                    node.clear() #clean up children
                    # Also eliminate now-empty references from the root node to
                    # elem (http://www.ibm.com/developerworks/xml/library/x-hiperfparse/)
                    #for ancestor in node.xpath('ancestor-or-self::*'):
                    while node.getprevious() is not None:
                        del node.getparent()[0]  # clean up preceding siblings
                    yield element

    def __del__(self):
        self.stream.close()

def isncname(name):
    #not entirely according to specs http://www.w3.org/TR/REC-xml/#NT-Name , but simplified:
    for i, c in enumerate(name):
        if i == 0:
            if not c.isalpha() and c != '_':
                raise ValueError('Invalid XML NCName identifier: ' + name + ' (at position ' + str(i+1)+')')
        else:
            if not c.isalnum() and not (c in ['-','_','.']):
                raise ValueError('Invalid XML NCName identifier: ' + name + ' (at position ' + str(i+1)+')')
    return True

def makencname(name):
    ncname = ""
    for i, c in enumerate(name):
        if i == 0:
            if not c.isalpha() and c != '_':
                ncname += "I"
        if c.isalnum() or c in ('-','_','.'):
            ncname += c
    if not ncname:
        raise ValueError("Unable to convert '" + str(name) + "' to a valid XML NCName")
    return ncname



def annotationtypeisspan(annotationtype):
    return issubclass(XML2CLASS[ANNOTATIONTYPE2XML[annotationtype]], AbstractSpanAnnotation)

def validate(filename,schema=None,deep=False):
    if not os.path.exists(filename):
        raise IOError("No such file")

    try:
        try:
            doc = ElementTree.parse(filename, ElementTree.XMLParser(collect_ids=False, huge_tree=True) )
        except TypeError:
            doc = ElementTree.parse(filename, ElementTree.XMLParser() ) #older lxml, may leak!
    except:
        raise MalformedXMLError("Malformed XML!")

    #See if there's inline IMDI and strip it off prior to validation (validator doesn't do IMDI)
    m = doc.xpath('//folia:metadata', namespaces={'f': 'http://ilk.uvt.nl/folia','folia': 'http://ilk.uvt.nl/folia' })
    if m:
        metadata = m[0]
        m = metadata.find('{http://www.mpi.nl/IMDI/Schema/IMDI}METATRANSCRIPT')
        if m is not None:
            metadata.remove(m)

    if not schema:
        schema = ElementTree.RelaxNG(relaxng())

    try:
        schema.assertValid(doc) #will raise exceptions
    except Exception as e:
        for error in schema.error_log:
            print("Error on line " + str(error.line) + ": " + error.message, file=sys.stderr)
        raise e


    if deep:
        doc = Document(tree=doc, deepvalidation=True)

#================================= FOLIA SPECIFICATION ==========================================================

#foliaspec:header
#This file was last updated according to the FoLiA specification for version 2.5.3 on 2023-09-09 22:13:59, using foliaspec.py
#Code blocks after a foliaspec comment (until the next newline) are automatically generated. **DO NOT EDIT THOSE** and **DO NOT REMOVE ANY FOLIASPEC COMMENTS** !!!

#foliaspec:structurescope:STRUCTURESCOPE
#Structure scope above the sentence level, used by next() and previous() methods
STRUCTURESCOPE = (Sentence, Paragraph, Division, ListItem, Text, Event, Caption, Head,)

#foliaspec:annotationtype_xml_map
#A mapping from annotation types to xml tags (strings)
ANNOTATIONTYPE2XML = {
    AnnotationType.ALTERNATIVE:  "alt" ,
    AnnotationType.CHUNKING:  "chunk" ,
    AnnotationType.COMMENT:  "comment" ,
    AnnotationType.RAWCONTENT:  "content" ,
    AnnotationType.COREFERENCE:  "coreferencechain" ,
    AnnotationType.CORRECTION:  "correction" ,
    AnnotationType.DEFINITION:  "def" ,
    AnnotationType.DEPENDENCY:  "dependency" ,
    AnnotationType.DESCRIPTION:  "desc" ,
    AnnotationType.DIVISION:  "div" ,
    AnnotationType.DOMAIN:  "domain" ,
    AnnotationType.ENTITY:  "entity" ,
    AnnotationType.ENTRY:  "entry" ,
    AnnotationType.ERRORDETECTION:  "errordetection" ,
    AnnotationType.ETYMOLOGY:  "etymology" ,
    AnnotationType.EVENT:  "event" ,
    AnnotationType.EXAMPLE:  "ex" ,
    AnnotationType.EXTERNAL:  "external" ,
    AnnotationType.FIGURE:  "figure" ,
    AnnotationType.GAP:  "gap" ,
    AnnotationType.HEAD:  "head" ,
    AnnotationType.HIDDENTOKEN:  "hiddenw" ,
    AnnotationType.HYPHENATION:  "t-hbr" ,
    AnnotationType.LANG:  "lang" ,
    AnnotationType.LEMMA:  "lemma" ,
    AnnotationType.LINEBREAK:  "br" ,
    AnnotationType.LIST:  "list" ,
    AnnotationType.METRIC:  "metric" ,
    AnnotationType.MODALITY:  "modality" ,
    AnnotationType.MORPHOLOGICAL:  "morpheme" ,
    AnnotationType.NOTE:  "note" ,
    AnnotationType.OBSERVATION:  "observation" ,
    AnnotationType.PARAGRAPH:  "p" ,
    AnnotationType.PART:  "part" ,
    AnnotationType.PHON:  "ph" ,
    AnnotationType.PHONOLOGICAL:  "phoneme" ,
    AnnotationType.POS:  "pos" ,
    AnnotationType.PREDICATE:  "predicate" ,
    AnnotationType.QUOTE:  "quote" ,
    AnnotationType.REFERENCE:  "ref" ,
    AnnotationType.RELATION:  "relation" ,
    AnnotationType.SEMROLE:  "semrole" ,
    AnnotationType.SENSE:  "sense" ,
    AnnotationType.SENTENCE:  "s" ,
    AnnotationType.SENTIMENT:  "sentiment" ,
    AnnotationType.SPANRELATION:  "spanrelation" ,
    AnnotationType.STATEMENT:  "statement" ,
    AnnotationType.STRING:  "str" ,
    AnnotationType.SUBJECTIVITY:  "subjectivity" ,
    AnnotationType.SYNTAX:  "su" ,
    AnnotationType.TABLE:  "table" ,
    AnnotationType.TERM:  "term" ,
    AnnotationType.TEXT:  "t" ,
    AnnotationType.HSPACE:  "t-hspace" ,
    AnnotationType.STYLE:  "t-style" ,
    AnnotationType.TIMESEGMENT:  "timesegment" ,
    AnnotationType.UTTERANCE:  "utt" ,
    AnnotationType.WHITESPACE:  "whitespace" ,
    AnnotationType.TOKEN:  "w" ,
}

#foliaspec:string_class_map
XML2CLASS = {
    "alt": Alternative,
    "altlayers": AlternativeLayers,
    "caption": Caption,
    "cell": Cell,
    "chunk": Chunk,
    "chunking": ChunkingLayer,
    "comment": Comment,
    "content": Content,
    "coreferencechain": CoreferenceChain,
    "coreferences": CoreferenceLayer,
    "coreferencelink": CoreferenceLink,
    "correction": Correction,
    "cue": Cue,
    "current": Current,
    "def": Definition,
    "dependencies": DependenciesLayer,
    "dependency": Dependency,
    "dep": DependencyDependent,
    "desc": Description,
    "div": Division,
    "domain": DomainAnnotation,
    "entities": EntitiesLayer,
    "entity": Entity,
    "entry": Entry,
    "errordetection": ErrorDetection,
    "etymology": EtymologyAnnotation,
    "event": Event,
    "ex": Example,
    "external": External,
    "feat": Feature,
    "figure": Figure,
    "foreign-data": ForeignData,
    "gap": Gap,
    "head": Head,
    "hd": Headspan,
    "hiddenw": Hiddenword,
    "t-hbr": Hyphbreak,
    "label": Label,
    "lang": LangAnnotation,
    "lemma": LemmaAnnotation,
    "br": Linebreak,
    "xref": LinkReference,
    "list": List,
    "item": ListItem,
    "metric": Metric,
    "modalities": ModalitiesLayer,
    "modality": Modality,
    "morpheme": Morpheme,
    "morphology": MorphologyLayer,
    "new": New,
    "note": Note,
    "observation": Observation,
    "observations": ObservationLayer,
    "original": Original,
    "p": Paragraph,
    "part": Part,
    "ph": PhonContent,
    "phoneme": Phoneme,
    "phonology": PhonologyLayer,
    "pos": PosAnnotation,
    "predicate": Predicate,
    "quote": Quote,
    "ref": Reference,
    "relation": Relation,
    "row": Row,
    "scope": Scope,
    "semrole": SemanticRole,
    "semroles": SemanticRolesLayer,
    "sense": SenseAnnotation,
    "s": Sentence,
    "sentiment": Sentiment,
    "sentiments": SentimentLayer,
    "source": Source,
    "spanrelation": SpanRelation,
    "spanrelations": SpanRelationLayer,
    "speech": Speech,
    "statement": Statement,
    "statements": StatementLayer,
    "rel": StatementRelation,
    "str": String,
    "subjectivity": SubjectivityAnnotation,
    "suggestion": Suggestion,
    "su": SyntacticUnit,
    "syntax": SyntaxLayer,
    "table": Table,
    "tablehead": TableHead,
    "target": Target,
    "term": Term,
    "text": Text,
    "t": TextContent,
    "t-correction": TextMarkupCorrection,
    "t-error": TextMarkupError,
    "t-gap": TextMarkupGap,
    "t-hspace": TextMarkupHSpace,
    "t-lang": TextMarkupLanguage,
    "t-ref": TextMarkupReference,
    "t-str": TextMarkupString,
    "t-style": TextMarkupStyle,
    "t-whitespace": TextMarkupWhitespace,
    "timesegment": TimeSegment,
    "timing": TimingLayer,
    "utt": Utterance,
    "whitespace": Whitespace,
    "w": Word,
    "wref": WordReference,
}


XML2CLASS['listitem'] = ListItem #backward compatibility for erroneous old FoLiA versions (XML tag is 'item' now, consistent with manual)

#foliaspec:oldtags_map
OLDTAGS = {
  "alignment": "relation",  "aref": "xref",  "complexalignment": "spanrelation",  "complexalignments": "spanrelations",  "listitem": "item",}

OLDTAGS_REVERSE = { value: key for key, value in OLDTAGS.items() }

#foliaspec:annotationtype_layerclass_map
ANNOTATIONTYPE2LAYERCLASS = {
    AnnotationType.CHUNKING:  ChunkingLayer ,
    AnnotationType.COREFERENCE:  CoreferenceLayer ,
    AnnotationType.DEPENDENCY:  DependenciesLayer ,
    AnnotationType.ENTITY:  EntitiesLayer ,
    AnnotationType.MODALITY:  ModalitiesLayer ,
    AnnotationType.MORPHOLOGICAL:  MorphologyLayer ,
    AnnotationType.OBSERVATION:  ObservationLayer ,
    AnnotationType.PHONOLOGICAL:  PhonologyLayer ,
    AnnotationType.SEMROLE:  SemanticRolesLayer ,
    AnnotationType.SENTIMENT:  SentimentLayer ,
    AnnotationType.SPANRELATION:  SpanRelationLayer ,
    AnnotationType.STATEMENT:  StatementLayer ,
    AnnotationType.SYNTAX:  SyntaxLayer ,
    AnnotationType.TIMESEGMENT:  TimingLayer ,
    AnnotationType.PREDICATE:  SemanticRolesLayer
}

#foliaspec:wrefables
#Elements that act as words and can be referable from span annotations
wrefables = ( Word, Hiddenword, Morpheme, Phoneme,)

#adds the element True so it can be pastsed to select(ignore=) , which then gets intepreted as defualt_ignore | ignore_wrefables
ignore_wrefables = tuple([True] + list(wrefables))

#foliaspec:default_ignore
#Default ignore list for the select() method, do not descend into these
default_ignore = ( Original, Suggestion, Alternative, AlternativeLayers, ForeignData,)

#foliaspec:default_ignore_annotations
#Default ignore list for token annotation
default_ignore_annotations = ( Original, Suggestion, Alternative, AlternativeLayers, MorphologyLayer, PhonologyLayer,)

#foliaspec:default_ignore_structure
#Default ignore list for structure annotation
default_ignore_structure = ( Original, Suggestion, Alternative, AlternativeLayers, AbstractAnnotationLayer,)

#foliaspec:defaultproperties
#Default properties which all elements inherit
AbstractElement.ACCEPTED_DATA = (Description, Comment,)
AbstractElement.ANNOTATIONTYPE = None
AbstractElement.AUTH = True
AbstractElement.AUTO_GENERATE_ID = False
AbstractElement.HIDDEN = False
AbstractElement.IMPLICITSPACE = False
AbstractElement.OCCURRENCES = 0
AbstractElement.OCCURRENCES_PER_SET = 0
AbstractElement.OPTIONAL_ATTRIBS = None
AbstractElement.PHONCONTAINER = False
AbstractElement.PRIMARYELEMENT = True
AbstractElement.PRINTABLE = False
AbstractElement.REQUIRED_ATTRIBS = None
AbstractElement.REQUIRED_DATA = None
AbstractElement.SETONLY = False
AbstractElement.SPEAKABLE = False
AbstractElement.SUBSET = None
AbstractElement.TEXTCONTAINER = False
AbstractElement.TEXTDELIMITER = None
AbstractElement.WREFABLE = False
AbstractElement.XLINK = False
AbstractElement.XMLTAG = None

#foliaspec:setelementproperties
#Sets all element properties for all elements
#------ AbstractAnnotationLayer -------
AbstractAnnotationLayer.ACCEPTED_DATA = (Comment, Correction, Description, ForeignData,)
AbstractAnnotationLayer.OPTIONAL_ATTRIBS = (Attrib.ID, Attrib.TAG,)
AbstractAnnotationLayer.PRINTABLE = False
AbstractAnnotationLayer.SETONLY = True
AbstractAnnotationLayer.SPEAKABLE = False
#------ AbstractContentAnnotation -------
AbstractContentAnnotation.OCCURRENCES = 0
AbstractContentAnnotation.OPTIONAL_ATTRIBS = (Attrib.CLASS, Attrib.ANNOTATOR, Attrib.CONFIDENCE, Attrib.DATETIME, Attrib.METADATA, Attrib.TAG,)
AbstractContentAnnotation.REQUIRED_ATTRIBS = None
#------ AbstractCorrectionChild -------
AbstractCorrectionChild.ACCEPTED_DATA = (AbstractInlineAnnotation, AbstractSpanAnnotation, AbstractStructureElement, Comment, Correction, Description, ForeignData, Metric, PhonContent, String, TextContent,)
AbstractCorrectionChild.OPTIONAL_ATTRIBS = (Attrib.ID, Attrib.ANNOTATOR, Attrib.CONFIDENCE, Attrib.DATETIME, Attrib.N, Attrib.TAG,)
AbstractCorrectionChild.PRINTABLE = True
AbstractCorrectionChild.SPEAKABLE = True
AbstractCorrectionChild.TEXTDELIMITER = None
#------ AbstractHigherOrderAnnotation -------
AbstractHigherOrderAnnotation.OPTIONAL_ATTRIBS = None
AbstractHigherOrderAnnotation.REQUIRED_ATTRIBS = None
#------ AbstractInlineAnnotation -------
AbstractInlineAnnotation.ACCEPTED_DATA = (Comment, Description, Feature, ForeignData, Metric,)
AbstractInlineAnnotation.OCCURRENCES_PER_SET = 1
AbstractInlineAnnotation.OPTIONAL_ATTRIBS = (Attrib.ID, Attrib.CLASS, Attrib.ANNOTATOR, Attrib.N, Attrib.CONFIDENCE, Attrib.DATETIME, Attrib.SRC, Attrib.BEGINTIME, Attrib.ENDTIME, Attrib.SPEAKER, Attrib.TEXTCLASS, Attrib.METADATA, Attrib.TAG,)
AbstractInlineAnnotation.REQUIRED_ATTRIBS = (Attrib.CLASS,)
#------ AbstractSpanAnnotation -------
AbstractSpanAnnotation.ACCEPTED_DATA = (AbstractInlineAnnotation, Comment, Description, ForeignData, LinkReference, Metric, Relation,)
AbstractSpanAnnotation.OPTIONAL_ATTRIBS = (Attrib.ID, Attrib.CLASS, Attrib.ANNOTATOR, Attrib.N, Attrib.CONFIDENCE, Attrib.DATETIME, Attrib.SRC, Attrib.BEGINTIME, Attrib.ENDTIME, Attrib.SPEAKER, Attrib.TEXTCLASS, Attrib.METADATA, Attrib.TAG,)
AbstractSpanAnnotation.PRINTABLE = True
AbstractSpanAnnotation.SPEAKABLE = True
#------ AbstractSpanRole -------
AbstractSpanRole.ACCEPTED_DATA = (AbstractInlineAnnotation, Comment, Description, Feature, ForeignData, LinkReference, Metric, Relation, WordReference,)
AbstractSpanRole.OPTIONAL_ATTRIBS = (Attrib.ID, Attrib.TAG,)
AbstractSpanRole.PRIMARYELEMENT = False
#------ AbstractStructureElement -------
AbstractStructureElement.ACCEPTED_DATA = (AbstractAnnotationLayer, Alternative, AlternativeLayers, Comment, Correction, Description, External, Feature, ForeignData, Metric, Part, Relation,)
AbstractStructureElement.AUTO_GENERATE_ID = True
AbstractStructureElement.OPTIONAL_ATTRIBS = (Attrib.ID, Attrib.CLASS, Attrib.ANNOTATOR, Attrib.N, Attrib.CONFIDENCE, Attrib.DATETIME, Attrib.SRC, Attrib.BEGINTIME, Attrib.ENDTIME, Attrib.SPEAKER, Attrib.METADATA, Attrib.SPACE, Attrib.TAG,)
AbstractStructureElement.PRINTABLE = True
AbstractStructureElement.REQUIRED_ATTRIBS = None
AbstractStructureElement.SPEAKABLE = True
AbstractStructureElement.TEXTDELIMITER = "\n\n"
#------ AbstractSubtokenAnnotation -------
AbstractSubtokenAnnotation.ACCEPTED_DATA = (AbstractAnnotationLayer, Alternative, AlternativeLayers, Comment, Correction, Description, Feature, ForeignData, Metric, Part, Relation,)
AbstractSubtokenAnnotation.AUTO_GENERATE_ID = True
AbstractSubtokenAnnotation.OPTIONAL_ATTRIBS = (Attrib.ID, Attrib.CLASS, Attrib.ANNOTATOR, Attrib.N, Attrib.CONFIDENCE, Attrib.DATETIME, Attrib.SRC, Attrib.BEGINTIME, Attrib.ENDTIME, Attrib.SPEAKER, Attrib.METADATA, Attrib.TAG,)
AbstractSubtokenAnnotation.PRINTABLE = True
AbstractSubtokenAnnotation.REQUIRED_ATTRIBS = None
AbstractSubtokenAnnotation.SPEAKABLE = True
AbstractSubtokenAnnotation.TEXTDELIMITER = "\n\n"
#------ AbstractTextMarkup -------
AbstractTextMarkup.ACCEPTED_DATA = (AbstractTextMarkup, Comment, Description, Feature, Linebreak,)
AbstractTextMarkup.OPTIONAL_ATTRIBS = (Attrib.ID, Attrib.CLASS, Attrib.ANNOTATOR, Attrib.N, Attrib.CONFIDENCE, Attrib.DATETIME, Attrib.SRC, Attrib.BEGINTIME, Attrib.ENDTIME, Attrib.SPEAKER, Attrib.METADATA, Attrib.TAG,)
AbstractTextMarkup.PRIMARYELEMENT = False
AbstractTextMarkup.PRINTABLE = True
AbstractTextMarkup.TEXTCONTAINER = True
AbstractTextMarkup.TEXTDELIMITER = ""
AbstractTextMarkup.XLINK = True
#------ ActorFeature -------
ActorFeature.SUBSET = "actor"
ActorFeature.XMLTAG = None
#------ Alternative -------
Alternative.ACCEPTED_DATA = (AbstractInlineAnnotation, Comment, Correction, Description, ForeignData, MorphologyLayer, PhonologyLayer,)
Alternative.ANNOTATIONTYPE = AnnotationType.ALTERNATIVE
Alternative.AUTH = False
Alternative.LABEL = "Alternative"
Alternative.OPTIONAL_ATTRIBS = (Attrib.ID, Attrib.ANNOTATOR, Attrib.N, Attrib.CONFIDENCE, Attrib.DATETIME, Attrib.SRC, Attrib.BEGINTIME, Attrib.ENDTIME, Attrib.SPEAKER, Attrib.METADATA, Attrib.TAG,)
Alternative.PRINTABLE = False
Alternative.REQUIRED_ATTRIBS = None
Alternative.SPEAKABLE = False
Alternative.XMLTAG = "alt"
#------ AlternativeLayers -------
AlternativeLayers.ACCEPTED_DATA = (AbstractAnnotationLayer, Comment, Description, ForeignData,)
AlternativeLayers.ANNOTATIONTYPE = AnnotationType.ALTERNATIVE
AlternativeLayers.AUTH = False
AlternativeLayers.LABEL = "Alternative Layers"
AlternativeLayers.OPTIONAL_ATTRIBS = (Attrib.ID, Attrib.ANNOTATOR, Attrib.N, Attrib.CONFIDENCE, Attrib.DATETIME, Attrib.SRC, Attrib.BEGINTIME, Attrib.ENDTIME, Attrib.SPEAKER, Attrib.METADATA, Attrib.TAG,)
AlternativeLayers.PRIMARYELEMENT = False
AlternativeLayers.PRINTABLE = False
AlternativeLayers.REQUIRED_ATTRIBS = None
AlternativeLayers.SPEAKABLE = False
AlternativeLayers.XMLTAG = "altlayers"
#------ BegindatetimeFeature -------
BegindatetimeFeature.SUBSET = "begindatetime"
BegindatetimeFeature.XMLTAG = None
#------ Caption -------
Caption.ACCEPTED_DATA = (AbstractAnnotationLayer, AbstractInlineAnnotation, Alternative, AlternativeLayers, Comment, Correction, Description, External, Feature, ForeignData, Gap, Linebreak, Metric, Paragraph, Part, PhonContent, Quote, Reference, Relation, Sentence, String, TextContent, Whitespace,)
Caption.LABEL = "Caption"
Caption.OCCURRENCES = 1
Caption.OPTIONAL_ATTRIBS = (Attrib.ID, Attrib.ANNOTATOR, Attrib.N, Attrib.CONFIDENCE, Attrib.DATETIME, Attrib.SRC, Attrib.BEGINTIME, Attrib.ENDTIME, Attrib.SPEAKER, Attrib.METADATA, Attrib.SPACE, Attrib.TAG,)
Caption.XMLTAG = "caption"
#------ Cell -------
Cell.ACCEPTED_DATA = (AbstractAnnotationLayer, AbstractInlineAnnotation, Alternative, AlternativeLayers, Comment, Correction, Description, Entry, Event, Example, External, Feature, Figure, ForeignData, Gap, Head, Hiddenword, Linebreak, List, Metric, Note, Paragraph, Part, Quote, Reference, Relation, Sentence, String, TextContent, Whitespace, Word,)
Cell.LABEL = "Cell"
Cell.OPTIONAL_ATTRIBS = (Attrib.ID, Attrib.ANNOTATOR, Attrib.N, Attrib.CONFIDENCE, Attrib.DATETIME, Attrib.SRC, Attrib.BEGINTIME, Attrib.ENDTIME, Attrib.SPEAKER, Attrib.METADATA, Attrib.SPACE, Attrib.TAG,)
Cell.TEXTDELIMITER = " | "
Cell.XMLTAG = "cell"
#------ Chunk -------
Chunk.ACCEPTED_DATA = (AbstractInlineAnnotation, Comment, Description, Feature, ForeignData, LinkReference, Metric, Relation, WordReference,)
Chunk.ANNOTATIONTYPE = AnnotationType.CHUNKING
Chunk.LABEL = "Chunk"
Chunk.XMLTAG = "chunk"
#------ ChunkingLayer -------
ChunkingLayer.ACCEPTED_DATA = (Chunk, Comment, Correction, Description, ForeignData,)
ChunkingLayer.ANNOTATIONTYPE = AnnotationType.CHUNKING
ChunkingLayer.PRIMARYELEMENT = False
ChunkingLayer.XMLTAG = "chunking"
#------ Comment -------
Comment.ANNOTATIONTYPE = AnnotationType.COMMENT
Comment.LABEL = "Comment"
Comment.OPTIONAL_ATTRIBS = (Attrib.ID, Attrib.ANNOTATOR, Attrib.CONFIDENCE, Attrib.DATETIME, Attrib.N, Attrib.METADATA, Attrib.TAG,)
Comment.PRINTABLE = False
Comment.XMLTAG = "comment"
#------ Content -------
Content.ANNOTATIONTYPE = AnnotationType.RAWCONTENT
Content.LABEL = "Raw Content"
Content.OCCURRENCES = 1
Content.PRINTABLE = True
Content.XMLTAG = "content"
#------ CoreferenceChain -------
CoreferenceChain.ACCEPTED_DATA = (AbstractInlineAnnotation, Comment, CoreferenceLink, Description, Feature, ForeignData, LinkReference, Metric, Relation,)
CoreferenceChain.ANNOTATIONTYPE = AnnotationType.COREFERENCE
CoreferenceChain.LABEL = "Coreference Chain"
CoreferenceChain.REQUIRED_DATA = (CoreferenceLink,)
CoreferenceChain.XMLTAG = "coreferencechain"
#------ CoreferenceLayer -------
CoreferenceLayer.ACCEPTED_DATA = (Comment, CoreferenceChain, Correction, Description, ForeignData,)
CoreferenceLayer.ANNOTATIONTYPE = AnnotationType.COREFERENCE
CoreferenceLayer.PRIMARYELEMENT = False
CoreferenceLayer.XMLTAG = "coreferences"
#------ CoreferenceLink -------
CoreferenceLink.ACCEPTED_DATA = (AbstractInlineAnnotation, Comment, Description, Feature, ForeignData, Headspan, LevelFeature, LinkReference, Metric, ModalityFeature, Relation, TimeFeature, WordReference,)
CoreferenceLink.ANNOTATIONTYPE = AnnotationType.COREFERENCE
CoreferenceLink.LABEL = "Coreference Link"
CoreferenceLink.PRIMARYELEMENT = False
CoreferenceLink.XMLTAG = "coreferencelink"
#------ Correction -------
Correction.ACCEPTED_DATA = (Comment, Current, Description, ErrorDetection, Feature, ForeignData, Metric, New, Original, Suggestion,)
Correction.ANNOTATIONTYPE = AnnotationType.CORRECTION
Correction.LABEL = "Correction"
Correction.OPTIONAL_ATTRIBS = (Attrib.ID, Attrib.CLASS, Attrib.ANNOTATOR, Attrib.N, Attrib.CONFIDENCE, Attrib.DATETIME, Attrib.SRC, Attrib.BEGINTIME, Attrib.ENDTIME, Attrib.SPEAKER, Attrib.METADATA, Attrib.TAG,)
Correction.PRINTABLE = True
Correction.SPEAKABLE = True
Correction.TEXTDELIMITER = None
Correction.XMLTAG = "correction"
#------ Cue -------
Cue.LABEL = "Cue"
Cue.OCCURRENCES = 1
Cue.PRIMARYELEMENT = False
Cue.XMLTAG = "cue"
#------ Current -------
Current.ANNOTATIONTYPE = AnnotationType.CORRECTION
Current.OCCURRENCES = 1
Current.OPTIONAL_ATTRIBS = (Attrib.TAG,)
Current.PRIMARYELEMENT = False
Current.XMLTAG = "current"
#------ Definition -------
Definition.ACCEPTED_DATA = (AbstractAnnotationLayer, AbstractInlineAnnotation, Alternative, AlternativeLayers, Comment, Correction, Description, External, Feature, Figure, ForeignData, Hiddenword, Linebreak, List, Metric, Paragraph, Part, PhonContent, Reference, Relation, Sentence, String, Table, TextContent, Utterance, Whitespace, Word,)
Definition.ANNOTATIONTYPE = AnnotationType.DEFINITION
Definition.LABEL = "Definition"
Definition.XMLTAG = "def"
#------ DependenciesLayer -------
DependenciesLayer.ACCEPTED_DATA = (Comment, Correction, Dependency, Description, ForeignData,)
DependenciesLayer.ANNOTATIONTYPE = AnnotationType.DEPENDENCY
DependenciesLayer.PRIMARYELEMENT = False
DependenciesLayer.XMLTAG = "dependencies"
#------ Dependency -------
Dependency.ACCEPTED_DATA = (AbstractInlineAnnotation, Comment, DependencyDependent, Description, Feature, ForeignData, Headspan, LinkReference, Metric, Relation,)
Dependency.ANNOTATIONTYPE = AnnotationType.DEPENDENCY
Dependency.LABEL = "Dependency"
Dependency.REQUIRED_DATA = (DependencyDependent, Headspan,)
Dependency.XMLTAG = "dependency"
#------ DependencyDependent -------
DependencyDependent.LABEL = "Dependent"
DependencyDependent.OCCURRENCES = 1
DependencyDependent.PRIMARYELEMENT = False
DependencyDependent.XMLTAG = "dep"
#------ Description -------
Description.ANNOTATIONTYPE = AnnotationType.DESCRIPTION
Description.LABEL = "Description"
Description.OCCURRENCES = 1
Description.OPTIONAL_ATTRIBS = (Attrib.ID, Attrib.ANNOTATOR, Attrib.CONFIDENCE, Attrib.DATETIME, Attrib.N, Attrib.METADATA, Attrib.TAG,)
Description.XMLTAG = "desc"
#------ Division -------
Division.ACCEPTED_DATA = (AbstractAnnotationLayer, AbstractInlineAnnotation, Alternative, AlternativeLayers, Comment, Correction, Description, Division, Entry, Event, Example, External, Feature, Figure, ForeignData, Gap, Head, Linebreak, List, Metric, Note, Paragraph, Part, PhonContent, Quote, Reference, Relation, Sentence, Table, TextContent, Utterance, Whitespace, Word,)
Division.ANNOTATIONTYPE = AnnotationType.DIVISION
Division.LABEL = "Division"
Division.TEXTDELIMITER = "\n\n\n"
Division.XMLTAG = "div"
#------ DomainAnnotation -------
DomainAnnotation.ANNOTATIONTYPE = AnnotationType.DOMAIN
DomainAnnotation.LABEL = "Domain"
DomainAnnotation.OCCURRENCES_PER_SET = 0
DomainAnnotation.XMLTAG = "domain"
#------ EnddatetimeFeature -------
EnddatetimeFeature.SUBSET = "enddatetime"
EnddatetimeFeature.XMLTAG = None
#------ EntitiesLayer -------
EntitiesLayer.ACCEPTED_DATA = (Comment, Correction, Description, Entity, ForeignData,)
EntitiesLayer.ANNOTATIONTYPE = AnnotationType.ENTITY
EntitiesLayer.PRIMARYELEMENT = False
EntitiesLayer.XMLTAG = "entities"
#------ Entity -------
Entity.ACCEPTED_DATA = (AbstractInlineAnnotation, Comment, Description, Feature, ForeignData, LinkReference, Metric, Relation, WordReference,)
Entity.ANNOTATIONTYPE = AnnotationType.ENTITY
Entity.LABEL = "Entity"
Entity.XMLTAG = "entity"
#------ Entry -------
Entry.ACCEPTED_DATA = (AbstractAnnotationLayer, Alternative, AlternativeLayers, Comment, Correction, Definition, Description, Example, External, Feature, ForeignData, Metric, Part, Relation, String, Term, TextContent,)
Entry.ANNOTATIONTYPE = AnnotationType.ENTRY
Entry.LABEL = "Entry"
Entry.XMLTAG = "entry"
#------ ErrorDetection -------
ErrorDetection.ANNOTATIONTYPE = AnnotationType.ERRORDETECTION
ErrorDetection.LABEL = "Error Detection"
ErrorDetection.OCCURRENCES_PER_SET = 0
ErrorDetection.XMLTAG = "errordetection"
#------ EtymologyAnnotation -------
EtymologyAnnotation.ANNOTATIONTYPE = AnnotationType.ETYMOLOGY
EtymologyAnnotation.LABEL = "Etymology"
EtymologyAnnotation.XMLTAG = "etymology"
#------ Event -------
Event.ACCEPTED_DATA = (AbstractAnnotationLayer, AbstractInlineAnnotation, ActorFeature, Alternative, AlternativeLayers, BegindatetimeFeature, Comment, Correction, Description, Division, EnddatetimeFeature, Entry, Event, Example, External, Feature, Figure, ForeignData, Gap, Head, Hiddenword, Linebreak, List, Metric, Note, Paragraph, Part, PhonContent, Quote, Reference, Relation, Sentence, String, Table, TextContent, Utterance, Whitespace, Word,)
Event.ANNOTATIONTYPE = AnnotationType.EVENT
Event.LABEL = "Event"
Event.XMLTAG = "event"
#------ Example -------
Example.ACCEPTED_DATA = (AbstractAnnotationLayer, AbstractInlineAnnotation, Alternative, AlternativeLayers, Comment, Correction, Description, External, Feature, Figure, ForeignData, Hiddenword, Linebreak, List, Metric, Paragraph, Part, PhonContent, Reference, Relation, Sentence, String, Table, TextContent, Utterance, Whitespace, Word,)
Example.ANNOTATIONTYPE = AnnotationType.EXAMPLE
Example.LABEL = "Example"
Example.XMLTAG = "ex"
#------ External -------
External.ACCEPTED_DATA = (Comment, Description,)
External.ANNOTATIONTYPE = AnnotationType.EXTERNAL
External.LABEL = "External"
External.OPTIONAL_ATTRIBS = (Attrib.ID, Attrib.ANNOTATOR, Attrib.CONFIDENCE, Attrib.DATETIME, Attrib.N, Attrib.METADATA, Attrib.BEGINTIME, Attrib.ENDTIME, Attrib.TAG,)
External.PRINTABLE = True
External.REQUIRED_ATTRIBS = (Attrib.SRC,)
External.SPEAKABLE = True
External.XMLTAG = "external"
#------ Feature -------
Feature.LABEL = "Feature"
Feature.XMLTAG = "feat"
#------ Figure -------
Figure.ACCEPTED_DATA = (AbstractAnnotationLayer, Alternative, AlternativeLayers, Caption, Comment, Correction, Description, External, Feature, ForeignData, Linebreak, Metric, Part, Relation, String, TextContent,)
Figure.ANNOTATIONTYPE = AnnotationType.FIGURE
Figure.LABEL = "Figure"
Figure.SPEAKABLE = False
Figure.TEXTDELIMITER = "\n\n"
Figure.XMLTAG = "figure"
#------ FontFeature -------
FontFeature.SUBSET = "font"
FontFeature.XMLTAG = None
#------ ForeignData -------
ForeignData.XMLTAG = "foreign-data"
#------ FunctionFeature -------
FunctionFeature.SUBSET = "function"
FunctionFeature.XMLTAG = None
#------ Gap -------
Gap.ACCEPTED_DATA = (Comment, Content, Description, Feature, ForeignData, Metric, Part,)
Gap.ANNOTATIONTYPE = AnnotationType.GAP
Gap.LABEL = "Gap"
Gap.OPTIONAL_ATTRIBS = (Attrib.ID, Attrib.CLASS, Attrib.ANNOTATOR, Attrib.N, Attrib.DATETIME, Attrib.SRC, Attrib.BEGINTIME, Attrib.ENDTIME, Attrib.METADATA, Attrib.TAG,)
Gap.XMLTAG = "gap"
#------ Head -------
Head.ACCEPTED_DATA = (AbstractAnnotationLayer, AbstractInlineAnnotation, Alternative, AlternativeLayers, Comment, Correction, Description, Event, External, Feature, ForeignData, Gap, Hiddenword, Linebreak, Metric, Paragraph, Part, PhonContent, Reference, Relation, Sentence, String, TextContent, Whitespace, Word,)
Head.ANNOTATIONTYPE = AnnotationType.HEAD
Head.LABEL = "Head"
Head.TEXTDELIMITER = "\n\n"
Head.XMLTAG = "head"
#------ HeadFeature -------
HeadFeature.SUBSET = "head"
HeadFeature.XMLTAG = None
#------ Headspan -------
Headspan.LABEL = "Head"
Headspan.OCCURRENCES = 1
Headspan.PRIMARYELEMENT = False
Headspan.XMLTAG = "hd"
#------ Hiddenword -------
Hiddenword.ACCEPTED_DATA = (AbstractAnnotationLayer, AbstractInlineAnnotation, Alternative, AlternativeLayers, Comment, Correction, Description, External, Feature, ForeignData, Metric, Part, PhonContent, Reference, Relation, String, TextContent,)
Hiddenword.ANNOTATIONTYPE = AnnotationType.HIDDENTOKEN
Hiddenword.HIDDEN = True
Hiddenword.LABEL = "Hidden Word/Token"
Hiddenword.OPTIONAL_ATTRIBS = (Attrib.ID, Attrib.CLASS, Attrib.ANNOTATOR, Attrib.N, Attrib.CONFIDENCE, Attrib.DATETIME, Attrib.SRC, Attrib.BEGINTIME, Attrib.ENDTIME, Attrib.SPEAKER, Attrib.TEXTCLASS, Attrib.METADATA, Attrib.SPACE, Attrib.TAG,)
Hiddenword.TEXTDELIMITER = " "
Hiddenword.WREFABLE = True
Hiddenword.XMLTAG = "hiddenw"
#------ Hyphbreak -------
Hyphbreak.ANNOTATIONTYPE = AnnotationType.HYPHENATION
Hyphbreak.IMPLICITSPACE = True
Hyphbreak.LABEL = "Hyphbreak"
Hyphbreak.TEXTDELIMITER = ""
Hyphbreak.XMLTAG = "t-hbr"
#------ Label -------
Label.ACCEPTED_DATA = (AbstractAnnotationLayer, AbstractInlineAnnotation, Alternative, AlternativeLayers, Comment, Correction, Description, External, Feature, ForeignData, Hiddenword, Linebreak, Metric, Part, PhonContent, Reference, Relation, String, TextContent, Whitespace, Word,)
Label.LABEL = "Label"
Label.XMLTAG = "label"
#------ LangAnnotation -------
LangAnnotation.ANNOTATIONTYPE = AnnotationType.LANG
LangAnnotation.LABEL = "Language"
LangAnnotation.XMLTAG = "lang"
#------ LemmaAnnotation -------
LemmaAnnotation.ANNOTATIONTYPE = AnnotationType.LEMMA
LemmaAnnotation.LABEL = "Lemma"
LemmaAnnotation.XMLTAG = "lemma"
#------ LevelFeature -------
LevelFeature.SUBSET = "level"
LevelFeature.XMLTAG = None
#------ Linebreak -------
Linebreak.ANNOTATIONTYPE = AnnotationType.LINEBREAK
Linebreak.IMPLICITSPACE = True
Linebreak.LABEL = "Linebreak"
Linebreak.TEXTDELIMITER = ""
Linebreak.XLINK = True
Linebreak.XMLTAG = "br"
#------ LinkReference -------
LinkReference.OPTIONAL_ATTRIBS = (Attrib.IDREF, Attrib.TAG,)
LinkReference.XMLTAG = "xref"
#------ List -------
List.ACCEPTED_DATA = (AbstractAnnotationLayer, AbstractInlineAnnotation, Alternative, AlternativeLayers, Caption, Comment, Correction, Description, Event, External, Feature, ForeignData, Linebreak, ListItem, Metric, Note, Part, PhonContent, Reference, Relation, String, TextContent,)
List.ANNOTATIONTYPE = AnnotationType.LIST
List.LABEL = "List"
List.TEXTDELIMITER = "\n\n"
List.XMLTAG = "list"
#------ ListItem -------
ListItem.ACCEPTED_DATA = (AbstractAnnotationLayer, AbstractInlineAnnotation, Alternative, AlternativeLayers, Comment, Correction, Description, Event, External, Feature, ForeignData, Gap, Hiddenword, Label, Linebreak, List, Metric, Note, Paragraph, Part, PhonContent, Quote, Reference, Relation, Sentence, String, TextContent, Whitespace, Word,)
ListItem.LABEL = "List Item"
ListItem.OPTIONAL_ATTRIBS = (Attrib.ID, Attrib.ANNOTATOR, Attrib.N, Attrib.CONFIDENCE, Attrib.DATETIME, Attrib.SRC, Attrib.BEGINTIME, Attrib.ENDTIME, Attrib.SPEAKER, Attrib.METADATA, Attrib.TAG,)
ListItem.TEXTDELIMITER = "\n"
ListItem.XMLTAG = "item"
#------ Metric -------
Metric.ACCEPTED_DATA = (Comment, Description, Feature, ForeignData, ValueFeature,)
Metric.ANNOTATIONTYPE = AnnotationType.METRIC
Metric.LABEL = "Metric"
Metric.OPTIONAL_ATTRIBS = (Attrib.ID, Attrib.CLASS, Attrib.ANNOTATOR, Attrib.N, Attrib.CONFIDENCE, Attrib.DATETIME, Attrib.SRC, Attrib.BEGINTIME, Attrib.ENDTIME, Attrib.SPEAKER, Attrib.METADATA, Attrib.TAG,)
Metric.XMLTAG = "metric"
#------ ModalitiesLayer -------
ModalitiesLayer.ACCEPTED_DATA = (Comment, Correction, Description, ForeignData, Modality,)
ModalitiesLayer.ANNOTATIONTYPE = AnnotationType.MODALITY
ModalitiesLayer.PRIMARYELEMENT = False
ModalitiesLayer.XMLTAG = "modalities"
#------ Modality -------
Modality.ACCEPTED_DATA = (AbstractInlineAnnotation, Comment, Cue, Description, Feature, ForeignData, LinkReference, Metric, PolarityFeature, Relation, Scope, Source, StrengthFeature, Target,)
Modality.ANNOTATIONTYPE = AnnotationType.MODALITY
Modality.LABEL = "Modality"
Modality.XMLTAG = "modality"
#------ ModalityFeature -------
ModalityFeature.SUBSET = "mod"
ModalityFeature.XMLTAG = None
#------ Morpheme -------
Morpheme.ACCEPTED_DATA = (AbstractAnnotationLayer, AbstractInlineAnnotation, Alternative, AlternativeLayers, Comment, Correction, Description, Feature, ForeignData, FunctionFeature, Metric, Morpheme, Part, PhonContent, Relation, String, TextContent,)
Morpheme.ANNOTATIONTYPE = AnnotationType.MORPHOLOGICAL
Morpheme.LABEL = "Morpheme"
Morpheme.TEXTDELIMITER = ""
Morpheme.WREFABLE = True
Morpheme.XMLTAG = "morpheme"
#------ MorphologyLayer -------
MorphologyLayer.ACCEPTED_DATA = (Comment, Correction, Description, ForeignData, Morpheme,)
MorphologyLayer.ANNOTATIONTYPE = AnnotationType.MORPHOLOGICAL
MorphologyLayer.PRIMARYELEMENT = False
MorphologyLayer.XMLTAG = "morphology"
#------ New -------
New.ANNOTATIONTYPE = AnnotationType.CORRECTION
New.OCCURRENCES = 1
New.OPTIONAL_ATTRIBS = (Attrib.TAG,)
New.PRIMARYELEMENT = False
New.XMLTAG = "new"
#------ Note -------
Note.ACCEPTED_DATA = (AbstractAnnotationLayer, AbstractInlineAnnotation, Alternative, AlternativeLayers, Comment, Correction, Description, Example, External, Feature, Figure, ForeignData, Head, Hiddenword, Linebreak, List, Metric, Paragraph, Part, PhonContent, Reference, Relation, Sentence, String, Table, TextContent, Utterance, Whitespace, Word,)
Note.ANNOTATIONTYPE = AnnotationType.NOTE
Note.LABEL = "Note"
Note.XMLTAG = "note"
#------ Observation -------
Observation.ACCEPTED_DATA = (AbstractInlineAnnotation, Comment, Description, Feature, ForeignData, LinkReference, Metric, Relation, WordReference,)
Observation.ANNOTATIONTYPE = AnnotationType.OBSERVATION
Observation.LABEL = "Observation"
Observation.XMLTAG = "observation"
#------ ObservationLayer -------
ObservationLayer.ACCEPTED_DATA = (Comment, Correction, Description, ForeignData, Observation,)
ObservationLayer.ANNOTATIONTYPE = AnnotationType.OBSERVATION
ObservationLayer.PRIMARYELEMENT = False
ObservationLayer.XMLTAG = "observations"
#------ Original -------
Original.ANNOTATIONTYPE = AnnotationType.CORRECTION
Original.AUTH = False
Original.OCCURRENCES = 1
Original.OPTIONAL_ATTRIBS = (Attrib.TAG,)
Original.PRIMARYELEMENT = False
Original.XMLTAG = "original"
#------ Paragraph -------
Paragraph.ACCEPTED_DATA = (AbstractAnnotationLayer, AbstractInlineAnnotation, Alternative, AlternativeLayers, Comment, Correction, Description, Entry, Event, Example, External, Feature, Figure, ForeignData, Gap, Head, Hiddenword, Linebreak, List, Metric, Note, Part, PhonContent, Quote, Reference, Relation, Sentence, String, TextContent, Whitespace, Word,)
Paragraph.ANNOTATIONTYPE = AnnotationType.PARAGRAPH
Paragraph.LABEL = "Paragraph"
Paragraph.TEXTDELIMITER = "\n\n"
Paragraph.XMLTAG = "p"
#------ Part -------
Part.ACCEPTED_DATA = (AbstractAnnotationLayer, AbstractInlineAnnotation, AbstractStructureElement, Alternative, AlternativeLayers, Comment, Correction, Description, External, Feature, ForeignData, Metric, Part, PhonContent, Relation, TextContent,)
Part.ANNOTATIONTYPE = AnnotationType.PART
Part.LABEL = "Part"
Part.TEXTDELIMITER = " "
Part.XMLTAG = "part"
#------ PhonContent -------
PhonContent.ACCEPTED_DATA = (Comment, Description, Feature,)
PhonContent.ANNOTATIONTYPE = AnnotationType.PHON
PhonContent.LABEL = "Phonetic Content"
PhonContent.PHONCONTAINER = True
PhonContent.PRINTABLE = False
PhonContent.SPEAKABLE = True
PhonContent.XMLTAG = "ph"
#------ Phoneme -------
Phoneme.ACCEPTED_DATA = (AbstractAnnotationLayer, AbstractInlineAnnotation, Alternative, AlternativeLayers, Comment, Correction, Description, Feature, ForeignData, FunctionFeature, Metric, Part, PhonContent, Phoneme, Relation, String, TextContent,)
Phoneme.ANNOTATIONTYPE = AnnotationType.PHONOLOGICAL
Phoneme.LABEL = "Phoneme"
Phoneme.TEXTDELIMITER = ""
Phoneme.WREFABLE = True
Phoneme.XMLTAG = "phoneme"
#------ PhonologyLayer -------
PhonologyLayer.ACCEPTED_DATA = (Comment, Correction, Description, ForeignData, Phoneme,)
PhonologyLayer.ANNOTATIONTYPE = AnnotationType.PHONOLOGICAL
PhonologyLayer.PRIMARYELEMENT = False
PhonologyLayer.XMLTAG = "phonology"
#------ PolarityFeature -------
PolarityFeature.SUBSET = "polarity"
PolarityFeature.XMLTAG = None
#------ PosAnnotation -------
PosAnnotation.ACCEPTED_DATA = (Comment, Description, Feature, ForeignData, HeadFeature, Metric,)
PosAnnotation.ANNOTATIONTYPE = AnnotationType.POS
PosAnnotation.LABEL = "Part-of-Speech"
PosAnnotation.XMLTAG = "pos"
#------ Predicate -------
Predicate.ACCEPTED_DATA = (AbstractInlineAnnotation, Comment, Description, Feature, ForeignData, LinkReference, Metric, Relation, SemanticRole, WordReference,)
Predicate.ANNOTATIONTYPE = AnnotationType.PREDICATE
Predicate.LABEL = "Predicate"
Predicate.XMLTAG = "predicate"
#------ Quote -------
Quote.ACCEPTED_DATA = (AbstractAnnotationLayer, AbstractInlineAnnotation, Alternative, AlternativeLayers, Comment, Correction, Description, Division, External, Feature, ForeignData, Gap, Hiddenword, Linebreak, Metric, Paragraph, Part, Quote, Reference, Relation, Sentence, String, TextContent, Utterance, Whitespace, Word,)
Quote.ANNOTATIONTYPE = AnnotationType.QUOTE
Quote.LABEL = "Quote"
Quote.XMLTAG = "quote"
#------ Reference -------
Reference.ACCEPTED_DATA = (AbstractAnnotationLayer, Alternative, AlternativeLayers, Comment, Correction, Description, External, Feature, ForeignData, Hiddenword, Linebreak, Metric, Paragraph, Part, PhonContent, Quote, Relation, Sentence, String, TextContent, Utterance, Whitespace, Word,)
Reference.ANNOTATIONTYPE = AnnotationType.REFERENCE
Reference.LABEL = "Reference"
Reference.TEXTDELIMITER = " "
Reference.XLINK = True
Reference.XMLTAG = "ref"
#------ Relation -------
Relation.ACCEPTED_DATA = (Comment, Description, Feature, ForeignData, LinkReference, Metric,)
Relation.ANNOTATIONTYPE = AnnotationType.RELATION
Relation.LABEL = "Relation"
Relation.OPTIONAL_ATTRIBS = (Attrib.ID, Attrib.CLASS, Attrib.ANNOTATOR, Attrib.N, Attrib.CONFIDENCE, Attrib.DATETIME, Attrib.SRC, Attrib.BEGINTIME, Attrib.ENDTIME, Attrib.SPEAKER, Attrib.METADATA, Attrib.TAG,)
Relation.PRINTABLE = False
Relation.REQUIRED_ATTRIBS = None
Relation.SPEAKABLE = False
Relation.XLINK = True
Relation.XMLTAG = "relation"
#------ Row -------
Row.ACCEPTED_DATA = (AbstractAnnotationLayer, AbstractInlineAnnotation, Alternative, AlternativeLayers, Cell, Comment, Correction, Description, External, Feature, ForeignData, Metric, Part, Relation,)
Row.LABEL = "Table Row"
Row.TEXTDELIMITER = "\n"
Row.XMLTAG = "row"
#------ Scope -------
Scope.ACCEPTED_DATA = (AbstractInlineAnnotation, Comment, Cue, Description, Feature, ForeignData, LinkReference, Metric, Relation, Source, Target, WordReference,)
Scope.LABEL = "Scope"
Scope.OCCURRENCES = 1
Scope.PRIMARYELEMENT = False
Scope.XMLTAG = "scope"
#------ SemanticRole -------
SemanticRole.ACCEPTED_DATA = (AbstractInlineAnnotation, Comment, Description, Feature, ForeignData, Headspan, LinkReference, Metric, Relation, WordReference,)
SemanticRole.ANNOTATIONTYPE = AnnotationType.SEMROLE
SemanticRole.LABEL = "Semantic Role"
SemanticRole.REQUIRED_ATTRIBS = (Attrib.CLASS,)
SemanticRole.XMLTAG = "semrole"
#------ SemanticRolesLayer -------
SemanticRolesLayer.ACCEPTED_DATA = (Comment, Correction, Description, ForeignData, Predicate, SemanticRole,)
SemanticRolesLayer.ANNOTATIONTYPE = AnnotationType.SEMROLE
SemanticRolesLayer.PRIMARYELEMENT = False
SemanticRolesLayer.XMLTAG = "semroles"
#------ SenseAnnotation -------
SenseAnnotation.ACCEPTED_DATA = (Comment, Description, Feature, ForeignData, Metric, SynsetFeature,)
SenseAnnotation.ANNOTATIONTYPE = AnnotationType.SENSE
SenseAnnotation.LABEL = "Semantic Sense"
SenseAnnotation.OCCURRENCES_PER_SET = 0
SenseAnnotation.XMLTAG = "sense"
#------ Sentence -------
Sentence.ACCEPTED_DATA = (AbstractAnnotationLayer, AbstractInlineAnnotation, Alternative, AlternativeLayers, Comment, Correction, Description, Entry, Event, Example, External, Feature, ForeignData, Gap, Hiddenword, Linebreak, Metric, Note, Part, PhonContent, Quote, Reference, Relation, String, TextContent, Whitespace, Word,)
Sentence.ANNOTATIONTYPE = AnnotationType.SENTENCE
Sentence.LABEL = "Sentence"
Sentence.TEXTDELIMITER = " "
Sentence.XMLTAG = "s"
#------ Sentiment -------
Sentiment.ACCEPTED_DATA = (AbstractInlineAnnotation, Comment, Description, Feature, ForeignData, Headspan, LinkReference, Metric, PolarityFeature, Relation, Source, StrengthFeature, Target, WordReference,)
Sentiment.ANNOTATIONTYPE = AnnotationType.SENTIMENT
Sentiment.LABEL = "Sentiment"
Sentiment.XMLTAG = "sentiment"
#------ SentimentLayer -------
SentimentLayer.ACCEPTED_DATA = (Comment, Correction, Description, ForeignData, Sentiment,)
SentimentLayer.ANNOTATIONTYPE = AnnotationType.SENTIMENT
SentimentLayer.PRIMARYELEMENT = False
SentimentLayer.XMLTAG = "sentiments"
#------ SizeFeature -------
SizeFeature.SUBSET = "size"
SizeFeature.XMLTAG = None
#------ Source -------
Source.LABEL = "Source"
Source.OCCURRENCES = 1
Source.PRIMARYELEMENT = False
Source.XMLTAG = "source"
#------ SpanRelation -------
SpanRelation.ACCEPTED_DATA = (Comment, Description, Feature, ForeignData, Metric, Relation,)
SpanRelation.ANNOTATIONTYPE = AnnotationType.SPANRELATION
SpanRelation.LABEL = "Span Relation"
SpanRelation.OPTIONAL_ATTRIBS = (Attrib.ID, Attrib.CLASS, Attrib.ANNOTATOR, Attrib.N, Attrib.CONFIDENCE, Attrib.DATETIME, Attrib.SRC, Attrib.BEGINTIME, Attrib.ENDTIME, Attrib.SPEAKER, Attrib.METADATA, Attrib.TAG,)
SpanRelation.PRINTABLE = False
SpanRelation.REQUIRED_ATTRIBS = None
SpanRelation.SPEAKABLE = False
SpanRelation.XMLTAG = "spanrelation"
#------ SpanRelationLayer -------
SpanRelationLayer.ACCEPTED_DATA = (Comment, Correction, Description, ForeignData, SpanRelation,)
SpanRelationLayer.ANNOTATIONTYPE = AnnotationType.SPANRELATION
SpanRelationLayer.PRIMARYELEMENT = False
SpanRelationLayer.XMLTAG = "spanrelations"
#------ Speech -------
Speech.ACCEPTED_DATA = (AbstractAnnotationLayer, AbstractInlineAnnotation, Alternative, AlternativeLayers, Comment, Correction, Description, Division, Entry, Event, Example, External, Feature, ForeignData, Gap, Hiddenword, List, Metric, Note, Paragraph, Part, PhonContent, Quote, Reference, Relation, Sentence, String, TextContent, Utterance, Word,)
Speech.LABEL = "Speech Body"
Speech.OPTIONAL_ATTRIBS = (Attrib.ID, Attrib.ANNOTATOR, Attrib.DATETIME, Attrib.SRC, Attrib.BEGINTIME, Attrib.ENDTIME, Attrib.SPEAKER, Attrib.METADATA, Attrib.SPACE, Attrib.TAG,)
Speech.TEXTDELIMITER = "\n\n\n"
Speech.XMLTAG = "speech"
#------ Statement -------
Statement.ACCEPTED_DATA = (AbstractInlineAnnotation, Comment, Description, Feature, ForeignData, Headspan, LinkReference, Metric, Relation, Source, StatementRelation, WordReference,)
Statement.ANNOTATIONTYPE = AnnotationType.STATEMENT
Statement.LABEL = "Statement"
Statement.XMLTAG = "statement"
#------ StatementLayer -------
StatementLayer.ACCEPTED_DATA = (Comment, Correction, Description, ForeignData, Statement,)
StatementLayer.ANNOTATIONTYPE = AnnotationType.STATEMENT
StatementLayer.PRIMARYELEMENT = False
StatementLayer.XMLTAG = "statements"
#------ StatementRelation -------
StatementRelation.LABEL = "Relation"
StatementRelation.OCCURRENCES = 1
StatementRelation.PRIMARYELEMENT = False
StatementRelation.XMLTAG = "rel"
#------ StrengthFeature -------
StrengthFeature.SUBSET = "strength"
StrengthFeature.XMLTAG = None
#------ String -------
String.ACCEPTED_DATA = (AbstractInlineAnnotation, Comment, Correction, Description, Feature, ForeignData, Metric, PhonContent, Relation, TextContent,)
String.ANNOTATIONTYPE = AnnotationType.STRING
String.LABEL = "String"
String.OCCURRENCES = 0
String.OPTIONAL_ATTRIBS = (Attrib.ID, Attrib.CLASS, Attrib.ANNOTATOR, Attrib.CONFIDENCE, Attrib.DATETIME, Attrib.N, Attrib.SRC, Attrib.BEGINTIME, Attrib.ENDTIME, Attrib.METADATA, Attrib.TAG,)
String.PRINTABLE = True
String.XMLTAG = "str"
#------ StyleFeature -------
StyleFeature.SUBSET = "style"
StyleFeature.XMLTAG = None
#------ SubjectivityAnnotation -------
SubjectivityAnnotation.ANNOTATIONTYPE = AnnotationType.SUBJECTIVITY
SubjectivityAnnotation.LABEL = "Subjectivity/Sentiment"
SubjectivityAnnotation.XMLTAG = "subjectivity"
#------ Suggestion -------
Suggestion.ANNOTATIONTYPE = AnnotationType.CORRECTION
Suggestion.AUTH = False
Suggestion.OCCURRENCES = 0
Suggestion.OPTIONAL_ATTRIBS = (Attrib.CONFIDENCE, Attrib.N, Attrib.TAG,)
Suggestion.PRIMARYELEMENT = False
Suggestion.XMLTAG = "suggestion"
#------ SynsetFeature -------
SynsetFeature.SUBSET = "synset"
SynsetFeature.XMLTAG = None
#------ SyntacticUnit -------
SyntacticUnit.ACCEPTED_DATA = (AbstractInlineAnnotation, Comment, Description, Feature, ForeignData, LinkReference, Metric, Relation, SyntacticUnit, WordReference,)
SyntacticUnit.ANNOTATIONTYPE = AnnotationType.SYNTAX
SyntacticUnit.LABEL = "Syntactic Unit"
SyntacticUnit.XMLTAG = "su"
#------ SyntaxLayer -------
SyntaxLayer.ACCEPTED_DATA = (Comment, Correction, Description, ForeignData, SyntacticUnit,)
SyntaxLayer.ANNOTATIONTYPE = AnnotationType.SYNTAX
SyntaxLayer.PRIMARYELEMENT = False
SyntaxLayer.XMLTAG = "syntax"
#------ Table -------
Table.ACCEPTED_DATA = (AbstractAnnotationLayer, AbstractInlineAnnotation, Alternative, AlternativeLayers, Comment, Correction, Description, External, Feature, ForeignData, Linebreak, Metric, Part, Relation, Row, TableHead,)
Table.ANNOTATIONTYPE = AnnotationType.TABLE
Table.LABEL = "Table"
Table.XMLTAG = "table"
#------ TableHead -------
TableHead.ACCEPTED_DATA = (AbstractAnnotationLayer, AbstractInlineAnnotation, Alternative, AlternativeLayers, Comment, Correction, Description, External, Feature, ForeignData, Metric, Part, Relation, Row,)
TableHead.LABEL = "Table Header"
TableHead.OPTIONAL_ATTRIBS = (Attrib.ID, Attrib.ANNOTATOR, Attrib.N, Attrib.CONFIDENCE, Attrib.DATETIME, Attrib.SRC, Attrib.BEGINTIME, Attrib.ENDTIME, Attrib.SPEAKER, Attrib.METADATA, Attrib.TAG,)
TableHead.XMLTAG = "tablehead"
#------ Target -------
Target.LABEL = "Target"
Target.OCCURRENCES = 1
Target.PRIMARYELEMENT = False
Target.XMLTAG = "target"
#------ Term -------
Term.ACCEPTED_DATA = (AbstractAnnotationLayer, AbstractInlineAnnotation, Alternative, AlternativeLayers, Comment, Correction, Description, Event, External, Feature, Figure, ForeignData, Gap, Hiddenword, Linebreak, List, Metric, Paragraph, Part, PhonContent, Reference, Relation, Sentence, String, Table, TextContent, Utterance, Whitespace, Word,)
Term.ANNOTATIONTYPE = AnnotationType.TERM
Term.LABEL = "Term"
Term.XMLTAG = "term"
#------ Text -------
Text.ACCEPTED_DATA = (AbstractAnnotationLayer, AbstractInlineAnnotation, Alternative, AlternativeLayers, Comment, Correction, Description, Division, Entry, Event, Example, External, Feature, Figure, ForeignData, Gap, Hiddenword, Linebreak, List, Metric, Note, Paragraph, Part, PhonContent, Quote, Reference, Relation, Sentence, String, Table, TextContent, Whitespace, Word,)
Text.LABEL = "Text Body"
Text.OPTIONAL_ATTRIBS = (Attrib.ID, Attrib.ANNOTATOR, Attrib.DATETIME, Attrib.SRC, Attrib.BEGINTIME, Attrib.ENDTIME, Attrib.SPEAKER, Attrib.METADATA, Attrib.SPACE, Attrib.TAG,)
Text.TEXTDELIMITER = "\n\n\n"
Text.XMLTAG = "text"
#------ TextContent -------
TextContent.ACCEPTED_DATA = (AbstractTextMarkup, Comment, Description, Feature, Linebreak,)
TextContent.ANNOTATIONTYPE = AnnotationType.TEXT
TextContent.LABEL = "Text"
TextContent.PRINTABLE = True
TextContent.SPEAKABLE = False
TextContent.TEXTCONTAINER = True
TextContent.XLINK = True
TextContent.XMLTAG = "t"
#------ TextMarkupCorrection -------
TextMarkupCorrection.ANNOTATIONTYPE = AnnotationType.CORRECTION
TextMarkupCorrection.PRIMARYELEMENT = False
TextMarkupCorrection.XMLTAG = "t-correction"
#------ TextMarkupError -------
TextMarkupError.ANNOTATIONTYPE = AnnotationType.ERRORDETECTION
TextMarkupError.PRIMARYELEMENT = False
TextMarkupError.XMLTAG = "t-error"
#------ TextMarkupGap -------
TextMarkupGap.ANNOTATIONTYPE = AnnotationType.GAP
TextMarkupGap.PRIMARYELEMENT = False
TextMarkupGap.XMLTAG = "t-gap"
#------ TextMarkupHSpace -------
TextMarkupHSpace.ANNOTATIONTYPE = AnnotationType.HSPACE
TextMarkupHSpace.IMPLICITSPACE = True
TextMarkupHSpace.TEXTDELIMITER = ""
TextMarkupHSpace.XMLTAG = "t-hspace"
#------ TextMarkupLanguage -------
TextMarkupLanguage.ANNOTATIONTYPE = AnnotationType.LANG
TextMarkupLanguage.PRIMARYELEMENT = False
TextMarkupLanguage.XMLTAG = "t-lang"
#------ TextMarkupReference -------
TextMarkupReference.ANNOTATIONTYPE = AnnotationType.REFERENCE
TextMarkupReference.PRIMARYELEMENT = False
TextMarkupReference.XMLTAG = "t-ref"
#------ TextMarkupString -------
TextMarkupString.ANNOTATIONTYPE = AnnotationType.STRING
TextMarkupString.PRIMARYELEMENT = False
TextMarkupString.XMLTAG = "t-str"
#------ TextMarkupStyle -------
TextMarkupStyle.ACCEPTED_DATA = (AbstractTextMarkup, Comment, Description, Feature, FontFeature, Linebreak, SizeFeature,)
TextMarkupStyle.ANNOTATIONTYPE = AnnotationType.STYLE
TextMarkupStyle.PRIMARYELEMENT = True
TextMarkupStyle.XMLTAG = "t-style"
#------ TextMarkupWhitespace -------
TextMarkupWhitespace.ANNOTATIONTYPE = AnnotationType.WHITESPACE
TextMarkupWhitespace.IMPLICITSPACE = True
TextMarkupWhitespace.PRIMARYELEMENT = False
TextMarkupWhitespace.TEXTDELIMITER = ""
TextMarkupWhitespace.XMLTAG = "t-whitespace"
#------ TimeFeature -------
TimeFeature.SUBSET = "time"
TimeFeature.XMLTAG = None
#------ TimeSegment -------
TimeSegment.ACCEPTED_DATA = (AbstractInlineAnnotation, ActorFeature, BegindatetimeFeature, Comment, Description, EnddatetimeFeature, Feature, ForeignData, LinkReference, Metric, Relation, WordReference,)
TimeSegment.ANNOTATIONTYPE = AnnotationType.TIMESEGMENT
TimeSegment.LABEL = "Time Segment"
TimeSegment.XMLTAG = "timesegment"
#------ TimingLayer -------
TimingLayer.ACCEPTED_DATA = (Comment, Correction, Description, ForeignData, TimeSegment,)
TimingLayer.ANNOTATIONTYPE = AnnotationType.TIMESEGMENT
TimingLayer.PRIMARYELEMENT = False
TimingLayer.XMLTAG = "timing"
#------ Utterance -------
Utterance.ACCEPTED_DATA = (AbstractAnnotationLayer, AbstractInlineAnnotation, Alternative, AlternativeLayers, Comment, Correction, Description, External, Feature, ForeignData, Gap, Hiddenword, Metric, Note, Part, PhonContent, Quote, Reference, Relation, Sentence, String, TextContent, Word,)
Utterance.ANNOTATIONTYPE = AnnotationType.UTTERANCE
Utterance.LABEL = "Utterance"
Utterance.TEXTDELIMITER = " "
Utterance.XMLTAG = "utt"
#------ ValueFeature -------
ValueFeature.SUBSET = "value"
ValueFeature.XMLTAG = None
#------ Whitespace -------
Whitespace.ANNOTATIONTYPE = AnnotationType.WHITESPACE
Whitespace.IMPLICITSPACE = True
Whitespace.LABEL = "Whitespace"
Whitespace.TEXTDELIMITER = ""
Whitespace.XMLTAG = "whitespace"
#------ Word -------
Word.ACCEPTED_DATA = (AbstractAnnotationLayer, AbstractInlineAnnotation, Alternative, AlternativeLayers, Comment, Correction, Description, External, Feature, ForeignData, Metric, Part, PhonContent, Reference, Relation, String, TextContent,)
Word.ANNOTATIONTYPE = AnnotationType.TOKEN
Word.LABEL = "Word/Token"
Word.OPTIONAL_ATTRIBS = (Attrib.ID, Attrib.CLASS, Attrib.ANNOTATOR, Attrib.N, Attrib.CONFIDENCE, Attrib.DATETIME, Attrib.SRC, Attrib.BEGINTIME, Attrib.ENDTIME, Attrib.SPEAKER, Attrib.TEXTCLASS, Attrib.METADATA, Attrib.SPACE, Attrib.TAG,)
Word.TEXTDELIMITER = " "
Word.WREFABLE = True
Word.XMLTAG = "w"
#------ WordReference -------
WordReference.OPTIONAL_ATTRIBS = (Attrib.IDREF, Attrib.TAG,)
WordReference.XMLTAG = "wref"

#EOF
