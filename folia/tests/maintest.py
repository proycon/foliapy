#!/usr/bin/env python
#-*- coding:utf-8 -*-


#---------------------------------------------------------------
# FoLiA Library - Test Units
#   by Maarten van Gompel
#   Centre for Language and Speech Technology
#   Radboud University Nijmegen
#   proycon AT anaproy DOT nl
#
#   Licensed under GPLv3
#
#----------------------------------------------------------------


from __future__ import print_function, unicode_literals, division, absolute_import

import sys
import os
import unittest
import gzip
import bz2
import re
from datetime import datetime
import lxml.objectify
from folia.helpers import u, isstring
import folia.main as folia
stderr = sys.stderr
stdout = sys.stdout


if os.path.exists("folia-repo"):
    FOLIAPATH = "folia-repo"
elif os.path.exists("../folia-repo"):
    FOLIAPATH = "../folia-repo"
elif os.path.exists("../../folia-repo"):
    FOLIAPATH = "../../folia-repo"
else:
    raise Exception("Please invoke this script from its base directory or the repository root")
if not os.path.exists(os.path.join(FOLIAPATH,"examples")):
    raise Exception("FoLiA repository not found, did you run 'git submodule init && git submodule update' are you in the test directory?")

if 'TMPDIR' in os.environ:
    TMPDIR = os.environ['TMPDIR']
else:
    TMPDIR = '/tmp/'

from io import StringIO, BytesIO
from lxml import etree as ElementTree
from folia.tests.helpers import xmlcheck, xmlnorm



###################### NEW TESTS ##########################

class Test_E001_Tokens_Structure(unittest.TestCase):
    """Simple Token & Structure Tests"""

    def setUp(self):
        self.doc = folia.Document(file=os.path.join(FOLIAPATH,"examples/tokens-structure.2.0.0.folia.xml"))

    def test_wordcount(self):
        """Simple Token & Structure - Word count"""
        self.assertEqual( self.doc.count(folia.Word), 8 ) #count only (most efficient)
        #explicitly obtain:
        self.assertEqual( len(list(self.doc.words())), 8 ) #shortcut
        self.assertEqual( len(list(self.doc.select(folia.Word))), 8 )

    def test_word_ids(self):
        """Simple Token & Structure - Word IDs"""
        self.assertEqual( [ word.id for word in self.doc.words() ], ["example.p.1.s.1.w.1", "example.p.1.s.1.w.2", "example.p.1.s.1.w.3", "example.p.1.s.2.w.1", "example.p.1.s.2.w.2", "example.p.1.s.2.w.3", "example.p.1.s.2.w.4", "example.p.1.s.2.w.5"] )

    def test_structurecount(self):
        """Simple Token & Structure Test - Structure Count"""
        self.assertEqual( self.doc.count(folia.Sentence), 2 ) #count only (most efficient)
        #explicitly obtain:
        self.assertEqual( len(list(self.doc.sentences())), 2 ) #shortcut
        self.assertEqual( len(list(self.doc.select(folia.Sentence))), 2 )

        self.assertEqual( self.doc.count(folia.Paragraph), 1 ) #count only (most efficient)
        #explicitly obtain:
        self.assertEqual( len(list(self.doc.paragraphs())), 1 ) #shortcut
        self.assertEqual( len(list(self.doc.select(folia.Paragraph))), 1 )


    def test_structure_ids(self):
        """Simple Token & Structure Test - Structure IDs"""
        self.assertEqual( [ s.id for s in self.doc.sentences() ], ["example.p.1.s.1","example.p.1.s.2" ] )
        self.assertEqual( [ s.id for s in self.doc.paragraphs() ], ["example.p.1" ] )

    def test_first_word(self):
        """Simple Token & Structure Test - First word"""
        #grab first word
        w = self.doc.words(0) # shortcut for doc.words()[0]
        self.assertTrue( isinstance(w, folia.Word) )
        self.assertEqual( w.id , 'example.p.1.s.1.w.1' )
        self.assertEqual( w.text() , "Hello" )
        self.assertEqual( str(w) , "Hello" )


    def test_last_word(self):
        """Simple Token & Structure Test - Last word"""
        #grab last word
        w = self.doc.words(-1) # shortcut for doc.words()[0]
        self.assertTrue( isinstance(w, folia.Word) )
        self.assertEqual( w.id , "example.p.1.s.2.w.5" )
        self.assertEqual( w.text() , "." )
        self.assertEqual( str(w) , "." )


    def test_sentence(self):
        """Simple Token & Structure Test - Sentence"""
        #grab second sentence
        s = self.doc.sentences(1)
        self.assertTrue( isinstance(s, folia.Sentence) )
        self.assertEqual( s.id, 'example.p.1.s.2' )
        self.assertFalse( s.hastext() ) #no explicit text
        self.assertEqual( str(s), "This is an example." )

    def test_index(self):
        """Simple Token & Structure Test - Index"""
        #grab something using the index
        w = self.doc['example.p.1.s.1.w.1']
        self.assertTrue( isinstance(w, folia.Word) )
        self.assertEqual( self.doc['example.p.1.s.1.w.1'] , self.doc.index['example.p.1.s.1.w.1'] )
        self.assertEqual( w.id , 'example.p.1.s.1.w.1' )
        self.assertEqual( w.text() , "Hello" )


    def test_declaration(self):
        """Simple Token & Structure Test - Declarations"""
        self.assertTrue( self.doc.declared(folia.AnnotationType.TOKEN) )
        self.assertTrue( self.doc.declared(folia.Word) ) #same as above, resolves automatically
        self.assertTrue( self.doc.declared(folia.AnnotationType.TEXT) )
        self.assertTrue( self.doc.declared(folia.TextContent) ) #same as above, resolves automatically
        self.assertTrue( self.doc.declared(folia.Sentence) )
        self.assertTrue( self.doc.declared(folia.Paragraph) )

    def test_resolveoffsets(self):
        """Simple Token & Structure Test - Resolve character offsets"""
        #grab something using the index
        s = self.doc['example.p.1.s.2']
        words = s.resolveoffsets(8,18) #"an example"
        self.assertEqual( words, [self.doc['example.p.1.s.2.w.3'] , self.doc['example.p.1.s.2.w.4'] ] )
        self.assertEqual( words[0].text() , "an" )
        self.assertEqual( words[1].text() , "example" )

class Test_Exxx_Hidden_Tokens(unittest.TestCase): #xxx -> replace with a number at some point when there are more new tests
    """Hidden token tests"""

    def setUp(self):
        self.doc = folia.Document(file=os.path.join(FOLIAPATH,"examples/hiddentokens.2.0.0.folia.xml"))
        self.maxDiff = None

    def test_wordcount(self):
        """Simple Token & Structure - Word count (does not include hidden words)"""
        #self.assertEqual( self.doc.count(folia.Word), 7 )
        #explicitly obtain:
        self.assertEqual( len(list(self.doc.words())), 7 )

        #explicitly obtain:
        sentence = self.doc['example.s.1']
        self.assertEqual( len(list(sentence.words())), 7 )
        self.assertEqual( len(list(sentence.select(folia.Word, ignore=folia.default_ignore_structure))), 7 )

    def test_text(self):
        """Text serialisation on sentence (no hidden words)"""
        sentence = self.doc['example.s.1']
        self.assertEqual( sentence.text() , "Isn't a whole lot left." )

    def test_text2(self):
        """Text serialisation on syntactic unit (no hidden words)"""
        su = self.doc['example.s.1.su.1']
        self.assertEqual( su.text() , "Isn't a whole lot left." )

    def test_text_hiddenword(self):
        """Text serialisation on the hidden word itself"""
        word = self.doc['example.s.1.w.0']
        self.assertEqual( word.text(hidden=True) , "*exp*" )

    def test_wrefs(self):
        """Check whether hidden word is part of wrefs of syntactic unit"""
        su = self.doc['example.s.1.su.1']
        self.assertEqual([ w.id for w in su.wrefs() ], ["example.s.1.w.0","example.s.1.w.1","example.s.1.w.2","example.s.1.w.3","example.s.1.w.4","example.s.1.w.5","example.s.1.w.6","example.s.1.w.7"])

    def test_text_hidden(self):
        """Text serialisation on syntactic unit (with hidden words)"""
        su = self.doc['example.s.1.su.1']
        self.assertEqual( su.text(hidden=True) , "*exp* Isn't a whole lot left." )

    def test_wrefs_xml(self):
        """Test XML serialisation of wrefs in syntactic unit (with hidden words)"""
        su = self.doc['example.s.1.su.1']
        self.assertTrue(xmlcheck(su.xmlstring(), """<su xmlns:xlink="http://www.w3.org/1999/xlink" xmlns="http://ilk.uvt.nl/folia" xml:id="example.s.1.su.1" class="IP-MAT"><su xml:id="example.s.1.su.2" class="NP-SBJ"><wref id="example.s.1.w.0"/></su><su xml:id="example.s.1.su.3" class="VP"><su xml:id="example.s.1.su.4" class="BEP"><wref id="example.s.1.w.1" t="Is"/></su><su xml:id="example.s.1.su.5" class="NEG"><wref id="example.s.1.w.2" t="n't"/></su><su xml:id="example.s.1.su.6" class="VP"><su xml:id="example.s.1.su.7" class="NP-LGS"><wref id="example.s.1.w.3" t="a"/><su xml:id="example.s.1.su.8" class="ADJP"><wref id="example.s.1.w.4" t="whole"/></su><wref id="example.s.1.w.5" t="lot"/></su><wref id="example.s.1.w.6" t="left"/></su></su><su class="PUNC"><wref id="example.s.1.w.7" t="."/></su></su>"""))

class Test_Exxx_Invalid_Wref(unittest.TestCase): #xxx -> replace with a number at some point when there are more new tests
    """Invalid Wref test"""

    def test(self):
        with self.assertRaises( folia.ParseError) as cm:
            folia.Document(file=os.path.join(FOLIAPATH,"examples/erroneous/invalid-wref.2.0.0.folia.xml"))
        self.assertEqual(cm.exception.cause.__class__, folia.InvalidReference)

class Test_Exxx_KeepVersion(unittest.TestCase):
    """Serialisation of older FoLiA versions"""

    def test(self):
        #write legacy example to file
        f = open(os.path.join(TMPDIR,'foliatest1.5.ref.xml'),'w',encoding='utf-8')
        f.write(xmlnorm(LEGACYEXAMPLE,"1.5",stripns=False))
        f.close()

        doc = folia.Document(string=LEGACYEXAMPLE, keepversion=True, debug=False)
        doc.save(os.path.join(TMPDIR,'foliatest1.5.xml'))
        retcode = os.system('xmldiff ' + os.path.join(TMPDIR,'foliatest1.5.ref.xml') + ' ' + os.path.join(TMPDIR,'foliatest1.5.xml'))
        #retcode = 1 #disabled (memory hog)
        self.assertEqual( retcode, 0)

class Test_Exxx_BackwardCompatibility(unittest.TestCase):
    def setUp(self):
        self.doc = folia.Document(file=os.path.join(FOLIAPATH,"examples/frog-deep-upgraded.2.0.2.folia.xml"))

    def test_read_annotator(self):
        """Test whether old-style annotator attribute works"""
        w = self.doc['example.deep.p.1.s.1.w.1']
        pos = w.annotation(folia.PosAnnotation)
        self.assertEqual(pos.annotator, "frog-mbpos-1.0")

    def test_read_annotatortype(self):
        """Test whether old-style annotatortype attribute works"""
        w = self.doc['example.deep.p.1.s.1.w.1']
        pos = w.annotation(folia.PosAnnotation)
        self.assertEqual(pos.annotatortype, "auto")

    def test_write_annotator(self):
        """Test whether old-style annotator attribute works"""
        w = self.doc['example.deep.p.1.s.1.w.1']
        #remove the old one
        pos = w.annotation(folia.PosAnnotation)
        w.remove(pos)
        #add a new one with old style information
        w.append(folia.PosAnnotation, annotator="testsuite", cls="LID(bep,stan,rest)", annotatortype=folia.AnnotatorType.AUTO)
        #get it
        pos = w.annotation(folia.PosAnnotation)
        self.assertEqual(pos.annotator, "testsuite")
        self.assertEqual(pos.annotatortype, "auto")
        #we should have a processor now
        self.assertEqual(pos.processor.name, "testsuite")


class Test_Exxx_SetAndSetLess(unittest.TestCase): #Issue #74
    def setUp(self):
        self.doc = folia.Document(file=os.path.join(FOLIAPATH,"examples/tests/set_and_setless.2.0.0.folia.xml"))

    def test_sets_setless(self):
        """Testing sanity with set-holding and setless annotation types similtaneously"""
        c1 = self.doc['example.p.1.s.1.chunk.1']
        self.assertEqual(c1.set, None)

    def test_sets_setholding(self):
        """Testing sanity with set-holding and setless annotation types similtaneously"""
        c1 = self.doc['example.p.1.s.1.chunkset.1']
        self.assertEqual(c1.set, "chunkset")

class Test_Provenance(unittest.TestCase):
    def test001_metadatasanity(self):
        """Provenance - Parse and sanity check"""
        doc = folia.Document(file=os.path.join(FOLIAPATH,'examples/provenance.2.0.0.folia.xml'), textvalidation=True, allowadhocsets=True)
        self.assertIsInstance(doc.provenance, folia.Provenance)
        self.assertEqual(doc.provenance['p0'].name, 'ucto')
        self.assertEqual(doc.provenance['p0.1'].name, 'libfolia')
        self.assertEqual(doc.provenance['p1'].name, 'frog')
        self.assertEqual(doc.provenance['p1'].type, folia.ProcessorType.AUTO)
        self.assertEqual(doc.provenance['p1'].version, "0.16")
        self.assertEqual(doc.provenance['p1.0'].name, 'libfolia')
        self.assertEqual(doc.provenance['p1.0'].type, folia.ProcessorType.GENERATOR)
        self.assertEqual(doc.provenance['p1.0'].name, 'libfolia')
        self.assertEqual(doc.provenance['p2.1'].name, 'proycon')
        self.assertEqual(doc.provenance['p2.1'].type, folia.ProcessorType.MANUAL)
        annotators = list(doc.getannotators(folia.PosAnnotation, "http://ilk.uvt.nl/folia/sets/frog-mbpos-cgn" ))
        self.assertEqual(len(annotators),  3)
        #basically the same thing as above, but resolved to Processor instances:
        processors = list(doc.getprocessors(folia.PosAnnotation, "http://ilk.uvt.nl/folia/sets/frog-mbpos-cgn" ))
        self.assertEqual(len(processors),  3)
        #let's see if we got the right ones:
        self.assertEqual(processors[0].id, "p1.1")
        self.assertEqual(processors[0].name, "mbpos")
        self.assertEqual(processors[0].type, folia.ProcessorType.AUTO)
        self.assertEqual(processors[1].name, "proycon")
        self.assertEqual(processors[1].type, folia.ProcessorType.MANUAL)

    def test002_annotationsanity(self):
        """Provenance - Annotation sanity check"""
        doc = folia.Document(file=os.path.join(FOLIAPATH,'examples/provenance.2.0.0.folia.xml'), textvalidation=True, allowadhocsets=True)
        word = doc['untitled.p.1.s.1.w.1']
        self.assertEqual(word.annotation(folia.PosAnnotation).processor.id , "p1.1")
        self.assertEqual(word.annotation(folia.PosAnnotation).processor.name , "mbpos")
        self.assertEqual(word.annotation(folia.PosAnnotation).processor.type , folia.AnnotatorType.AUTO)
        #The old annotator attribute can also still be used and refers to the processor name (for backward API compatibility)
        self.assertEqual(word.annotation(folia.PosAnnotation).annotator, "mbpos")
        #The old annotatortype attribute can also still be used and refers to the processor type:
        self.assertEqual(word.annotation(folia.PosAnnotation).annotatortype , folia.AnnotatorType.AUTO)

        word = doc['untitled.p.1.s.1.w.2']
        self.assertEqual(word.annotation(folia.PosAnnotation).processor.id , "p2.1")
        self.assertEqual(word.annotation(folia.PosAnnotation).processor.name , "proycon")
        self.assertEqual(word.annotation(folia.PosAnnotation).processor.type , folia.AnnotatorType.MANUAL)
        self.assertEqual(word.annotation(folia.PosAnnotation).annotator, "proycon")

    def test003_default(self):
        """Provenance - Checking default/implicit processor/annotator"""
        doc = folia.Document(file=os.path.join(FOLIAPATH,'examples/provenance.2.0.0.folia.xml'), textvalidation=True, allowadhocsets=True)
        word = doc['untitled.p.1.s.1.w.2']
        self.assertEqual(word.annotation(folia.LemmaAnnotation).processor.id , "p1.2")
        self.assertEqual(word.annotation(folia.LemmaAnnotation).processor.name , "mblem")
        self.assertEqual(word.annotation(folia.LemmaAnnotation).processor.type , folia.AnnotatorType.AUTO)
        #The old annotator attribute can also still be used and refers to the processor name:
        self.assertEqual(word.annotation(folia.LemmaAnnotation).annotator, "mblem")

    def test004_create(self):
        """Provenance - Create a document with a processor"""
        doc = folia.Document(id="test", processor=folia.Processor("TestSuite",id="p0"))
        self.assertIsInstance(doc.provenance, folia.Provenance)
        self.assertEqual(doc.provenance['p0'].name, 'TestSuite')
        xmlref = """<FoLiA xmlns:xlink="http://www.w3.org/1999/xlink" xmlns="http://ilk.uvt.nl/folia" xml:id="test" version="2.0.0" generator="foliapy-v2.0.0">
  <metadata type="native">
    <annotations>
      <text-annotation set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/text.foliaset.ttl"/>
    </annotations>
    <provenance>
      <processor xml:id="p0" name="TestSuite" type="auto"/>
    </provenance>
  </metadata>
</FoLiA>
"""
        self.assertTrue( xmlcheck(doc.xmlstring(), xmlref) )

    def test005a_create_flat_explicit(self):
        """Provenance - Create a document with flat processors - Explicit processor assignment"""
        doc = folia.Document(id="test")
        doc.declare(folia.AnnotationType.TOKEN, "adhoc", folia.Processor("SomeTokeniser", id="p0.1",version=1))
        doc.declare(folia.AnnotationType.SENTENCE, "adhoc", folia.Processor("SentenceSplitter", id="p0.2",version=1))
        body = doc.append(folia.Text)
        sentence = body.append(folia.Sentence, processor="p0.2")
        w = sentence.append(folia.Word, "hello", processor="p0.1")
        sentence.append(folia.Word, "world", processor="p0.1")
        self.assertEqual(w.processor, doc.provenance["p0.1"])
        with open(os.path.join(FOLIAPATH,'examples/tests/provenance-flat-implicit.2.0.0.folia.xml'),'r',encoding='utf-8') as f: #not a typo, 'implicit' refers to the fact annotation don't get a processor attribute
            xmlref = f.read()
        self.assertTrue( xmlcheck(doc.xmlstring(), xmlref) )

    def test005b_create_flat_implicit(self):
        """Provenance - Create a document with flat processors - Implicit processor assignment (defaults)"""
        doc = folia.Document(id="test")
        doc.declare(folia.AnnotationType.TOKEN, "adhoc", folia.Processor("SomeTokeniser", id="p0.1",version=1))
        doc.declare(folia.AnnotationType.SENTENCE, "adhoc", folia.Processor("SentenceSplitter", id="p0.2",version=1))
        body = doc.append(folia.Text)
        sentence = body.append(folia.Sentence)
        w = sentence.append(folia.Word, "hello")
        sentence.append(folia.Word, "world")
        self.assertEqual(w.processor, doc.provenance["p0.1"]) #even though implicit, the processor attribute should be there!!!
        #This reference is identical to the previous test
        with open(os.path.join(FOLIAPATH,'examples/tests/provenance-flat-implicit.2.0.0.folia.xml'),'r',encoding='utf-8') as f:
            xmlref = f.read()
        self.assertTrue( xmlcheck(doc.xmlstring(), xmlref) )

    def test005c_create_flat_explicit_multi(self):
        """Provenance - Create a document with flat processors - Explicit multiple processor assignment"""
        doc = folia.Document(id="test")
        doc.declare(folia.AnnotationType.TOKEN, "adhoc", folia.Processor("SomeTokeniser", id="p0.1",version=1))
        doc.declare(folia.AnnotationType.SENTENCE, "adhoc", folia.Processor("SentenceSplitter", id="p0.2",version=1))
        #we declare some extra processors (even though we don't really use them), but this means the annotations will need to serialise an explicit processor= attribute
        doc.declare(folia.AnnotationType.TOKEN, "adhoc", folia.Processor("SomeOtherTokeniser", id="p0.3",version=1))
        doc.declare(folia.AnnotationType.SENTENCE, "adhoc", folia.Processor("OtherSentenceSplitter", id="p0.4",version=1))
        body = doc.append(folia.Text)
        sentence = body.append(folia.Sentence, processor="p0.2")
        w = sentence.append(folia.Word, "hello", processor="p0.1")
        sentence.append(folia.Word, "world", processor="p0.1")
        self.assertEqual(w.processor, doc.provenance["p0.1"])
        with open(os.path.join(FOLIAPATH,'examples/tests/provenance-flat-explicit.2.0.0.folia.xml'),'r',encoding='utf-8') as f: #not a typo, 'implicit' refers to the fact annotation don't get a processor attribute
            xmlref = f.read()
        self.assertTrue( xmlcheck(doc.xmlstring(), xmlref) )

    def test005d_create_flat_implicit_multi(self):
        """Provenance - Create a document with flat processors - Implicit multiple processor assignment (impossible)"""
        doc = folia.Document(id="test")
        doc.declare(folia.AnnotationType.TOKEN, "adhoc", folia.Processor("SomeTokeniser", id="p0.1",version=1))
        doc.declare(folia.AnnotationType.SENTENCE, "adhoc", folia.Processor("SentenceSplitter", id="p0.2",version=1))
        #we declare some extra processors (even though we don't really use them), but this means the annotations will need to serialise an explicit processor= attribute
        doc.declare(folia.AnnotationType.TOKEN, "adhoc", folia.Processor("SomeOtherTokeniser", id="p0.3",version=1))
        doc.declare(folia.AnnotationType.SENTENCE, "adhoc", folia.Processor("OtherSentenceSplitter", id="p0.4",version=1))
        body = doc.append(folia.Text)
        sentence = body.append(folia.Sentence, processor="p0.2") #ok, explicit processor
        self.assertRaises( folia.NoDefaultError, sentence.append, folia.Word, "hello") #exception, implicit processor is ambiguous

    def test006_create_nested(self):
        """Provenance - Create a document with a nested processors (implicit)"""
        doc = folia.Document(id="test", processor=folia.Processor("TestSuite",id="p0"))
        doc.declare(folia.AnnotationType.TOKEN, "adhoc", folia.Processor("SomeTokeniser", id="p0.1",version=1))
        doc.declare(folia.AnnotationType.SENTENCE, "adhoc", folia.Processor("SentenceSplitter", id="p0.2",version=1))
        body = doc.append(folia.Text)
        sentence = body.append(folia.Sentence)
        w = sentence.append(folia.Word, "hello")
        sentence.append(folia.Word, "world")
        self.assertEqual(w.processor, doc.provenance["p0.1"]) #even though implicit, the processor attribute should be there!!!
        with open(os.path.join(FOLIAPATH,'examples/tests/provenance-nested-implicit.2.0.0.folia.xml'),'r',encoding='utf-8') as f: #not a typo, 'implicit' refers to the fact annotation don't get a processor attribute
            xmlref = f.read()
        self.assertTrue( xmlcheck(doc.xmlstring(), xmlref) )

###################### OLD TESTS ##########################


class Test01Read(unittest.TestCase):

    def test1_readfromfile(self):
        """Reading from file"""
        #write example to file
        f = open(os.path.join(TMPDIR,'foliatest.xml'),'w',encoding='utf-8')
        f.write(LEGACYEXAMPLE)
        f.close()

        doc = folia.Document(file=os.path.join(TMPDIR,'foliatest.xml'))
        self.assertTrue(isinstance(doc,folia.Document))

        #sanity check: reading from file must yield the exact same data as reading from string
        doc2 = folia.Document(string=LEGACYEXAMPLE)
        self.assertEqual( doc, doc2)

    def test1a_readfromfile(self):
        """Reading from GZ file"""
        #write example to file
        f = gzip.GzipFile(os.path.join(TMPDIR,'foliatest.xml.gz'),'w')
        f.write(LEGACYEXAMPLE.encode('utf-8'))
        f.close()

        doc = folia.Document(file=os.path.join(TMPDIR,'foliatest.xml.gz'))
        self.assertTrue(isinstance(doc,folia.Document))

        #sanity check: reading from file must yield the exact same data as reading from string
        doc2 = folia.Document(string=LEGACYEXAMPLE)
        self.assertEqual( doc, doc2)


    def test1b_readfromfile(self):
        """Reading from BZ2 file"""
        #write example to file
        f = bz2.BZ2File(os.path.join(TMPDIR,'foliatest.xml.bz2'),'w')
        f.write(LEGACYEXAMPLE.encode('utf-8'))
        f.close()

        doc = folia.Document(file=os.path.join(TMPDIR,'foliatest.xml.bz2'))
        self.assertTrue(isinstance(doc,folia.Document))

        #sanity check: reading from file must yield the exact same data as reading from string
        doc2 = folia.Document(string=LEGACYEXAMPLE)
        self.assertEqual( doc, doc2)


    def test2_readfromstring(self):
        """Reading from string (unicode)"""
        doc = folia.Document(string=LEGACYEXAMPLE)
        self.assertTrue(isinstance(doc,folia.Document))

    def test2b_readfromstring(self):
        """Reading from string (bytes)"""
        doc = folia.Document(string=LEGACYEXAMPLE.encode('utf-8'))
        self.assertTrue(isinstance(doc,folia.Document))

    def test3_readfromstring(self):
        """Reading from pre-parsed XML tree (as unicode(Py2)/str(Py3) obj)"""
        doc = folia.Document(tree=ElementTree.parse(BytesIO(LEGACYEXAMPLE.encode('utf-8'))))
        self.assertTrue(isinstance(doc,folia.Document))



class Test02Sanity(unittest.TestCase):

    def setUp(self):
        self.doc = folia.Document(string=LEGACYEXAMPLE, textvalidation=True)

    def test000_count_text(self):
        """Sanity check - One text """
        self.assertEqual( len(self.doc), 1)
        self.assertTrue( isinstance( self.doc[0], folia.Text ))

    def test001_count_paragraphs(self): #Covered by new test E001
        """Sanity check - Paragraph count"""
        self.assertEqual( len(list(self.doc.paragraphs())) , 3)

    def test002_count_sentences(self): #Covered by new test E001
        """Sanity check - Sentences count"""
        self.assertEqual( len(list(self.doc.sentences())) , 17)

    def test003a_count_words(self): #Covered by new test E001
        """Sanity check - Word count"""
        self.assertEqual( len(list(self.doc.words())) , 190)

    def test003b_iter_words(self): #Covered by new test E001
        """Sanity check - Words"""
        self.assertEqual( [x.id for x in self.doc.words() ], ['WR-P-E-J-0000000001.head.1.s.1.w.1', 'WR-P-E-J-0000000001.p.1.s.1.w.1', 'WR-P-E-J-0000000001.p.1.s.1.w.2', 'WR-P-E-J-0000000001.p.1.s.1.w.3', 'WR-P-E-J-0000000001.p.1.s.1.w.4', 'WR-P-E-J-0000000001.p.1.s.1.w.5', 'WR-P-E-J-0000000001.p.1.s.1.w.6', 'WR-P-E-J-0000000001.p.1.s.1.w.7', 'WR-P-E-J-0000000001.p.1.s.1.w.8', 'WR-P-E-J-0000000001.p.1.s.2.w.1', 'WR-P-E-J-0000000001.p.1.s.2.w.2', 'WR-P-E-J-0000000001.p.1.s.2.w.3', 'WR-P-E-J-0000000001.p.1.s.2.w.4', 'WR-P-E-J-0000000001.p.1.s.2.w.5', 'WR-P-E-J-0000000001.p.1.s.2.w.6', 'WR-P-E-J-0000000001.p.1.s.2.w.7', 'WR-P-E-J-0000000001.p.1.s.2.w.8', 'WR-P-E-J-0000000001.p.1.s.2.w.9', 'WR-P-E-J-0000000001.p.1.s.2.w.10', 'WR-P-E-J-0000000001.p.1.s.2.w.11', 'WR-P-E-J-0000000001.p.1.s.2.w.12', 'WR-P-E-J-0000000001.p.1.s.2.w.13', 'WR-P-E-J-0000000001.p.1.s.2.w.14', 'WR-P-E-J-0000000001.p.1.s.2.w.15', 'WR-P-E-J-0000000001.p.1.s.2.w.16', 'WR-P-E-J-0000000001.p.1.s.2.w.17', 'WR-P-E-J-0000000001.p.1.s.2.w.18', 'WR-P-E-J-0000000001.p.1.s.2.w.19', 'WR-P-E-J-0000000001.p.1.s.2.w.20', 'WR-P-E-J-0000000001.p.1.s.2.w.21', 'WR-P-E-J-0000000001.p.1.s.2.w.22', 'WR-P-E-J-0000000001.p.1.s.2.w.23', 'WR-P-E-J-0000000001.p.1.s.2.w.24-25', 'WR-P-E-J-0000000001.p.1.s.2.w.26', 'WR-P-E-J-0000000001.p.1.s.2.w.27', 'WR-P-E-J-0000000001.p.1.s.2.w.28', 'WR-P-E-J-0000000001.p.1.s.2.w.29', 'WR-P-E-J-0000000001.p.1.s.3.w.1', 'WR-P-E-J-0000000001.p.1.s.3.w.2', 'WR-P-E-J-0000000001.p.1.s.3.w.3', 'WR-P-E-J-0000000001.p.1.s.3.w.4', 'WR-P-E-J-0000000001.p.1.s.3.w.5', 'WR-P-E-J-0000000001.p.1.s.3.w.6', 'WR-P-E-J-0000000001.p.1.s.3.w.7', 'WR-P-E-J-0000000001.p.1.s.3.w.8', 'WR-P-E-J-0000000001.p.1.s.3.w.9', 'WR-P-E-J-0000000001.p.1.s.3.w.10', 'WR-P-E-J-0000000001.p.1.s.3.w.11', 'WR-P-E-J-0000000001.p.1.s.3.w.12', 'WR-P-E-J-0000000001.p.1.s.3.w.13', 'WR-P-E-J-0000000001.p.1.s.3.w.14', 'WR-P-E-J-0000000001.p.1.s.3.w.15', 'WR-P-E-J-0000000001.p.1.s.3.w.16', 'WR-P-E-J-0000000001.p.1.s.3.w.17', 'WR-P-E-J-0000000001.p.1.s.3.w.18', 'WR-P-E-J-0000000001.p.1.s.3.w.19', 'WR-P-E-J-0000000001.p.1.s.3.w.20', 'WR-P-E-J-0000000001.p.1.s.3.w.21', 'WR-P-E-J-0000000001.p.1.s.4.w.1', 'WR-P-E-J-0000000001.p.1.s.4.w.2', 'WR-P-E-J-0000000001.p.1.s.4.w.3', 'WR-P-E-J-0000000001.p.1.s.4.w.4', 'WR-P-E-J-0000000001.p.1.s.4.w.5', 'WR-P-E-J-0000000001.p.1.s.4.w.6', 'WR-P-E-J-0000000001.p.1.s.4.w.7', 'WR-P-E-J-0000000001.p.1.s.4.w.8', 'WR-P-E-J-0000000001.p.1.s.4.w.9', 'WR-P-E-J-0000000001.p.1.s.4.w.10', 'WR-P-E-J-0000000001.p.1.s.5.w.1', 'WR-P-E-J-0000000001.p.1.s.5.w.2', 'WR-P-E-J-0000000001.p.1.s.5.w.3', 'WR-P-E-J-0000000001.p.1.s.5.w.4', 'WR-P-E-J-0000000001.p.1.s.5.w.5', 'WR-P-E-J-0000000001.p.1.s.5.w.6', 'WR-P-E-J-0000000001.p.1.s.5.w.7', 'WR-P-E-J-0000000001.p.1.s.5.w.8', 'WR-P-E-J-0000000001.p.1.s.5.w.9', 'WR-P-E-J-0000000001.p.1.s.5.w.10', 'WR-P-E-J-0000000001.p.1.s.5.w.11', 'WR-P-E-J-0000000001.p.1.s.5.w.12', 'WR-P-E-J-0000000001.p.1.s.5.w.13', 'WR-P-E-J-0000000001.p.1.s.5.w.14', 'WR-P-E-J-0000000001.p.1.s.5.w.15', 'WR-P-E-J-0000000001.p.1.s.5.w.16', 'WR-P-E-J-0000000001.p.1.s.5.w.17', 'WR-P-E-J-0000000001.p.1.s.5.w.18', 'WR-P-E-J-0000000001.p.1.s.5.w.19', 'WR-P-E-J-0000000001.p.1.s.5.w.20', 'WR-P-E-J-0000000001.p.1.s.5.w.21', 'WR-P-E-J-0000000001.p.1.s.6.w.1', 'WR-P-E-J-0000000001.p.1.s.6.w.2', 'WR-P-E-J-0000000001.p.1.s.6.w.3', 'WR-P-E-J-0000000001.p.1.s.6.w.4', 'WR-P-E-J-0000000001.p.1.s.6.w.5', 'WR-P-E-J-0000000001.p.1.s.6.w.6', 'WR-P-E-J-0000000001.p.1.s.6.w.7', 'WR-P-E-J-0000000001.p.1.s.6.w.8', 'WR-P-E-J-0000000001.p.1.s.6.w.9', 'WR-P-E-J-0000000001.p.1.s.6.w.10', 'WR-P-E-J-0000000001.p.1.s.6.w.11', 'WR-P-E-J-0000000001.p.1.s.6.w.12', 'WR-P-E-J-0000000001.p.1.s.6.w.13', 'WR-P-E-J-0000000001.p.1.s.6.w.14', 'WR-P-E-J-0000000001.p.1.s.6.w.15', 'WR-P-E-J-0000000001.p.1.s.6.w.16', 'WR-P-E-J-0000000001.p.1.s.6.w.17', 'WR-P-E-J-0000000001.p.1.s.6.w.18', 'WR-P-E-J-0000000001.p.1.s.6.w.19', 'WR-P-E-J-0000000001.p.1.s.6.w.20', 'WR-P-E-J-0000000001.p.1.s.6.w.21', 'WR-P-E-J-0000000001.p.1.s.6.w.22', 'WR-P-E-J-0000000001.p.1.s.6.w.23', 'WR-P-E-J-0000000001.p.1.s.6.w.24', 'WR-P-E-J-0000000001.p.1.s.6.w.25', 'WR-P-E-J-0000000001.p.1.s.6.w.26', 'WR-P-E-J-0000000001.p.1.s.6.w.27', 'WR-P-E-J-0000000001.p.1.s.6.w.28', 'WR-P-E-J-0000000001.p.1.s.6.w.29', 'WR-P-E-J-0000000001.p.1.s.6.w.30', 'WR-P-E-J-0000000001.p.1.s.6.w.31', 'WR-P-E-J-0000000001.p.1.s.6.w.32', 'WR-P-E-J-0000000001.p.1.s.6.w.33', 'WR-P-E-J-0000000001.p.1.s.6.w.34', 'WR-P-E-J-0000000001.p.1.s.7.w.1', 'WR-P-E-J-0000000001.p.1.s.7.w.2', 'WR-P-E-J-0000000001.p.1.s.7.w.3', 'WR-P-E-J-0000000001.p.1.s.7.w.4', 'WR-P-E-J-0000000001.p.1.s.7.w.5', 'WR-P-E-J-0000000001.p.1.s.7.w.6', 'WR-P-E-J-0000000001.p.1.s.7.w.7', 'WR-P-E-J-0000000001.p.1.s.7.w.8', 'WR-P-E-J-0000000001.p.1.s.7.w.9', 'WR-P-E-J-0000000001.p.1.s.7.w.10', 'WR-P-E-J-0000000001.p.1.s.8.w.1', 'WR-P-E-J-0000000001.p.1.s.8.w.2', 'WR-P-E-J-0000000001.p.1.s.8.w.3', 'WR-P-E-J-0000000001.p.1.s.8.w.4', 'WR-P-E-J-0000000001.p.1.s.8.w.5', 'WR-P-E-J-0000000001.p.1.s.8.w.6', 'WR-P-E-J-0000000001.p.1.s.8.w.7', 'WR-P-E-J-0000000001.p.1.s.8.w.8', 'WR-P-E-J-0000000001.p.1.s.8.w.9', 'WR-P-E-J-0000000001.p.1.s.8.w.10', 'WR-P-E-J-0000000001.p.1.s.8.w.11', 'WR-P-E-J-0000000001.p.1.s.8.w.12', 'WR-P-E-J-0000000001.p.1.s.8.w.13', 'WR-P-E-J-0000000001.p.1.s.8.w.14', 'WR-P-E-J-0000000001.p.1.s.8.w.15', 'WR-P-E-J-0000000001.p.1.s.8.w.16', 'WR-P-E-J-0000000001.p.1.s.8.w.17', 'entry.1.term.1.w.1', 'sandbox.list.1.listitem.1.s.1.w.1', 'sandbox.list.1.listitem.1.s.1.w.2', 'sandbox.list.1.listitem.2.s.1.w.1', 'sandbox.list.1.listitem.2.s.1.w.2', 'sandbox.figure.1.caption.s.1.w.1', 'sandbox.figure.1.caption.s.1.w.2', 'WR-P-E-J-0000000001.sandbox.2.s.1.w.1', 'WR-P-E-J-0000000001.sandbox.2.s.1.w.2', 'WR-P-E-J-0000000001.sandbox.2.s.1.w.3', 'WR-P-E-J-0000000001.sandbox.2.s.1.w.4', 'WR-P-E-J-0000000001.sandbox.2.s.1.w.5', 'WR-P-E-J-0000000001.sandbox.2.s.1.w.6', 'WR-P-E-J-0000000001.sandbox.2.s.2.w.1', 'WR-P-E-J-0000000001.sandbox.2.s.2.w.2', 'WR-P-E-J-0000000001.sandbox.2.s.2.w.3', 'WR-P-E-J-0000000001.sandbox.2.s.2.w.4', 'WR-P-E-J-0000000001.sandbox.2.s.2.w.5', 'WR-P-E-J-0000000001.sandbox.2.s.2.w.6', 'WR-P-E-J-0000000001.sandbox.2.s.2.w.7', 'WR-P-E-J-0000000001.sandbox.2.s.2.w.8', 'WR-P-E-J-0000000001.sandbox.2.s.3.w.1', 'WR-P-E-J-0000000001.sandbox.2.s.3.w.2', 'WR-P-E-J-0000000001.sandbox.2.s.3.w.3', 'WR-P-E-J-0000000001.sandbox.2.s.3.w.4', 'WR-P-E-J-0000000001.sandbox.2.s.3.w.6', 'example.table.1.w.1', 'example.table.1.w.2', 'example.table.1.w.3', 'example.table.1.w.4', 'example.table.1.w.5', 'example.table.1.w.6', 'example.table.1.w.7', 'example.table.1.w.8', 'example.table.1.w.9', 'example.table.1.w.10', 'example.table.1.w.11', 'example.table.1.w.12', 'example.table.1.w.13', 'example.table.1.w.14'] )

    def test004_first_word(self): #Covered by new test E001
        """Sanity check - First word"""
        #grab first word
        w = self.doc.words(0) # shortcut for doc.words()[0]
        self.assertTrue( isinstance(w, folia.Word) )
        self.assertEqual( w.id , 'WR-P-E-J-0000000001.head.1.s.1.w.1' )
        self.assertEqual( w.text() , "Stemma" )
        self.assertEqual( str(w) , "Stemma" ) #should be unicode object also in Py2!


    def test005_last_word(self): #Covered by new test E001
        """Sanity check - Last word"""
        #grab last word
        w = self.doc.words(-1) # shortcut for doc.words()[0]
        self.assertTrue( isinstance(w, folia.Word) )
        self.assertEqual( w.id , "example.table.1.w.14" )
        self.assertEqual( w.text() , "University" )
        self.assertEqual( str(w) , "University" )

    def test006_second_sentence(self): #Covered by new test E001
        """Sanity check - Sentence"""
        #grab second sentence
        s = self.doc.sentences(1)
        self.assertTrue( isinstance(s, folia.Sentence) )
        self.assertEqual( s.id, 'WR-P-E-J-0000000001.p.1.s.1' )
        self.assertFalse( s.hastext() )
        self.assertEqual( str(s), "Stemma is een ander woord voor stamboom." )

    def test006b_sentencetest(self):
        """Sanity check - Sentence text (including retaining tokenisation)"""
        #grab second sentence
        s = self.doc['WR-P-E-J-0000000001.p.1.s.5']
        self.assertTrue( isinstance(s, folia.Sentence) )
        self.assertFalse( s.hastext() )
        self.assertEqual( s.text(), "De andere handschriften krijgen ook een letter die verband kan houden met hun plaats van oorsprong óf plaats van bewaring.")
        self.assertEqual( s.text('current',True), "De andere handschriften krijgen ook een letter die verband kan houden met hun plaats van oorsprong óf plaats van bewaring .") #not detokenised
        self.assertEqual( s.toktext(), "De andere handschriften krijgen ook een letter die verband kan houden met hun plaats van oorsprong óf plaats van bewaring .") #just an alias for the above

    def test007_index(self): #Covered by new test E001
        """Sanity check - Index"""
        #grab something using the index
        w = self.doc['WR-P-E-J-0000000001.p.1.s.2.w.7']
        self.assertTrue( isinstance(w, folia.Word) )
        self.assertEqual( self.doc['WR-P-E-J-0000000001.p.1.s.2.w.7'] , self.doc.index['WR-P-E-J-0000000001.p.1.s.2.w.7'] )
        self.assertEqual( w.id , 'WR-P-E-J-0000000001.p.1.s.2.w.7' )
        self.assertEqual( w.text() , "stamboom" )

    def test008_division(self):
        """Sanity check - Division + head"""

        #grab something using the index
        div = self.doc['WR-P-E-J-0000000001.div0.1']
        self.assertTrue( isinstance(div, folia.Division) )
        self.assertEqual( div.head() , self.doc['WR-P-E-J-0000000001.head.1'] )
        self.assertEqual( len(div.head()) ,1 ) #Head contains one element (one sentence)

    def test009_pos(self):
        """Sanity check - Token Annotation - Pos"""
        #grab first word
        w = self.doc.words(0)


        self.assertEqual( w.annotation(folia.PosAnnotation), next(w.select(folia.PosAnnotation)) ) #w.annotation() selects the single first annotation of that type, select is the generic method to retrieve pretty much everything
        self.assertTrue( isinstance(w.annotation(folia.PosAnnotation), folia.PosAnnotation) )
        self.assertTrue( issubclass(folia.PosAnnotation, folia.AbstractInlineAnnotation) )

        self.assertEqual( w.annotation(folia.PosAnnotation).cls, 'N(soort,ev,basis,onz,stan)' ) #cls is used everywhere instead of class, since class is a reserved keyword in python
        self.assertEqual( w.pos(),'N(soort,ev,basis,onz,stan)' ) #w.pos() is just a direct shortcut for getting the class
        self.assertEqual( w.annotation(folia.PosAnnotation).set, 'https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn' )
        self.assertEqual( w.annotation(folia.PosAnnotation).annotator, 'frog' )
        self.assertEqual( w.annotation(folia.PosAnnotation).annotatortype, folia.AnnotatorType.AUTO )


    def test010_lemma(self):
        """Sanity check - Token Annotation - Lemma"""
        #grab first word
        w = self.doc.words(0)

        self.assertEqual( w.annotation(folia.LemmaAnnotation), w.annotation(folia.LemmaAnnotation) ) #w.lemma() is just a shortcut
        self.assertEqual( w.annotation(folia.LemmaAnnotation), next(w.select(folia.LemmaAnnotation)) ) #w.annotation() selects the single first annotation of that type, select is the generic method to retrieve pretty much everything
        self.assertTrue( isinstance(w.annotation(folia.LemmaAnnotation), folia.LemmaAnnotation))

        self.assertEqual( w.annotation(folia.LemmaAnnotation).cls, 'stemma' )
        self.assertEqual( w.lemma(),'stemma' ) #w.lemma() is just a direct shortcut for getting the class
        self.assertEqual( w.annotation(folia.LemmaAnnotation).set, 'lemmas-nl' )
        self.assertEqual( w.annotation(folia.LemmaAnnotation).annotator, 'tadpole' )
        self.assertEqual( w.annotation(folia.LemmaAnnotation).annotatortype, folia.AnnotatorType.AUTO )

    def test011_tokenannot_notexist(self):
        """Sanity check - Token Annotation - Non-existing element"""
        #grab first word
        w = self.doc.words(0)

        self.assertEqual( w.count(folia.SenseAnnotation), 0)  #list
        self.assertRaises( folia.NoSuchAnnotation, w.annotation, folia.SenseAnnotation) #exception



    def test012_correction(self):
        """Sanity check - Correction - Text"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.6.w.31']
        c = w.annotation(folia.Correction)

        self.assertEqual( len(list(c.new())), 1)
        self.assertEqual( len(list(c.original())), 1)

        self.assertEqual( w.text(), 'vierkante')
        self.assertEqual( c.new(0), 'vierkante')
        self.assertEqual( c.original(0) , 'vierkant')

    def test013_correction(self):
        """Sanity check - Correction - Token Annotation"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.6.w.32']
        c = w.annotation(folia.Correction)

        self.assertEqual( len(list(c.new())), 1)
        self.assertEqual( len(list(c.original())), 1)

        self.assertEqual( w.annotation(folia.LemmaAnnotation).cls , 'haak')
        self.assertEqual( c.new(0).cls, 'haak')
        self.assertEqual( c.original(0).cls, 'haaak')


    def test014_correction(self):
        """Sanity check - Correction - Suggestions (text)"""
        #grab first word
        w = self.doc['WR-P-E-J-0000000001.p.1.s.8.w.14']
        c = w.annotation(folia.Correction)
        self.assertTrue( isinstance(c, folia.Correction) )
        self.assertEqual( len(list(c.suggestions())), 2 )
        self.assertEqual( str(c.suggestions(0).text()), 'twijfelachtige' )
        self.assertEqual( str(c.suggestions(1).text()), 'ongewisse' )

    def test015_parenttest(self):
        """Sanity check - Checking if all elements know who's their daddy"""

        def check(parent, indent = ''):

            for child in parent:
                if isinstance(child, folia.AbstractElement) and not (isinstance(parent, folia.AbstractSpanAnnotation) and (isinstance(child, folia.Word) or isinstance(child, folia.Morpheme))): #words and morphemes are exempted in abstractspanannotation
                    #print indent + repr(child), child.id, child.cls
                    self.assertTrue( child.parent is parent)
                    check(child, indent + '  ')
            return True

        self.assertTrue( check(self.doc.data[0],'  ') )

    def test016a_description(self):
        """Sanity Check - Description"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.1.w.6']
        self.assertEqual( w.description(), 'Dit woordje is een voorzetsel, het is maar dat je het weet...')

    def test016b_description(self):
        """Sanity Check - Error on non-existing description"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.1.w.7']
        self.assertRaises( folia.NoSuchAnnotation,  w.description)

    def test017_gap(self):
        """Sanity Check - Gap"""
        gap = self.doc["WR-P-E-J-0000000001.gap.1"]
        self.assertEqual( gap.content().strip()[:11], 'De tekst is')
        self.assertEqual( gap.cls, 'backmatter')
        self.assertEqual( gap.description(), 'Backmatter')

    def test018_subtokenannot(self):
        """Sanity Check - Subtoken annotation (part of speech)"""
        w= self.doc['WR-P-E-J-0000000001.p.1.s.2.w.5']
        p = w.annotation(folia.PosAnnotation)
        self.assertEqual( p.feat('wvorm'), 'pv' )
        self.assertEqual( p.feat('pvtijd'), 'tgw' )
        self.assertEqual( p.feat('pvagr'), 'met-t' )

    def test019_relation(self):
        """Sanity Check - Relation in same document"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.3.w.10']
        a = w.annotation(folia.Relation)
        target = next(a.resolve())
        self.assertEqual( target, self.doc['WR-P-E-J-0000000001.p.1.s.3.w.5'] )



    def test020a_spanannotation(self):
        """Sanity Check - Span Annotation (Syntax)"""
        s = self.doc['WR-P-E-J-0000000001.p.1.s.1']
        l = s.annotation(folia.SyntaxLayer)

        self.assertTrue( isinstance(l[0], folia.SyntacticUnit ) )
        self.assertEqual( l[0].cls,  'sentence' )
        self.assertEqual( l[0][0].cls,  'subject' )
        self.assertEqual( l[0][0].text(),  'Stemma' )
        self.assertEqual( l[0][1].cls,  'verb' )
        self.assertEqual( l[0][2].cls,  'predicate' )
        self.assertEqual( l[0][2][0].cls,  'np' )
        self.assertEqual( l[0][2][1].cls,  'pp' )
        self.assertEqual( l[0][2][1].text(),  'voor stamboom' )
        self.assertEqual( l[0][2].text(),  'een ander woord voor stamboom' )

    def test020b_spanannotation(self):
        """Sanity Check - Span Annotation (Chunking)"""
        s = self.doc['WR-P-E-J-0000000001.p.1.s.1']
        l = s.annotation(folia.ChunkingLayer)

        self.assertTrue( isinstance(l[0], folia.Chunk ) )
        self.assertEqual( l[0].text(),  'een ander woord' )
        self.assertEqual( l[1].text(),  'voor stamboom' )

    def test020c_spanannotation(self):
        """Sanity Check - Span Annotation (Entities)"""
        s = self.doc['WR-P-E-J-0000000001.p.1.s.1']
        l = s.annotation(folia.EntitiesLayer)

        self.assertTrue( isinstance(l[0], folia.Entity) )
        self.assertEqual( l[0].text(),  'ander woord' )


    def test020d_spanannotation(self):
        """Sanity Check - Span Annotation (Dependencies)"""
        s = self.doc['WR-P-E-J-0000000001.p.1.s.1']
        l = s.annotation(folia.DependenciesLayer)

        self.assertTrue( isinstance(l[0], folia.Dependency) )
        self.assertEqual( l[0].head().text(),  'is' )
        self.assertEqual( l[0].dependent().text(),  'Stemma' )
        self.assertEqual( l[0].cls,  'su' )

        self.assertTrue( isinstance(l[1], folia.Dependency) )
        self.assertEqual( l[1].head().text(),  'is' )
        self.assertEqual( l[1].dependent().text(),  'woord' )
        self.assertEqual( l[1].cls,'predc' )

        self.assertTrue( isinstance(l[2], folia.Dependency) )
        self.assertEqual( l[2].head().text(),  'woord' )
        self.assertEqual( l[2].dependent().text(),  'een' )
        self.assertEqual( l[2].cls,'det' )

        self.assertTrue( isinstance(l[3], folia.Dependency) )
        self.assertEqual( l[3].head().text(),  'woord' )
        self.assertEqual( l[3].dependent().text(),  'ander' )
        self.assertEqual( l[3].cls,'mod' )

        self.assertTrue( isinstance(l[4], folia.Dependency) )
        self.assertEqual( l[4].head().text(),  'woord' )
        self.assertEqual( l[4].dependent().text(),  'voor' )
        self.assertEqual( l[4].cls,'mod' )

        self.assertTrue( isinstance(l[5], folia.Dependency) )
        self.assertEqual( l[5].head().text(),  'voor' )
        self.assertEqual( l[5].dependent().text(),  'stamboom' )
        self.assertEqual( l[5].cls,'obj1' )

    def test020e_spanannotation(self):
        """Sanity Check - Span Annotation (Timedevent)"""
        s = self.doc['WR-P-E-J-0000000001.p.1.s.1']
        l = s.annotation(folia.TimingLayer)

        self.assertTrue( isinstance(l[0], folia.TimeSegment ) )
        self.assertEqual( l[0].text(),  'een ander woord' )
        self.assertEqual( l[1].cls, 'cough' )
        self.assertEqual( l[2].text(),  'voor stamboom' )

    def test020f_spanannotation(self):
        """Sanity Check - Co-Reference"""
        div = self.doc["WR-P-E-J-0000000001.div0.1"]
        deplayer = div.annotation(folia.DependenciesLayer)
        deps = list(deplayer.annotations(folia.Dependency))

        self.assertEqual( deps[0].cls,  'su' )
        self.assertEqual( deps[1].cls,  'predc' )
        self.assertEqual( deps[2].cls,  'det' )
        self.assertEqual( deps[3].cls,  'mod' )
        self.assertEqual( deps[4].cls,  'mod' )
        self.assertEqual( deps[5].cls,  'obj1' )

        self.assertEqual( deps[2].head().wrefs(0), self.doc['WR-P-E-J-0000000001.p.1.s.1.w.5'] )
        self.assertEqual( deps[2].dependent().wrefs(0), self.doc['WR-P-E-J-0000000001.p.1.s.1.w.3'] )


    def test020g_spanannotation(self):
        """Sanity Check - Semantic Role Labelling"""
        s = self.doc['WR-P-E-J-0000000001.p.1.s.7']
        semrolelayer = s.annotation(folia.SemanticRolesLayer)
        predicate = semrolelayer.annotation(folia.Predicate)
        self.assertEqual( predicate.cls,  'aanduiden' )

        roles = list(predicate.annotations(folia.SemanticRole))

        self.assertEqual( roles[0].cls,  'actor' )
        self.assertEqual( roles[1].cls,  'patient' )

        self.assertEqual( roles[0].wrefs(0), self.doc['WR-P-E-J-0000000001.p.1.s.7.w.3'] )
        self.assertEqual( roles[1].wrefs(0), self.doc['WR-P-E-J-0000000001.p.1.s.7.w.4'] )
        self.assertEqual( roles[1].wrefs(1), self.doc['WR-P-E-J-0000000001.p.1.s.7.w.5'] )


    def test021_previousword(self):
        """Sanity Check - Obtaining previous word"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.2.w.7']
        prevw = w.previous()
        self.assertTrue( isinstance(prevw, folia.Word) )
        self.assertEqual( prevw.text(),  "zo'n" )

    def test021b_previousword_noscope(self):
        """Sanity Check - Obtaining previous word without scope constraint"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.4.w.1']
        prevw = w.previous(folia.Word, None)
        self.assertTrue( isinstance(prevw, folia.Word) )
        self.assertEqual( prevw.text(),  "." )

    def test021c_previousword_constrained(self):
        """Sanity Check - Obtaining non-existing previous word with scope constraint"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.4.w.1']
        prevw = w.previous(folia.Word, [folia.Sentence])
        self.assertEqual(prevw, None)

    def test022_nextword(self):
        """Sanity Check - Obtaining next word"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.2.w.7']
        nextw = w.next()
        self.assertTrue( isinstance(nextw, folia.Word) )
        self.assertEqual( nextw.text(),  "," )

    def test023_leftcontext(self):
        """Sanity Check - Obtaining left context"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.2.w.7']
        context = w.leftcontext(3)
        self.assertEqual( [ x.text() for x in context ], ['wetenschap','wordt',"zo'n"] )

    def test024_rightcontext(self):
        """Sanity Check - Obtaining right context"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.2.w.7']
        context = w.rightcontext(3)
        self.assertEqual( [ x.text() for x in context ], [',','onder','de'] )

    def test025_fullcontext(self):
        """Sanity Check - Obtaining full context"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.2.w.7']
        context = w.context(3)
        self.assertEqual( [ x.text() for x in context ], ['wetenschap','wordt',"zo'n",'stamboom',',','onder','de'] )

    def test026_feature(self):
        """Sanity Check - Features"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.6.w.1']
        pos = w.annotation(folia.PosAnnotation)
        self.assertTrue( isinstance(pos, folia.PosAnnotation) )
        self.assertEqual(pos.cls,'WW(vd,prenom,zonder)')
        self.assertEqual( len(pos),  1)
        features = list(pos.select(folia.Feature))
        self.assertEqual( len(features),  1)
        self.assertTrue( isinstance(features[0], folia.Feature))
        self.assertEqual( features[0].subset, 'head')
        self.assertEqual( features[0].cls, 'WW')

    def test027_datetime(self):
        """Sanity Check - Time stamp"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.8.w.15']

        pos = w.annotation(folia.PosAnnotation)
        self.assertEqual( pos.datetime, datetime(2011, 7, 20, 19, 0, 1) )

        self.assertTrue( xmlcheck(pos.xmlstring(), '<pos xmlns="http://ilk.uvt.nl/folia" set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" class="N(soort,ev,basis,zijd,stan)" datetime="2011-07-20T19:00:01"/>') )

    def test028_wordparents(self):
        """Sanity Check - Finding parents of word"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.8.w.15']

        s = w.sentence()
        self.assertTrue( isinstance(s, folia.Sentence) )
        self.assertEqual( s.id, 'WR-P-E-J-0000000001.p.1.s.8')

        p = w.paragraph()
        self.assertTrue( isinstance(p, folia.Paragraph) )
        self.assertEqual( p.id, 'WR-P-E-J-0000000001.p.1')

        div = w.division()
        self.assertTrue( isinstance(div, folia.Division) )
        self.assertEqual( div.id, 'WR-P-E-J-0000000001.div0.1')

        self.assertEqual( w.incorrection(), None)

    def test0029_quote(self):
        """Sanity Check - Quote"""
        q = self.doc['WR-P-E-J-0000000001.p.1.s.8.q.1']
        self.assertTrue( isinstance(q, folia.Quote) )
        self.assertEqual(q.text(), 'volle lijn')

        s = self.doc['WR-P-E-J-0000000001.p.1.s.8']
        self.assertEqual(s.text(), 'Een volle lijn duidt op een verwantschap , terweil een stippelijn op een onzekere verwantschap duidt .') #(spelling errors are present in sentence)

        #a word from the quote
        w = self.doc['WR-P-E-J-0000000001.p.1.s.8.w.2']
        #check if sentence matches
        self.assertTrue( (w.sentence() is s) )

    def test030_textcontent(self):
        """Sanity check - Text Content"""
        s = self.doc['WR-P-E-J-0000000001.p.1.s.4']

        self.assertEqual( s.text(), 'De hoofdletter A wordt gebruikt voor het originele handschrift.')
        self.assertEqual( s.stricttext(), 'De hoofdletter A wordt gebruikt voor het originele handschrift.')
        self.assertEqual( s.textcontent().text(), 'De hoofdletter A wordt gebruikt voor het originele handschrift.')
        self.assertEqual( s.textcontent('original').text(), 'De hoofdletter A wordt gebruikt voor het originele handschrift.')
        self.assertRaises( folia.NoSuchText, s.text, 'BLAH' )


        w = self.doc['WR-P-E-J-0000000001.p.1.s.4.w.2']
        self.assertEqual( w.text(), 'hoofdletter')

        self.assertEqual( w.textcontent().text(), 'hoofdletter')
        self.assertEqual( w.textcontent().offset, 3)

        w2 = self.doc['WR-P-E-J-0000000001.p.1.s.6.w.31']
        self.assertEqual( w2.text(), 'vierkante')
        self.assertEqual( w2.stricttext(), 'vierkante')


    def test030b_textcontent(self):
        """Sanity check - Text Content (2)"""
        s = self.doc['sandbox.3.head']
        t = s.textcontent()
        self.assertEqual( len(t), 3)
        self.assertEqual( t.text(), "De \nFoLiA developers zijn:")
        self.assertEqual( t[0], "De ")
        self.assertTrue( isinstance(t[1], folia.TextMarkupString) )
        self.assertEqual( t[1].text(), "\nFoLiA developers")
        self.assertEqual( t[2], " zijn:")

    def test030c_textclassattrib(self):
        """Sanity check - Text class attribute"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.4.w.5']
        self.assertEqual( w.annotation(folia.PosAnnotation).textclass , 'original')
        self.assertEqual( w.annotation(folia.LemmaAnnotation).textclass , 'original')

    def test030d_textclassattrib_default(self):
        """Sanity check - Text class attribute (default)"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.4.w.4']
        self.assertEqual( w.annotation(folia.PosAnnotation).textclass , 'current')
        self.assertEqual( w.annotation(folia.LemmaAnnotation).textclass , 'current')

    def test031_sense(self):
        """Sanity Check - Lexical Semantic Sense Annotation"""
        w = self.doc['sandbox.list.1.listitem.1.s.1.w.1']
        sense = w.annotation(folia.SenseAnnotation)

        self.assertEqual( sense.cls , 'some.sense.id')
        self.assertEqual( sense.feat('synset') , 'some.synset.id')

    def test032_event(self):
        """Sanity Check - Events"""
        l= self.doc['sandbox']
        event = l.annotation(folia.Event)

        self.assertEqual( event.cls , 'applause')
        self.assertEqual( event.feat('actor') , 'audience')

    def test033_list(self):
        """Sanity Check - List"""
        l = self.doc['sandbox.list.1']
        self.assertTrue( isinstance( l[0], folia.ListItem) )
        self.assertEqual( l[0].n, '1' ) #testing common n attribute
        self.assertEqual( l[0].text(), 'Eerste testitem')
        self.assertTrue( isinstance( l[-1], folia.ListItem) )
        self.assertEqual( l[1].text(), 'Tweede testitem')
        self.assertEqual( l[1].n, '2' )

    def test034_figure(self):
        """Sanity Check - Figure"""
        fig = self.doc['sandbox.figure.1']
        self.assertEqual( fig.src, "http://upload.wikimedia.org/wikipedia/commons/8/8e/Family_tree.svg")
        self.assertEqual( fig.caption(), 'Een stamboom')

    def test035_event(self):
        """Sanity Check - Event"""
        e = self.doc['sandbox.event.1']
        self.assertEqual( e.feat('actor'), 'proycon')
        self.assertEqual( e.feat('begindatetime'), '2011-12-15T19:01')
        self.assertEqual( e.feat('enddatetime'), '2011-12-15T19:05')

    def test036_parsen(self):
        """Sanity Check - Paragraph and Sentence annotation"""
        p = self.doc['WR-P-E-J-0000000001.p.1']
        self.assertEqual( p.cls, 'firstparagraph' )
        s = self.doc['WR-P-E-J-0000000001.p.1.s.6']
        self.assertEqual( s.cls, 'sentence' )


    def test037a_feat(self):
        """Sanity Check - Feature test (including shortcut)"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
<metadata src="test.cmdi.xml" type="cmdi">
<annotations>
    <pos-annotation set="test"/>
</annotations>
</metadata>
<text xml:id="test.text">
    <div xml:id="div">
    <head xml:id="head">
        <s xml:id="head.1.s.1">
            <w xml:id="head.1.s.1.w.1">
                <t>blah</t>
                <pos class="NN(blah)" head="NN" />
            </w>
        </s>
    </head>
    <p xml:id="p.1">
        <s xml:id="p.1.s.1">
            <w xml:id="p.1.s.1.w.1">
                <t>blah</t>
                <pos class="NN(blah)">
                    <feat subset="head" class="NN" />
                </pos>
            </w>
        </s>
    </p>
    </div>
</text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml)
        self.assertEqual( doc['head.1.s.1.w.1'].pos() , 'NN(blah)')
        self.assertEqual( doc['head.1.s.1.w.1'].annotation(folia.PosAnnotation).feat('head') , 'NN')
        self.assertEqual( doc['p.1.s.1.w.1'].pos() , 'NN(blah)')
        self.assertEqual( doc['p.1.s.1.w.1'].annotation(folia.PosAnnotation).feat('head') , 'NN')

    def test037b_multiclassfeat(self):
        """Sanity Check - Multiclass feature"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
<metadata src="test.cmdi.xml" type="cmdi">
<annotations>
    <pos-annotation set="test"/>
</annotations>
</metadata>
<text xml:id="test.text">
    <div xml:id="div">
    <p xml:id="p.1">
        <s xml:id="p.1.s.1">
            <w xml:id="p.1.s.1.w.1">
                <t>blah</t>
                <pos class="NN(a,b,c)">
                    <feat subset="x" class="a" />
                    <feat subset="x" class="b" />
                    <feat subset="x" class="c" />
                </pos>
            </w>
        </s>
    </p>
    </div>
</text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml)
        self.assertEqual( doc['p.1.s.1.w.1'].pos() , 'NN(a,b,c)')
        self.assertEqual( doc['p.1.s.1.w.1'].annotation(folia.PosAnnotation).feat('x') , ['a','b','c'] )

    def test038a_morphemeboundary(self):
        """Sanity check - Obtaining annotation should not descend into morphology layer"""
        self.assertRaises( folia.NoSuchAnnotation,  self.doc['WR-P-E-J-0000000001.sandbox.2.s.1.w.2'].annotation , folia.PosAnnotation)

    def test038b_morphemeboundary(self):
        """Sanity check - Obtaining morphemes and token annotation under morphemes"""

        w = self.doc['WR-P-E-J-0000000001.sandbox.2.s.1.w.2']
        l = list(w.morphemes()) #get all morphemes
        self.assertEqual(len(l), 2)
        m = w.morpheme(1) #get second morpheme
        self.assertEqual(m.annotation(folia.PosAnnotation).cls, 'n')

    def test039_findspan(self):
        """Sanity Check - Find span on layer"""
        s = self.doc['WR-P-E-J-0000000001.p.1.s.7']
        semrolelayer = s.annotation(folia.SemanticRolesLayer)
        roles = list(semrolelayer.annotations(folia.SemanticRole))
        self.assertEqual(semrolelayer.findspan( self.doc['WR-P-E-J-0000000001.p.1.s.7.w.4'], self.doc['WR-P-E-J-0000000001.p.1.s.7.w.5']), roles[1] )

    def test040_spaniter(self):
        """Sanity Check - Iteration over spans"""
        t = []
        sentence = self.doc["WR-P-E-J-0000000001.p.1.s.1"]
        for layer in sentence.select(folia.EntitiesLayer):
            for entity in layer.select(folia.Entity):
                for word in entity.wrefs():
                    t.append(word.text())
        self.assertEqual(t, ['ander','woord'])

    def test041_findspans(self):
        """Sanity check - Find spans given words (no set)"""
        t = []
        word = self.doc["WR-P-E-J-0000000001.p.1.s.1.w.4"]
        for entity in word.findspans(folia.EntitiesLayer):
            for word in entity.wrefs():
                t.append(word.text())
        self.assertEqual(t, ['ander','woord'])

    def test041b_findspans(self):
        """Sanity check - Find spans given words (specific set)"""
        t = []
        word = self.doc["example.table.1.w.3"]
        for entity in word.findspans(folia.EntitiesLayer, "http://raw.github.com/proycon/folia/master/setdefinitions/namedentities.foliaset.xml"):
            for word in entity.wrefs():
                t.append(word.text())
        self.assertEqual(t, ['Maarten','van','Gompel'])

    def test041c_findspans(self):
        """Sanity check - Find spans given words (specific set, by SpanAnnotation class)"""
        t = []
        word = self.doc["example.table.1.w.3"]
        for entity in word.findspans(folia.Entity, "http://raw.github.com/proycon/folia/master/setdefinitions/namedentities.foliaset.xml"):
            for word in entity.wrefs():
                t.append(word.text())
        self.assertEqual(t, ['Maarten','van','Gompel'])

    def test042_table(self):
        """Sanity check - Table"""
        table = self.doc["example.table.1"]
        self.assertTrue( isinstance(table, folia.Table))
        self.assertTrue( isinstance(table[0], folia.TableHead))
        self.assertTrue( isinstance(table[0][0], folia.Row))
        self.assertEqual( len(table[0][0]), 2) #two cells
        self.assertTrue( isinstance(table[0][0][0], folia.Cell))
        self.assertEqual( table[0][0][0].text(), "Naam" )
        self.assertEqual( table[0][0].text(), "Naam | Universiteit" ) #text of whole row


    def test043_string(self):
        """Sanity check - String"""
        s = self.doc["sandbox.3.head"]
        self.assertTrue( s.hasannotation(folia.String) )
        st = next(s.select(folia.String))
        self.assertEqual( st.text(), "FoLiA developers")
        self.assertEqual( st.annotation(folia.LangAnnotation).cls, "eng")

    def test044_textmarkup(self):
        """Sanity check - Text Markup"""
        s = self.doc["sandbox.3.head"]
        t = s.textcontent()
        self.assertEqual( s.count(folia.TextMarkupString), 1)
        self.assertEqual( t.count(folia.TextMarkupString), 1)

        st = next(t.select(folia.TextMarkupString))
        self.assertEqual( st.text(), "\nFoLiA developers" ) #testing value (full text value)

        self.assertEqual( st.resolve(), self.doc['sandbox.3.str']) #testing resolving references


        self.assertTrue( isinstance( self.doc['WR-P-E-J-0000000001.p.1.s.6'].textcontent()[-1], folia.Linebreak) )  #did we get the linebreak properly?

        #testing nesting
        self.assertEqual( len(st), 2)
        self.assertEqual( st[0], self.doc['sandbox.3.str.bold'])

        #testing TextMarkup.text()
        self.assertEqual( st[0].text(), '\nFoLiA' )

        #resolving returns self if it's not a reference
        self.assertEqual( self.doc['sandbox.3.str.bold'].resolve(), self.doc['sandbox.3.str.bold'])


    def test045_spancorrection(self):
        """Sanity Check - Corrections over span elements"""
        s = self.doc['example.last.cell']
        entities = list(s.select(folia.Entity,set="http://raw.github.com/proycon/folia/master/setdefinitions/namedentities.foliaset.xml"))
        self.assertEqual( len(entities),1 )
        self.assertEqual( entities[0].id , "example.tilburg.university.org" )


    def test046_entry(self):
        """Sanity Check - Checking entry, term, definition and example"""
        entry = self.doc['entry.1']
        terms = list(entry.select(folia.Term))
        self.assertEqual( len(terms),1 )
        self.assertEqual( terms[0].text() ,"Stemma" )
        definitions = list(entry.select(folia.Definition))
        self.assertEqual( len(definitions),2 )
        examples = list(entry.select(folia.Example))
        self.assertEqual( len(examples),1 )

    def test046a_text(self):
        """Sanity Check - Text serialisation test with linebreaks and whitespaces"""
        p = self.doc['WR-P-E-J-0000000001.p.1'] #this is a bit of a malformed paragraph due to the explicit whitespace and linebreaks in it, but makes for a nice test:
        self.maxDiff = 3000
        self.assertEqual( p.text(), "Stemma is een ander woord voor stamboom. In de historische wetenschap wordt zo'n stamboom , onder de naam stemma codicum ( handschriftelijke genealogie ) , gebruikt om de verwantschap tussen handschriften weer te geven . \n\nWerkwijze\n\nHiervoor worden de handschriften genummerd en gedateerd zodat ze op de juiste plaats van hun afstammingsgeschiedenis geplaatst kunnen worden . De hoofdletter A wordt gebruikt voor het originele handschrift. De andere handschriften krijgen ook een letter die verband kan houden met hun plaats van oorsprong óf plaats van bewaring. Verdwenen handschriften waarvan men toch vermoedt dat ze ooit bestaan hebben worden ook in het stemma opgenomen en worden weergegeven door de laatste letters van het alfabet en worden tussen vierkante haken geplaatst.\nTenslotte gaat men de verwantschap tussen de handschriften aanduiden . Een volle lijn duidt op een verwantschap , terweil een stippelijn op een onzekere verwantschap duidt .")


    def test046b_text(self):
        """Sanity Check - Text serialisation on lists"""
        l = self.doc['sandbox.list.1'] #this is a bit of a malformed paragraph due to the explicit whitespace and linebreaks in it, but makes for a nice test:
        self.assertEqual( l.text(), "Eerste testitem\nTweede testitem")

    def test047_relation(self):
        """Sanity check - Relation"""
        word = self.doc['WR-P-E-J-0000000001.p.1.s.3.w.10']
        a = word.annotation(folia.Relation)
        self.assertEqual( a.cls, "reference")
        xref = next(a.select(folia.LinkReference,ignore=False))
        self.assertEqual( xref.id,"WR-P-E-J-0000000001.p.1.s.3.w.5" )
        self.assertEqual( xref.type, 'w' )
        self.assertEqual( xref.t,"handschriften" )

    def test048_observations(self):
        """Sanity check - Observations"""
        word = self.doc['WR-P-E-J-0000000001.p.1.s.8.w.9']
        observation = list(word.findspans(folia.ObservationLayer))[0]
        self.assertEqual( observation.cls , "ei_ij_error")
        self.assertEqual( observation.description() , "Confusion between EI and IJ diphtongues")

    def test049_sentiment(self):
        """Sanity check - Sentiments"""
        sentence = self.doc['WR-P-E-J-0000000001.sandbox.2.s.3']
        sentiments = sentence.annotation(folia.SentimentLayer)
        sentiment = sentiments.annotation(folia.Sentiment)
        self.assertEqual( sentiment.cls , "disappointment")
        self.assertEqual( sentiment.feat('polarity') , "negative")
        self.assertEqual( sentiment.feat('strength') , "strong")
        self.assertEqual( sentiment.annotation(folia.Source).text(), "Hij")
        self.assertEqual( sentiment.annotation(folia.Headspan).text(), "erg teleurgesteld")

    def test050_statement(self):
        """Sanity check - Statements"""
        sentence = self.doc['WR-P-E-J-0000000001.sandbox.2.s.2']
        sentiments = sentence.annotation(folia.StatementLayer)
        sentiment = sentiments.annotation(folia.Statement)
        self.assertEqual( sentiment.cls , "promise")
        self.assertEqual( sentiment.annotation(folia.Source).text(), "Hij")
        self.assertEqual( sentiment.annotation(folia.Headspan).text(), "hij zou winnen")

    def test099_write(self):
        """Sanity Check - Writing to file"""
        self.doc.save(os.path.join(TMPDIR,'foliasavetest.xml'))

    def test099b_write(self):
        """Sanity Check - Writing to GZ file"""
        self.doc.save(os.path.join(TMPDIR,'foliasavetest.xml.gz'))

    def test099c_write(self):
        """Sanity Check - Writing to BZ2 file"""
        self.doc.save(os.path.join(TMPDIR,'foliasavetest.xml.bz2'))

    def test100a_sanity(self):
        """Sanity Check - A - Checking output file against input (should be equal)"""
        #uses a partial rather than full legacy example without elements that have been renamed in FoLiA 2.0
        doc = folia.Document(string=PARTIALLEGACYEXAMPLE, debug=False, keepversion=True)
        doc.save(os.path.join(TMPDIR,'foliatest100.xml'))
        reloadeddoc = folia.Document(file=os.path.join(TMPDIR,'foliatest100.xml'),version='1.5.0', keepversion=True,debug=False)
        self.assertEqual( reloadeddoc , doc )

    def test100b_sanity_xmldiff(self):
        """Sanity Check - B - Checking output file against input using xmldiff (should be equal)"""
        #uses a partial rather than full legacy example without elements that have been renamed in FoLiA 2.0
        f = open(os.path.join(TMPDIR,'foliatest.xml'),'w',encoding='utf-8')
        f.write( re.sub(r' version="[^"]*" generator="[^"]*"', ' version="1.5" generator="foliapy-v' + folia.LIBVERSION + '"', PARTIALLEGACYEXAMPLE, re.MULTILINE) )
        f.close()
        #use xmldiff to compare the two:
        doc = folia.Document(string=PARTIALLEGACYEXAMPLE, debug=False, keepversion=True)
        doc.save(os.path.join(TMPDIR,'foliatest100.xml'))
        retcode = os.system('xmldiff ' + os.path.join(TMPDIR,'foliatest.xml') + ' ' + os.path.join(TMPDIR,'foliatest100.xml'))
        #retcode = 1 #disabled (memory hog)
        self.assertEqual( retcode, 0)

    def test101a_metadataextref(self):
        """Sanity Check - Metadata external reference (CMDI)"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
<metadata src="test.cmdi.xml" type="cmdi">
<annotations>
    <event-annotation set="test"/>
</annotations>
</metadata>
<text xml:id="test.text" />
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml)
        self.assertEqual( doc.metadatatype, "cmdi")
        self.assertEqual( doc.metadata.url, 'test.cmdi.xml' )

    def test101c_metadatainternal(self):
        """Sanity Check - Metadata internal (foreign data) (Dublin Core)"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
<metadata type="dc">
  <annotations>
  </annotations>
  <foreign-data xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier>mydoc</dc:identifier>
    <dc:format>text/xml</dc:format>
    <dc:type>Example</dc:type>
    <dc:contributor>proycon</dc:contributor>
    <dc:creator>proycon</dc:creator>
    <dc:language>en</dc:language>
    <dc:publisher>Radboud University</dc:publisher>
    <dc:rights>public Domain</dc:rights>
  </foreign-data>
</metadata>
<text xml:id="test.text" />
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml)
        self.assertEqual( doc.metadatatype, "dc" )
        self.assertEqual( doc.metadata.node.xpath('//dc:creator', namespaces={'dc':'http://purl.org/dc/elements/1.1/'})[0].text , 'proycon' )
        xmlcheck(doc.xmlstring(), xml)

    def test101d_metadatainternal(self):
        """Sanity Check - Metadata internal (double)"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
<metadata type="dc">
  <annotations>
  </annotations>
  <foreign-data xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier>mydoc</dc:identifier>
    <dc:format>text/xml</dc:format>
    <dc:type>Example</dc:type>
    <dc:contributor>proycon</dc:contributor>
    <dc:creator>proycon</dc:creator>
    <dc:language>en</dc:language>
    <dc:publisher>Radboud University</dc:publisher>
  </foreign-data>
  <foreign-data xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:rights>public Domain</dc:rights>
  </foreign-data>
</metadata>
<text xml:id="test.text" />
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml)
        self.assertEqual( doc.metadatatype, "dc" )
        self.assertEqual( doc.metadata.node.xpath('//dc:creator', namespaces={'dc':'http://purl.org/dc/elements/1.1/'})[0].text , 'proycon' )
        xmlcheck(doc.xmlstring(), xml)

    def test101e_metadatalegacyimdi(self):
        """Sanity Check - Legacy inline IMDI metadata"""
        #adapted from foliatests/tests/folia.imdi.xml
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="imdi">
    <annotations>
      <event-annotation set="test"/>
    </annotations>
    <imdi:METATRANSCRIPT xmlns:imdi="http://www.mpi.nl/IMDI/Schema/IMDI">
      <imdi:Session>
	<imdi:Title>Een imdi file</imdi:Title>
	<imdi:Date>28/09/2017</imdi:Date>
      </imdi:Session>
    </imdi:METATRANSCRIPT>
  </metadata>
  <text xml:id="test.text"/>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml)
        self.assertEqual( doc.metadatatype, "imdi" )
        self.assertEqual( doc.metadata.node.xpath('//imdi:Title', namespaces={'imdi':'http://www.mpi.nl/IMDI/Schema/IMDI'})[0].text , 'Een imdi file' )

    def test102a_declarations(self):
        """Sanity Check - Declarations - Default set"""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
      <gap-annotation annotator="sloot" set="gap-set"/>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <gap class="X" />
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml)
        self.assertEqual( next(doc['example.text.1'].select(folia.Gap)).set, 'gap-set' )


    def test102a2_declarations(self):
        """Sanity Check - Declarations - Default set, no further defaults"""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
      <gap-annotation set="gap-set"/>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <gap class="X" annotator="proycon" annotatortype="manual" />
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml)
        self.assertEqual( next(doc['example.text.1'].select(folia.Gap)).set, 'gap-set' )
        self.assertEqual( next(doc['example.text.1'].select(folia.Gap)).annotator, 'proycon' )
        self.assertEqual( next(doc['example.text.1'].select(folia.Gap)).annotatortype, folia.AnnotatorType.MANUAL)

    def test102b_declarations(self):
        """Sanity Check - Declarations - Set mismatching """
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
      <gap-annotation annotator="sloot" set="gap-set"/>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <gap class="X" set="extended-gap-set" />
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        with self.assertRaises( folia.ParseError) as cm:
            folia.Document(string=xml)
        self.assertEqual(cm.exception.cause.__class__, folia.DeclarationError)


    def test102c_declarations(self):
        """Sanity Check - Declarations - Multiple sets for the same annotation type"""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
      <gap-annotation annotator="sloot" set="extended-gap-set"/>
      <gap-annotation annotator="sloot" set="gap-set"/>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <gap class="X" set="gap-set"/>
    <gap class="Y" set="extended-gap-set"/>
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml)
        self.assertEqual( next(doc['example.text.1'].select(folia.Gap)).set, 'gap-set' )
        self.assertEqual( list(doc['example.text.1'].select(folia.Gap))[1].set, 'extended-gap-set' )

    def test102d1_declarations(self):
        """Sanity Check - Declarations - Missing set in when multiple sets for the same annotation type are declared (testing failure)"""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
      <gap-annotation annotator="sloot" set="extended-gap-set"/>
      <gap-annotation annotator="sloot" set="gap-set"/>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <gap class="X" set="gap-set"/>
    <gap class="Y" />
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        with self.assertRaises( folia.ParseError) as cm:
            folia.Document(string=xml)
        self.assertEqual(cm.exception.cause.__class__, folia.DeclarationError)





    def test102d2_declarations(self):
        """Sanity Check - Declarations - Multiple sets for the same annotation type (testing failure)"""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
      <gap-annotation annotator="sloot" set="extended-gap-set"/>
      <gap-annotation annotator="sloot" set="gap-set"/>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <gap class="X" set="gap-set"/>
    <gap class="Y" set="gip-set"/>
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        with self.assertRaises( folia.ParseError) as cm:
            folia.Document(string=xml)
        self.assertEqual(cm.exception.cause.__class__, folia.DeclarationError)

    def test102d3_declarations(self):
        """Sanity Check - Declarations - Ignore Duplicates"""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
      <gap-annotation annotator="sloot" set="gap-set"/>
      <gap-annotation annotator="sloot" set="gap-set"/>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <gap class="X" set="gap-set"/>
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)

        doc = folia.Document(string=xml)
        self.assertEqual( doc.defaultset(folia.AnnotationType.GAP), 'gap-set' )
        self.assertEqual( doc.defaultannotator(folia.AnnotationType.GAP), "sloot" )


    def test102e_declarations(self):
        """Sanity Check - Declarations - Missing declaration"""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <gap class="X" set="extended-gap-set" />
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        with self.assertRaises( folia.ParseError) as cm:
            folia.Document(string=xml)
        self.assertEqual(cm.exception.cause.__class__, folia.DeclarationError)

    def test102f_declarations(self):
        """Sanity Check - Declarations - Declaration not needed"""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <gap />
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        folia.Document(string=xml)


    def test102g_declarations(self):
        """Sanity Check - Declarations - 'Undefined' set in declaration"""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
        <gap-annotation annotator="sloot" />
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <gap class="X"  />
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml)
        self.assertEqual( next(doc['example.text.1'].select(folia.Gap)).set, 'undefined' )

    def test102h_declarations(self):
        """Sanity Check - Declarations - Ambiguous set"""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
         <gap-annotation annotator="sloot" set="gap-set"/>
         <gap-annotation annotator="proycon" set="gap-set2"/>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <gap />
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        with self.assertRaises( folia.ParseError) as cm:
            folia.Document(string=xml)
        self.assertEqual(cm.exception.cause.__class__, folia.DeclarationError)

    def test102i_declarations(self):
        """Sanity Check - Declarations - miscellaneous trouble"""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
         <gap-annotation annotator="sloot" set="gap1-set"/>
         <gap-annotation annotator="sloot" set="gap2-set"/>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <gap class="X" set="gap1-set"/>
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml)
        self.assertEqual( doc.defaultannotator(folia.AnnotationType.GAP,"gap1-set"), "sloot" )
        doc.declare(folia.AnnotationType.GAP, "gap1-set", annotator='proycon' ) #slightly different behaviour from libfolia: here this overrides the earlier default
        self.assertEqual( doc.defaultannotator(folia.AnnotationType.GAP,"gap1-set"), "proycon" )
        self.assertEqual( doc.defaultannotator(folia.AnnotationType.GAP,"gap2-set"), "sloot" )

        text = doc["example.text.1"]
        text.append( folia.Gap(doc, set='gap1-set', cls='Y', annotator='proycon') )
        text.append( folia.Gap(doc, set='gap1-set', cls='Z1' ) )
        text.append( folia.Gap(doc, set='gap2-set', cls='Z2' ) )
        text.append( folia.Gap(doc, set='gap2-set', cls='Y2', annotator='onbekend' ) )
        gaps = list(text.select(folia.Gap))
        self.assertTrue( xmlcheck(gaps[0].xmlstring(), '<gap xmlns="http://ilk.uvt.nl/folia" annotator="sloot" class="X" set="gap1-set"/>' ) )
        self.assertTrue( xmlcheck(gaps[1].xmlstring(), '<gap xmlns="http://ilk.uvt.nl/folia" class="Y" set="gap1-set"/>') )
        self.assertTrue( xmlcheck(gaps[2].xmlstring(), '<gap xmlns="http://ilk.uvt.nl/folia" class="Z1" set="gap1-set"/>') )
        self.assertTrue( xmlcheck(gaps[3].xmlstring(), '<gap xmlns="http://ilk.uvt.nl/folia" class="Z2" set="gap2-set"/>') )
        self.assertTrue( xmlcheck(gaps[4].xmlstring(), '<gap xmlns="http://ilk.uvt.nl/folia" annotator="onbekend" class="Y2" set="gap2-set"/>') )


    def test102j_declarations(self):
        """Sanity Check - Declarations - Adding a declaration in other set."""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
         <gap-annotation annotator="sloot" set="gap-set"/>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <gap class="X" />
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml)
        text = doc["example.text.1"]
        doc.declare(folia.AnnotationType.GAP, "other-set", annotator='proycon' )
        text.append( folia.Gap(doc, set='other-set', cls='Y', annotator='proycon') )
        text.append( folia.Gap(doc, set='other-set', cls='Z' ) )

        gaps = list(text.select(folia.Gap))
        self.assertTrue( xmlcheck(gaps[0].xmlstring(), '<gap class="X" set="gap-set"/>') )
        self.assertTrue( xmlcheck(gaps[1].xmlstring(), '<gap class="Y" set="other-set"/>') )
        self.assertTrue( xmlcheck(gaps[2].xmlstring(), '<gap class="Z" set="other-set"/>') )


    def test102k_declarations(self):
        """Sanity Check - Declarations - Several annotator types."""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
         <gap-annotation annotatortype="auto" set="gap-set"/>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <gap class="X" />
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml)
        self.assertEqual( doc.defaultannotatortype(folia.AnnotationType.GAP, 'gap-set'),  folia.AnnotatorType.AUTO)
        text = doc["example.text.1"]
        gaps = list(text.select(folia.Gap))
        self.assertTrue( xmlcheck(gaps[0].xmlstring(), '<gap xmlns="http://ilk.uvt.nl/folia" class="X"/>' ) )

        doc.declare(folia.AnnotationType.GAP, "gap-set", annotatortype=folia.AnnotatorType.MANUAL )
        self.assertEqual( doc.defaultannotatortype(folia.AnnotationType.GAP), folia.AnnotatorType.MANUAL )
        self.assertRaises( ValueError, folia.Gap, doc, set='gap-set', cls='Y', annotatortype='unknown' )

        text.append( folia.Gap(doc, set='gap-set', cls='Y', annotatortype='manual' ) )
        text.append( folia.Gap(doc, set='gap-set', cls='Z', annotatortype='auto' ) )

        gaps = list(text.select(folia.Gap))
        self.assertTrue( xmlcheck(gaps[0].xmlstring(), '<gap xmlns="http://ilk.uvt.nl/folia" annotatortype="auto" class="X" />') )
        self.assertTrue( xmlcheck(gaps[1].xmlstring(), '<gap xmlns="http://ilk.uvt.nl/folia" class="Y" />') )
        self.assertTrue( xmlcheck(gaps[2].xmlstring(), '<gap xmlns="http://ilk.uvt.nl/folia" annotatortype="auto" class="Z" />') )



    def test102l_declarations(self):
        """Sanity Check - Declarations - Datetime default."""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
         <gap-annotation set="gap-set" datetime="2011-12-15T19:00" />
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <gap class="X" />
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml)
        self.assertEqual( doc.defaultdatetime(folia.AnnotationType.GAP, 'gap-set'),  folia.parse_datetime('2011-12-15T19:00') )

        self.assertEqual( next(doc["example.text.1"].select(folia.Gap)).datetime ,  folia.parse_datetime('2011-12-15T19:00') )

    def test102m_declarations(self):
        """Sanity Check - Declarations - Adding a declaration of a FoLiA v1.4 RDF Set Definition."""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml)
        doc.declare(folia.AnnotationType.ENTITY, "https://github.com/proycon/folia/blob/master/setdefinitions/namedentities.foliaset.ttl", annotator='proycon' )

    def test102n_aliases(self):
        """Sanity Check - Declarations - Testing Aliases"""
        xml = """<?xml version="1.0"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
      <gap-annotation set="some very convoluted url or such which clutters all" alias="gap-set" datetime="2012-06-18T17:49"/>
      <division-annotation set="a long div annotation name" alias="div-set" datetime="2012-06-18T17:49"/>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <gap class="X" />
    <gap class="Y" datetime="2012-06-18T17:50"/>
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)

        doc = folia.Document(string=xml)
        doc.declare(folia.AnnotationType.GAP, "nog zon ingewikkelde en veels te lange declaratie", alias='gap-set2' )
        self.doc.xmlstring() #check if serialisation works

        #declaring a setname which is already an alias is an error
        self.assertRaises( ValueError,  doc.declare, folia.AnnotationType.GAP, "gap-set2")

        #declaring an alias  which is already an alias is an error
        self.assertRaises( ValueError,  doc.declare, folia.AnnotationType.GAP, "gap-set3", alias="gap-set2")

        #declaring an alias  which is already a setname is an error
        self.assertRaises( ValueError,  doc.declare, folia.AnnotationType.GAP, "gap-set3", alias="nog zon ingewikkelde en veels te lange declaratie")

        #just declaring again is NOT an error!
        doc.declare(folia.AnnotationType.GAP, "nog zon ingewikkelde en veels te lange declaratie", alias='gap-set2' )

        self.doc.xmlstring() #check if serialisation still works

        #declaring again with another alias IS an error!
        self.assertRaises(ValueError, doc.declare,folia.AnnotationType.GAP, "nog zon ingewikkelde en veels te lange declaratie", alias='gap-set3' )

        #declaring again with same alias and another setname IS an error!
        self.assertRaises(ValueError, doc.declare, folia.AnnotationType.GAP, "niet zon ingewikkelde en veels te lange declaratie", alias='gap-set2' )




    def test103_namespaces(self):
        """Sanity Check - Alien namespaces - Checking whether properly ignored"""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns:xlink="http://www.w3.org/1999/xlink" xmlns="http://ilk.uvt.nl/folia" xmlns:alien="http://somewhere.else" xml:id="example" generator="{generator}" version="1.5.0">
  <metadata type="native">
    <annotations>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <s xml:id="example.text.1.s.1">
        <alien:blah>
            <w xml:id="example.text.1.s.1.alienword">
                <t>blah</t>
            </w>
        </alien:blah>
        <w xml:id="example.text.1.s.1.w.1">
            <t>word</t>
            <alien:invasion number="99999" />
        </w>
    </s>
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml)
        self.assertTrue( len(list(doc['example.text.1.s.1'].words())) == 1 ) #second word is in alien namespace, not read
        self.assertRaises( KeyError,  doc.__getitem__, 'example.text.1.s.1.alienword') #doesn't exist


    def test104_speech(self):
        """Sanity Check - Speech data (without attributes)"""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
        <utterance-annotation set="utterances" />
        <token-annotation />
        <phon-annotation />
    </annotations>
  </metadata>
  <speech xml:id="example.speech">
    <utt xml:id="example.speech.utt.1">
        <ph>həlˈəʊ wˈɜːld</ph>
    </utt>
    <utt xml:id="example.speech.utt.2">
        <w xml:id="example.speech.utt.2.w.1">
          <ph>həlˈəʊ</ph>
        </w>
        <w xml:id="example.speech.utt.2.w.2">
           <ph>wˈɜːld</ph>
        </w>
    </utt>
  </speech>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml)
        self.assertTrue( isinstance(doc.data[0], folia.Speech) )
        self.assertTrue( isinstance(doc['example.speech.utt.1'], folia.Utterance) )
        self.assertEqual( doc['example.speech.utt.1'].phon(), "həlˈəʊ wˈɜːld" )
        self.assertRaises( folia.NoSuchText,  doc['example.speech.utt.1'].text) #doesn't exist
        self.assertEqual( doc['example.speech.utt.2'].phon(), "həlˈəʊ wˈɜːld" )


    def test104b_speech(self):
        """Sanity Check - Speech data with speech attributes"""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
        <utterance-annotation set="utterances" />
        <token-annotation />
        <phon-annotation />
    </annotations>
  </metadata>
  <speech xml:id="example.speech" src="helloworld.ogg" speaker="proycon">
    <utt xml:id="example.speech.utt.1" begintime="00:00:00" endtime="00:00:02.012">
        <ph>həlˈəʊ wˈɜːld</ph>
    </utt>
    <utt xml:id="example.speech.utt.2">
        <w xml:id="example.speech.utt.2.w.1" begintime="00:00:00" endtime="00:00:01">
          <ph>həlˈəʊ</ph>
        </w>
        <w xml:id="example.speech.utt.2.w.2" begintime="00:00:01.267" endtime="00:00:02.012">
           <ph>wˈɜːld</ph>
        </w>
    </utt>
  </speech>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml)
        self.assertTrue( isinstance(doc.data[0], folia.Speech) )
        self.assertTrue( isinstance(doc['example.speech.utt.1'], folia.Utterance) )
        self.assertEqual( doc['example.speech.utt.1'].phon(), "həlˈəʊ wˈɜːld" )
        self.assertRaises( folia.NoSuchText,  doc['example.speech.utt.1'].text) #doesn't exist
        self.assertEqual( doc['example.speech.utt.2'].phon(), "həlˈəʊ wˈɜːld" )
        self.assertEqual( doc['example.speech'].speech_speaker(), "proycon" )
        self.assertEqual( doc['example.speech'].speech_src(), "helloworld.ogg" )
        self.assertEqual( doc['example.speech.utt.1'].begintime, (0,0,0,0) )
        self.assertEqual( doc['example.speech.utt.1'].endtime, (0,0,2,12) )
        #testing inheritance
        self.assertEqual( doc['example.speech.utt.2.w.2'].speech_speaker(), "proycon" )
        self.assertEqual( doc['example.speech.utt.2.w.2'].speech_src(), "helloworld.ogg" )
        self.assertEqual( doc['example.speech.utt.2.w.2'].begintime, (0,0,1,267) )
        self.assertEqual( doc['example.speech.utt.2.w.2'].endtime, (0,0,2,12) )


    def test104c_speech(self):
        """Sanity Check - Testing serialisation of speech data with speech attributes"""
        speechxml = """<speech xmlns="http://ilk.uvt.nl/folia" xml:id="example.speech" src="helloworld.ogg" speaker="proycon">
        <utt xml:id="example.speech.utt.1" begintime="00:00:00.000" endtime="00:00:02.012">
        <ph>həlˈəʊ wˈɜːld</ph>
    </utt>
    <utt xml:id="example.speech.utt.2">
        <w xml:id="example.speech.utt.2.w.1" begintime="00:00:00.000" endtime="00:00:01.000">
          <ph>həlˈəʊ</ph>
        </w>
        <w xml:id="example.speech.utt.2.w.2" begintime="00:00:01.267" endtime="00:00:02.012">
           <ph>wˈɜːld</ph>
        </w>
    </utt>
  </speech>"""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns:xlink="http://www.w3.org/1999/xlink" xmlns="http://ilk.uvt.nl/folia" xml:id="example" generator="manual" version="0.12">
  <metadata type="native">
    <annotations>
        <utterance-annotation set="utterances" />
    </annotations>
  </metadata>
  %s
</FoLiA>""" % speechxml
        doc = folia.Document(string=xml)
        self.assertTrue( xmlcheck( doc['example.speech'].xmlstring(), u(speechxml)) )

    def test105_spanrelation(self):
        """Sanity Check - Span Relation"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="2.0.0" generator="{generator}">
<metadata type="native">
 <annotations>
    <spanrelation-annotation set="blah" />
    <relation-annotation set="blah" />
    <paragraph-annotation />
    <sentence-annotation />
    <text-annotation />
 </annotations>
</metadata>
<text xml:id="test.text">
    <p xml:id="p.1">
	<s xml:id="p.1.s.1"><t>Dit is een test.</t></s>
	<s xml:id="p.1.s.2"><t>Ik wil kijken of het werkt.</t></s>
	<spanrelations>
	    <spanrelation>
            <relation class="source">
                <xref id="p.1.s.1" type="s" />
                <xref id="p.1.s.2" type="s" />
            </relation>
            <relation class="translation" xlink:href="en.folia.xml" xlink:type="simple">
                <xref id="p.1.s.1" type="s" />
            </relation>
	    </spanrelation>
	</spanrelations>
    </p>
</text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml)
        self.assertTrue(doc.xml() is not None) #serialisation check

        l = doc.paragraphs(0).annotation(folia.SpanRelationLayer)
        ca = list(l.annotations(folia.SpanRelation))
        self.assertEqual(len(ca),1)
        relations = list(ca[0].select(folia.Relation))
        self.assertEqual(len(relations),2)
        self.assertEqual(relations[1].href, "en.folia.xml")

    def test106_submetadata(self):
        """Sanity Check - Submetadata"""
        self.assertEqual(self.doc['WR-P-E-J-0000000001.div0.1'].getmetadata(), self.doc.submetadata['wikipedia.stemma'])
        self.assertTrue(isinstance(self.doc['WR-P-E-J-0000000001.div0.1'].getmetadata(), folia.NativeMetaData))
        self.assertEqual(self.doc.submetadatatype[self.doc['WR-P-E-J-0000000001.div0.1'].metadata], 'native')
        self.assertEqual(self.doc['WR-P-E-J-0000000001.div0.1'].getmetadata('originalsource'), 'https://nl.wikipedia.org/wiki/Stemma')
        self.assertEqual(self.doc['WR-P-E-J-0000000001.p.1.s.1.w.1'].getmetadata(), self.doc.submetadata['wikipedia.stemma'])
        self.assertEqual(self.doc['sandbox.3'].getmetadata(), self.doc.submetadata['sandbox.3.metadata'])
        self.assertEqual(self.doc['sandbox.3'].getmetadata('author'), 'proycon')
        self.assertEqual(self.doc['example.table.1.w.1'].getmetadata(), self.doc.submetadata['sandbox.3.metadata'])

    def test107a_submetadataextref(self):
        """Sanity Check - Submetadata external reference (CMDI)"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
<metadata type="native">
    <annotations>
    </annotations>
    <submetadata xml:id="test.metadata" src="test.cmdi.xml" type="cmdi" />
</metadata>
<text xml:id="test.text" metadata="test.metadata" />
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml)
        self.assertEqual( doc.submetadatatype['test.metadata'], 'cmdi')
        self.assertTrue( isinstance(doc['test.text'].getmetadata(), folia.ExternalMetaData) )
        self.assertEqual( doc['test.text'].getmetadata().url, 'test.cmdi.xml' )


    def test107b_metadatainternal(self):
        """Sanity Check - Submetadata internal (foreign data) (Dublin Core)"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
<metadata>
  <annotations>
  </annotations>
  <submetadata xml:id="test.metadata" type="dc">
      <foreign-data xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:identifier>mydoc</dc:identifier>
        <dc:format>text/xml</dc:format>
        <dc:type>Example</dc:type>
        <dc:contributor>proycon</dc:contributor>
        <dc:creator>proycon</dc:creator>
        <dc:language>en</dc:language>
        <dc:publisher>Radboud University</dc:publisher>
        <dc:rights>public Domain</dc:rights>
      </foreign-data>
    </submetadata>
</metadata>
<text xml:id="test.text" metadata="test.metadata" />
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml)
        self.assertEqual( doc.submetadatatype['test.metadata'], 'dc')
        self.assertTrue( isinstance(doc['test.text'].getmetadata(), folia.ForeignData) )

    def test108_text_with_comment(self):
        """Sanity Check - Text with XML comment"""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
   <t><!-- Comment -->This is the real text</t>
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml)
        self.assertEqual(doc['example.text.1'].text(),"This is the real text")

    def test108b_text_with_comment(self):
        """Sanity Check - Text with XML comment"""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
   <t>This is the real text<!-- Comment --></t>
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml)
        self.assertEqual(doc['example.text.1'].text(),"This is the real text")

    def test108c_text_with_comment(self):
        """Sanity Check - Text with FoLiA comment"""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
   <t>This is the real text<comment annotator="pkampschreur" annotatortype="manual" datetime="2017-11-01T20:55:50">Overbodig</comment></t>
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml)
        self.assertEqual(doc['example.text.1'].text(),"This is the real text")

    def test109_precedes(self):
        """Sanity Check - Check precedes() method"""
        self.assertTrue( self.doc["WR-P-E-J-0000000001.p.1.s.1.w.1"].precedes(self.doc["WR-P-E-J-0000000001.p.1.s.1.w.2"]) )
        self.assertFalse( self.doc["WR-P-E-J-0000000001.p.1.s.1.w.2"].precedes(self.doc["WR-P-E-J-0000000001.p.1.s.1.w.1"]) )
        self.assertTrue( self.doc["WR-P-E-J-0000000001.p.1.s.1.w.1"].precedes(self.doc["WR-P-E-J-0000000001.p.1.s.1.w.2"]) )
        self.assertTrue( self.doc["WR-P-E-J-0000000001.p.1.s.1.w.1"].precedes(self.doc["WR-P-E-J-0000000001.p.1.s.2.w.9"]) )
        self.assertFalse( self.doc["WR-P-E-J-0000000001.p.1.s.2.w.9"].precedes(self.doc["WR-P-E-J-0000000001.p.1.s.1.w.1"]) )

    def test110_spansort(self):
        """Sanity Check - Checking span sorting"""
        XML = """<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="folia2html.xsl"?>
<FoLiA xmlns:xlink="http://www.w3.org/1999/xlink" xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001" version="1.5" generator="manual">
  <metadata type="native">
    <annotations>
      <token-annotation annotator="ilktok" annotatortype="auto" />
      <syntax-annotation set="syntax-set" />
    </annotations>
  </metadata>
  <text>
    <s xml:id="WR-P-E-J-0000000001.p.1.s.1">
      <w xml:id="WR-P-E-J-0000000001.p.1.s.1.w.1">
        <t>Stemma</t>
      </w>
      <w xml:id="WR-P-E-J-0000000001.p.1.s.1.w.2">
        <t>is</t>
      </w>
      <w xml:id="WR-P-E-J-0000000001.p.1.s.1.w.3">
        <t>een</t>
      </w>
      <w xml:id="WR-P-E-J-0000000001.p.1.s.1.w.4">
        <t>ander</t>
      </w>
      <w xml:id="WR-P-E-J-0000000001.p.1.s.1.w.5">
        <t>woord</t>
      </w>
      <w xml:id="WR-P-E-J-0000000001.p.1.s.1.w.6">
        <t>voor</t>
      </w>
      <w xml:id="WR-P-E-J-0000000001.p.1.s.1.w.7" space="no">
        <t>stamboom</t>
      </w>
      <w xml:id="WR-P-E-J-0000000001.p.1.s.1.w.8">
        <t>.</t>
      </w>
      <syntax>
        <su xml:id="WR-P-E-J-0000000001.p.1.s.1.su.sentence" class="sentence">
          <su xml:id="WR-P-E-J-0000000001.p.1.s.1.su.subject" class="subject">
            <wref id="WR-P-E-J-0000000001.p.1.s.1.w.1" t="Stemma"/>
          </su>
          <su xml:id="WR-P-E-J-0000000001.p.1.s.1.su.verb" class="verb">
            <wref id="WR-P-E-J-0000000001.p.1.s.1.w.2" t="is"/>
          </su>
          <su xml:id="WR-P-E-J-0000000001.p.1.s.1.su.pred" class="predicate">
            <su xml:id="WR-P-E-J-0000000001.p.1.s.1.su.pp" class="pp">
              <wref id="WR-P-E-J-0000000001.p.1.s.1.w.6" t="voor"/>
              <wref id="WR-P-E-J-0000000001.p.1.s.1.w.7" t="stamboom"/>
            </su>
            <su xml:id="WR-P-E-J-0000000001.p.1.s.1.su.np" class="np">
              <wref id="WR-P-E-J-0000000001.p.1.s.1.w.3" t="een"/>
              <su xml:id="WR-P-E-J-0000000001.p.1.s.1.su.adj" class="adj">
                  <wref id="WR-P-E-J-0000000001.p.1.s.1.w.4" t="ander"/>
              </su>
              <wref id="WR-P-E-J-0000000001.p.1.s.1.w.5" t="woord"/>
            </su>
          </su>
          <wref id="WR-P-E-J-0000000001.p.1.s.1.w.8" t="."/>
        </su>
      </syntax>
    </s>
  </text>
</FoLiA>
"""
        self.doc = folia.Document(string=XML)
        s = self.doc['WR-P-E-J-0000000001.p.1.s.1']
        layer = next(s.select(folia.SyntaxLayer))
        self.assertTrue( xmlcheck(layer.xmlstring(),"""<syntax xmlns="http://ilk.uvt.nl/folia"><su class="sentence" xml:id="WR-P-E-J-0000000001.p.1.s.1.su.sentence"><su class="subject" xml:id="WR-P-E-J-0000000001.p.1.s.1.su.subject"><wref id="WR-P-E-J-0000000001.p.1.s.1.w.1" t="Stemma"/></su><su class="verb" xml:id="WR-P-E-J-0000000001.p.1.s.1.su.verb"><wref id="WR-P-E-J-0000000001.p.1.s.1.w.2" t="is"/></su><su class="predicate" xml:id="WR-P-E-J-0000000001.p.1.s.1.su.pred"><su class="np" xml:id="WR-P-E-J-0000000001.p.1.s.1.su.np"><wref id="WR-P-E-J-0000000001.p.1.s.1.w.3" t="een"/><su class="adj" xml:id="WR-P-E-J-0000000001.p.1.s.1.su.adj"><wref id="WR-P-E-J-0000000001.p.1.s.1.w.4" t="ander"/></su><wref id="WR-P-E-J-0000000001.p.1.s.1.w.5" t="woord"/></su><su class="pp" xml:id="WR-P-E-J-0000000001.p.1.s.1.su.pp"><wref id="WR-P-E-J-0000000001.p.1.s.1.w.6" t="voor"/><wref id="WR-P-E-J-0000000001.p.1.s.1.w.7" t="stamboom"/></su></su><wref id="WR-P-E-J-0000000001.p.1.s.1.w.8" t="."/></su></syntax>"""))


class Test04Edit(unittest.TestCase):

    def setUp(self):
        self.doc = folia.Document(string=LEGACYEXAMPLE, textvalidation=True)

    def test001_addsentence(self):
        """Edit Check - Adding a sentence to first paragraph (verbose)"""

        #grab last paragraph
        p = self.doc.paragraphs(0)

        #how many sentences?
        tmp = len(list(p.sentences()))

        #make a sentence
        s = folia.Sentence(self.doc, generate_id_in=p)
        #add words to the sentence
        s.append( folia.Word(self.doc, text='Dit',generate_id_in=s, annotator='testscript', annotatortype=folia.AnnotatorType.AUTO) )
        s.append( folia.Word(self.doc, text='is',generate_id_in=s, annotator='testscript', annotatortype=folia.AnnotatorType.AUTO) )
        s.append( folia.Word(self.doc, text='een',generate_id_in=s, annotator='testscript', annotatortype=folia.AnnotatorType.AUTO) )
        s.append( folia.Word(self.doc, text='nieuwe',generate_id_in=s, annotator='testscript', annotatortype=folia.AnnotatorType.AUTO) )
        s.append( folia.Word(self.doc, text='zin',generate_id_in=s, annotator='testscript', annotatortype=folia.AnnotatorType.AUTO, space=False ) )
        s.append( folia.Word(self.doc, text='.',generate_id_in=s, annotator='testscript', annotatortype=folia.AnnotatorType.AUTO) )

        #add the sentence
        p.append(s)

        #ID check
        self.assertEqual( s[0].id, s.id + '.w.1' )
        self.assertEqual( s[1].id, s.id + '.w.2' )
        self.assertEqual( s[2].id, s.id + '.w.3' )
        self.assertEqual( s[3].id, s.id + '.w.4' )
        self.assertEqual( s[4].id, s.id + '.w.5' )
        self.assertEqual( s[5].id, s.id + '.w.6' )

        #index check
        self.assertEqual( self.doc[s.id], s )
        self.assertEqual( self.doc[s.id + '.w.3'], s[2] )

        #attribute check
        self.assertEqual( s[0].annotator, 'testscript' )
        self.assertEqual( s[0].annotatortype, folia.AnnotatorType.AUTO )

        #addition to paragraph correct?
        self.assertEqual( len(list(p.sentences())) , tmp + 1)
        self.assertEqual( p[-1] , s)

        # text() ok?
        self.assertEqual( s.text(), "Dit is een nieuwe zin." )

        # xml() ok?
        self.assertTrue( xmlcheck( s.xmlstring(), '<s xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.9"><w xml:id="WR-P-E-J-0000000001.p.1.s.9.w.1" annotator="testscript"><t>Dit</t></w><w xml:id="WR-P-E-J-0000000001.p.1.s.9.w.2" annotator="testscript"><t>is</t></w><w xml:id="WR-P-E-J-0000000001.p.1.s.9.w.3" annotator="testscript"><t>een</t></w><w xml:id="WR-P-E-J-0000000001.p.1.s.9.w.4" annotator="testscript"><t>nieuwe</t></w><w xml:id="WR-P-E-J-0000000001.p.1.s.9.w.5" annotator="testscript" space="no"><t>zin</t></w><w xml:id="WR-P-E-J-0000000001.p.1.s.9.w.6" annotator="testscript"><t>.</t></w></s>') )

    def test001b_addsentence(self):
        """Edit Check - Adding a sentence to first paragraph (shortcut)"""

        #grab last paragraph
        p = self.doc.paragraphs(0)

        #how many sentences?
        tmp = len(list(p.sentences()))

        s = p.append(folia.Sentence)
        s.append(folia.Word,'Dit')
        s.append(folia.Word,'is')
        s.append(folia.Word,'een')
        s.append(folia.Word,'nieuwe')
        w = s.append(folia.Word,'zin')
        s.append(folia.Word,'.',cls='PUNCTUATION')

        self.assertEqual( s.id, 'WR-P-E-J-0000000001.p.1.s.9')
        self.assertEqual( len(list(s.words())), 6 ) #number of words in sentence
        self.assertEqual( w.text(), 'zin' ) #text check
        self.assertEqual( self.doc[w.id], w ) #index check

        #addition to paragraph correct?
        self.assertEqual( len(list(p.sentences())) , tmp + 1)
        self.assertEqual( p[-1] , s)

        self.assertTrue( xmlcheck(s.xmlstring(), '<s xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.9"><w xml:id="WR-P-E-J-0000000001.p.1.s.9.w.1"><t>Dit</t></w><w xml:id="WR-P-E-J-0000000001.p.1.s.9.w.2"><t>is</t></w><w xml:id="WR-P-E-J-0000000001.p.1.s.9.w.3"><t>een</t></w><w xml:id="WR-P-E-J-0000000001.p.1.s.9.w.4"><t>nieuwe</t></w><w xml:id="WR-P-E-J-0000000001.p.1.s.9.w.5"><t>zin</t></w><w xml:id="WR-P-E-J-0000000001.p.1.s.9.w.6" class="PUNCTUATION"><t>.</t></w></s>'))


    def test001c_addsentence(self):
        """Edit Check - Adding a sentence to first paragraph (using add instead of append)"""

        #grab last paragraph
        p = self.doc.paragraphs(0)

        #how many sentences?
        tmp = len(list(p.sentences()))

        s = p.add(folia.Sentence)
        s.add(folia.Word,'Dit')
        s.add(folia.Word,'is')
        s.add(folia.Word,'een')
        s.add(folia.Word,'nieuwe')
        w = s.add(folia.Word,'zin')
        s.add(folia.Word,'.',cls='PUNCTUATION')

        self.assertEqual( len(list(s.words())), 6 ) #number of words in sentence
        self.assertEqual( w.text(), 'zin' ) #text check
        self.assertEqual( self.doc[w.id], w ) #index check

        #addition to paragraph correct?
        self.assertEqual( len(list(p.sentences())) , tmp + 1)
        self.assertEqual( p[-1] , s)

        self.assertTrue( xmlcheck(s.xmlstring(), '<s xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.9"><w xml:id="WR-P-E-J-0000000001.p.1.s.9.w.1"><t>Dit</t></w><w xml:id="WR-P-E-J-0000000001.p.1.s.9.w.2"><t>is</t></w><w xml:id="WR-P-E-J-0000000001.p.1.s.9.w.3"><t>een</t></w><w xml:id="WR-P-E-J-0000000001.p.1.s.9.w.4"><t>nieuwe</t></w><w xml:id="WR-P-E-J-0000000001.p.1.s.9.w.5"><t>zin</t></w><w xml:id="WR-P-E-J-0000000001.p.1.s.9.w.6" class="PUNCTUATION"><t>.</t></w></s>'))

    def test002_addannotation(self):
        """Edit Check - Adding a token annotation (pos, lemma) (pre-generated instances)"""

        #grab a word (naam)
        w = self.doc['WR-P-E-J-0000000001.p.1.s.2.w.11']

        self.doc.declare(folia.PosAnnotation, 'adhocpos')
        self.doc.declare(folia.LemmaAnnotation, 'adhoclemma')

        #add a pos annotation (in a different set than the one already present, to prevent conflict)
        w.append( folia.PosAnnotation(self.doc, set='adhocpos', cls='NOUN', annotator='testscript', annotatortype=folia.AnnotatorType.AUTO) )
        w.append( folia.LemmaAnnotation(self.doc, set='adhoclemma', cls='NAAM', annotator='testscript', annotatortype=folia.AnnotatorType.AUTO, datetime=datetime(1982, 12, 15, 19, 0, 1) ) )

        #retrieve and check
        p = w.annotation(folia.PosAnnotation, 'adhocpos')
        self.assertTrue( isinstance(p, folia.PosAnnotation) )
        self.assertEqual( p.cls, 'NOUN' )

        l = w.annotation(folia.LemmaAnnotation, 'adhoclemma')
        self.assertTrue( isinstance(l, folia.LemmaAnnotation) )
        self.assertEqual( l.cls, 'NAAM' )

        self.assertTrue( xmlcheck(w.xmlstring(), '<w xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.2.w.11"><t>naam</t><pos class="N(soort,ev,basis,zijd,stan)" set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn"/><lemma class="naam" set="lemmas-nl"/><pos class="NOUN" set="adhocpos" annotatortype="auto" annotator="testscript"/><lemma set="adhoclemma" class="NAAM" datetime="1982-12-15T19:00:01" annotatortype="auto" annotator="testscript"/></w>') )

    def test002b_addannotation(self):
        """Edit Check - Adding a token annotation (pos, lemma) (instances generated on the fly)"""

        #grab a word (naam)
        w = self.doc['WR-P-E-J-0000000001.p.1.s.2.w.11']

        self.doc.declare(folia.PosAnnotation, 'adhocpos')
        self.doc.declare(folia.LemmaAnnotation, 'adhoclemma')

        #add a pos annotation (in a different set than the one already present, to prevent conflict)
        w.append( folia.PosAnnotation, set='adhocpos', cls='NOUN', annotator='testscript', annotatortype=folia.AnnotatorType.AUTO)
        w.append( folia.LemmaAnnotation, set='adhoclemma', cls='NAAM', annotator='testscript', annotatortype=folia.AnnotatorType.AUTO )

        #retrieve and check
        p = w.annotation(folia.PosAnnotation, 'adhocpos')
        self.assertTrue( isinstance(p, folia.PosAnnotation) )
        self.assertEqual( p.cls, 'NOUN' )

        l = w.annotation(folia.LemmaAnnotation, 'adhoclemma')
        self.assertTrue( isinstance(l, folia.LemmaAnnotation) )
        self.assertEqual( l.cls, 'NAAM' )

        self.assertTrue( xmlcheck(w.xmlstring(), '<w xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.2.w.11"><t>naam</t><pos class="N(soort,ev,basis,zijd,stan)" set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn"/><lemma class="naam" set="lemmas-nl"/><pos class="NOUN" set="adhocpos" annotatortype="auto" annotator="testscript"/><lemma class="NAAM" set="adhoclemma" annotatortype="auto" annotator="testscript"/></w>'))

    def test002c_addannotation(self):
        """Edit Check - Adding a token annotation (pos, lemma) (using add instead of append)"""

        #grab a word (naam)
        w = self.doc['WR-P-E-J-0000000001.p.1.s.2.w.11']

        self.doc.declare(folia.PosAnnotation, 'adhocpos')
        self.doc.declare(folia.LemmaAnnotation, 'adhoclemma')

        #add a pos annotation (in a different set than the one already present, to prevent conflict)
        w.add( folia.PosAnnotation(self.doc, set='adhocpos', cls='NOUN', annotator='testscript', annotatortype=folia.AnnotatorType.AUTO) )
        w.add( folia.LemmaAnnotation(self.doc, set='adhoclemma', cls='NAAM', annotator='testscript', annotatortype=folia.AnnotatorType.AUTO, datetime=datetime(1982, 12, 15, 19, 0, 1) ) )

        #retrieve and check
        p = w.annotation(folia.PosAnnotation, 'adhocpos')
        self.assertTrue( isinstance(p, folia.PosAnnotation) )
        self.assertEqual( p.cls, 'NOUN' )

        l = w.annotation(folia.LemmaAnnotation, 'adhoclemma')
        self.assertTrue( isinstance(l, folia.LemmaAnnotation) )
        self.assertEqual( l.cls, 'NAAM' )

        self.assertTrue( xmlcheck(w.xmlstring(), '<w xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.2.w.11"><t>naam</t><pos class="N(soort,ev,basis,zijd,stan)" set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn"/><lemma class="naam" set="lemmas-nl"/><pos class="NOUN" set="adhocpos" annotatortype="auto" annotator="testscript"/><lemma set="adhoclemma" class="NAAM" datetime="1982-12-15T19:00:01" annotatortype="auto" annotator="testscript"/></w>') )

    def test004_addinvalidannotation(self):
        """Edit Check - Adding a token default-set annotation that clashes with the existing one"""
        #grab a word (naam)
        w = self.doc['WR-P-E-J-0000000001.p.1.s.2.w.11']

        #add a pos annotation without specifying a set (should take default set), but this will clash with existing tag!

        self.assertRaises( folia.DuplicateAnnotationError, w.append, folia.PosAnnotation(self.doc,  cls='N', annotator='testscript', annotatortype=folia.AnnotatorType.AUTO, set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" ) )
        self.assertRaises( folia.DuplicateAnnotationError, w.append, folia.LemmaAnnotation(self.doc, cls='naam', annotator='testscript', annotatortype=folia.AnnotatorType.AUTO ) )

    def test005_addalternative(self):
        """Edit Check - Adding an alternative token annotation"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.2.w.11']
        w.append( folia.Alternative(self.doc, generate_id_in=w, contents=folia.PosAnnotation(self.doc, cls='V', set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" )))

        #reobtaining it:
        alt = list(w.alternatives()) #all alternatives

        set = "https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" #pylint: disable=redefined-builtin

        alt2 = list(w.alternatives(folia.PosAnnotation, set))

        self.assertEqual( alt[0],alt2[0] )
        self.assertEqual( len(alt),1 )
        self.assertEqual( len(alt2),1 )
        self.assertTrue( isinstance(alt[0].annotation(folia.PosAnnotation, set), folia.PosAnnotation) )

        self.assertTrue( xmlcheck(w.xmlstring(), '<w xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.2.w.11"><t>naam</t><pos set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" class="N(soort,ev,basis,zijd,stan)"/><lemma class="naam"/><alt xml:id="WR-P-E-J-0000000001.p.1.s.2.w.11.alt.1" auth="no"><pos set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" class="V"/></alt></w>'))


    def test006_addcorrection(self):
        """Edit Check - Correcting Text"""
        w = self.doc.index['WR-P-E-J-0000000001.p.1.s.8.w.11'] #stippelijn

        w.correct(new='stippellijn', set='corrections',cls='spelling',annotator='testscript', annotatortype=folia.AnnotatorType.AUTO)
        self.assertEqual( w.annotation(folia.Correction).original(0).text() ,'stippelijn' )
        self.assertEqual( w.annotation(folia.Correction).new(0).text() ,'stippellijn' )
        self.assertEqual( w.text(), 'stippellijn')

        self.assertTrue( xmlcheck(w.xmlstring(),'<w xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.8.w.11"><pos set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" class="FOUTN(soort,ev,basis,zijd,stan)"/><lemma class="stippelijn"/><correction xml:id="WR-P-E-J-0000000001.p.1.s.8.w.11.correction.1" class="spelling" annotatortype="auto" annotator="testscript"><new><t>stippellijn</t></new><original auth="no"><t>stippelijn</t></original></correction></w>'))

    def test006b_addcorrection(self):
        """Edit Check - Correcting Text (2)"""
        w = self.doc.index['WR-P-E-J-0000000001.p.1.s.8.w.11'] #stippelijn

        w.correct(new=folia.TextContent(self.doc,value='stippellijn',cls='current'), set='corrections',cls='spelling',annotator='testscript', annotatortype=folia.AnnotatorType.AUTO)
        self.assertEqual( w.annotation(folia.Correction).original(0).text() ,'stippelijn' )
        self.assertEqual( w.annotation(folia.Correction).new(0).text() ,'stippellijn' )
        self.assertEqual( w.text(), 'stippellijn')

        self.assertTrue( xmlcheck(w.xmlstring(),'<w xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.8.w.11"><pos set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" class="FOUTN(soort,ev,basis,zijd,stan)"/><lemma class="stippelijn"/><correction xml:id="WR-P-E-J-0000000001.p.1.s.8.w.11.correction.1" class="spelling" annotatortype="auto" annotator="testscript"><new><t>stippellijn</t></new><original auth="no"><t>stippelijn</t></original></correction></w>'))

    def test007_addcorrection2(self):
        """Edit Check - Correcting a Token Annotation element"""
        w = self.doc.index['WR-P-E-J-0000000001.p.1.s.8.w.11'] #stippelijn
        oldpos = w.annotation(folia.PosAnnotation)
        newpos = folia.PosAnnotation(self.doc, cls='N(soort,ev,basis,zijd,stan)', set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" )
        w.correct(original=oldpos,new=newpos, set='corrections',cls='spelling',annotator='testscript', annotatortype=folia.AnnotatorType.AUTO)

        self.assertEqual( w.annotation(folia.Correction).original(0) ,oldpos )
        self.assertEqual( w.annotation(folia.Correction).new(0),newpos )

        self.assertTrue( xmlcheck(w.xmlstring(),'<w xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.8.w.11"><t>stippelijn</t><correction xml:id="WR-P-E-J-0000000001.p.1.s.8.w.11.correction.1" class="spelling" annotatortype="auto" annotator="testscript"><new><pos set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" class="N(soort,ev,basis,zijd,stan)"/></new><original auth="no"><pos set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" class="FOUTN(soort,ev,basis,zijd,stan)"/></original></correction><lemma class="stippelijn"/></w>'))

    def test008_addsuggestion(self):
        """Edit Check - Suggesting a text correction"""
        w = self.doc.index['WR-P-E-J-0000000001.p.1.s.8.w.11'] #stippelijn
        w.correct(suggestion='stippellijn', set='corrections',cls='spelling',annotator='testscript', annotatortype=folia.AnnotatorType.AUTO)

        self.assertTrue( isinstance(w.annotation(folia.Correction), folia.Correction) )
        self.assertEqual( w.annotation(folia.Correction).suggestions(0).text() , 'stippellijn' )
        self.assertEqual( w.text(), 'stippelijn')

        self.assertTrue( xmlcheck(w.xmlstring(),'<w xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.8.w.11"><t>stippelijn</t><pos set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" class="FOUTN(soort,ev,basis,zijd,stan)"/><lemma class="stippelijn"/><correction xml:id="WR-P-E-J-0000000001.p.1.s.8.w.11.correction.1" class="spelling" annotatortype="auto" annotator="testscript"><suggestion auth="no"><t>stippellijn</t></suggestion></correction></w>'))

    def test009a_idclash(self):
        """Edit Check - Checking for exception on adding a duplicate ID"""
        w = self.doc.index['WR-P-E-J-0000000001.p.1.s.8.w.11']

        self.assertRaises( folia.DuplicateIDError,  w.sentence().append, folia.Word, id='WR-P-E-J-0000000001.p.1.s.8.w.11', text='stippellijn')


    #def test009b_textcorrectionlevel(self):
    #    """Edit Check - Checking for exception on an adding TextContent of wrong level"""
    #    w = self.doc.index['WR-P-E-J-0000000001.p.1.s.8.w.11']
    #
    #    self.assertRaises(  ValueError, w.append, folia.TextContent, value='blah', corrected=folia.TextCorrectionLevel.ORIGINAL )
    #

    #def test009c_duptextcontent(self):
    #    """Edit Check - Checking for exception on an adding duplicate textcontent"""
    #    w = self.doc.index['WR-P-E-J-0000000001.p.1.s.8.w.11']
    #
    #    self.assertRaises(  folia.DuplicateAnnotationError, w.append, folia.TextContent, value='blah', corrected=folia.TextCorrectionLevel.PROCESSED )

    def test010_documentlesselement(self):
        """Edit Check - Creating an initially document-less tokenannotation element and adding it to a word"""

        #not associated with any document yet (first argument is None instead of Document instance)
        pos = folia.PosAnnotation(None, set='fakecgn', cls='N')

        w = self.doc.index['WR-P-E-J-0000000001.p.1.s.8.w.11']
        w.append(pos)

        self.assertEqual( w.annotation(folia.PosAnnotation,'fakecgn'), pos)
        self.assertEqual( pos.parent, w)
        self.assertEqual( pos.doc, w.doc)

        self.assertTrue( xmlcheck(w.xmlstring(), '<w xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.8.w.11"><t>stippelijn</t><pos set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" class="FOUTN(soort,ev,basis,zijd,stan)"/><lemma class="stippelijn"/><pos class="N" set="fakecgn"/></w>'))

    def test011_subtokenannot(self):
        """Edit Check - Adding morphemes"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.5.w.3']
        l = w.append( folia.MorphologyLayer )
        l.append( folia.Morpheme(self.doc, folia.TextContent(self.doc, value='handschrift', offset=0), folia.LemmaAnnotation(self.doc, cls='handschrift'), cls='stem',function='lexical'  ))
        l.append( folia.Morpheme(self.doc, folia.TextContent(self.doc, value='en', offset=11), cls='suffix',function='inflexional' ))


        self.assertEqual( len(l), 2) #two morphemes
        self.assertTrue( isinstance(l[0], folia.Morpheme ) )
        self.assertEqual( l[0].text(), 'handschrift' )
        self.assertEqual( l[0].cls , 'stem' )
        self.assertEqual( l[0].feat('function'), 'lexical' )
        self.assertEqual( l[1].text(), 'en' )
        self.assertEqual( l[1].cls, 'suffix' )
        self.assertEqual( l[1].feat('function'), 'inflexional' )



        self.assertTrue( xmlcheck(w.xmlstring(),'<w xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.5.w.3"><t>handschriften</t><pos set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" class="N(soort,mv,basis)"/><lemma class="handschrift"/><morphology><morpheme function="lexical" class="stem"><t offset="0">handschrift</t><lemma class="handschrift"/></morpheme><morpheme function="inflexional" class="suffix"><t offset="11">en</t></morpheme></morphology></w>'))

    def test012_relation(self):
        """Edit Check - Adding Relation"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.6.w.8']

        a = w.append( folia.Relation, cls="coreference")
        a.append( folia.LinkReference, id='WR-P-E-J-0000000001.p.1.s.6.w.1', type=folia.Word)
        a.append( folia.LinkReference, id='WR-P-E-J-0000000001.p.1.s.6.w.2', type=folia.Word)

        self.assertEqual( next(a.resolve()), self.doc['WR-P-E-J-0000000001.p.1.s.6.w.1'] )
        self.assertEqual( list(a.resolve())[1], self.doc['WR-P-E-J-0000000001.p.1.s.6.w.2'] )

        self.assertTrue( xmlcheck(w.xmlstring(),'<w xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.6.w.8"><t>ze</t><pos set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" class="VNW(pers,pron,stan,red,3,mv)"/><lemma class="ze"/><relation class="coreference"><xref type="w" id="WR-P-E-J-0000000001.p.1.s.6.w.1"/><xref type="w" id="WR-P-E-J-0000000001.p.1.s.6.w.2"/></relation></w>'))



    def test013_spanannot(self):
        """Edit Check - Adding nested Span Annotatation (syntax)"""

        s = self.doc['WR-P-E-J-0000000001.p.1.s.4']
        #sentence: 'De hoofdletter A wordt gebruikt voor het originele handschrift .'
        layer = s.append(folia.SyntaxLayer)
        layer.append(
            folia.SyntacticUnit(self.doc,cls='s',contents=[
                folia.SyntacticUnit(self.doc,cls='np', contents=[
                    folia.SyntacticUnit(self.doc, self.doc['WR-P-E-J-0000000001.p.1.s.4.w.1'] ,cls='det'),
                    folia.SyntacticUnit(self.doc, self.doc['WR-P-E-J-0000000001.p.1.s.4.w.2'], cls='n'),
                    folia.SyntacticUnit(self.doc, self.doc['WR-P-E-J-0000000001.p.1.s.4.w.3'], cls='n'),
                ]),
                folia.SyntacticUnit(self.doc,cls='vp',contents=[
                    folia.SyntacticUnit(self.doc,cls='vp',contents=[
                        folia.SyntacticUnit(self.doc, self.doc['WR-P-E-J-0000000001.p.1.s.4.w.4'], cls='v'),
                        folia.SyntacticUnit(self.doc, self.doc['WR-P-E-J-0000000001.p.1.s.4.w.5'], cls='participle'),
                    ]),
                    folia.SyntacticUnit(self.doc, cls='pp',contents=[
                        folia.SyntacticUnit(self.doc, self.doc['WR-P-E-J-0000000001.p.1.s.4.w.6'], cls='prep'),
                        folia.SyntacticUnit(self.doc, cls='np',contents=[
                            folia.SyntacticUnit(self.doc, self.doc['WR-P-E-J-0000000001.p.1.s.4.w.7'], cls='det'),
                            folia.SyntacticUnit(self.doc, self.doc['WR-P-E-J-0000000001.p.1.s.4.w.8'], cls='adj'),
                            folia.SyntacticUnit(self.doc, self.doc['WR-P-E-J-0000000001.p.1.s.4.w.9'], cls='n'),
                        ])
                    ])
                ])
            ])
        )

        self.assertTrue( xmlcheck(layer.xmlstring(),'<syntax xmlns="http://ilk.uvt.nl/folia"><su class="s"><su class="np"><su class="det"><wref id="WR-P-E-J-0000000001.p.1.s.4.w.1" t="De"/></su><su class="n"><wref id="WR-P-E-J-0000000001.p.1.s.4.w.2" t="hoofdletter"/></su><su class="n"><wref id="WR-P-E-J-0000000001.p.1.s.4.w.3" t="A"/></su></su><su class="vp"><su class="vp"><su class="v"><wref id="WR-P-E-J-0000000001.p.1.s.4.w.4" t="wordt"/></su><su class="participle"><wref id="WR-P-E-J-0000000001.p.1.s.4.w.5" t="gebruikt"/></su></su><su class="pp"><su class="prep"><wref id="WR-P-E-J-0000000001.p.1.s.4.w.6" t="voor"/></su><su class="np"><su class="det"><wref id="WR-P-E-J-0000000001.p.1.s.4.w.7" t="het"/></su><su class="adj"><wref id="WR-P-E-J-0000000001.p.1.s.4.w.8" t="originele"/></su><su class="n"><wref id="WR-P-E-J-0000000001.p.1.s.4.w.9" t="handschrift"/></su></su></su></su></su></syntax>'))

    def test013a_spanannot(self):
        """Edit Check - Adding Span Annotation (entity, from word using add)"""
        word = self.doc["WR-P-E-J-0000000001.p.1.s.4.w.2"] #hoofdletter
        word2 = self.doc["WR-P-E-J-0000000001.p.1.s.4.w.3"] #A
        entity = word.add(folia.Entity, word, word2, cls="misc",set="http://raw.github.com/proycon/folia/master/setdefinitions/namedentities.foliaset.xml")

        self.assertIsInstance(entity, folia.Entity)
        self.assertTrue(xmlcheck(entity.parent.parent.xmlstring(),'<part xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.4.part.1"><w xml:id="WR-P-E-J-0000000001.p.1.s.4.w.1"><t offset="0" ref="WR-P-E-J-0000000001.p.1.s.4">De</t><t class="original" offset="0" ref="WR-P-E-J-0000000001.p.1.s.4">De</t><pos class="LID(bep,stan,rest)" set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn"/><lemma class="de"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.4.w.2"><t offset="3" ref="WR-P-E-J-0000000001.p.1.s.4">hoofdletter</t><t class="original" offset="3" ref="WR-P-E-J-0000000001.p.1.s.4">hoofdletter</t><pos class="N(soort,ev,basis,zijd,stan)" set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn"/><lemma class="hoofdletter"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.4.w.3"><t>A</t><t class="original">A</t><pos class="SPEC(symb)" set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn"/><lemma class="_"/></w><entities><entity class="misc" set="http://raw.github.com/proycon/folia/master/setdefinitions/namedentities.foliaset.xml"><wref id="WR-P-E-J-0000000001.p.1.s.4.w.2" t="hoofdletter"/><wref id="WR-P-E-J-0000000001.p.1.s.4.w.3" t="A"/></entity></entities></part>'))
    def test013b_spanannot(self):
        """Edit Check - Adding nested Span Annotatation (add as append)"""

        s = self.doc['WR-P-E-J-0000000001.p.1.s.4']
        #sentence: 'De hoofdletter A wordt gebruikt voor het originele handschrift .'
        layer = s.add(folia.SyntaxLayer)
        layer.add(
            folia.SyntacticUnit(self.doc,cls='s',contents=[
                folia.SyntacticUnit(self.doc,cls='np', contents=[
                    folia.SyntacticUnit(self.doc, self.doc['WR-P-E-J-0000000001.p.1.s.4.w.1'] ,cls='det'),
                    folia.SyntacticUnit(self.doc, self.doc['WR-P-E-J-0000000001.p.1.s.4.w.2'], cls='n'),
                    folia.SyntacticUnit(self.doc, self.doc['WR-P-E-J-0000000001.p.1.s.4.w.3'], cls='n'),
                ]),
                folia.SyntacticUnit(self.doc,cls='vp',contents=[
                    folia.SyntacticUnit(self.doc,cls='vp',contents=[
                        folia.SyntacticUnit(self.doc, self.doc['WR-P-E-J-0000000001.p.1.s.4.w.4'], cls='v'),
                        folia.SyntacticUnit(self.doc, self.doc['WR-P-E-J-0000000001.p.1.s.4.w.5'], cls='participle'),
                    ]),
                    folia.SyntacticUnit(self.doc, cls='pp',contents=[
                        folia.SyntacticUnit(self.doc, self.doc['WR-P-E-J-0000000001.p.1.s.4.w.6'], cls='prep'),
                        folia.SyntacticUnit(self.doc, cls='np',contents=[
                            folia.SyntacticUnit(self.doc, self.doc['WR-P-E-J-0000000001.p.1.s.4.w.7'], cls='det'),
                            folia.SyntacticUnit(self.doc, self.doc['WR-P-E-J-0000000001.p.1.s.4.w.8'], cls='adj'),
                            folia.SyntacticUnit(self.doc, self.doc['WR-P-E-J-0000000001.p.1.s.4.w.9'], cls='n'),
                        ])
                    ])
                ])
            ])
        )

        self.assertTrue( xmlcheck(layer.xmlstring(),'<syntax xmlns="http://ilk.uvt.nl/folia"><su class="s"><su class="np"><su class="det"><wref id="WR-P-E-J-0000000001.p.1.s.4.w.1" t="De"/></su><su class="n"><wref id="WR-P-E-J-0000000001.p.1.s.4.w.2" t="hoofdletter"/></su><su class="n"><wref id="WR-P-E-J-0000000001.p.1.s.4.w.3" t="A"/></su></su><su class="vp"><su class="vp"><su class="v"><wref id="WR-P-E-J-0000000001.p.1.s.4.w.4" t="wordt"/></su><su class="participle"><wref id="WR-P-E-J-0000000001.p.1.s.4.w.5" t="gebruikt"/></su></su><su class="pp"><su class="prep"><wref id="WR-P-E-J-0000000001.p.1.s.4.w.6" t="voor"/></su><su class="np"><su class="det"><wref id="WR-P-E-J-0000000001.p.1.s.4.w.7" t="het"/></su><su class="adj"><wref id="WR-P-E-J-0000000001.p.1.s.4.w.8" t="originele"/></su><su class="n"><wref id="WR-P-E-J-0000000001.p.1.s.4.w.9" t="handschrift"/></su></su></su></su></su></syntax>'))

    def test013c_spanannotcorrection(self):
        """Edit Check - Correcting Span Annotation"""
        s = self.doc['example.cell']
        l = s.annotation(folia.EntitiesLayer)
        l.correct(original=self.doc['example.radboud.university.nijmegen.org'], new=folia.Entity(self.doc, *self.doc['example.radboud.university.nijmegen.org'].wrefs(), cls="loc",set="http://raw.github.com/proycon/folia/master/setdefinitions/namedentities.foliaset.xml") ,set='corrections',cls='wrongclass')

        self.assertTrue( xmlcheck(l.xmlstring(), '<entities xmlns="http://ilk.uvt.nl/folia"><correction xml:id="example.cell.correction.1" class="wrongclass"><new><entity class="loc" set="http://raw.github.com/proycon/folia/master/setdefinitions/namedentities.foliaset.xml"><wref t="Radboud" id="example.table.1.w.6"/><wref t="University" id="example.table.1.w.7"/><wref t="Nijmegen" id="example.table.1.w.8"/></entity></new><original auth="no"><entity xml:id="example.radboud.university.nijmegen.org" class="org" set="http://raw.github.com/proycon/folia/master/setdefinitions/namedentities.foliaset.xml"><comment annotator="proycon">This is our university!</comment><wref t="Radboud" id="example.table.1.w.6"/><wref t="University" id="example.table.1.w.7"/><wref t="Nijmegen" id="example.table.1.w.8"/></entity></original></correction></entities>'))

    def test013d_spanannot(self):
        """Edit Check - Adding Span Annotation (entity, from sentence using add)"""
        sentence = self.doc["WR-P-E-J-0000000001.p.1.s.4"]
        word = self.doc["WR-P-E-J-0000000001.p.1.s.4.w.2"] #hoofdletter
        word2 = self.doc["WR-P-E-J-0000000001.p.1.s.4.w.3"] #A
        entity = sentence.add(folia.Entity, word, word2, cls="misc",set="http://raw.github.com/proycon/folia/master/setdefinitions/namedentities.foliaset.xml")

        self.assertIsInstance(entity, folia.Entity)
        self.assertTrue(xmlcheck(entity.parent.parent.xmlstring(),'<s xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.4"><t>De hoofdletter A wordt gebruikt voor het originele handschrift.</t><t class="original">De hoofdletter A wordt gebruikt voor het originele handschrift.</t><t class="translate">Uppercase A is used for the original.</t><part xml:id="WR-P-E-J-0000000001.p.1.s.4.part.1"><w xml:id="WR-P-E-J-0000000001.p.1.s.4.w.1"><t offset="0" ref="WR-P-E-J-0000000001.p.1.s.4">De</t><t class="original" offset="0" ref="WR-P-E-J-0000000001.p.1.s.4">De</t><pos class="LID(bep,stan,rest)" set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn"/><lemma class="de"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.4.w.2"><t offset="3" ref="WR-P-E-J-0000000001.p.1.s.4">hoofdletter</t><t class="original" offset="3" ref="WR-P-E-J-0000000001.p.1.s.4">hoofdletter</t><pos class="N(soort,ev,basis,zijd,stan)" set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn"/><lemma class="hoofdletter"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.4.w.3"><t>A</t><t class="original">A</t><pos class="SPEC(symb)" set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn"/><lemma class="_"/></w></part><part xml:id="WR-P-E-J-0000000001.p.1.s.4.part.2"><w xml:id="WR-P-E-J-0000000001.p.1.s.4.w.4"><t>wordt</t><t class="original">wordt</t><pos class="WW(pv,tgw,met-t)" set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn"/><lemma class="worden"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.4.w.5"><t>gebruikt</t><t class="original">gebruikt</t><pos class="WW(vd,vrij,zonder)" set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" textclass="original"/><lemma class="gebruiken" textclass="original"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.4.w.6"><t>voor</t><t class="original">voor</t><pos class="VZ(init)" set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn"/><lemma class="voor"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.4.w.7"><t>het</t><t class="original">het</t><pos class="LID(bep,stan,evon)" set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn"/><lemma class="het"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.4.w.8"><t>originele</t><t class="original">originele</t><pos class="ADJ(prenom,basis,met-e,stan)" set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn"/><lemma class="origineel"/></w><w space="no" xml:id="WR-P-E-J-0000000001.p.1.s.4.w.9"><t>handschrift</t><t class="original">handschrift</t><pos class="N(soort,ev,basis,onz,stan)" set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn"/><lemma class="handschrift"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.4.w.10"><t>.</t><t class="original">.</t><pos class="LET()" set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn"/><lemma class="."/></w></part><entities><entity class="misc" set="http://raw.github.com/proycon/folia/master/setdefinitions/namedentities.foliaset.xml"><wref id="WR-P-E-J-0000000001.p.1.s.4.w.2" t="hoofdletter"/><wref id="WR-P-E-J-0000000001.p.1.s.4.w.3" t="A"/></entity></entities></s>'))

    def test013e_spanannot(self):
        """Edit Check - Adding nested Span Annotation"""
        word = self.doc["WR-P-E-J-0000000001.p.1.s.1.w.7"] #stamboom
        for su in word.findspans(folia.SyntacticUnit):
            if su.cls == 'pp':
                parentspan = su
        self.assertIsInstance(parentspan, folia.SyntacticUnit)
        self.assertEqual(parentspan.wrefs(recurse=False) , [self.doc["WR-P-E-J-0000000001.p.1.s.1.w.6"],self.doc["WR-P-E-J-0000000001.p.1.s.1.w.7"]]) #prior to adding
        newspan = parentspan.add(folia.SyntacticUnit, word, cls='np')
        self.doc.done() #signal we are done editing, needed to invoke postprocessing
        self.assertEqual(parentspan.wrefs(recurse=False) , [self.doc["WR-P-E-J-0000000001.p.1.s.1.w.6"]]) #after adding, parent span wref gone (moved to child)
        self.assertEqual(parentspan.wrefs(recurse=True) , [self.doc["WR-P-E-J-0000000001.p.1.s.1.w.6"],self.doc["WR-P-E-J-0000000001.p.1.s.1.w.7"]]) #result is still the same with recursion
        self.assertEqual(newspan.wrefs() , [self.doc["WR-P-E-J-0000000001.p.1.s.1.w.7"]])

    def test014_replace(self):
        """Edit Check - Replacing an annotation"""
        word = self.doc['WR-P-E-J-0000000001.p.1.s.3.w.14']
        word.replace(folia.PosAnnotation(self.doc, cls='BOGUS', set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" ) )

        self.assertEqual( len(list(word.annotations(folia.PosAnnotation))), 1)
        self.assertEqual( word.annotation(folia.PosAnnotation).cls, 'BOGUS')

        self.assertTrue( xmlcheck(word.xmlstring(), '<w xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.3.w.14"><t>plaats</t><lemma class="plaats"/><pos set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" class="BOGUS"/></w>'))

    def test015_remove(self):
        """Edit Check - Removing an annotation"""
        word = self.doc['WR-P-E-J-0000000001.p.1.s.3.w.14']
        word.remove( word.annotation(folia.PosAnnotation) )

        self.assertRaises( folia.NoSuchAnnotation, word.annotation, folia.PosAnnotation )

        self.assertTrue( xmlcheck(word.xmlstring(), '<w xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.3.w.14"><t>plaats</t><lemma class="plaats"/></w>'))

    def test016_datetime(self):
        """Edit Check - Time stamp"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.8.w.16']
        pos = w.annotation(folia.PosAnnotation)
        pos.datetime = datetime(1982, 12, 15, 19, 0, 1) #(the datetime of my joyful birth)

        self.assertTrue( xmlcheck(pos.xmlstring(), '<pos xmlns="http://ilk.uvt.nl/folia" set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" class="WW(pv,tgw,met-t)" datetime="1982-12-15T19:00:01"/>'))

    def test017_wordtext(self):
        """Edit Check - Altering word text"""

        #Important note: directly altering text is usually bad practise, you'll want to use proper corrections instead.
        #this may also lead to inconsistencies if there is redundant text on higher levels
        w = self.doc['WR-P-E-J-0000000001.p.1.s.8.w.9']
        self.assertEqual(w.text(), 'terweil')

        w.settext('terwijl')
        self.assertEqual(w.text(), 'terwijl')

    def test017b_wordtext(self):
        """Edit Check - Altering word text with reserved symbols"""

        #Important note: directly altering text is usually bad practise, you'll want to use proper corrections instead.
        #This test just serves to test reserved symbols
        w = self.doc['WR-P-E-J-0000000001.p.1.s.8.w.9']

        w.settext('1 & 1 > 0')
        self.assertEqual(w.text(), '1 & 1 > 0')
        self.assertTrue(xmlcheck(w.textcontent().xmlstring(), '<t>1 &amp; 1 &gt; 0</t>'))

    def test018a_sentencetext(self):
        """Edit Check - Altering sentence text (untokenised by definition)"""
        s = self.doc['WR-P-E-J-0000000001.p.1.s.1']

        self.assertEqual(s.text(), 'Stemma is een ander woord voor stamboom.') #text is obtained from children, since there is no direct text associated

        self.assertFalse(s.hastext()) #no text DIRECTLY associated with the sentence

        #associating text directly with the sentence (should be in agreement with text from children)
        s.settext('Stemma is een ander woord voor stamboom.')
        self.assertTrue(s.hastext())
        self.assertEqual(s.text(), 'Stemma is een ander woord voor stamboom.') #text still obtained from children rather than directly associated text!!
        self.assertEqual(s.stricttext(), 'Stemma is een ander woord voor stamboom.') #text obtained directly


    def test018b_sentencetext(self):
        """Edit Check - Altering sentence text (untokenised by definition)"""

        s = self.doc['WR-P-E-J-0000000001.p.1.s.8']

        self.assertEqual( s.text(), 'Een volle lijn duidt op een verwantschap , terweil een stippelijn op een onzekere verwantschap duidt .' ) #dynamic from children

        #s.settext('Een volle lijn duidt op een verwantschap, terwijl een stippellijn op een onzekere verwantschap duidt.' ) #setting the correct text here will cause a mismatch with the text on deeper levels, but is permitted (deep validation should detect it)

        s.settext('Een volle lijn duidt op een verwantschap, terweil een stippelijn op een onzekere verwantschap duidt.', 'original' )

        self.assertEqual( s.text(), 'Een volle lijn duidt op een verwantschap , terweil een stippelijn op een onzekere verwantschap duidt .' ) #from children by default (child has erroneous stippelijn and terweil)
        self.assertTrue( s.hastext('original') )
        self.assertEqual( s.stricttext('original'), 'Een volle lijn duidt op een verwantschap, terweil een stippelijn op een onzekere verwantschap duidt.' )

        self.assertTrue( xmlcheck(s.xmlstring(), '<s xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.8"><t class="original">Een volle lijn duidt op een verwantschap, terweil een stippelijn op een onzekere verwantschap duidt.</t><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.1"><t>Een</t><pos set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" class="LID(onbep,stan,agr)"/><lemma class="een"/></w><quote xml:id="WR-P-E-J-0000000001.p.1.s.8.q.1"><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.2"><t>volle</t><pos set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" class="ADJ(prenom,basis,met-e,stan)"/><lemma class="vol"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.3"><t>lijn</t><pos set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" class="N(soort,ev,basis,zijd,stan)"/><lemma class="lijn"/></w></quote><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.4"><t>duidt</t><pos set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" class="WW(pv,tgw,met-t)"/><lemma class="duiden"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.5"><t>op</t><pos set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" class="VZ(init)"/><lemma class="op"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.6"><t>een</t><pos set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" class="LID(onbep,stan,agr)"/><lemma class="een"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.7"><t>verwantschap</t><pos set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" class="N(soort,ev,basis,zijd,stan)"/><lemma class="verwantschap"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.8"><t>,</t><pos set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" class="LET()"/><lemma class=","/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.9"><t>terweil</t><errordetection class="spelling"/><pos set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" class="VG(onder)"/><lemma class="terweil"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.10"><t>een</t><pos set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" class="LID(onbep,stan,agr)"/><lemma class="een"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.11"><t>stippelijn</t><pos set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" class="FOUTN(soort,ev,basis,zijd,stan)"/><lemma class="stippelijn"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.12"><t>op</t><pos set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" class="VZ(init)"/><lemma class="op"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.13"><t>een</t><pos set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" class="LID(onbep,stan,agr)"/><lemma class="een"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.14"><t>onzekere</t><pos set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" class="ADJ(prenom,basis,met-e,stan)"/><lemma class="onzeker"/><correction xml:id="WR-P-E-J-0000000001.p.1.s.8.w.14.c.1" class="spelling"><suggestion  auth="no" n="1/2"><t>twijfelachtige</t></suggestion><suggestion  auth="no" n="2/2"><t>ongewisse</t></suggestion></correction></w><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.15"><t>verwantschap</t><pos set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" class="N(soort,ev,basis,zijd,stan)" datetime="2011-07-20T19:00:01"/><lemma class="verwantschap"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.16"><t>duidt</t><pos set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" class="WW(pv,tgw,met-t)"/><lemma class="duiden"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.17"><t>.</t><pos set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" class="LET()"/><lemma class="."/></w><observations><observation class="ei_ij_error"><desc>Confusion between EI and IJ diphtongues</desc><wref id="WR-P-E-J-0000000001.p.1.s.8.w.9" t="terweil"/></observation></observations></s>'))

    def test019_adderrordetection(self):
        """Edit Check - Error Detection"""
        w = self.doc.index['WR-P-E-J-0000000001.p.1.s.8.w.11'] #stippelijn

        w.append( folia.ErrorDetection(self.doc, cls="spelling", annotator="testscript", annotatortype=folia.AnnotatorType.AUTO) )
        self.assertEqual( w.annotation(folia.ErrorDetection).cls ,'spelling' )

        #self.assertTrue( xmlcheck(w.xmlstring(),'<w xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.8.w.11"><pos class="FOUTN(soort,ev,basis,zijd,stan)"/><lemma class="stippelijn"/><correction xml:id="WR-P-E-J-0000000001.p.1.s.8.w.11.correction.1" class="spelling" annotatortype="auto" annotator="testscript"><new><t>stippellijn</t></new><original auth="no"><t>stippelijn</t></original></correction></w>'))

    #def test008_addaltcorrection(self):
    #    """Edit Check - Adding alternative corrections"""
    #    w = self.doc.index['WR-P-E-J-0000000001.p.1.s.8.w.11'] #stippelijn
    #    w.correcttext('stippellijn', set='corrections',cls='spelling',annotator='testscript', annotatortype='auto', alternative=True)
    #
    #    alt = w.alternatives(folia.AnnotationType.CORRECTION)
    #    self.assertEqual( alt[0].annotation(folia.Correction).original[0] ,'stippelijn' )
    #    self.assertEqual( alt[0].annotation(folia.Correction).new[0] ,'stippellijn' )

    #def test009_addaltcorrection2(self):
    #    """Edit Check - Adding an alternative and a selected correction"""
    #    w = self.doc.index['WR-P-E-J-0000000001.p.1.s.8.w.11'] #stippelijn
    #    w.correcttext('stippel-lijn', set='corrections',cls='spelling',annotator='testscript', annotatortype='auto', alternative=True)

    #    w.correcttext('stippellijn', set='corrections',cls='spelling',annotator='testscript', annotatortype='auto')

    #    alt = w.alternatives(folia.AnnotationType.CORRECTION)
    #    self.assertEqual( alt[0].annotation(folia.Correction).id ,'WR-P-E-J-0000000001.p.1.s.8.w.11.correction.1' )
    #    self.assertEqual( alt[0].annotation(folia.Correction).original[0] ,'stippelijn' )
    #    self.assertEqual( alt[0].annotation(folia.Correction).new[0] ,'stippel-lijn' )

    #    self.assertEqual( w.annotation(folia.Correction).id ,'WR-P-E-J-0000000001.p.1.s.8.w.11.correction.2' )
    #    self.assertEqual( w.annotation(folia.Correction).original[0] ,'stippelijn' )
    #    self.assertEqual( w.annotation(folia.Correction).new[0] ,'stippellijn' )
    #    self.assertEqual( w.text(), 'stippellijn')

class Test04Create(unittest.TestCase):
    def test001_create(self):
        """Creating a FoLiA Document from scratch"""
        self.doc = folia.Document(id='example')
        self.assertTrue( self.doc.autodeclare )
        self.doc.declare(folia.AnnotationType.TOKEN, 'adhocset',annotator='proycon')

        self.assertEqual(self.doc.defaultset(folia.AnnotationType.TOKEN), 'adhocset')
        self.assertEqual(self.doc.defaultannotator(folia.AnnotationType.TOKEN, 'adhocset'), 'proycon')

        text = folia.Text(self.doc, id=self.doc.id + '.text.1')
        self.doc.append( text )

        text.append(
            folia.Sentence(self.doc,id=self.doc.id + '.s.1', contents=[
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.1', text="De"),
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.2', text="site"),
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.3', text="staat"),
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.4', text="online"),
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.5', text=".")
            ])
        )

        self.assertEqual( len(self.doc.index[self.doc.id + '.s.1']), 5)

class Test05Correction(unittest.TestCase):
    def setUp(self):
        self.doc = folia.Document(id='example', textvalidation=True)
        self.doc.declare(folia.AnnotationType.TOKEN, set='adhocset',annotator='proycon')
        self.doc.declare(folia.AnnotationType.TEXT)
        self.text = folia.Text(self.doc, id=self.doc.id + '.text.1')
        self.doc.append( self.text )


    def test001_splitcorrection(self):
        """Correction - Split correction"""

        self.text.append(
            folia.Sentence(self.doc,id=self.doc.id + '.s.1', contents=[
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.1', text="De"),
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.2', text="site"),
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.3', text="staat"),
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.4', text="online"),
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.5', text=".")
            ])
        )


        w = self.doc.index[self.doc.id + '.s.1.w.4']

        w.split( folia.Word(self.doc, id=self.doc.id + '.s.1.w.4a', text="on"), folia.Word(self.doc, id=self.doc.id + '.s.1.w.4b', text="line") )

        s = self.doc.index[self.doc.id + '.s.1']
        self.assertEqual( s.words(-3).text(), 'on' )
        self.assertEqual( s.words(-2).text(), 'line' )
        self.assertEqual( s.text(), 'De site staat on line .' )
        self.assertEqual( len(list(s.words())), 6 )
        self.assertTrue( xmlcheck(s.xmlstring(),  '<s xmlns="http://ilk.uvt.nl/folia" xml:id="example.s.1"><w xml:id="example.s.1.w.1"><t>De</t></w><w xml:id="example.s.1.w.2"><t>site</t></w><w xml:id="example.s.1.w.3"><t>staat</t></w><correction xml:id="example.s.1.correction.1"><new><w xml:id="example.s.1.w.4a"><t>on</t></w><w xml:id="example.s.1.w.4b"><t>line</t></w></new><original auth="no"><w xml:id="example.s.1.w.4"><t>online</t></w></original></correction><w xml:id="example.s.1.w.5"><t>.</t></w></s>'))


    def test001_splitcorrection2(self):
        """Correction - Split suggestion"""

        self.text.append(
            folia.Sentence(self.doc,id=self.doc.id + '.s.1', contents=[
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.1', text="De"),
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.2', text="site"),
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.3', text="staat"),
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.4', text="online"),
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.5', text=".")
            ])
        )


        w = self.doc.index[self.doc.id + '.s.1.w.4']

        s = self.doc.index[self.doc.id + '.s.1']
        w.split( folia.Word(self.doc, generate_id_in=s, text="on"), folia.Word(self.doc, generate_id_in=s, text="line"), suggest=True )

        self.assertEqual( len(list(s.words())), 5 )
        self.assertEqual( s.words(-2).text(), 'online' )
        self.assertEqual( s.text(), 'De site staat online .' )

        self.assertTrue( xmlcheck(s.xmlstring(), '<s xmlns="http://ilk.uvt.nl/folia" xml:id="example.s.1"><w xml:id="example.s.1.w.1"><t>De</t></w><w xml:id="example.s.1.w.2"><t>site</t></w><w xml:id="example.s.1.w.3"><t>staat</t></w><correction xml:id="example.s.1.correction.1"><current><w xml:id="example.s.1.w.4"><t>online</t></w></current><suggestion auth="no"><w xml:id="example.s.1.w.6"><t>on</t></w><w xml:id="example.s.1.w.7"><t>line</t></w></suggestion></correction><w xml:id="example.s.1.w.5"><t>.</t></w></s>'))


    def test002_mergecorrection(self):
        """Correction - Merge corrections"""
        self.text.append(
            folia.Sentence(self.doc,id=self.doc.id + '.s.1', contents=[
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.1', text="De"),
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.2', text="site"),
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.3', text="staat"),
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.4', text="on"),
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.5', text="line"),
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.6', text=".")
            ])
        )

        s = self.doc.index[self.doc.id + '.s.1']


        s.mergewords( folia.Word(self.doc, 'online', id=self.doc.id + '.s.1.w.4-5') , self.doc.index[self.doc.id + '.s.1.w.4'], self.doc.index[self.doc.id + '.s.1.w.5'] )

        self.assertEqual( len(list(s.words())), 5 )
        self.assertEqual( s.text(), 'De site staat online .')

        #incorrection() test, check if newly added word correctly reports being part of a correction
        w = self.doc.index[self.doc.id + '.s.1.w.4-5']
        self.assertTrue( isinstance(w.incorrection(), folia.Correction) ) #incorrection return the correction the word is part of, or None if not part of a correction,


        self.assertTrue( xmlcheck(s.xmlstring(),  '<s xmlns="http://ilk.uvt.nl/folia" xml:id="example.s.1"><w xml:id="example.s.1.w.1"><t>De</t></w><w xml:id="example.s.1.w.2"><t>site</t></w><w xml:id="example.s.1.w.3"><t>staat</t></w><correction xml:id="example.s.1.correction.1"><new><w xml:id="example.s.1.w.4-5"><t>online</t></w></new><original auth="no"><w xml:id="example.s.1.w.4"><t>on</t></w><w xml:id="example.s.1.w.5"><t>line</t></w></original></correction><w xml:id="example.s.1.w.6"><t>.</t></w></s>'))


    def test003_deletecorrection(self):
        """Correction - Deletion"""

        self.text.append(
            folia.Sentence(self.doc,id=self.doc.id + '.s.1', contents=[
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.1', text="Ik"),
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.2', text="zie"),
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.3', text="een"),
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.4', text="groot"),
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.5', text="huis"),
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.6', text=".")
            ])
        )
        s = self.doc.index[self.doc.id + '.s.1']
        s.deleteword(self.doc.index[self.doc.id + '.s.1.w.4'])
        self.assertEqual( len(list(s.words())), 5 )
        self.assertEqual( s.text(), 'Ik zie een huis .')

        self.assertTrue( xmlcheck(s.xmlstring(), '<s xmlns="http://ilk.uvt.nl/folia" xml:id="example.s.1"><w xml:id="example.s.1.w.1"><t>Ik</t></w><w xml:id="example.s.1.w.2"><t>zie</t></w><w xml:id="example.s.1.w.3"><t>een</t></w><correction xml:id="example.s.1.correction.1"><new/><original auth="no"><w xml:id="example.s.1.w.4"><t>groot</t></w></original></correction><w xml:id="example.s.1.w.5"><t>huis</t></w><w xml:id="example.s.1.w.6"><t>.</t></w></s>') )

    def test004_insertcorrection(self):
        """Correction - Insert"""
        self.text.append(
            folia.Sentence(self.doc,id=self.doc.id + '.s.1', contents=[
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.1', text="Ik"),
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.2', text="zie"),
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.3', text="een"),
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.4', text="huis"),
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.5', text=".")
            ])
        )
        s = self.doc.index[self.doc.id + '.s.1']
        s.insertword( folia.Word(self.doc, id=self.doc.id+'.s.1.w.3b',text='groot'),  self.doc.index[self.doc.id + '.s.1.w.3'])
        self.assertEqual( len(list(s.words())), 6 )

        self.assertEqual( s.text(), 'Ik zie een groot huis .')
        self.assertTrue( xmlcheck( s.xmlstring(), '<s xmlns="http://ilk.uvt.nl/folia" xml:id="example.s.1"><w xml:id="example.s.1.w.1"><t>Ik</t></w><w xml:id="example.s.1.w.2"><t>zie</t></w><w xml:id="example.s.1.w.3"><t>een</t></w><correction xml:id="example.s.1.correction.1"><new><w xml:id="example.s.1.w.3b"><t>groot</t></w></new></correction><w xml:id="example.s.1.w.4"><t>huis</t></w><w xml:id="example.s.1.w.5"><t>.</t></w></s>'))

    def test005_reusecorrection(self):
        """Correction - Re-using a correction with only suggestions"""
        self.doc = folia.Document(string=LEGACYEXAMPLE)

        w = self.doc.index['WR-P-E-J-0000000001.p.1.s.8.w.11'] #stippelijn
        w.correct(suggestion='stippellijn', set='corrections',cls='spelling',annotator='testscript', annotatortype=folia.AnnotatorType.AUTO)
        c = w.annotation(folia.Correction)

        self.assertTrue( isinstance(w.annotation(folia.Correction), folia.Correction) )
        self.assertEqual( w.annotation(folia.Correction).suggestions(0).text() , 'stippellijn' )
        self.assertEqual( w.text(), 'stippelijn')

        w.correct(new='stippellijn',set='corrections',cls='spelling',annotator='John Doe', annotatortype=folia.AnnotatorType.MANUAL,reuse=c.id)

        self.assertEqual( w.text(), 'stippellijn')
        self.assertEqual( len(list(w.annotations(folia.Correction))), 1 )
        self.assertEqual( w.annotation(folia.Correction).suggestions(0).text() , 'stippellijn' )
        self.assertEqual( w.annotation(folia.Correction).new(0).text() , 'stippellijn' )
        self.assertEqual( w.annotation(folia.Correction).annotator , 'John Doe' )
        self.assertEqual( w.annotation(folia.Correction).annotatortype , folia.AnnotatorType.MANUAL)

        self.assertTrue( xmlcheck(w.xmlstring(), '<w xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.8.w.11"><pos set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" class="FOUTN(soort,ev,basis,zijd,stan)"/><lemma class="stippelijn"/><correction xml:id="WR-P-E-J-0000000001.p.1.s.8.w.11.correction.1" class="spelling" annotator="John Doe"><suggestion auth="no"><t>stippellijn</t></suggestion><new><t>stippellijn</t></new><original auth="no"><t>stippelijn</t></original></correction></w>'))

    def test006_deletionsuggestion(self):
        """Correction - Suggestion for deletion with parent merge suggestion"""
        self.text.append(
            folia.Sentence(self.doc,id=self.doc.id + '.s.1', contents=[
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.1', text="De"),
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.2', text="site"),
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.3', text="staat"),
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.4', text="on"),
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.5', text="line"),
                folia.Word(self.doc,id=self.doc.id + '.s.1.w.6', text=".")
            ]),
        )
        self.text.append(
            folia.Sentence(self.doc,id=self.doc.id + '.s.2', contents=[
                folia.Word(self.doc,id=self.doc.id + '.s.2.w.1', text="sinds"),
                folia.Word(self.doc,id=self.doc.id + '.s.2.w.2', text="vorige"),
                folia.Word(self.doc,id=self.doc.id + '.s.2.w.3', text="week"),
                folia.Word(self.doc,id=self.doc.id + '.s.2.w.4', text="zondag"),
                folia.Word(self.doc,id=self.doc.id + '.s.2.w.6', text=".")
            ])
        )

        s = self.doc.index[self.doc.id + '.s.1']
        s2 = self.doc.index[self.doc.id + '.s.2']
        w = self.doc.index[self.doc.id + '.s.1.w.6']
        s.remove(w)
        s.append( folia.Correction(self.doc, folia.Current(self.doc, w), folia.Suggestion(self.doc, merge=s2.id)) )

        self.assertTrue( xmlcheck(s.xmlstring(),  '<s xmlns="http://ilk.uvt.nl/folia" xml:id="example.s.1"><w xml:id="example.s.1.w.1"><t>De</t></w><w xml:id="example.s.1.w.2"><t>site</t></w><w xml:id="example.s.1.w.3"><t>staat</t></w><w xml:id="example.s.1.w.4"><t>on</t></w><w xml:id="example.s.1.w.5"><t>line</t></w><correction><current><w xml:id="example.s.1.w.6"><t>.</t></w></current><suggestion merge="example.s.2" auth="no"/></correction></s>'))



class Test06Query(unittest.TestCase):
    def setUp(self):
        self.doc = folia.Document(string=LEGACYEXAMPLE, textvalidation=True)

    def test001_findwords_simple(self):
        """Querying - Find words (simple)"""
        matches = list(self.doc.findwords( folia.Pattern('van','het','alfabet') ))
        self.assertEqual( len(matches), 1 )
        self.assertEqual( len(matches[0]), 3 )
        self.assertEqual( matches[0][0].text(), 'van' )
        self.assertEqual( matches[0][1].text(), 'het' )
        self.assertEqual( matches[0][2].text(), 'alfabet' )


    def test002_findwords_wildcard(self):
        """Querying - Find words (with wildcard)"""
        matches = list(self.doc.findwords( folia.Pattern('van','het',True) ))
        self.assertEqual( len(matches), 1 )
        self.assertEqual( len(matches[0]), 3 )

        self.assertEqual( matches[0][0].text(), 'van' )
        self.assertEqual( matches[0][1].text(), 'het' )
        self.assertEqual( matches[0][2].text(), 'alfabet' )

    def test003_findwords_annotation(self):
        """Querying - Find words by annotation"""
        matches = list(self.doc.findwords( folia.Pattern('de','historisch','wetenschap','worden', matchannotation=folia.LemmaAnnotation) ))
        self.assertEqual( len(matches), 1 )
        self.assertEqual( len(matches[0]), 4 )
        self.assertEqual( matches[0][0].text(), 'de' )
        self.assertEqual( matches[0][1].text(), 'historische' )
        self.assertEqual( matches[0][2].text(), 'wetenschap' )
        self.assertEqual( matches[0][3].text(), 'wordt' )



    def test004_findwords_multi(self):
        """Querying - Find words using a conjunction of multiple patterns """
        matches = list(self.doc.findwords( folia.Pattern('de','historische',True, 'wordt'), folia.Pattern('de','historisch','wetenschap','worden', matchannotation=folia.LemmaAnnotation) ))
        self.assertEqual( len(matches), 1 )
        self.assertEqual( len(matches[0]), 4 )
        self.assertEqual( matches[0][0].text(), 'de' )
        self.assertEqual( matches[0][1].text(), 'historische' )
        self.assertEqual( matches[0][2].text(), 'wetenschap' )
        self.assertEqual( matches[0][3].text(), 'wordt' )

    def test005_findwords_none(self):
        """Querying - Find words that don't exist"""
        matches = list(self.doc.findwords( folia.Pattern('bli','bla','blu')))
        self.assertEqual( len(matches), 0)

    def test006_findwords_overlap(self):
        """Querying - Find words with overlap"""
        doc = folia.Document(id='test')
        text = folia.Text(doc, id='test.text')

        text.append(
            folia.Sentence(doc,id=doc.id + '.s.1', contents=[
                folia.Word(doc,id=doc.id + '.s.1.w.1', text="a"),
                folia.Word(doc,id=doc.id + '.s.1.w.2', text="a"),
                folia.Word(doc,id=doc.id + '.s.1.w.3', text="a"),
                folia.Word(doc,id=doc.id + '.s.1.w.4', text="A"),
                folia.Word(doc,id=doc.id + '.s.1.w.5', text="b"),
                folia.Word(doc,id=doc.id + '.s.1.w.6', text="a"),
                folia.Word(doc,id=doc.id + '.s.1.w.7', text="a"),
            ])
        )
        doc.append(text)

        matches = list(doc.findwords( folia.Pattern('a','a')))
        self.assertEqual( len(matches), 4)
        matches = list(doc.findwords( folia.Pattern('a','a',casesensitive=True)))
        self.assertEqual( len(matches), 3)

    def test007_findwords_context(self):
        """Querying - Find words with context"""
        matches = list(self.doc.findwords( folia.Pattern('van','het','alfabet'), leftcontext=3, rightcontext=3 ))
        self.assertEqual( len(matches), 1 )
        self.assertEqual( len(matches[0]), 9 )
        self.assertEqual( matches[0][0].text(), 'de' )
        self.assertEqual( matches[0][1].text(), 'laatste' )
        self.assertEqual( matches[0][2].text(), 'letters' )
        self.assertEqual( matches[0][3].text(), 'van' )
        self.assertEqual( matches[0][4].text(), 'het' )
        self.assertEqual( matches[0][5].text(), 'alfabet' )
        self.assertEqual( matches[0][6].text(), 'en' )
        self.assertEqual( matches[0][7].text(), 'worden' )
        self.assertEqual( matches[0][8].text(), 'tussen' )

    def test008_findwords_disjunction(self):
        """Querying - Find words with disjunctions"""
        matches = list(self.doc.findwords( folia.Pattern('de',('historische','hedendaagse'),'wetenschap','wordt') ))
        self.assertEqual( len(matches), 1 )
        self.assertEqual( len(matches[0]), 4 )
        self.assertEqual( matches[0][0].text(), 'de' )
        self.assertEqual( matches[0][1].text(), 'historische' )
        self.assertEqual( matches[0][2].text(), 'wetenschap' )
        self.assertEqual( matches[0][3].text(), 'wordt' )

    def test009_findwords_regexp(self):
        """Querying - Find words with regular expressions"""
        matches = list(self.doc.findwords( folia.Pattern('de',folia.RegExp('hist.*'),folia.RegExp('.*schap'),folia.RegExp('w[oae]rdt')) ))
        self.assertEqual( len(matches), 1 )
        self.assertEqual( len(matches[0]), 4 )
        self.assertEqual( matches[0][0].text(), 'de' )
        self.assertEqual( matches[0][1].text(), 'historische' )
        self.assertEqual( matches[0][2].text(), 'wetenschap' )
        self.assertEqual( matches[0][3].text(), 'wordt' )


    def test010a_findwords_variablewildcard(self):
        """Querying - Find words with variable wildcard"""
        matches = list(self.doc.findwords( folia.Pattern('de','laatste','*','alfabet') ))
        self.assertEqual( len(matches), 1 )
        self.assertEqual( len(matches[0]), 6 )
        self.assertEqual( matches[0][0].text(), 'de' )
        self.assertEqual( matches[0][1].text(), 'laatste' )
        self.assertEqual( matches[0][2].text(), 'letters' )
        self.assertEqual( matches[0][3].text(), 'van' )
        self.assertEqual( matches[0][4].text(), 'het' )
        self.assertEqual( matches[0][5].text(), 'alfabet' )

    def test010b_findwords_varwildoverlap(self):
        """Querying - Find words with variable wildcard and overlap"""
        doc = folia.Document(id='test')
        text = folia.Text(doc, id='test.text')

        text.append(
            folia.Sentence(doc,id=doc.id + '.s.1', contents=[
                folia.Word(doc,id=doc.id + '.s.1.w.1', text="a"),
                folia.Word(doc,id=doc.id + '.s.1.w.2', text="b"),
                folia.Word(doc,id=doc.id + '.s.1.w.3', text="c"),
                folia.Word(doc,id=doc.id + '.s.1.w.4', text="d"),
                folia.Word(doc,id=doc.id + '.s.1.w.5', text="a"),
                folia.Word(doc,id=doc.id + '.s.1.w.6', text="b"),
                folia.Word(doc,id=doc.id + '.s.1.w.7', text="c"),
            ])
        )
        doc.append(text)

        matches = list(doc.findwords( folia.Pattern('a','*', 'c')))
        self.assertEqual( len(matches), 3)


    def test011_findwords_annotation_na(self):
        """Querying - Find words by non existing annotation"""
        matches = list(self.doc.findwords( folia.Pattern('bli','bla','blu', matchannotation=folia.SenseAnnotation) ))
        self.assertEqual( len(matches), 0 )



class Test09Reader(unittest.TestCase):
    def setUp(self):
        f = open(os.path.join(TMPDIR,'foliatest.xml'),'w',encoding='utf-8')
        f.write(re.sub(r' version="[^"]*" generator="[^"]*"', ' version="1.5.0" generator="foliapy-v' + folia.LIBVERSION + '"', LEGACYEXAMPLE, re.MULTILINE))
        f.close()
        self.reader = folia.Reader(os.path.join(TMPDIR,"foliatest.xml"), folia.Word)

    def test000_worditer(self):
        """Stream reader - Iterating over words"""
        count = 0
        for _ in self.reader:
            count += 1
        self.assertEqual(count, 192)

    def test001_findwords_simple(self):
        """Querying using stream reader - Find words (simple)"""
        matches = list(self.reader.findwords( folia.Pattern('van','het','alfabet') ))
        self.assertEqual( len(matches), 1 )
        self.assertEqual( len(matches[0]), 3 )
        self.assertEqual( matches[0][0].text(), 'van' )
        self.assertEqual( matches[0][1].text(), 'het' )
        self.assertEqual( matches[0][2].text(), 'alfabet' )


    def test002_findwords_wildcard(self):
        """Querying using stream reader - Find words (with wildcard)"""
        matches = list(self.reader.findwords( folia.Pattern('van','het',True) ))
        self.assertEqual( len(matches), 1 )
        self.assertEqual( len(matches[0]), 3 )

        self.assertEqual( matches[0][0].text(), 'van' )
        self.assertEqual( matches[0][1].text(), 'het' )
        self.assertEqual( matches[0][2].text(), 'alfabet' )

    def test003_findwords_annotation(self):
        """Querying using stream reader - Find words by annotation"""
        matches = list(self.reader.findwords( folia.Pattern('de','historisch','wetenschap','worden', matchannotation=folia.LemmaAnnotation) ))
        self.assertEqual( len(matches), 1 )
        self.assertEqual( len(matches[0]), 4 )
        self.assertEqual( matches[0][0].text(), 'de' )
        self.assertEqual( matches[0][1].text(), 'historische' )
        self.assertEqual( matches[0][2].text(), 'wetenschap' )
        self.assertEqual( matches[0][3].text(), 'wordt' )



    def test004_findwords_multi(self):
        """Querying using stream reader - Find words using a conjunction of multiple patterns """
        matches = list(self.reader.findwords( folia.Pattern('de','historische',True, 'wordt'), folia.Pattern('de','historisch','wetenschap','worden', matchannotation=folia.LemmaAnnotation) ))
        self.assertEqual( len(matches), 1 )
        self.assertEqual( len(matches[0]), 4 )
        self.assertEqual( matches[0][0].text(), 'de' )
        self.assertEqual( matches[0][1].text(), 'historische' )
        self.assertEqual( matches[0][2].text(), 'wetenschap' )
        self.assertEqual( matches[0][3].text(), 'wordt' )

    def test005_findwords_none(self):
        """Querying using stream reader - Find words that don't exist"""
        matches = list(self.reader.findwords( folia.Pattern('bli','bla','blu')))
        self.assertEqual( len(matches), 0)


    def test011_findwords_annotation_na(self):
        """Querying using stream reader - Find words by non existing annotation"""
        matches = list(self.reader.findwords( folia.Pattern('bli','bla','blu', matchannotation=folia.SenseAnnotation) ))
        self.assertEqual( len(matches), 0 )

class Test07XpathQuery(unittest.TestCase):
    def setUp(self):
        f = open(os.path.join(TMPDIR,'foliatest.xml'),'w',encoding='utf-8')
        f.write(re.sub(r' version="[^"]*" generator="[^"]*"', ' version="1.5.0" generator="foliapy-v' + folia.LIBVERSION + '"', LEGACYEXAMPLE, re.MULTILINE))
        f.close()

    def test050_findwords_xpath(self):
        """Xpath Querying - Collect all words (including non-authoritative)"""
        count = 0
        for word in folia.Query(os.path.join(TMPDIR,'foliatest.xml'),'//f:w'):
            count += 1
            self.assertTrue( isinstance(word, folia.Word) )
        self.assertEqual(count, 192)

    #def test051_findwords_xpath(self):
    #    """Xpath Querying - Collect all words (authoritative only)"""
    #    count = 0
    #    for word in folia.Query(os.path.join(TMPDIR,'foliatest.xml'),'//f:w[not(ancestor-or-self::*/@auth)]'):
    #        count += 1
    #        self.assertTrue( isinstance(word, folia.Word) )
    #    self.assertEqual(count, 190)


class Test08Validation(unittest.TestCase):
    def test000_relaxng(self):
        """Validation - RelaxNG schema generation"""
        folia.relaxng()

    def test001_shallowvalidation(self):
        """Validation - Shallow validation against automatically generated RelaxNG schema"""
        folia.validate(os.path.join(TMPDIR,'foliasavetest.xml'))

    def test002_loadsetdefinitions(self):
        """Validation - Loading of set definitions"""
        doc = folia.Document(file=os.path.join(TMPDIR,'foliatest.xml'), loadsetdefinitions=True)
        assert isinstance( doc.setdefinitions["http://raw.github.com/proycon/folia/master/setdefinitions/namedentities.foliaset.xml"], folia.SetDefinition)

class Test09Validation(unittest.TestCase):
    def test001_deepvalidation(self):
        """Validation - Deep Validation"""
        folia.Document(file=os.path.join(FOLIAPATH,'examples/frog-deep.1.3.2.folia.xml'), deepvalidation=True, textvalidation=True, allowadhocsets=True)

    def test002_textvalidation(self):
        """Validation - Text Validation"""
        folia.Document(file=os.path.join(FOLIAPATH,'examples/textvalidation.1.5.0.folia.xml'), textvalidation=True)

    def test003_invalid_text_misspelled(self):
        """Validation - Invalid Text (Misspelled word)"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
      <token-annotation annotator="ucto" annotatortype="auto" datetime="2017-09-25T10:29:52" set="tokconfig-nld"/>
    </annotations>
  </metadata>
  <text xml:id="example.text">
    <p xml:id="example.p.1">
      <t>Is het creëren van een volwaardig literair oeuvre voorbehouden aan schrijvers als Couperus, Haasse, of Grunberg?</t>
      <s xml:id="example.p.1.s.1">
        <t>Is het creëren van een volwaardig literrair oeuvre voorbehouden aan schrijvers
	als Couperus, 	Haasse, of
	Grunberg?</t>
      </s>
    </p>
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        self.assertRaises( folia.InconsistentText, folia.Document, string=xml, textvalidation=True) #exception


    def test004_invalid_text_missing(self):
        """Validation - Invalid Text (Missing Word)"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
      <token-annotation annotator="ucto" annotatortype="auto" datetime="2017-09-25T10:29:52" set="tokconfig-nld"/>
    </annotations>
  </metadata>
  <text xml:id="example.text">
    <p xml:id="example.p.1">
      <t>Is het creëren van een volwaardig literair oeuvre voorbehouden aan schrijvers als Couperus, Haasse, of Grunberg?</t>
      <s xml:id="example.p.1.s.1">
        <t>Is het creëren van een volwaardig oeuvre voorbehouden aan schrijvers
	als Couperus, 	Haasse, of
	Grunberg?</t>
      </s>
    </p>
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        self.assertRaises( folia.InconsistentText, folia.Document, string=xml, textvalidation=True) #exception


    def test005_textvalidation_intermittent_redundancy(self):
        """Validation - Text Validation (Intermittent Redundancy)"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
      <token-annotation annotator="ucto" annotatortype="auto" datetime="2017-09-25T10:29:52" set="tokconfig-nld"/>
    </annotations>
  </metadata>
  <text xml:id="example.text">
    <t>Is het creëren van een volwaardig literair oeuvre voorbehouden aan schrijvers als Couperus, Haasse, of Grunberg? Of kan ik het ook?</t>
    <p xml:id="example.p.1">
      <!-- Note: no text here on paragraph level -->
      <s xml:id="example.p.1.s.1">
        <t>Is het creëren van een volwaardig oeuvre voorbehouden aan schrijvers
	als Couperus, 	Haasse, of
	Grunberg?</t>
      </s>
      <s xml:id="example.p.1.s.2">
        <t> Of kan ik
het    ook   ?
	    </t>
      </s>
    </p>
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        folia.Document(file=os.path.join(FOLIAPATH,'examples/textvalidation.1.5.0.folia.xml'), textvalidation=True)

    def test006_multiple_textclasses(self):
        """Validation - Invalid Text (Multiple classes)"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
      <token-annotation annotator="ucto" annotatortype="auto" datetime="2017-09-25T10:29:52" set="tokconfig-nld"/>
    </annotations>
  </metadata>
  <text xml:id="example.text">
    <p xml:id="example.p.1">
      <t>Is het creëren van een volwaardig literair oeuvre voorbehouden aan schrijvers als Couperus, Haasse, of Grunberg?</t>
      <t class="missingword">Is het creëren van een volwaardig oeuvre voorbehouden aan schrijvers als Couperus, Haasse, of Grunberg?</t>
      <s xml:id="example.p.1.s.1">
        <t>Is het creëren van een volwaardig literair oeuvre voorbehouden aan schrijvers
	als Couperus, 	Haasse, of
	Grunberg?</t>
        <t class="missingword">Is het creëren van een volwaardig oeuvre voorbehouden aan schrijvers
	als Couperus, 	Haasse, of
	Grunberg?</t>
      </s>
    </p>
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        folia.Document(string=xml, textvalidation=True)

    def test007_textcheck_no_morphemes(self):
        """Validation - No text checking on (nested) morphemes"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
      <token-annotation annotator="ucto" annotatortype="auto" datetime="2017-09-25T10:29:52" set="tokconfig-nld"/>
      <pos-annotation set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn" annotator="frog" annotatortype="auto" />
      <pos-annotation annotator="frog-mbma-1.0" annotatortype="auto" datetime="2017-04-20T16:48:45" set="http://ilk.uvt.nl/folia/sets/frog-mbpos-clex"/>
      <lemma-annotation set="lemmas-nl" annotator="tadpole" annotatortype="auto" />
      <morphological-annotation annotator="proycon" annotatortype="manual" />
    </annotations>
  </metadata>
  <text xml:id="example.text">
      <w xml:id="WR-P-E-J-0000000001.p.1.s.2.w.16">
        <t>genealogie</t>
        <pos class="N(soort,ev,basis,zijd,stan)" set="https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn"/>
        <lemma class="genealogie"/>
        <morphology>
          <morpheme class="complex">
            <t>genealogie</t>
            <feat class="[[genealogisch]adjective[ie]]noun/singular" subset="structure"/>
            <pos class="N" set="http://ilk.uvt.nl/folia/sets/frog-mbpos-clex"/>
            <morpheme class="complex">
              <feat class="N_A*" subset="applied_rule"/>
              <feat class="[[genealogisch]adjective[ie]]noun" subset="structure"/>
              <pos class="N" set="http://ilk.uvt.nl/folia/sets/frog-mbpos-clex"/>
              <morpheme class="stem">
                <t>genealogisch</t>
                <pos class="A" set="http://ilk.uvt.nl/folia/sets/frog-mbpos-clex"/>
              </morpheme>
              <morpheme class="affix">
                <t>ie</t>
                <feat class="[ie]" subset="structure"/>
              </morpheme>
             </morpheme>
             <morpheme class="inflection">
              <feat class="singular" subset="inflection"/>
             </morpheme>
          </morpheme>
        </morphology>
      </w>
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        folia.Document(string=xml, textvalidation=True)


    def test008_offset(self):
        """Validation - Offset validation"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
      <token-annotation annotator="ucto" annotatortype="auto" datetime="2017-09-25T10:29:52" set="tokconfig-nld"/>
    </annotations>
  </metadata>
  <text xml:id="example.text">
    <p xml:id="example.p.1">
      <s xml:id="example.p.1.s.1">
        <t>Is het creëren van een volwaardig literair oeuvre voorbehouden aan schrijvers
	als Couperus, 	Haasse, of
	Grunberg?</t>
        <w xml:id="example.p.1.s.1.w.1" class="WORD">
          <t offset="0">Is</t>
        </w>
        <w xml:id="example.p.1.s.1.w.2" class="WORD">
          <t offset="3">het</t>
        </w>
        <w xml:id="example.p.1.s.1.w.3" class="WORD">
          <t offset="7">creëren</t>
        </w>
        <w xml:id="example.p.1.s.1.w.4" class="WORD">
          <t offset="15">van</t>
        </w>
        <w xml:id="example.p.1.s.1.w.5" class="WORD">
          <t offset="19">een</t>
        </w>
        <w xml:id="example.p.1.s.1.w.6" class="WORD">
          <t offset="23">volwaardig</t>
        </w>
        <w xml:id="example.p.1.s.1.w.7" class="WORD">
          <t offset="34">literair</t>
        </w>
        <w xml:id="example.p.1.s.1.w.8" class="WORD">
          <t offset="43">oeuvre</t>
        </w>
        <w xml:id="example.p.1.s.1.w.9" class="WORD">
          <t offset="50">voorbehouden</t>
        </w>
        <w xml:id="example.p.1.s.1.w.10" class="WORD">
          <t offset="63">aan</t>
        </w>
        <w xml:id="example.p.1.s.1.w.11" class="WORD">
          <t offset="67">schrijvers</t>
        </w>
        <w xml:id="example.p.1.s.1.w.12" class="WORD">
          <t offset="79">als</t>
        </w>
        <w xml:id="example.p.1.s.1.w.13" class="WORD" space="no">
          <t offset="83">Couperus</t>
        </w>
        <w xml:id="example.p.1.s.1.w.14" class="PUNCTUATION">
          <t offset="91">,</t>
        </w>
        <w xml:id="example.p.1.s.1.w.15" class="WORD" space="no">
          <t offset="94">Haasse</t>
        </w>
        <w xml:id="example.p.1.s.1.w.16" class="PUNCTUATION">
          <t offset="100">,</t>
        </w>
        <w xml:id="example.p.1.s.1.w.17" class="WORD">
          <t offset="102">of</t>
        </w>
        <w xml:id="example.p.1.s.1.w.18" class="WORD" space="no">
          <t offset="106">Grunberg</t>
        </w>
        <w xml:id="example.p.1.s.1.w.19" class="PUNCTUATION">
          <t offset="114">?</t>
        </w>
      </s>
    </p>
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml, textvalidation=True)
        self.assertEqual( doc['example.p.1.s.1.w.19'].textcontent().getreference(), doc['example.p.1.s.1'] ) #testing resolving implicit reference



    def test009_invalid_offset(self):
        """Validation - Offset validation (invalid)"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
      <token-annotation annotator="ucto" annotatortype="auto" datetime="2017-09-25T10:29:52" set="tokconfig-nld"/>
    </annotations>
  </metadata>
  <text xml:id="example.text">
    <p xml:id="example.p.1">
      <s xml:id="example.p.1.s.1">
        <t>Is het creëren van een volwaardig literair oeuvre voorbehouden aan schrijvers
	als Couperus, 	Haasse, of
	Grunberg?</t>
        <w xml:id="example.p.1.s.1.w.1" class="WORD">
          <t offset="0">Is</t>
        </w>
        <w xml:id="example.p.1.s.1.w.2" class="WORD">
          <t offset="3">het</t>
        </w>
        <w xml:id="example.p.1.s.1.w.3" class="WORD">
          <t offset="7">creëren</t>
        </w>
        <w xml:id="example.p.1.s.1.w.4" class="WORD">
          <t offset="10">van</t> <!-- this one is invalid -->
        </w>
        <w xml:id="example.p.1.s.1.w.5" class="WORD">
          <t offset="19">een</t>
        </w>
        <w xml:id="example.p.1.s.1.w.6" class="WORD">
          <t offset="23">volwaardig</t>
        </w>
        <w xml:id="example.p.1.s.1.w.7" class="WORD">
          <t offset="34">literair</t>
        </w>
        <w xml:id="example.p.1.s.1.w.8" class="WORD">
          <t offset="43">oeuvre</t>
        </w>
        <w xml:id="example.p.1.s.1.w.9" class="WORD">
          <t offset="50">voorbehouden</t>
        </w>
        <w xml:id="example.p.1.s.1.w.10" class="WORD">
          <t offset="63">aan</t>
        </w>
        <w xml:id="example.p.1.s.1.w.11" class="WORD">
          <t offset="67">schrijvers</t>
        </w>
        <w xml:id="example.p.1.s.1.w.12" class="WORD">
          <t offset="79">als</t>
        </w>
        <w xml:id="example.p.1.s.1.w.13" class="WORD" space="no">
          <t offset="83">Couperus</t>
        </w>
        <w xml:id="example.p.1.s.1.w.14" class="PUNCTUATION">
          <t offset="91">,</t>
        </w>
        <w xml:id="example.p.1.s.1.w.15" class="WORD" space="no">
          <t offset="94">Haasse</t>
        </w>
        <w xml:id="example.p.1.s.1.w.16" class="PUNCTUATION">
          <t offset="100">,</t>
        </w>
        <w xml:id="example.p.1.s.1.w.17" class="WORD">
          <t offset="102">of</t>
        </w>
        <w xml:id="example.p.1.s.1.w.18" class="WORD" space="no">
          <t offset="106">Grunberg</t>
        </w>
        <w xml:id="example.p.1.s.1.w.19" class="PUNCTUATION">
          <t offset="114">?</t>
        </w>
      </s>
    </p>
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        self.assertRaises( folia.UnresolvableTextContent, folia.Document, string=xml, textvalidation=True) #exception

    def test010_offset_reference(self):
        """Validation - Offset validation with explicit references"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
      <token-annotation annotator="ucto" annotatortype="auto" datetime="2017-09-25T10:29:52" set="tokconfig-nld"/>
    </annotations>
  </metadata>
  <text xml:id="example.text">
    <p xml:id="example.p.1">
      <t>Is het creëren van een volwaardig literair oeuvre voorbehouden aan schrijvers
	als Couperus, 	Haasse, of
	Grunberg?</t>
      <s xml:id="example.p.1.s.1">
        <w xml:id="example.p.1.s.1.w.1" class="WORD">
          <t offset="0" ref="example.p.1">Is</t>
        </w>
        <w xml:id="example.p.1.s.1.w.2" class="WORD">
          <t offset="3" ref="example.p.1">het</t>
        </w>
        <w xml:id="example.p.1.s.1.w.3" class="WORD">
          <t offset="7" ref="example.p.1">creëren</t>
        </w>
        <w xml:id="example.p.1.s.1.w.4" class="WORD">
          <t offset="15" ref="example.p.1">van</t>
        </w>
        <w xml:id="example.p.1.s.1.w.5" class="WORD">
          <t offset="19" ref="example.p.1">een</t>
        </w>
        <w xml:id="example.p.1.s.1.w.6" class="WORD">
          <t offset="23" ref="example.p.1">volwaardig</t>
        </w>
        <w xml:id="example.p.1.s.1.w.7" class="WORD">
          <t offset="34" ref="example.p.1">literair</t>
        </w>
        <w xml:id="example.p.1.s.1.w.8" class="WORD">
          <t offset="43" ref="example.p.1">oeuvre</t>
        </w>
        <w xml:id="example.p.1.s.1.w.9" class="WORD">
          <t offset="50" ref="example.p.1">voorbehouden</t>
        </w>
        <w xml:id="example.p.1.s.1.w.10" class="WORD">
          <t offset="63" ref="example.p.1">aan</t>
        </w>
        <w xml:id="example.p.1.s.1.w.11" class="WORD">
          <t offset="67" ref="example.p.1">schrijvers</t>
        </w>
        <w xml:id="example.p.1.s.1.w.12" class="WORD">
          <t offset="79" ref="example.p.1">als</t>
        </w>
        <w xml:id="example.p.1.s.1.w.13" class="WORD" space="no">
          <t offset="83" ref="example.p.1">Couperus</t>
        </w>
        <w xml:id="example.p.1.s.1.w.14" class="PUNCTUATION">
          <t offset="91" ref="example.p.1">,</t>
        </w>
        <w xml:id="example.p.1.s.1.w.15" class="WORD" space="no">
          <t offset="94" ref="example.p.1">Haasse</t>
        </w>
        <w xml:id="example.p.1.s.1.w.16" class="PUNCTUATION">
          <t offset="100" ref="example.p.1">,</t>
        </w>
        <w xml:id="example.p.1.s.1.w.17" class="WORD">
          <t offset="102" ref="example.p.1">of</t>
        </w>
        <w xml:id="example.p.1.s.1.w.18" class="WORD" space="no">
          <t offset="106" ref="example.p.1">Grunberg</t>
        </w>
        <w xml:id="example.p.1.s.1.w.19" class="PUNCTUATION">
          <t offset="114" ref="example.p.1">?</t>
        </w>
      </s>
    </p>
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml, textvalidation=True)
        self.assertEqual( doc['example.p.1.s.1.w.19'].textcontent().getreference(), doc['example.p.1'] ) #testing resolving explicit reference

    def test011a_offset_textmarkup(self):
        """Validation - Offset validation with text markup (non-text-modifiers)"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
      <token-annotation annotator="ucto" annotatortype="auto" datetime="2017-09-25T10:29:52" set="tokconfig-nld"/>
      <style-annotation />
    </annotations>
  </metadata>
  <text xml:id="example.text">
    <p xml:id="example.p.1">
      <s xml:id="example.p.1.s.1">
        <t>Is het creëren van een <t-style class="emphasis">volwaardig</t-style> literair oeuvre voorbehouden aan schrijvers
\tals <t-str xlink:href="https://nl.wikipedia.org/wiki/Louis_Couperus" xlink:type="simple">Couperus</t-str>, 	Haasse, of
\tGrunberg?</t>
        <w xml:id="example.p.1.s.1.w.1" class="WORD">
          <t offset="0">Is</t>
        </w>
        <w xml:id="example.p.1.s.1.w.2" class="WORD">
          <t offset="3">het</t>
        </w>
        <w xml:id="example.p.1.s.1.w.3" class="WORD">
          <t offset="7">creëren</t>
        </w>
        <w xml:id="example.p.1.s.1.w.4" class="WORD">
          <t offset="15">van</t>
        </w>
        <w xml:id="example.p.1.s.1.w.5" class="WORD">
          <t offset="19">een</t>
        </w>
        <w xml:id="example.p.1.s.1.w.6" class="WORD">
          <t offset="23">volwaardig</t>
        </w>
        <w xml:id="example.p.1.s.1.w.7" class="WORD">
          <t offset="34">literair</t>
        </w>
        <w xml:id="example.p.1.s.1.w.8" class="WORD">
          <t offset="43">oeuvre</t>
        </w>
        <w xml:id="example.p.1.s.1.w.9" class="WORD">
          <t offset="50">voorbehouden</t>
        </w>
        <w xml:id="example.p.1.s.1.w.10" class="WORD">
          <t offset="63">aan</t>
        </w>
        <w xml:id="example.p.1.s.1.w.11" class="WORD">
          <t offset="67">schrijvers</t>
        </w>
        <w xml:id="example.p.1.s.1.w.12" class="WORD">
          <t offset="79">als</t>
        </w>
        <w xml:id="example.p.1.s.1.w.13" class="WORD" space="no">
          <t offset="83">Couperus</t>
        </w>
        <w xml:id="example.p.1.s.1.w.14" class="PUNCTUATION">
          <t offset="91">,</t>
        </w>
        <w xml:id="example.p.1.s.1.w.15" class="WORD" space="no">
          <t offset="94">Haasse</t>
        </w>
        <w xml:id="example.p.1.s.1.w.16" class="PUNCTUATION">
          <t offset="100">,</t>
        </w>
        <w xml:id="example.p.1.s.1.w.17" class="WORD">
          <t offset="102">of</t>
        </w>
        <w xml:id="example.p.1.s.1.w.18" class="WORD" space="no">
          <t offset="106">Grunberg</t>
        </w>
        <w xml:id="example.p.1.s.1.w.19" class="PUNCTUATION">
          <t offset="114">?</t>
        </w>
      </s>
    </p>
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml, textvalidation=True)
        self.assertEqual( doc['example.p.1.s.1.w.19'].textcontent().getreference(), doc['example.p.1.s.1'] ) #testing resolving implicit reference

    def test011b_offset_textmarkup(self):
        """Validation - Offset validation with text markup (with text modifiers like br)"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
      <token-annotation annotator="ucto" annotatortype="auto" datetime="2017-09-25T10:29:52" set="tokconfig-nld"/>
      <style-annotation />
    </annotations>
  </metadata>
  <text xml:id="example.text">
    <p xml:id="example.p.1">
      <s xml:id="example.p.1.s.1">
        <t>Is het creëren van een <t-style class="emphasis">volwaardig</t-style> literair oeuvre voorbehouden aan schrijvers<br/>\tals <t-str xlink:href="https://nl.wikipedia.org/wiki/Louis_Couperus" xlink:type="simple">Couperus</t-str>, 	Haasse, of
\tGrunberg?</t>
        <w xml:id="example.p.1.s.1.w.1" class="WORD">
          <t offset="0">Is</t>
        </w>
        <w xml:id="example.p.1.s.1.w.2" class="WORD">
          <t offset="3">het</t>
        </w>
        <w xml:id="example.p.1.s.1.w.3" class="WORD">
          <t offset="7">creëren</t>
        </w>
        <w xml:id="example.p.1.s.1.w.4" class="WORD">
          <t offset="15">van</t>
        </w>
        <w xml:id="example.p.1.s.1.w.5" class="WORD">
          <t offset="19">een</t>
        </w>
        <w xml:id="example.p.1.s.1.w.6" class="WORD">
          <t offset="23">volwaardig</t>
        </w>
        <w xml:id="example.p.1.s.1.w.7" class="WORD">
          <t offset="34">literair</t>
        </w>
        <w xml:id="example.p.1.s.1.w.8" class="WORD">
          <t offset="43">oeuvre</t>
        </w>
        <w xml:id="example.p.1.s.1.w.9" class="WORD">
          <t offset="50">voorbehouden</t>
        </w>
        <w xml:id="example.p.1.s.1.w.10" class="WORD">
          <t offset="63">aan</t>
        </w>
        <w xml:id="example.p.1.s.1.w.11" class="WORD">
          <t offset="67">schrijvers</t>
        </w>
        <w xml:id="example.p.1.s.1.w.12" class="WORD">
          <t offset="79">als</t>
        </w>
        <w xml:id="example.p.1.s.1.w.13" class="WORD" space="no">
          <t offset="83">Couperus</t>
        </w>
        <w xml:id="example.p.1.s.1.w.14" class="PUNCTUATION">
          <t offset="91">,</t>
        </w>
        <w xml:id="example.p.1.s.1.w.15" class="WORD" space="no">
          <t offset="94">Haasse</t>
        </w>
        <w xml:id="example.p.1.s.1.w.16" class="PUNCTUATION">
          <t offset="100">,</t>
        </w>
        <w xml:id="example.p.1.s.1.w.17" class="WORD">
          <t offset="102">of</t>
        </w>
        <w xml:id="example.p.1.s.1.w.18" class="WORD" space="no">
          <t offset="106">Grunberg</t>
        </w>
        <w xml:id="example.p.1.s.1.w.19" class="PUNCTUATION">
          <t offset="114">?</t>
        </w>
      </s>
    </p>
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml, textvalidation=True)
        self.assertEqual( doc['example.p.1.s.1.w.19'].textcontent().getreference(), doc['example.p.1.s.1'] ) #testing resolving implicit reference

    def test012_string(self):
        """Validation - Text Validation on String"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
      <token-annotation annotator="ucto" annotatortype="auto" datetime="2017-09-25T10:29:52" set="tokconfig-nld"/>
      <style-annotation />
    </annotations>
  </metadata>
  <text xml:id="example.text">
    <p xml:id="example.p.1">
      <s xml:id="example.p.1.s.1">
        <t>Is het creëren van een <t-style class="emphasis">volwaardig</t-style> literair oeuvre voorbehouden aan schrijvers<br/>\tals <t-str xlink:href="https://nl.wikipedia.org/wiki/Louis_Couperus" xlink:type="simple">Couperus</t-str>, 	Haasse, of
\tGrunberg?</t>
        <str xml:id="example.string">
            <t offset="7">creëren</t>
        </str>
      </s>
    </p>
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml, textvalidation=True)
        self.assertEqual( doc['example.string'].textcontent().getreference(), doc['example.p.1.s.1'] ) #testing resolving implicit reference

    def test013a_correction(self):
        """Validation - Text Validation on Correction (single text layer)"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
      <token-annotation annotator="ucto" annotatortype="auto" datetime="2017-09-25T10:29:52" set="tokconfig-nld"/>
      <style-annotation />
    </annotations>
  </metadata>
  <text xml:id="example.text">
    <p xml:id="example.p.1">
      <s xml:id="example.p.1.s.1">
        <t>Is het creëren van een volwaardig literair oeuvre voorbehouden aan schrijvers?</t>
        <w xml:id="example.p.1.s.1.w.1" class="WORD">
          <t offset="0">Is</t>
        </w>
        <w xml:id="example.p.1.s.1.w.2" class="WORD">
          <t offset="3">het</t>
        </w>
        <w xml:id="example.p.1.s.1.w.3" class="WORD">
          <correction>
           <new>
              <t offset="7">creëren</t>
           </new>
           <original auth="no">
              <t offset="7">creeren</t>
           </original>
          </correction>
        </w>
        <w xml:id="example.p.1.s.1.w.4" class="WORD">
          <t offset="15">van</t>
        </w>
        <w xml:id="example.p.1.s.1.w.5" class="WORD">
          <t offset="19">een</t>
        </w>
        <w xml:id="example.p.1.s.1.w.6" class="WORD">
          <t offset="23">volwaardig</t>
        </w>
        <w xml:id="example.p.1.s.1.w.7" class="WORD">
          <t offset="34">literair</t>
        </w>
        <w xml:id="example.p.1.s.1.w.8" class="WORD">
          <t offset="43">oeuvre</t>
        </w>
        <w xml:id="example.p.1.s.1.w.9" class="WORD">
          <t offset="50">voorbehouden</t>
        </w>
        <w xml:id="example.p.1.s.1.w.10" class="WORD">
          <t offset="63">aan</t>
        </w>
        <w xml:id="example.p.1.s.1.w.11" class="WORD" space="no">
          <t offset="67">schrijvers</t>
        </w>
        <w xml:id="example.p.1.s.1.w.12" class="WORD">
          <t offset="77">?</t>
        </w>
      </s>
    </p>
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml, textvalidation=True)

    def test013b_correction(self):
        """Validation - Text Validation on Correction (Double text layers)"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
      <token-annotation annotator="ucto" annotatortype="auto" datetime="2017-09-25T10:29:52" set="tokconfig-nld"/>
      <style-annotation />
    </annotations>
  </metadata>
  <text xml:id="example.text">
    <p xml:id="example.p.1">
      <s xml:id="example.p.1.s.1">
        <t>Is het creëren van een volwaardig literair oeuvre voorbehouden aan schrijvers?</t>
        <t class="original">Is het creeren van een volwaardig litterair oeuvre voorbehouden aan schrijvers?</t>
        <w xml:id="example.p.1.s.1.w.1" class="WORD">
          <t offset="0">Is</t>
          <t class="original" offset="0">Is</t>
        </w>
        <w xml:id="example.p.1.s.1.w.2" class="WORD">
          <t offset="3">het</t>
          <t class="original" offset="3">het</t>
        </w>
        <w xml:id="example.p.1.s.1.w.3" class="WORD">
          <correction>
           <new>
              <t offset="7">creëren</t>
           </new>
           <original auth="no">
              <t class="original" offset="7">creeren</t>
           </original>
          </correction>
        </w>
        <w xml:id="example.p.1.s.1.w.4" class="WORD">
          <t offset="15">van</t>
          <t class="original" offset="15">van</t>
        </w>
        <w xml:id="example.p.1.s.1.w.5" class="WORD">
          <t offset="19">een</t>
          <t class="original" offset="19">een</t>
        </w>
        <w xml:id="example.p.1.s.1.w.6" class="WORD">
          <t offset="23">volwaardig</t>
          <t class="original" offset="23">volwaardig</t>
        </w>
        <w xml:id="example.p.1.s.1.w.7" class="WORD">
          <t offset="34">literair</t>
          <t class="original" offset="34">litterair</t>
        </w>
        <w xml:id="example.p.1.s.1.w.8" class="WORD">
          <t offset="43">oeuvre</t>
          <t class="original" offset="44">oeuvre</t>
        </w>
        <w xml:id="example.p.1.s.1.w.9" class="WORD">
          <t offset="50">voorbehouden</t>
          <t class="original" offset="51">voorbehouden</t>
        </w>
        <w xml:id="example.p.1.s.1.w.10" class="WORD">
          <t offset="63">aan</t>
          <t class="original" offset="64">aan</t>
        </w>
        <w xml:id="example.p.1.s.1.w.11" class="WORD" space="no">
          <t offset="67">schrijvers</t>
          <t class="original" offset="68">schrijvers</t>
        </w>
        <w xml:id="example.p.1.s.1.w.12" class="WORD">
          <t offset="77">?</t>
          <t class="original" offset="78">?</t>
        </w>
      </s>
    </p>
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml, textvalidation=True)

    def test013c_correction(self):
        """Validation - Text Validation on Correction (Double text layers, structural changes)"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
      <token-annotation annotator="ucto" annotatortype="auto" datetime="2017-09-25T10:29:52" set="tokconfig-nld"/>
      <style-annotation />
    </annotations>
  </metadata>
  <text xml:id="example.text">
    <p xml:id="example.p.1">
      <s xml:id="example.p.1.s.1">
        <t>Is het creëren van een volwaardig literair oeuvre voorbehouden aan schrijvers?</t>
        <t class="original">Is het creeren van een volwaardig litterair oeuvre voor behouden aan schrijvers?</t>
        <w xml:id="example.p.1.s.1.w.1" class="WORD">
          <t offset="0">Is</t>
          <t class="original" offset="0">Is</t>
        </w>
        <w xml:id="example.p.1.s.1.w.2" class="WORD">
          <t offset="3">het</t>
          <t class="original" offset="3">het</t>
        </w>
        <w xml:id="example.p.1.s.1.w.3" class="WORD">
          <correction>
           <new>
              <t offset="7">creëren</t>
           </new>
           <original auth="no">
              <t class="original" offset="7">creeren</t>
           </original>
          </correction>
        </w>
        <w xml:id="example.p.1.s.1.w.4" class="WORD">
          <t offset="15">van</t>
          <t class="original" offset="15">van</t>
        </w>
        <w xml:id="example.p.1.s.1.w.5" class="WORD">
          <t offset="19">een</t>
          <t class="original" offset="19">een</t>
        </w>
        <w xml:id="example.p.1.s.1.w.6" class="WORD">
          <t offset="23">volwaardig</t>
          <t class="original" offset="23">volwaardig</t>
        </w>
        <w xml:id="example.p.1.s.1.w.7" class="WORD">
          <t offset="34">literair</t>
          <t class="original" offset="34">litterair</t>
        </w>
        <w xml:id="example.p.1.s.1.w.8" class="WORD">
          <t offset="43">oeuvre</t>
          <t class="original" offset="44">oeuvre</t>
        </w>
        <correction>
         <new>
            <w xml:id="example.p.1.s.1.w.9" class="WORD">
              <t offset="50">voorbehouden</t>
            </w>
         </new>
         <original>
            <w xml:id="example.p.1.s.1.w.9a" class="WORD">
              <t class="original" offset="51">voor</t>
            </w>
            <w xml:id="example.p.1.s.1.w.9b" class="WORD">
              <t class="original" offset="56">behouden</t>
            </w>
         </original>
        </correction>
        <w xml:id="example.p.1.s.1.w.10" class="WORD">
          <t offset="63">aan</t>
          <t class="original" offset="65">aan</t>
        </w>
        <w xml:id="example.p.1.s.1.w.11" class="WORD" space="no">
          <t offset="67">schrijvers</t>
          <t class="original" offset="69">schrijvers</t>
        </w>
        <w xml:id="example.p.1.s.1.w.12" class="WORD">
          <t offset="77">?</t>
          <t class="original" offset="79">?</t>
        </w>
      </s>
    </p>
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml, textvalidation=True)

    def test013d_correction(self):
        """Validation - Text Validation on Correction (Double text layers, structural changes, custom class)"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
      <token-annotation annotator="ucto" annotatortype="auto" datetime="2017-09-25T10:29:52" set="tokconfig-nld"/>
      <style-annotation />
    </annotations>
  </metadata>
  <text xml:id="example.text">
    <p xml:id="example.p.1">
      <s xml:id="example.p.1.s.1">
        <t>Is het creëren van een volwaardig literair oeuvre voorbehouden aan schrijvers?</t>
        <t class="old">Is het creeren van een volwaardig litterair oeuvre voor behouden aan schrijvers?</t>
        <w xml:id="example.p.1.s.1.w.1" class="WORD">
          <t offset="0">Is</t>
          <t class="old" offset="0">Is</t>
        </w>
        <w xml:id="example.p.1.s.1.w.2" class="WORD">
          <t offset="3">het</t>
          <t class="old" offset="3">het</t>
        </w>
        <w xml:id="example.p.1.s.1.w.3" class="WORD">
          <correction>
           <new>
              <t offset="7">creëren</t>
           </new>
           <original auth="no">
              <t class="old" offset="7">creeren</t>
           </original>
          </correction>
        </w>
        <w xml:id="example.p.1.s.1.w.4" class="WORD">
          <t offset="15">van</t>
          <t class="old" offset="15">van</t>
        </w>
        <w xml:id="example.p.1.s.1.w.5" class="WORD">
          <t offset="19">een</t>
          <t class="old" offset="19">een</t>
        </w>
        <w xml:id="example.p.1.s.1.w.6" class="WORD">
          <t offset="23">volwaardig</t>
          <t class="old" offset="23">volwaardig</t>
        </w>
        <w xml:id="example.p.1.s.1.w.7" class="WORD">
          <t offset="34">literair</t>
          <t class="old" offset="34">litterair</t>
        </w>
        <w xml:id="example.p.1.s.1.w.8" class="WORD">
          <t offset="43">oeuvre</t>
          <t class="old" offset="44">oeuvre</t>
        </w>
        <correction>
         <new>
            <w xml:id="example.p.1.s.1.w.9" class="WORD">
              <t offset="50">voorbehouden</t>
            </w>
         </new>
         <original>
            <w xml:id="example.p.1.s.1.w.9a" class="WORD">
              <t class="old" offset="51">voor</t>
            </w>
            <w xml:id="example.p.1.s.1.w.9b" class="WORD">
              <t class="old" offset="56">behouden</t>
            </w>
         </original>
        </correction>
        <w xml:id="example.p.1.s.1.w.10" class="WORD">
          <t offset="63">aan</t>
          <t class="old" offset="65">aan</t>
        </w>
        <w xml:id="example.p.1.s.1.w.11" class="WORD" space="no">
          <t offset="67">schrijvers</t>
          <t class="old" offset="69">schrijvers</t>
        </w>
        <w xml:id="example.p.1.s.1.w.12" class="WORD">
          <t offset="77">?</t>
          <t class="old" offset="79">?</t>
        </w>
      </s>
    </p>
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml, textvalidation=True)

    def test013e_correction(self):
        """Validation - Text Validation on complex nested correction (Double text layers, structural changes, custom class)"""
        #NOTE: Current library implementation won't be able to validate nested layers and will just skip those!
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
      <token-annotation annotator="ucto" annotatortype="auto" datetime="2017-09-25T10:29:52" set="tokconfig-nld"/>
      <style-annotation />
    </annotations>
  </metadata>
  <text xml:id="example.text">
    <p xml:id="example.p.1">
      <s xml:id="example.p.1.s.1">
        <t>Is het creëren van een volwaardig literair oeuvre voorbehouden aan schrijvers?</t>
        <t class="old">Is het creeren van een volwaardig litterair oeuvre voor behouden aan schrijvers?</t>
        <t class="older">Is het CREEREN van een volwaardig litterair oeuvre voor behouden aan schrijvers?</t>
        <w xml:id="example.p.1.s.1.w.1" class="WORD">
          <t offset="0">Is</t>
          <t class="old" offset="0">Is</t>
          <t class="older" offset="0">Is</t>
        </w>
        <w xml:id="example.p.1.s.1.w.2" class="WORD">
          <t offset="3">het</t>
          <t class="old" offset="3">het</t>
          <t class="older" offset="3">het</t>
        </w>
        <w xml:id="example.p.1.s.1.w.3" class="WORD">
          <correction>
           <new>
              <t offset="7">creëren</t>
           </new>
           <original auth="no">
              <correction>
                  <new>
                      <t class="old" offset="7">creeren</t>
                  </new>
                  <original auth="no">
                      <t class="older" offset="7">CREEREN</t>
                  </original>
              </correction>
           </original>
          </correction>
        </w>
        <w xml:id="example.p.1.s.1.w.4" class="WORD">
          <t offset="15">van</t>
          <t class="old" offset="15">van</t>
          <t class="older" offset="15">van</t>
        </w>
        <w xml:id="example.p.1.s.1.w.5" class="WORD">
          <t offset="19">een</t>
          <t class="old" offset="19">een</t>
          <t class="older" offset="19">een</t>
        </w>
        <w xml:id="example.p.1.s.1.w.6" class="WORD">
          <t offset="23">volwaardig</t>
          <t class="old" offset="23">volwaardig</t>
          <t class="older" offset="23">volwaardig</t>
        </w>
        <w xml:id="example.p.1.s.1.w.7" class="WORD">
          <t offset="34">literair</t>
          <t class="old" offset="34">litterair</t>
          <t class="older" offset="34">litterair</t>
        </w>
        <w xml:id="example.p.1.s.1.w.8" class="WORD">
          <t offset="43">oeuvre</t>
          <t class="old" offset="44">oeuvre</t>
          <t class="older" offset="44">oeuvre</t>
        </w>
        <correction>
         <new>
            <w xml:id="example.p.1.s.1.w.9" class="WORD">
              <t offset="50">voorbehouden</t>
            </w>
         </new>
         <original>
            <correction>
                <new>
                    <w xml:id="example.p.1.s.1.w.9a" class="WORD">
                      <t class="old" offset="51">voor</t>
                    </w>
                    <w xml:id="example.p.1.s.1.w.9b" class="WORD">
                      <t class="old" offset="56">behouden</t>
                    </w>
                </new>
                <original>
                    <w xml:id="example.p.1.s.1.w.9c" class="WORD">
                      <t class="older" offset="51">voor</t>
                    </w>
                    <w xml:id="example.p.1.s.1.w.9d" class="WORD">
                      <t class="older" offset="56">behouden</t>
                    </w>
                </original>
            </correction>
         </original>
        </correction>
        <w xml:id="example.p.1.s.1.w.10" class="WORD">
          <t offset="63">aan</t>
          <t class="old" offset="65">aan</t>
          <t class="older" offset="65">aan</t>
        </w>
        <w xml:id="example.p.1.s.1.w.11" class="WORD" space="no">
          <t offset="67">schrijvers</t>
          <t class="old" offset="69">schrijvers</t>
          <t class="older" offset="69">schrijvers</t>
        </w>
        <w xml:id="example.p.1.s.1.w.12" class="WORD">
          <t offset="77">?</t>
          <t class="old" offset="79">?</t>
          <t class="older" offset="79">?</t>
        </w>
      </s>
    </p>
  </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml, textvalidation=True)

    def test013f_correction(self):
        """Validation - Text Validation with redundancy on construction"""
        #NOTE: Current library implementation won't be able to validate nested layers and will just skip those!
        doc = folia.Document(id='example',textvalidation=True)

        text = folia.Text(doc, id=doc.id + '.text.1')

        text.append(
            folia.Sentence(doc,id=doc.id + '.s.1', text="De site staat online . ", contents=[
                folia.Word(doc,id=doc.id + '.s.1.w.1', text="De"),
                folia.Word(doc,id=doc.id + '.s.1.w.2', text="site"),
                folia.Word(doc,id=doc.id + '.s.1.w.3', text="staat"),
                folia.Word(doc,id=doc.id + '.s.1.w.4', text="online"),
                folia.Word(doc,id=doc.id + '.s.1.w.5', text=".")
            ])
        )
        doc.xmlstring() #serialisation forces validation

    def test013g_correction(self):
        """Validation - Text Validation with redundancy on partial construction"""
        #NOTE: Current library implementation won't be able to validate nested layers and will just skip those!
        doc = folia.Document(id='example',textvalidation=True)
        doc.declare(folia.TextContent)

        text = folia.Text(doc, id=doc.id + '.text.1')

        raised = False
        try:
            text.append(
                folia.Sentence(doc,id=doc.id + '.s.1', text="De site staat online . ", contents=[
                    folia.Word(doc,id=doc.id + '.s.1.w.1', text="De"),
                    folia.Word(doc,id=doc.id + '.s.1.w.2', text="site"),
                    folia.Word(doc,id=doc.id + '.s.1.w.3', text="staat"),
                ])
            )
        except folia.InconsistentText:
            raised = True
        self.assertTrue(raised)

    def test014_fullparagraph(self):
        """Validation - Text Validation with sentence text delimiter inheritance"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
      <paragraph-annotation set="undefined" />
      <token-annotation annotator="ucto" annotatortype="auto" datetime="2017-09-25T10:29:52" set="tokconfig-nld"/>
    </annotations>
  </metadata>
  <text xml:id="test.text">
        <p xml:id="TEI.1.text.1.front.1.div1.1.p.13" class="p">
          <t class="default">Versoek van het Zuyd-Hollandse Synode aan Haar Ho. Mo., dat bij het inwilligen van een nieuw octroy de Compagnie een goede somme gelds soude contribueeren tot onderhoud van een Seminarium. Het getal der predikanten in Indiën a°. 1647 gebragt op ’t getal van 28. Verdeelinge van deselve (blz. 12).</t>
          <s xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.1">
            <t class="default">Versoek van het Zuyd-Hollandse Synode aan Haar Ho.</t>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.1.w.1" class="WORD" set="tokconfig-nld">
              <t class="default">Versoek</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.1.w.2" class="WORD" set="tokconfig-nld">
              <t class="default">van</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.1.w.3" class="WORD" set="tokconfig-nld">
              <t class="default">het</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.1.w.4" class="WORD-COMPOUND" set="tokconfig-nld">
              <t class="default">Zuyd-Hollandse</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.1.w.5" class="WORD" set="tokconfig-nld">
              <t class="default">Synode</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.1.w.6" class="WORD" set="tokconfig-nld">
              <t class="default">aan</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.1.w.7" class="WORD" set="tokconfig-nld">
              <t class="default">Haar</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.1.w.8" class="WORD" set="tokconfig-nld" space="no">
              <t class="default">Ho</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.1.w.9" class="PUNCTUATION" set="tokconfig-nld">
              <t class="default">.</t>
            </w>
          </s>
          <s xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.2">
            <t class="default">Mo.</t>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.2.w.1" class="WORD" set="tokconfig-nld" space="no">
              <t class="default">Mo</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.2.w.2" class="PUNCTUATION" set="tokconfig-nld" space="no">
              <t class="default">.</t>
            </w>
          </s>
          <s xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.3">
            <t class="default">, dat bij het inwilligen van een nieuw octroy de Compagnie een goede somme gelds soude contribueeren tot onderhoud van een Seminarium.</t>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.3.w.1" class="PUNCTUATION" set="tokconfig-nld">
              <t class="default">,</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.3.w.2" class="WORD" set="tokconfig-nld">
              <t class="default">dat</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.3.w.3" class="WORD" set="tokconfig-nld">
              <t class="default">bij</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.3.w.4" class="WORD" set="tokconfig-nld">
              <t class="default">het</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.3.w.5" class="WORD" set="tokconfig-nld">
              <t class="default">inwilligen</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.3.w.6" class="WORD" set="tokconfig-nld">
              <t class="default">van</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.3.w.7" class="WORD" set="tokconfig-nld">
              <t class="default">een</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.3.w.8" class="WORD" set="tokconfig-nld">
              <t class="default">nieuw</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.3.w.9" class="WORD" set="tokconfig-nld">
              <t class="default">octroy</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.3.w.10" class="WORD" set="tokconfig-nld">
              <t class="default">de</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.3.w.11" class="WORD" set="tokconfig-nld">
              <t class="default">Compagnie</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.3.w.12" class="WORD" set="tokconfig-nld">
              <t class="default">een</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.3.w.13" class="WORD" set="tokconfig-nld">
              <t class="default">goede</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.3.w.14" class="WORD" set="tokconfig-nld">
              <t class="default">somme</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.3.w.15" class="WORD" set="tokconfig-nld">
              <t class="default">gelds</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.3.w.16" class="WORD" set="tokconfig-nld">
              <t class="default">soude</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.3.w.17" class="WORD" set="tokconfig-nld">
              <t class="default">contribueeren</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.3.w.18" class="WORD" set="tokconfig-nld">
              <t class="default">tot</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.3.w.19" class="WORD" set="tokconfig-nld">
              <t class="default">onderhoud</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.3.w.20" class="WORD" set="tokconfig-nld">
              <t class="default">van</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.3.w.21" class="WORD" set="tokconfig-nld">
              <t class="default">een</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.3.w.22" class="WORD" set="tokconfig-nld" space="no">
              <t class="default">Seminarium</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.3.w.23" class="PUNCTUATION" set="tokconfig-nld">
              <t class="default">.</t>
            </w>
          </s>
          <s xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.4">
            <t class="default">Het getal der predikanten in Indiën a°.</t>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.4.w.1" class="WORD" set="tokconfig-nld">
              <t class="default">Het</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.4.w.2" class="WORD" set="tokconfig-nld">
              <t class="default">getal</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.4.w.3" class="WORD" set="tokconfig-nld">
              <t class="default">der</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.4.w.4" class="WORD" set="tokconfig-nld">
              <t class="default">predikanten</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.4.w.5" class="WORD" set="tokconfig-nld">
              <t class="default">in</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.4.w.6" class="WORD" set="tokconfig-nld">
              <t class="default">Indiën</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.4.w.7" class="WORD" set="tokconfig-nld" space="no">
              <t class="default">a</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.4.w.8" class="SYMBOL" set="tokconfig-nld" space="no">
              <t class="default">°</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.4.w.9" class="PUNCTUATION" set="tokconfig-nld">
              <t class="default">.</t>
            </w>
          </s>
          <s xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.5">
            <t class="default">1647 gebragt op ’t getal van 28.</t>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.5.w.1" class="NUMBER" set="tokconfig-nld">
              <t class="default">1647</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.5.w.2" class="WORD" set="tokconfig-nld">
              <t class="default">gebragt</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.5.w.3" class="WORD" set="tokconfig-nld">
              <t class="default">op</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.5.w.4" class="WORD-TOKEN" set="tokconfig-nld">
              <t class="default">’t</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.5.w.5" class="WORD" set="tokconfig-nld">
              <t class="default">getal</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.5.w.6" class="WORD" set="tokconfig-nld">
              <t class="default">van</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.5.w.7" class="NUMBER" set="tokconfig-nld" space="no">
              <t class="default">28</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.5.w.8" class="PUNCTUATION" set="tokconfig-nld">
              <t class="default">.</t>
            </w>
          </s>
          <s xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.6">
            <t class="default">Verdeelinge van deselve (blz. 12).</t>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.6.w.1" class="WORD" set="tokconfig-nld">
              <t class="default">Verdeelinge</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.6.w.2" class="WORD" set="tokconfig-nld">
              <t class="default">van</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.6.w.3" class="WORD" set="tokconfig-nld">
              <t class="default">deselve</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.6.w.4" class="PUNCTUATION" set="tokconfig-nld" space="no">
              <t class="default">(</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.6.w.5" class="ABBREVIATION-KNOWN" set="tokconfig-nld">
              <t class="default">blz.</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.6.w.6" class="NUMBER" set="tokconfig-nld" space="no">
              <t class="default">12</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.6.w.7" class="PUNCTUATION" set="tokconfig-nld" space="no">
              <t class="default">)</t>
            </w>
            <w xml:id="TEI.1.text.1.front.1.div1.1.p.13.s.6.w.8" class="PUNCTUATION" set="tokconfig-nld">
              <t class="default">.</t>
            </w>
          </s>
        </p>
    </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml, textvalidation=True)


    def test015_textwhitespace(self):
        """Validation - Whitespace in text content sanity check"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="1.5.0" generator="{generator}">
  <metadata type="native">
    <annotations>
    </annotations>
  </metadata>
  <text xml:id="test.text">
      <s xml:id="test.s"><t>Dit
         is een rare test.
         </t>
      </s>
    </text>
</FoLiA>""".format(version=folia.FOLIAVERSION, generator='foliapy-v' + folia.LIBVERSION)
        doc = folia.Document(string=xml, textvalidation=True)
        self.assertEqual( doc['test.s'].text(), "Dit\n         is een rare test.")


with open(os.path.join(FOLIAPATH, 'examples/full-legacy.1.5.folia.xml'), 'r',encoding='utf-8') as foliaexample_f:
    LEGACYEXAMPLE = foliaexample_f.read()

with open(os.path.join(FOLIAPATH, 'examples/partial-legacy.1.5.folia.xml'), 'r',encoding='utf-8') as foliaexample_f:
    PARTIALLEGACYEXAMPLE = foliaexample_f.read()

#We cheat, by setting the generator and version attributes to match the library, so xmldiff doesn't complain when we compare against this reference
#LEGACYEXAMPLE = re.sub(r' version="[^"]*" generator="[^"]*"', ' version="' + folia.FOLIAVERSION + '" generator="foliapy-v' + folia.LIBVERSION + '"', LEGACYEXAMPLE, re.MULTILINE)

#Another cheat, alien namespace attributes are ignored by the folia library, strip them so xmldiff doesn't complain
LEGACYEXAMPLE = re.sub(r' xmlns:alien="[^"]*" alien:attrib="[^"]*"', '', LEGACYEXAMPLE, re.MULTILINE)

PARTIALLEGACYEXAMPLE = re.sub(r' xmlns:alien="[^"]*" alien:attrib="[^"]*"', '', PARTIALLEGACYEXAMPLE, re.MULTILINE)

if __name__ == '__main__':
    unittest.main()
