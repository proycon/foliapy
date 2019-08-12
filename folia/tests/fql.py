#!/usr/bin/env python
#-*- coding:utf-8 -*-


#---------------------------------------------------------------
# FoLiA Library - Test Units for FoLiA Query Language
#   by Maarten van Gompel, Radboud University Nijmegen
#   proycon AT anaproy DOT nl
#
#   Licensed under GPLv3
#----------------------------------------------------------------


from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from folia.helpers import u, isstring
from folia.tests.helpers import xmlcheck, xmlnorm
import sys
if sys.version < '3':
    from codecs import getwriter
    stderr = getwriter('utf-8')(sys.stderr)
    stdout = getwriter('utf-8')(sys.stdout)
else:
    stderr = sys.stderr
    stdout = sys.stdout

import sys
import os
import unittest
import io
from folia import fql
import folia.main as folia
try:
    from pynlpl.formats import cql
    HAVE_CQL = True
except ImportError:
    HAVE_CQL = False

Q1 = 'SELECT pos WHERE class = "n" FOR w WHERE text = "house" AND class != "punct" RETURN focus'
Q2 = 'ADD w WITH text "house" (ADD pos WITH class "n") FOR ID sentence'

Qselect_focus = "SELECT lemma OF \"lemmas-nl\" WHERE class = \"stamboom\" FOR w RETURN focus"
Qselect_target = "SELECT lemma OF \"lemmas-nl\" WHERE class = \"stamboom\" FOR w RETURN target"
Qselect_singlefocus = "SELECT lemma OF \"lemmas-nl\" WHERE class = \"hoofdletter\" FOR w RETURN focus FORMAT single-python"
Qselect_singletarget = "SELECT lemma OF \"lemmas-nl\" WHERE class = \"hoofdletter\" FOR w RETURN target FORMAT single-python"



Qselect_multitarget_focus = "SELECT lemma OF \"lemmas-nl\" FOR ID \"WR-P-E-J-0000000001.p.1.s.4.w.4\" , ID \"WR-P-E-J-0000000001.p.1.s.4.w.5\""
Qselect_multitarget = "SELECT lemma OF \"lemmas-nl\" FOR ID \"WR-P-E-J-0000000001.p.1.s.4.w.4\" , ID \"WR-P-E-J-0000000001.p.1.s.4.w.5\" RETURN target"
Qselect_nestedtargets = "SELECT lemma OF \"lemmas-nl\" WHERE class = \"stamboom\" FOR w FOR s ID \"WR-P-E-J-0000000001.p.1.s.2\" RETURN target FORMAT single-python"

Qselect_startend = "SELECT FOR w START ID \"WR-P-E-J-0000000001.p.1.s.2.w.2\" END ID \"WR-P-E-J-0000000001.p.1.s.2.w.4\"" #inclusive
Qselect_startend2 = "SELECT FOR w START ID \"WR-P-E-J-0000000001.p.1.s.2.w.2\" ENDBEFORE ID \"WR-P-E-J-0000000001.p.1.s.2.w.4\"" #exclusive


Qin = "SELECT ph IN w"
Qin2 = "SELECT ph IN term"
Qin2ref = "SELECT ph FOR term"

Qedit = "EDIT lemma OF \"lemmas-nl\" WHERE class = \"stamboom\" WITH class \"blah\" FOR w FOR s ID \"WR-P-E-J-0000000001.p.1.s.2\""
Qeditconfidence = "EDIT lemma OF \"lemmas-nl\" WHERE class = \"stamboom\" WITH class \"blah\" confidence 0.5 FOR w FOR s ID \"WR-P-E-J-0000000001.p.1.s.2\""
Qeditconfidence2 = "EDIT lemma OF \"lemmas-nl\" WHERE class = \"stamboom\" WITH class \"blah\" confidence NONE FOR w FOR s ID \"WR-P-E-J-0000000001.p.1.s.2\""
Qadd = "ADD lemma OF \"lemmas-nl\" WITH class \"hebben\" FOR w ID \"WR-P-E-J-0000000001.sandbox.2.s.1.w.3\""
Qeditadd = "EDIT lemma OF \"lemmas-nl\" WITH class \"hebben\" FOR w ID \"WR-P-E-J-0000000001.sandbox.2.s.1.w.3\""
Qdelete = "DELETE lemma OF \"lemmas-nl\" WHERE class = \"stamboom\" FOR w"
Qdelete_target = "DELETE lemma OF \"lemmas-nl\" WHERE class = \"stamboom\" FOR w RETURN target"

Qcomplexadd = "APPEND w (ADD t WITH text \"gisteren\" ADD lemma OF \"lemmas-nl\" WITH class \"gisteren\") FOR ID \"WR-P-E-J-0000000001.sandbox.2.s.1.w.3\""

Qedittext = "EDIT w WHERE text = \"terweil\" WITH text \"terwijl\""
Qedittext2 = "EDIT t WITH text \"terwijl\" FOR w WHERE text = \"terweil\" RETURN target"
Qedittext3 = "EDIT t WITH text \"de\" FOR w ID \"WR-P-E-J-0000000001.p.1.s.8.w.10\" RETURN target"
Qedittext4 = "EDIT t WITH text \"ter\nwijl\" FOR w WHERE text = \"terweil\" RETURN target"

Qhas = "SELECT w WHERE (pos HAS class = \"LET()\")"
Qhas_shortcut = "SELECT w WHERE :pos = \"LET()\""

Qboolean = "SELECT w WHERE (pos HAS class = \"LET()\") AND ((lemma HAS class = \".\") OR (lemma HAS class = \",\"))"

Qcontext = "SELECT w WHERE (PREVIOUS w WHERE text = \"de\")"
Qcontext2 = "SELECT FOR SPAN w WHERE (pos HAS class CONTAINS \"LID(\") & w WHERE (pos HAS class CONTAINS \"ADJ(\") & w WHERE (pos HAS class CONTAINS \"N(\")"

Qselect_span = "SELECT entity OF \"http://raw.github.com/proycon/folia/master/setdefinitions/namedentities.foliaset.xml\" WHERE class = \"per\" FOR ID \"example.table.1.w.3\""
Qselect_span2 = "SELECT entity OF \"http://raw.github.com/proycon/folia/master/setdefinitions/namedentities.foliaset.xml\" WHERE class = \"per\" FOR SPAN ID \"example.table.1.w.3\" & ID \"example.table.1.w.4\" & ID \"example.table.1.w.5\""
Qselect_span2_returntarget = "SELECT entity OF \"http://raw.github.com/proycon/folia/master/setdefinitions/namedentities.foliaset.xml\" WHERE class = \"per\" FOR SPAN ID \"example.table.1.w.3\" & ID \"example.table.1.w.4\" & ID \"example.table.1.w.5\" RETURN target"

Qadd_span = "ADD entity OF \"http://raw.github.com/proycon/folia/master/setdefinitions/namedentities.foliaset.xml\" WITH class \"misc\" FOR SPAN ID \"WR-P-E-J-0000000001.p.1.s.4.w.2\" & ID \"WR-P-E-J-0000000001.p.1.s.4.w.3\""
Qadd_span_returntarget = "ADD entity OF \"http://raw.github.com/proycon/folia/master/setdefinitions/namedentities.foliaset.xml\" WITH class \"misc\" FOR SPAN ID \"WR-P-E-J-0000000001.p.1.s.4.w.2\" & ID \"WR-P-E-J-0000000001.p.1.s.4.w.3\" RETURN target"
Qadd_span_returnancestortarget = "ADD entity OF \"http://raw.github.com/proycon/folia/master/setdefinitions/namedentities.foliaset.xml\" WITH class \"misc\" FOR SPAN ID \"WR-P-E-J-0000000001.p.1.s.4.w.2\" & ID \"WR-P-E-J-0000000001.p.1.s.4.w.3\" RETURN ancestor-target"
Qadd_span2 = "ADD entity OF \"http://raw.github.com/proycon/folia/master/setdefinitions/namedentities.foliaset.xml\" WITH class \"misc\" SPAN ID \"WR-P-E-J-0000000001.p.1.s.4.w.2\" & ID \"WR-P-E-J-0000000001.p.1.s.4.w.3\" FOR ID \"WR-P-E-J-0000000001.p.1.s.4\""
Qadd_span3 = "ADD entity OF \"http://raw.github.com/proycon/folia/master/setdefinitions/namedentities.foliaset.xml\" WITH class \"misc\" RESPAN ID \"WR-P-E-J-0000000001.p.1.s.4.w.3\" FOR SPAN ID \"WR-P-E-J-0000000001.p.1.s.4.w.2\" & ID \"WR-P-E-J-0000000001.p.1.s.4.w.3\""
Qadd_span4 = "ADD entity OF \"http://raw.github.com/proycon/folia/master/setdefinitions/namedentities.foliaset.xml\" WITH class \"misc\" RESPAN NONE FOR SPAN ID \"WR-P-E-J-0000000001.p.1.s.4.w.2\" & ID \"WR-P-E-J-0000000001.p.1.s.4.w.3\""

Qadd_span_subqueries = "ADD dependency OF alpino-set WITH class \"test\" RESPAN NONE (ADD dep SPAN ID WR-P-E-J-0000000001.p.1.s.2.w.6) (ADD hd SPAN ID WR-P-E-J-0000000001.p.1.s.2.w.7) FOR SPAN ID WR-P-E-J-0000000001.p.1.s.2.w.6 & ID WR-P-E-J-0000000001.p.1.s.2.w.7 RETURN focus"
Qedit_spanrole = "EDIT hd SPAN ID \"WR-P-E-J-0000000001.p.1.s.1.w.3\" & ID \"WR-P-E-J-0000000001.p.1.s.1.w.4\" & ID \"WR-P-E-J-0000000001.p.1.s.1.w.5\" FOR dependency ID \"WR-P-E-J-0000000001.p.1.s.1.dep.2\" RETURN target"
Qedit_spanrole_id = "EDIT hd ID \"test\" SPAN ID \"WR-P-E-J-0000000001.p.1.s.1.w.3\" & ID \"WR-P-E-J-0000000001.p.1.s.1.w.4\" & ID \"WR-P-E-J-0000000001.p.1.s.1.w.5\" FOR dependency ID \"WR-P-E-J-0000000001.p.1.s.1.dep.2\" RETURN target"

Qadd_nested_span = "ADD su OF \"syntax-set\" WITH class \"np\" SPAN ID \"WR-P-E-J-0000000001.p.1.s.1.w.4\" & ID \"WR-P-E-J-0000000001.p.1.s.1.w.5\" FOR ID \"WR-P-E-J-0000000001.p.1.s.1.su.0\""

Qinsert_nested_span = "ADD su OF \"syntax-set\" WITH class \"adj\" SPAN ID \"WR-P-E-J-0000000001.p.1.s.1.w.4\" FOR ID \"WR-P-E-J-0000000001.p.1.s.1.su.0\""

Qalt = "EDIT lemma WHERE class = \"terweil\" WITH class \"terwijl\" (AS ALTERNATIVE WITH confidence 0.9)"

Qdeclare = "DECLARE correction OF \"http://raw.github.com/proycon/folia/master/setdefinitions/spellingcorrection.foliaset.xml\" WITH annotator \"me\" annotatortype \"manual\""

#implicitly tests auto-declaration:
Qcorrect1 = "EDIT lemma WHERE class = \"terweil\" WITH class \"terwijl\" (AS CORRECTION OF \"http://raw.github.com/proycon/folia/master/setdefinitions/spellingcorrection.foliaset.xml\" WITH class \"nonworderror\" confidence 0.9)"
Qcorrect2 = "EDIT lemma WHERE class = \"terweil\" (AS CORRECTION OF \"http://raw.github.com/proycon/folia/master/setdefinitions/spellingcorrection.foliaset.xml\" class \"terwijl\" WITH class \"nonworderror\" confidence 0.9)"

Qsuggest1 = "EDIT lemma WHERE class = \"terweil\" (AS CORRECTION OF \"http://raw.github.com/proycon/folia/master/setdefinitions/spellingcorrection.foliaset.xml\" WITH class \"nonworderror\" SUGGESTION class \"terwijl\" WITH confidence 0.9 SUGGESTION class \"gedurende\" WITH confidence 0.1)"
Qcorrectsuggest = "EDIT lemma WHERE class = \"terweil\" WITH class \"terwijl\" (AS CORRECTION OF \"http://raw.github.com/proycon/folia/master/setdefinitions/spellingcorrection.foliaset.xml\" WITH class \"nonworderror\" confidence 0.9 SUGGESTION class \"gedurende\" WITH confidence 0.1)"

Qcorrect_text = "EDIT t WHERE text = \"terweil\" WITH text \"terwijl\" (AS CORRECTION OF \"http://raw.github.com/proycon/folia/master/setdefinitions/spellingcorrection.foliaset.xml\" WITH class \"nonworderror\" confidence 0.9)"
Qsuggest_text = "EDIT t WHERE text = \"terweil\" (AS CORRECTION OF \"http://raw.github.com/proycon/folia/master/setdefinitions/spellingcorrection.foliaset.xml\" WITH class \"nonworderror\" SUGGESTION text \"terwijl\" WITH confidence 0.9 SUGGESTION text \"gedurende\" WITH confidence 0.1)"

Qcorrect_span = "EDIT entity OF \"http://raw.github.com/proycon/folia/master/setdefinitions/namedentities.foliaset.xml\" WHERE class = \"per\" WITH class \"misc\" (AS CORRECTION OF \"https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/namedentitycorrection.foliaset.xml\" WITH class \"wrongclass\" confidence 0.2) FOR ID \"example.table.1.w.3\""

Qrespan = "EDIT semrole WHERE class = \"actor\" RESPAN ID \"WR-P-E-J-0000000001.p.1.s.7.w.2\" & ID \"WR-P-E-J-0000000001.p.1.s.7.w.3\" FOR SPAN ID \"WR-P-E-J-0000000001.p.1.s.7.w.3\""

Qmerge = "SUBSTITUTE w WITH text \"weertegeven\" FOR SPAN ID \"WR-P-E-J-0000000001.p.1.s.2.w.26\" & ID \"WR-P-E-J-0000000001.p.1.s.2.w.27\" & ID \"WR-P-E-J-0000000001.p.1.s.2.w.28\""

Qsplit = "SUBSTITUTE w WITH text \"weer\" SUBSTITUTE w WITH text \"gegeven\" FOR SPAN ID \"WR-P-E-J-0000000001.p.1.s.6.w.20\""

Qcorrect_merge = "SUBSTITUTE w WITH text \"weertegeven\" (AS CORRECTION OF \"http://raw.github.com/proycon/folia/master/setdefinitions/spellingcorrection.foliaset.xml\" WITH class \"spliterror\") FOR SPAN ID \"WR-P-E-J-0000000001.p.1.s.2.w.26\" & ID \"WR-P-E-J-0000000001.p.1.s.2.w.27\" & ID \"WR-P-E-J-0000000001.p.1.s.2.w.28\""

Qcorrect_split = "SUBSTITUTE w WITH text \"weer\" SUBSTITUTE w WITH text \"gegeven\" (AS CORRECTION OF \"http://raw.github.com/proycon/folia/master/setdefinitions/spellingcorrection.foliaset.xml\" WITH class \"runonerror\") FOR SPAN ID \"WR-P-E-J-0000000001.p.1.s.6.w.20\""

Qsuggest_split = "SUBSTITUTE (AS CORRECTION OF \"http://raw.github.com/proycon/folia/master/setdefinitions/spellingcorrection.foliaset.xml\" WITH class \"runonerror\" SUGGESTION (SUBSTITUTE w WITH text \"weer\" SUBSTITUTE w WITH text \"gegeven\")) FOR SPAN ID \"WR-P-E-J-0000000001.p.1.s.6.w.20\""


Qprepend = "PREPEND w WITH text \"heel\" FOR ID \"WR-P-E-J-0000000001.p.1.s.1.w.4\""
Qcorrect_prepend = "PREPEND w WITH text \"heel\" (AS CORRECTION OF \"http://raw.github.com/proycon/folia/master/setdefinitions/spellingcorrection.foliaset.xml\" WITH class \"insertion\") FOR ID \"WR-P-E-J-0000000001.p.1.s.1.w.4\""

Qcorrect_delete = "DELETE w ID \"WR-P-E-J-0000000001.p.1.s.8.w.6\" (AS CORRECTION OF \"http://raw.github.com/proycon/folia/master/setdefinitions/spellingcorrection.foliaset.xml\" WITH class \"redundantword\")"

Qcql_context = '"de" [ tag="ADJ\(.*" ] [ tag="N\(.*" & lemma!="blah" ]'
Qcql_context2 = '[ pos = "LID\(.*" ]? [ pos = "ADJ\(.*" ]* [ pos = "N\(.*" ]'
Qcql_context3 = '[ pos = "N\(.*" ]{2}'
Qcql_context4 = '[ pos = "WW\(.*" ]+ [] [ pos = "WW\(.*" ]+'
Qcql_context5 = '[ pos = "VG\(.*" ] [ pos = "WW\(.*" ]* []?'
Qcql_context6 = '[ pos = "VG\(.*|VZ\.*" ]'

#test 4: advanced corrections (higher order corrections):
Qsplit2 = "SUBSTITUTE w WITH text \"Ik\" SUBSTITUTE w WITH text \"hoor\" (AS CORRECTION OF \"http://raw.github.com/proycon/folia/master/setdefinitions/spellingcorrection.foliaset.xml\" WITH class \"runonerror\") FOR SPAN ID \"correctionexample.s.4.w.1\""

Qmerge2 = "SUBSTITUTE w WITH text \"onweer\" (AS CORRECTION OF \"http://raw.github.com/proycon/folia/master/setdefinitions/spellingcorrection.foliaset.xml\" WITH class \"spliterror\") FOR SPAN ID \"correctionexample.s.4.w.2\" & ID \"correctionexample.s.4.w.3\""


Qdeletion2 = "DELETE w ID \"correctionexample.s.8.w.3\" (AS CORRECTION OF \"http://raw.github.com/proycon/folia/master/setdefinitions/spellingcorrection.foliaset.xml\" WITH class \"redundantword\")"
#Qdeletion2b = "SUBSTITUTE w ID \"correctionexample.s.8.w.3\" (AS CORRECTION OF \"http://raw.github.com/proycon/folia/master/setdefinitions/spellingcorrection.foliaset.xml\" WITH class \"redundantword\") FOR SPAN ID \"correctionexample.s.8.correction.1\""

#insertions when there is an existing suggestion, SUBSTITUTE insead of APPEND/PREPEND:
Qinsertion2 = "SUBSTITUTE w WITH text \".\" (AS CORRECTION OF \"http://raw.github.com/proycon/folia/master/setdefinitions/spellingcorrection.foliaset.xml\" WITH class \"missingpunctuation\") FOR SPAN ID \"correctionexample.s.9.correction.1\""


Qsuggest_insertion = "PREPEND (AS CORRECTION OF \"http://raw.github.com/proycon/folia/master/setdefinitions/spellingcorrection.foliaset.xml\" WITH class \"insertion\" SUGGESTION (ADD w WITH text \"heel\")) FOR ID \"WR-P-E-J-0000000001.p.1.s.1.w.4\""
Qsuggest_insertion2 = "APPEND (AS CORRECTION OF \"http://raw.github.com/proycon/folia/master/setdefinitions/spellingcorrection.foliaset.xml\" WITH class \"insertion\" SUGGESTION (ADD w WITH text \"heel\")) FOR ID \"WR-P-E-J-0000000001.p.1.s.1.w.3\""

Qcomment = "ADD comment WITH text \"This is our university!\" FOR entity ID \"example.radboud.university.nijmegen.org\""

Qfeat = "SELECT feat WHERE subset = \"wvorm\" FOR pos WHERE class = \"WW(pv,tgw,met-t)\" FOR ID \"WR-P-E-J-0000000001.p.1.s.2.w.5\""
Qfeat2 = "EDIT feat WHERE subset = \"wvorm\" WITH class \"inf\" FOR pos WHERE class = \"WW(pv,tgw,met-t)\" FOR ID \"WR-P-E-J-0000000001.p.1.s.2.w.5\""
Qfeat3 = "ADD feat WITH subset \"wvorm\" class \"inf\" FOR pos WHERE class = \"WW(inf,vrij,zonder)\" FOR ID \"WR-P-E-J-0000000001.p.1.s.2.w.28\""
Qfeat4 = "EDIT feat WHERE subset = \"strength\" AND class = \"strong\"  WITH class \"verystrong\"  FOR ID \"WR-P-E-J-0000000001.text.sentiment.1\""

Qdelete_correction = "DELETE correction ID \"correctionexample.s.1.w.2.correction.1\" RESTORE ORIGINAL RETURN ancestor-focus"
Qdelete_structural_correction = "DELETE correction ID \"correctionexample.s.3.correction.1\" RESTORE ORIGINAL RETURN ancestor-focus"
Qdelete_structural_correction2 = "DELETE correction ID \"correctionexample.s.3.correction.2\" RESTORE ORIGINAL RETURN ancestor-focus"

Qprovenance = "PROCESSOR id \"test.pos\" name \"test\" type \"auto\" ADD pos OF \"https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/universal-pos.foliaset.ttl\" WITH class \"NOUN\" FOR w ID \"example.p.1.s.1.w.2\"" #declaration is implied

Qprovenance_nested = "PROCESSOR id \"test.pos\" name \"test.pos\" type \"auto\" IN PROCESSOR id \"test\" name \"test\" ADD pos OF \"https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/universal-pos.foliaset.ttl\" WITH class \"NOUN\" FOR w ID \"example.p.1.s.1.w.2\""

Qprovenance_no_id = "PROCESSOR name \"test\" type \"auto\" ADD pos OF \"https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/universal-pos.foliaset.ttl\" WITH class \"NOUN\" FOR w ID \"example.p.1.s.1.w.2\"" #declaration is implied, ID will be autogenerated

Qprovenance_nested_no_id = "PROCESSOR name \"test.pos\" type \"auto\" IN PROCESSOR name \"test\" ADD pos OF \"https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/universal-pos.foliaset.ttl\" WITH class \"NOUN\" FOR w ID \"example.p.1.s.1.w.2\""

Qprovenance_nested_no_id2 = "PROCESSOR name \"test.pos\" type \"auto\" IN PROCESSOR name \"test\" ADD pos OF \"https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/universal-pos.foliaset.ttl\" WITH class \"NOUN\" FOR w ID \"example.p.1.s.2.w.4\""

Qprovenance_nested_no_id3 = "PROCESSOR name \"test2.pos\" type \"auto\" IN PROCESSOR name \"test\" ADD pos OF \"https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/universal-pos.foliaset.ttl\" WITH class \"NOUN2\" FOR w ID \"example.p.1.s.2.w.4\""

Qprovenance_nested_no_id_edit = "PROCESSOR name \"test2.pos\" type \"auto\" IN PROCESSOR name \"test\" EDIT pos OF \"https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/universal-pos.foliaset.ttl\" WITH class \"VERB\" FOR w ID \"example.p.1.s.1.w.2\""


Qrespannone_respan= "EDIT su ID \"WR-P-E-J-0000000001.p.1.s.1.su.0\" WITH class \"np\" datetime now RESPAN ID \"WR-P-E-J-0000000001.p.1.s.1.w.4\" & ID \"WR-P-E-J-0000000001.p.1.s.1.w.5\""
Qrespannone_child_left = "ADD su WITH id \"leftchild\" class \"det\" SPAN ID \"WR-P-E-J-0000000001.p.1.s.1.w.3\" FOR su ID \"WR-P-E-J-0000000001.p.1.s.1.su.0\""
Qrespannone = "EDIT su ID \"WR-P-E-J-0000000001.p.1.s.1.su.0\" WITH class \"np\" datetime now RESPAN NONE"
Qrespannone_child_right = "ADD su WITH id \"rightchild\" class \"np2\" SPAN ID \"WR-P-E-J-0000000001.p.1.s.1.w.4\" & ID \"WR-P-E-J-0000000001.p.1.s.1.w.5\" FOR su ID \"WR-P-E-J-0000000001.p.1.s.1.su.0\""

Qselectalt = "SELECT domain (AS ALTERNATIVE) FOR ID \"example.p.1.s.1.w.5\""
Qselectalt2 = "SELECT domain (AS ALTERNATIVE) FOR ID \"example.p.1.s.1.w.5\" RETURN alternative"
Qselectalt3 = "SELECT domain WHERE class = \"geology\" (AS ALTERNATIVE) FOR ID \"example.p.1.s.1.w.5\""
Qdirecteditalt = "EDIT domain WHERE class = \"geology\" WITH class \"water\" FOR alt ID \"example.p.1.s.1.w.5.alt.2\"" #the explicit way
Qeditalt = "EDIT domain WHERE class = \"geology\" WITH class \"water\" (AS ALTERNATIVE ID \"example.p.1.s.1.w.5.alt.2\")" #the implicit way
Qaddalt = "ADD domain WITH class \"general\" (AS ALTERNATIVE) FOR ID \"example.p.1.s.1.w.4\""
Qaddalt_exp = "ADD domain WITH class \"general\" (AS ALTERNATIVE ID \"example.p.1.s.1.w.4.alt.1\") FOR ID \"example.p.1.s.1.w.4\""
Qaddalt2 = "ADD domain WITH class \"general\" (AS ALTERNATIVE) FOR ID \"example.p.1.s.1.w.4\" RETURN alternative"

Qselectaltspan = "SELECT chunk (AS ALTERNATIVE) FOR SPAN ID \"example.p.1.s.1.w.1\" & ID \"example.p.1.s.1.w.2\""
Qselectaltspan2 = "SELECT chunk (AS ALTERNATIVE) FOR SPAN ID \"example.p.1.s.1.w.1\" & ID \"example.p.1.s.1.w.2\" RETURN alternative"

Qmetric = "ADD metric OF \"adhoc\" WITH class \"length\" value \"5\" FOR ID \"WR-P-E-J-0000000001.sandbox.2.s.1.w.3\""

Qrelation = "ADD relation OF \"adhoc\" WITH class \"punc-to-wh\" (TO su ID \"s1.WNP-1\") FOR su ID \"s1.PUNC\""
Qrelation_chained = "ADD relation OF \"adhoc\" WITH class \"punc-to-wh\" (TO su ID \"s1.WNP-1\") (TO su ID \"s1.NP-PRD\") FOR su ID \"s1.PUNC\""
Qrelation_external = "ADD relation OF \"adhoc\" WITH class \"dbpedia\" href \"http://dbpedia.org/page/India\" format \"text/html\" FOR entity ID \"example.p.1.s.1.entity.3\""
Qrelation_edit_xrefs = "EDIT relation OF \"adhoc\" WHERE class = \"punc-to-wh\" (TO su ID \"s1.BEP-2\") FOR su ID \"s1.PUNC\""

class Test1UnparsedQuery(unittest.TestCase):

    def test1_basic(self):
        """Basic query with some literals"""
        qs = Q1
        qu = fql.UnparsedQuery(qs)

        self.assertEqual( qu.q, ['SELECT','pos','WHERE','class','=','n','FOR','w','WHERE','text','=','house','AND','class','!=','punct','RETURN','focus'])
        self.assertEqual( qu.mask, [0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,1,0,0] )

    def test2_paren(self):
        """Query with parentheses"""
        qs = Q2
        qu = fql.UnparsedQuery(qs)

        self.assertEqual( len(qu), 9 )
        self.assertTrue( isinstance(qu.q[5], fql.UnparsedQuery))
        self.assertEqual( qu.mask, [0,0,0,0,1,2,0,0,0] )

    def test3_complex(self):
        """Query with parentheses"""
        qu = fql.UnparsedQuery(Qboolean)
        self.assertEqual( len(qu.q), 6)



class Test2ParseQuery(unittest.TestCase):
    def test01_parse(self):
        """Parsing """ + Q1
        q = fql.Query(Q1)

    def test02_parse(self):
        """Parsing """ + Q2
        q = fql.Query(Q2)

    def test03_parse(self):
        """Parsing """ + Qselect_target
        q = fql.Query(Qselect_target)

    def test04_parse(self):
        """Parsing """ + Qcomplexadd
        q = fql.Query(Qcomplexadd)
        self.assertEqual( len(q.action.subactions), 1) #test whether subaction is parsed
        self.assertTrue( isinstance(q.action.subactions[0].nextaction, fql.Action) ) #test whether subaction has proper chain of two actions

    def test05_parse(self):
        """Parsing """ + Qhas
        q = fql.Query(Qhas)

    def test06_parse(self):
        """Parsing """ + Qhas_shortcut
        q = fql.Query(Qhas_shortcut)

    def test07_parse(self):
        """Parsing """ + Qboolean
        q = fql.Query(Qboolean)

    def test08_parse(self):
        """Parsing """ + Qcontext
        q = fql.Query(Qcontext)

    def test09_parse(self):
        """Parsing """ + Qalt
        q = fql.Query(Qalt)

    def test10_parse(self):
        """Parsing """ + Qcorrect1
        q = fql.Query(Qcorrect1)

    def test11_parse(self):
        """Parsing """ + Qcorrect2
        q = fql.Query(Qcorrect2)

    def test12_parse(self):
        """Parsing """ + Qsuggest_split
        q = fql.Query(Qsuggest_split)
        self.assertIsInstance(q.action.form, fql.Correction)
        self.assertEqual( len(q.action.form.suggestions),1)


class Test3Evaluation(unittest.TestCase):
    def setUp(self):
        self.doc = folia.Document(string=FOLIAEXAMPLE)

    def test01_evaluate_select_focus(self):
        q = fql.Query(Qselect_focus)
        results = q(self.doc)
        self.assertTrue(isinstance(results[0], folia.LemmaAnnotation))
        self.assertEqual(len(results),2)
        self.assertTrue(isinstance(results[1], folia.LemmaAnnotation))

    def test02_evaluate_select_singlefocus(self):
        q = fql.Query(Qselect_singlefocus)
        result = q(self.doc)
        self.assertTrue(isinstance(result, folia.LemmaAnnotation))

    def test03_evaluate_select_target(self):
        q = fql.Query(Qselect_target)
        results = q(self.doc)
        self.assertTrue(isinstance(results[0], folia.Word))
        self.assertEqual(len(results),2)
        self.assertTrue(isinstance(results[1], folia.Word))

    def test04_evaluate_select_singletarget(self):
        q = fql.Query(Qselect_singletarget)
        result = q(self.doc)
        self.assertTrue(isinstance(result, folia.Word))

    def test05_evaluate_select_nestedtargets(self):
        q = fql.Query(Qselect_nestedtargets)
        result = q(self.doc)
        self.assertTrue(isinstance(result, folia.Word))

    def test05a_evaluate_select_multitarget_focus(self):
        q = fql.Query(Qselect_multitarget_focus)
        results = q(self.doc)
        self.assertTrue(isinstance(results[0], folia.LemmaAnnotation))
        self.assertEqual(len(results),2)
        self.assertTrue(isinstance(results[1], folia.LemmaAnnotation))

    def test05b_evaluate_select_multitarget(self):
        q = fql.Query(Qselect_multitarget)
        results = q(self.doc)
        self.assertTrue(isinstance(results[0], folia.Word))
        self.assertEqual(len(results),2)
        self.assertTrue(isinstance(results[1], folia.Word))

    def test06_evaluate_edit(self):
        q = fql.Query(Qedit)
        results = q(self.doc)
        self.assertTrue(isinstance(results[0], folia.LemmaAnnotation))
        self.assertEqual(results[0].cls, "blah")

    def test06a_evaluate_editconfidence(self):
        q = fql.Query(Qeditconfidence)
        results = q(self.doc)
        self.assertTrue(isinstance(results[0], folia.LemmaAnnotation))
        self.assertEqual(results[0].cls, "blah")
        self.assertEqual(results[0].confidence, 0.5)

    def test06b_evaluate_editconfidence2(self):
        q = fql.Query(Qeditconfidence2)
        results = q(self.doc)
        self.assertTrue(isinstance(results[0], folia.LemmaAnnotation))
        self.assertEqual(results[0].cls, "blah")
        self.assertEqual(results[0].confidence, None)

    def test07_evaluate_add(self):
        q = fql.Query(Qadd)
        results = q(self.doc)
        self.assertTrue(isinstance(results[0], folia.LemmaAnnotation))
        self.assertEqual(results[0].cls, "hebben")

    def test08_evaluate_editadd(self):
        q = fql.Query(Qeditadd)
        results = q(self.doc)
        self.assertTrue(isinstance(results[0], folia.LemmaAnnotation))
        self.assertEqual(results[0].cls, "hebben")

    def test09_evaluate_delete(self):
        q = fql.Query(Qdelete)
        results = q(self.doc)
        self.assertEqual(len(results),2) #returns that what was deleted

    def test10_evaluate_delete(self):
        q = fql.Query(Qdelete_target)
        results = q(self.doc)
        self.assertTrue(isinstance(results[0], folia.Word))
        self.assertEqual(len(results),2)
        self.assertTrue(isinstance(results[1], folia.Word))

    def test11_complexadd(self):
        q = fql.Query(Qcomplexadd)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Word)
        self.assertIsInstance(results[0][0], folia.TextContent)
        self.assertIsInstance(results[0][1], folia.LemmaAnnotation)

    def test12_edittext(self):
        q = fql.Query(Qedittext)
        results = q(self.doc)
        self.assertEqual(results[0].text(), "terwijl")

    def test12b_edittext(self):
        q = fql.Query(Qedittext2)
        results = q(self.doc)
        self.assertEqual(results[0].text(), "terwijl")

    def test12c_edittext(self):
        q = fql.Query(Qedittext3)
        results = q(self.doc)
        self.assertEqual(results[0].text(), "de")

    def test12d_edittext(self):
        q = fql.Query(Qedittext4)
        results = q(self.doc)
        self.assertEqual(results[0].text(), "ter\nwijl")
        self.assertTrue(xmlcheck(results[0].xmlstring(), "<w xmlns=\"http://ilk.uvt.nl/folia\" xml:id=\"WR-P-E-J-0000000001.p.1.s.8.w.9\"><t>ter\nwijl</t><errordetection class=\"spelling\"/><pos class=\"VG(onder)\" set=\"https://raw.githubusercontent.com/proycon/folia/master/setdefinitions/frog-mbpos-cgn\"/><lemma class=\"terweil\"/></w>"))

    def test13_subfilter(self):
        q = fql.Query(Qhas)
        results = q(self.doc)
        for result in results:
            self.assertIn(result.text(), (".",",","(",")"))

    def test14_subfilter_shortcut(self):
        q = fql.Query(Qhas_shortcut)
        results = q(self.doc)
        self.assertTrue( len(results) > 0 )
        for result in results:
            self.assertIn(result.text(), (".",",","(",")"))

    def test15_boolean(self):
        q = fql.Query(Qboolean)
        results = q(self.doc)
        self.assertTrue( len(results) > 0 )
        for result in results:
            self.assertIn(result.text(), (".",","))

    def test16_context(self):
        """Obtaining all words following 'de'"""
        q = fql.Query(Qcontext)
        results = q(self.doc)
        self.assertTrue( len(results) > 0 )
        self.assertEqual(results[0].text(), "historische")
        self.assertEqual(results[1].text(), "naam")
        self.assertEqual(results[2].text(), "verwantschap")
        self.assertEqual(results[3].text(), "handschriften")
        self.assertEqual(results[4].text(), "juiste")
        self.assertEqual(results[5].text(), "laatste")
        self.assertEqual(results[6].text(), "verwantschap")
        self.assertEqual(results[7].text(), "handschriften")

    def test16b_context(self):
        """Obtaining LID ADJ N sequences"""
        q = fql.Query(Qcontext2)
        results = q(self.doc)
        self.assertTrue( len(results) > 0 )
        for result in results:
            self.assertIsInstance(result, fql.SpanSet)
            #print("RESULT: ", [w.text() for w in result])
            self.assertEqual(len(result), 3)
            self.assertIsInstance(result[0], folia.Word)
            self.assertIsInstance(result[1], folia.Word)
            self.assertIsInstance(result[2], folia.Word)
            self.assertEqual(result[0].pos()[:4], "LID(")
            self.assertEqual(result[1].pos()[:4], "ADJ(")
            self.assertEqual(result[2].pos()[:2], "N(")

    def test17_select_span(self):
        """Select span"""
        q = fql.Query(Qselect_span)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Entity)
        self.assertEqual(results[0].cls, 'per')
        self.assertEqual(len(list(results[0].wrefs())), 3)

    def test18_select_span2(self):
        """Select span"""
        q = fql.Query(Qselect_span2)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Entity)
        results = list(results[0].wrefs())
        self.assertIsInstance(results[0], folia.Word)
        self.assertEqual(results[0].text(), "Maarten")
        self.assertIsInstance(results[1], folia.Word)
        self.assertEqual(results[1].text(), "van")
        self.assertIsInstance(results[2], folia.Word)
        self.assertEqual(results[2].text(), "Gompel")

    def test19_select_span2_returntarget(self):
        """Select span"""
        q = fql.Query(Qselect_span2_returntarget)
        results = q(self.doc)
        self.assertIsInstance(results[0], fql.SpanSet)
        results = results[0]
        self.assertIsInstance(results[0], folia.Word)
        self.assertEqual(results[0].text(), "Maarten")
        self.assertIsInstance(results[1], folia.Word)
        self.assertEqual(results[1].text(), "van")
        self.assertIsInstance(results[2], folia.Word)
        self.assertEqual(results[2].text(), "Gompel")

    def test20a_add_span(self):
        """Add span"""
        q = fql.Query(Qadd_span)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Entity)
        self.assertEqual(results[0].cls, 'misc')
        results = list(results[0].wrefs())
        self.assertIsInstance(results[0], folia.Word)
        self.assertEqual(results[0].text(), "hoofdletter")
        self.assertIsInstance(results[1], folia.Word)
        self.assertEqual(results[1].text(), "A")

    def test20b_add_span_returntarget(self):
        """Add span (return target)"""
        q = fql.Query(Qadd_span_returntarget)
        results = q(self.doc)
        self.assertIsInstance(results[0], fql.SpanSet )
        results = results[0]
        self.assertIsInstance(results[0], folia.Word)
        self.assertEqual(results[0].text(), "hoofdletter")
        self.assertIsInstance(results[1], folia.Word)
        self.assertEqual(results[1].text(), "A")

    def test20c_add_span_returnancestortarget(self):
        """Add span (return ancestor target)"""
        q = fql.Query(Qadd_span_returnancestortarget)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Part )

    def test20d_add_span(self):
        """Add span (using SPAN instead of FOR SPAN)"""
        q = fql.Query(Qadd_span2)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Entity)
        self.assertEqual(results[0].cls, 'misc')
        results = list(results[0].wrefs())
        self.assertIsInstance(results[0], folia.Word)
        self.assertEqual(results[0].text(), "hoofdletter")
        self.assertIsInstance(results[1], folia.Word)
        self.assertEqual(results[1].text(), "A")
        self.assertEqual(len(results), 2)

    def test20e_add_span(self):
        """Add span (using RESPAN and FOR SPAN, immediately respanning)"""
        q = fql.Query(Qadd_span3)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Entity)
        self.assertEqual(results[0].cls, 'misc')
        results = list(results[0].wrefs())
        self.assertIsInstance(results[0], folia.Word)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].text(), "A")

    def test20f_add_span(self):
        """Add span (using RESPAN NONE, immediately respanning)"""
        q = fql.Query(Qadd_span4)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Entity)
        self.assertEqual(results[0].cls, 'misc')
        results = list(results[0].wrefs())
        self.assertEqual(len(results), 0)


    def test21_edit_alt(self):
        """Add alternative token annotation"""
        q = fql.Query(Qalt)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.LemmaAnnotation)
        self.assertEqual(results[0].cls, "terwijl")
        self.assertIsInstance(results[0].parent, folia.Alternative)

    def test22_declare(self):
        """Explicit declaration"""
        q = fql.Query(Qdeclare)
        results = q(self.doc)

    def test23a_edit_correct(self):
        """Add correction on token annotation"""
        q = fql.Query(Qcorrect1)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Correction)
        self.assertEqual(results[0].cls, "nonworderror")
        self.assertEqual(results[0].confidence, 0.9)
        self.assertIsInstance(results[0].new(0), folia.LemmaAnnotation)
        self.assertEqual(results[0].new(0).cls, "terwijl")

    def test23b_edit_correct(self):
        """Add correction on token annotation (2)"""
        q = fql.Query(Qcorrect2)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Correction)
        self.assertEqual(results[0].cls, "nonworderror")
        self.assertEqual(results[0].confidence, 0.9)
        self.assertIsInstance(results[0].new(0), folia.LemmaAnnotation)
        self.assertEqual(results[0].new(0).cls, "terwijl")

    def test24a_edit_suggest(self):
        """Add suggestions for correction on token annotation"""
        q = fql.Query(Qsuggest1)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Correction)
        self.assertEqual(results[0].cls, "nonworderror")
        self.assertEqual(results[0].parent.lemma(),"terweil")
        self.assertIsInstance(results[0].suggestions(0), folia.Suggestion)
        self.assertEqual(results[0].suggestions(0).confidence, 0.9)
        self.assertIsInstance(results[0].suggestions(0)[0], folia.LemmaAnnotation)
        self.assertEqual(results[0].suggestions(0)[0].cls, "terwijl")
        self.assertIsInstance(results[0].suggestions(1), folia.Suggestion)
        self.assertEqual(results[0].suggestions(1).confidence, 0.1)
        self.assertIsInstance(results[0].suggestions(1)[0], folia.LemmaAnnotation)
        self.assertEqual(results[0].suggestions(1)[0].cls, "gedurende")

    def test24b_edit_correctsuggest(self):
        """Add correction as well as suggestions on token annotation"""
        q = fql.Query(Qcorrectsuggest)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Correction)
        self.assertEqual(results[0].cls, "nonworderror")
        self.assertEqual(results[0].confidence, 0.9)
        self.assertIsInstance(results[0].new(0), folia.LemmaAnnotation)
        self.assertEqual(results[0].new(0).cls, "terwijl")
        self.assertIsInstance(results[0].suggestions(0), folia.Suggestion)
        self.assertEqual(results[0].suggestions(0).confidence, 0.1)
        self.assertIsInstance(results[0].suggestions(0)[0], folia.LemmaAnnotation)
        self.assertEqual(results[0].suggestions(0)[0].cls, "gedurende")

    def test25a_edit_correct_text(self):
        """Add correction on text"""
        q = fql.Query(Qcorrect_text)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Correction)
        self.assertEqual(results[0].cls, "nonworderror")
        self.assertEqual(results[0].confidence, 0.9)
        self.assertIsInstance(results[0].new(0), folia.TextContent)
        self.assertEqual(results[0].new(0).text(), "terwijl")

    def test25b_edit_suggest_text(self):
        """Add suggestion for correction on text"""
        q = fql.Query(Qsuggest_text)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Correction)
        self.assertEqual(results[0].cls, "nonworderror")
        self.assertEqual(results[0].parent.text(),"terweil") #original
        self.assertIsInstance(results[0].suggestions(0), folia.Suggestion)
        self.assertEqual(results[0].suggestions(0).confidence, 0.9)
        self.assertIsInstance(results[0].suggestions(0)[0], folia.TextContent)
        self.assertEqual(results[0].suggestions(0)[0].text(), "terwijl")
        self.assertIsInstance(results[0].suggestions(1), folia.Suggestion)
        self.assertEqual(results[0].suggestions(1).confidence, 0.1)
        self.assertIsInstance(results[0].suggestions(1)[0], folia.TextContent)
        self.assertEqual(results[0].suggestions(1)[0].text(), "gedurende")

    def test26_correct_span(self):
        """Correction of span annotation"""
        q = fql.Query(Qcorrect_span)
        #print(repr(q.action.focus),file=sys.stderr)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Correction)
        self.assertIsInstance(results[0].new(0), folia.Entity)
        self.assertEqual(results[0].new(0).cls, 'misc')
        self.assertEqual(len(list(results[0].new(0).wrefs())), 3)

    def test27_edit_respan(self):
        """Re-spanning"""
        q = fql.Query(Qrespan)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.SemanticRole)
        self.assertEqual(results[0].cls, "actor")
        results = list(results[0].wrefs())
        self.assertIsInstance(results[0], folia.Word)
        self.assertEqual(results[0].text(), "gaat") #yes, this is not a proper semantic role for class 'actor', I know.. but I had to make up a test
        self.assertIsInstance(results[1], folia.Word)
        self.assertEqual(results[1].text(), "men")

    def test28a_merge(self):
        """Substitute - Merging"""
        q = fql.Query(Qmerge)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Word)
        self.assertEqual(results[0].text(), "weertegeven")

    def test28b_split(self):
        """Substitute - Split"""
        q = fql.Query(Qsplit)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Word)
        self.assertIsInstance(results[1], folia.Word)
        self.assertEqual(results[0].text(), "weer")
        self.assertEqual(results[1].text(), "gegeven")

    def test28a_correct_merge(self):
        """Merge Correction"""
        q = fql.Query(Qcorrect_merge)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Correction)
        self.assertEqual(results[0].cls, "spliterror")
        self.assertEqual(results[0].new(0).text(), "weertegeven")

    def test28b_correct_split(self):
        """Split Correction"""
        q = fql.Query(Qcorrect_split)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Correction)
        self.assertEqual(results[0].cls, "runonerror")
        self.assertIsInstance(results[0].new(0), folia.Word)
        self.assertIsInstance(results[0].new(1), folia.Word)
        self.assertEqual(results[0].new(0).text(), "weer")
        self.assertEqual(results[0].new(1).text(), "gegeven")
        self.assertEqual(results[0].original(0).text(), "weergegeven")

    def test28b_suggest_split(self):
        """Split Suggestion for Correction"""
        q = fql.Query(Qsuggest_split)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Correction)
        self.assertEqual(results[0].cls, "runonerror")
        self.assertIsInstance(results[0].suggestions(0)[0], folia.Word)
        self.assertIsInstance(results[0].suggestions(0)[1], folia.Word)
        self.assertEqual(results[0].suggestions(0)[0].text(), "weer")
        self.assertEqual(results[0].suggestions(0)[1].text(), "gegeven")
        self.assertEqual(results[0].current(0).text(), "weergegeven")

    def test29a_prepend(self):
        """Insertion using prepend"""
        q = fql.Query(Qprepend)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Word)
        self.assertEqual(results[0].text(), "heel")
        self.assertEqual(results[0].next(folia.Word).text(), "ander")

    def test29b_correct_prepend(self):
        """Insertion as correction (prepend)"""
        q = fql.Query(Qcorrect_prepend)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Correction)
        self.assertEqual(results[0].cls, "insertion")
        self.assertEqual(results[0].text(), "heel")
        self.assertEqual(results[0].next(folia.Word).text(), "ander")

    def test30_select_startend(self):
        q = fql.Query(Qselect_startend)
        results = q(self.doc)
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0].text(), "de")
        self.assertEqual(results[1].text(), "historische")
        self.assertEqual(results[2].text(), "wetenschap")

    def test30_select_startend2(self):
        q = fql.Query(Qselect_startend2)
        results = q(self.doc)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].text(), "de")
        self.assertEqual(results[1].text(), "historische")

    def test31_in(self):
        q = fql.Query(Qin)
        results = q(self.doc)
        self.assertEqual(len(results), 2)

    def test31b_in2(self):
        q = fql.Query(Qin2)
        results = q(self.doc)
        self.assertEqual(len(results), 0)

    def test31c_in2ref(self):
        q = fql.Query(Qin2ref)
        results = q(self.doc)
        self.assertEqual(len(results), 6) #includes ph under phoneme

    def test31d_tfor(self):
        q = fql.Query("SELECT t FOR w ID \"WR-P-E-J-0000000001.sandbox.2.s.1.w.2\"")
        results = q(self.doc)
        self.assertEqual(len(results), 3) #includes t under morpheme

    def test31e_tin(self):
        q = fql.Query("SELECT t IN w ID \"WR-P-E-J-0000000001.sandbox.2.s.1.w.2\"")
        results = q(self.doc)
        self.assertEqual(len(results), 1)

    def test32_correct_delete(self):
        """Deletion as correction"""
        q = fql.Query(Qcorrect_delete)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Correction)
        self.assertEqual(results[0].cls, "redundantword")
        self.assertEqual(results[0].hastext(), False)
        self.assertEqual(results[0].text(correctionhandling=folia.CorrectionHandling.ORIGINAL), "een")

    def test33_suggest_insertion(self):
        """Insertion as suggestion (prepend)"""
        q = fql.Query(Qsuggest_insertion)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Correction)
        self.assertEqual(results[0].cls, "insertion")
        self.assertEqual(results[0].suggestions(0).text(), "heel")
        self.assertEqual(results[0].next(folia.Word,None).text(), "ander")

    def test34_suggest_insertion2(self):
        """Insertion as suggestion (append)"""
        q = fql.Query(Qsuggest_insertion2)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Correction)
        self.assertEqual(results[0].cls, "insertion")
        self.assertEqual(results[0].suggestions(0).text(), "heel")
        self.assertEqual(results[0].next(folia.Word,None).text(), "ander")

    def test35_comment(self):
        """Adding a comment"""
        q = fql.Query(Qcomment)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Comment)
        self.assertEqual(results[0].value, "This is our university!")
        self.assertEqual(results[0].parent.id, "example.radboud.university.nijmegen.org")

    def test36_feature(self):
        """Selecting a feature"""
        q = fql.Query(Qfeat)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Feature)
        self.assertEqual(results[0].subset, "wvorm")
        self.assertEqual(results[0].cls, "pv")

    def test36b_feature(self):
        """Editing a feature"""
        q = fql.Query(Qfeat2)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Feature)
        self.assertEqual(results[0].subset, "wvorm")
        self.assertEqual(results[0].cls, "inf")

    def test36c_feature(self):
        """Adding a feature"""
        q = fql.Query(Qfeat3)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Feature)
        self.assertEqual(results[0].subset, "wvorm")
        self.assertEqual(results[0].cls, "inf")

    def test36d_feature(self):
        """Editing a feature that has a predefined subset"""
        q = fql.Query(Qfeat4)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Feature)
        self.assertEqual(results[0].subset, "strength")
        self.assertEqual(results[0].cls, "verystrong")

    def test37_subqueries(self):
        """Adding a complex span annotation with span roles, using subqueries"""
        q = fql.Query(Qadd_span_subqueries)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Dependency)
        self.assertEqual(results[0].cls, "test")
        self.assertEqual(list(results[0].annotation(folia.Headspan).wrefs()), [ results[0].doc['WR-P-E-J-0000000001.p.1.s.2.w.7'] ] )
        self.assertEqual(list(results[0].annotation(folia.DependencyDependent).wrefs()), [ results[0].doc['WR-P-E-J-0000000001.p.1.s.2.w.6'] ] )
        self.assertEqual(results[0].ancestor(folia.AbstractStructureElement).id,  'WR-P-E-J-0000000001.p.1.s.2')

    def test38_nested_span(self):
        """Adding a nested span"""
        q = fql.Query(Qadd_nested_span)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.SyntacticUnit)
        self.assertIsInstance(results[0].parent, folia.SyntacticUnit)
        self.assertEqual(results[0].parent.id, "WR-P-E-J-0000000001.p.1.s.1.su.0")
        self.assertEqual(list(results[0].wrefs()), [ results[0].doc['WR-P-E-J-0000000001.p.1.s.1.w.4'],results[0].doc['WR-P-E-J-0000000001.p.1.s.1.w.5'] ] )

    def test38b_nested_span(self):
        """Insert a nested span (verify order)"""
        q = fql.Query(Qinsert_nested_span)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.SyntacticUnit)
        self.assertIsInstance(results[0].parent, folia.SyntacticUnit)
        self.assertEqual(results[0].parent.id, "WR-P-E-J-0000000001.p.1.s.1.su.0")
        self.assertEqual(list(results[0].wrefs()), [ results[0].doc['WR-P-E-J-0000000001.p.1.s.1.w.4'] ] )
        self.assertEqual(list(results[0].parent.wrefs()), [ results[0].doc['WR-P-E-J-0000000001.p.1.s.1.w.3'], results[0].doc['WR-P-E-J-0000000001.p.1.s.1.w.4'],results[0].doc['WR-P-E-J-0000000001.p.1.s.1.w.5'] ] )

    def test39_edit_spanrole(self):
        """Editing a spanrole"""
        q = fql.Query(Qedit_spanrole)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Dependency)
        self.assertEqual(list(results[0].annotation(folia.Headspan).wrefs()), [ results[0].doc['WR-P-E-J-0000000001.p.1.s.1.w.3'], results[0].doc['WR-P-E-J-0000000001.p.1.s.1.w.4'], results[0].doc['WR-P-E-J-0000000001.p.1.s.1.w.5'] ] )
        self.assertEqual(results[0].ancestor(folia.AbstractStructureElement).id,  'WR-P-E-J-0000000001.p.1.s.1')

    def test39b_edit_spanrole(self):
        """Editing a spanrole (with ID)"""
        #ID does not exist yet, we add it first:
        q = fql.Query("SELECT hd FOR ID \"WR-P-E-J-0000000001.p.1.s.1.dep.2\"")
        hd = q(self.doc)[0]
        hd.id = "test"
        self.doc.index["test"] = hd
        #now the actual test:
        q = fql.Query(Qedit_spanrole_id)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Dependency)
        self.assertEqual(list(results[0].annotation(folia.Headspan).wrefs()), [ results[0].doc['WR-P-E-J-0000000001.p.1.s.1.w.3'], results[0].doc['WR-P-E-J-0000000001.p.1.s.1.w.4'], results[0].doc['WR-P-E-J-0000000001.p.1.s.1.w.5'] ] )
        self.assertEqual(results[0].ancestor(folia.AbstractStructureElement).id,  'WR-P-E-J-0000000001.p.1.s.1')

    def test40_edit_respannone_existing_child(self):
        """Editing with RESPAN NONE when there is an existing child"""
        self.assertEqual(self.doc["WR-P-E-J-0000000001.p.1.s.1.su.0"].cls, "np")
        self.assertEqual(self.doc["WR-P-E-J-0000000001.p.1.s.1.su.0"].text(), "een ander woord")
        self.assertEqual(self.doc["WR-P-E-J-0000000001.p.1.s.1.su.0"].wrefs(), [ self.doc["WR-P-E-J-0000000001.p.1.s.1.w.3"],self.doc["WR-P-E-J-0000000001.p.1.s.1.w.4"],self.doc["WR-P-E-J-0000000001.p.1.s.1.w.5"]] )
        q = fql.Query(Qrespannone_respan)
        results = q(self.doc)
        self.assertEqual(self.doc["WR-P-E-J-0000000001.p.1.s.1.su.0"].wrefs(), [ self.doc["WR-P-E-J-0000000001.p.1.s.1.w.4"],self.doc["WR-P-E-J-0000000001.p.1.s.1.w.5"]] )
        q = fql.Query(Qrespannone_child_left)
        results = q(self.doc)
        self.assertEqual(self.doc["leftchild"].wrefs(), [ self.doc["WR-P-E-J-0000000001.p.1.s.1.w.3"]])
        self.assertEqual(self.doc["WR-P-E-J-0000000001.p.1.s.1.su.0"].wrefs(), [ self.doc["WR-P-E-J-0000000001.p.1.s.1.w.3"],self.doc["WR-P-E-J-0000000001.p.1.s.1.w.4"],self.doc["WR-P-E-J-0000000001.p.1.s.1.w.5"]] ) #recurses by default
        q = fql.Query(Qrespannone)
        results = q(self.doc)
        self.assertEqual(self.doc["WR-P-E-J-0000000001.p.1.s.1.su.0"].wrefs(), [ self.doc["WR-P-E-J-0000000001.p.1.s.1.w.3"]] ) #recurses
        q = fql.Query(Qrespannone_child_right)
        results = q(self.doc)
        self.assertEqual(self.doc["rightchild"].wrefs(), [ self.doc["WR-P-E-J-0000000001.p.1.s.1.w.4"], self.doc["WR-P-E-J-0000000001.p.1.s.1.w.5"]])
        self.assertEqual(self.doc["WR-P-E-J-0000000001.p.1.s.1.su.0"].wrefs(), [ self.doc["WR-P-E-J-0000000001.p.1.s.1.w.3"],self.doc["WR-P-E-J-0000000001.p.1.s.1.w.4"],self.doc["WR-P-E-J-0000000001.p.1.s.1.w.5"]] ) #recurses by default

    def test41_metric(self):
        q = fql.Query(Qmetric)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Metric)
        self.assertEqual(results[0].cls, "length")
        self.assertEqual(results[0].set, "adhoc")
        self.assertEqual(results[0].feat("value"), "5")


if HAVE_CQL:
    class Test4CQL(unittest.TestCase):
        def setUp(self):
            self.doc = folia.Document(string=FOLIAEXAMPLE)

        def test01_context(self):
            q = fql.Query(cql.cql2fql(Qcql_context))
            results = q(self.doc)
            self.assertTrue( len(results) > 0 )
            for result in results:
                self.assertIsInstance(result, fql.SpanSet)
                #print("RESULT: ", [w.text() for w in result])
                self.assertEqual(len(result), 3)
                self.assertIsInstance(result[0], folia.Word)
                self.assertIsInstance(result[1], folia.Word)
                self.assertIsInstance(result[2], folia.Word)
                self.assertEqual(result[0].text(), "de")
                self.assertEqual(result[1].pos()[:4], "ADJ(")
                self.assertEqual(result[2].pos()[:2], "N(")

        def test02_context(self):
            q = fql.Query(cql.cql2fql(Qcql_context2))
            results = q(self.doc)
            self.assertTrue( len(results) > 0 )

            textresults = []
            for result in results:
                self.assertIsInstance(result, fql.SpanSet)
                textresults.append(  tuple([w.text() for w in result]) )

            self.assertTrue( ('het','alfabet') in textresults )
            self.assertTrue( ('vierkante','haken') in textresults )
            self.assertTrue( ('plaats',) in textresults )
            self.assertTrue( ('het','originele','handschrift') in textresults )
            self.assertTrue( ('Een','volle','lijn') in textresults )

        def test03_context(self):
            q = fql.Query(cql.cql2fql(Qcql_context3))
            results = q(self.doc)
            self.assertEqual( len(results), 2 )

            textresults = []
            for result in results:
                self.assertIsInstance(result, fql.SpanSet)
                self.assertEqual(len(result), 2)
                textresults.append(  tuple([w.text() for w in result]) )

            #print(textresults,file=sys.stderr)

            self.assertTrue( ('naam','stemma') in textresults )
            self.assertTrue( ('stemma','codicum') in textresults )

        def test04_context(self):
            q = fql.Query(cql.cql2fql(Qcql_context4))
            results = q(self.doc)
            self.assertEqual( len(results),2  )

            textresults = []
            for result in results:
                self.assertIsInstance(result, fql.SpanSet)
                textresults.append(  tuple([w.text() for w in result]) )

            #print(textresults,file=sys.stderr)

            self.assertTrue( ('genummerd','en','gedateerd') in textresults )
            self.assertTrue( ('opgenomen','en','worden','weergegeven') in textresults )

        def test05_context(self):
            q = fql.Query(cql.cql2fql(Qcql_context5))
            results = q(self.doc)
            self.assertTrue( len(results) > 0 )

            textresults = []
            for result in results:
                self.assertIsInstance(result, fql.SpanSet)
                textresults.append(  tuple([w.text() for w in result]) )

            #print(textresults,file=sys.stderr)

            self.assertTrue( ('en','gedateerd','zodat') in textresults )
            self.assertTrue( ('en','worden','weergegeven','door') in textresults )
            self.assertTrue( ('zodat','ze') in textresults )
            self.assertTrue( ('en','worden','tussen') in textresults )
            self.assertTrue( ('terweil','een') in textresults )

        def test06_context(self):
            q = fql.Query(cql.cql2fql(Qcql_context6))
            results = q(self.doc)
            self.assertTrue( len(results) > 0 )

            for result in results:
                self.assertIsInstance(result, fql.SpanSet)
                self.assertEqual(len(result), 1)
                self.assertTrue(result[0].pos()[:2] == "VZ" or result[0].pos()[:2] == "VG" )

class Test4Evaluation(unittest.TestCase):
    """Higher-order corrections  (corrections on corrections)"""
    def setUp(self):
        self.doc = folia.Document(string=FOLIACORRECTIONEXAMPLE)

    def test1_split2(self):
        """Substitute - Split (higher-order)"""
        q = fql.Query(Qsplit2)
        results = q(self.doc)
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], folia.Correction)
        self.assertEqual(results[0].text(), "Ik hoor")

    def test2_merge2(self):
        """Substitute - Merge (higher-order)"""
        q = fql.Query(Qmerge2)
        results = q(self.doc)
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], folia.Correction)
        self.assertEqual(results[0].text(), "onweer")

    def test3_deletion2(self):
        """Deletion (higher-order)"""
        q = fql.Query(Qdeletion2)
        results = q(self.doc)
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], folia.Correction)
        self.assertEqual(results[0].hastext(), False)
        self.assertEqual(results[0].original().text(), "een")
        self.assertEqual(results[0].previous(None).id, "correctionexample.s.8.w.2")
        self.assertEqual(results[0].next(None).id, "correctionexample.s.8.w.4")

    def test3_insertion2(self):
        """Substitute - Insertion (higher-order)"""
        q = fql.Query(Qinsertion2)
        results = q(self.doc)
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], folia.Correction)
        self.assertEqual(results[0].text(), '.')
        self.assertIsInstance(results[0].original()[0], folia.Correction)

    def test4_delete_correction(self):
        """Deleting a correction and restoring the original"""
        q = fql.Query(Qdelete_correction)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Word)
        self.assertEqual(results[0].text(), "word")

    def test4b_delete_structural_correction(self):
        """Deleting a structural correction and restoring the original (runon error)"""
        q = fql.Query(Qdelete_structural_correction)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Sentence)
        self.assertIsInstance(results[0][0], folia.Word)
        self.assertEqual(results[0][0].text(), "Ikhoor")

    def test4c_delete_structural_correction(self):
        """Deleting a structural correction and restoring the original (split error)"""
        q = fql.Query(Qdelete_structural_correction2)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.Sentence)
        self.assertIsInstance(results[0][1], folia.Word)
        self.assertIsInstance(results[0][2], folia.Word)
        self.assertEqual(results[0][1].text(), "on")
        self.assertEqual(results[0][2].text(), "weer")

class Test5Provenance(unittest.TestCase):
    def setUp(self):
        self.doc = folia.Document(file=os.path.join(FOLIAPATH, 'examples','tokens-structure.2.0.0.folia.xml'))

    def test1_addprocessor(self):
        q = fql.Query(Qprovenance)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.PosAnnotation)
        self.assertEqual(results[0].cls, "NOUN")
        doc = results[0].doc
        processor = results[0].processor
        self.assertEqual(processor.name, 'test')
        self.assertEqual(processor.type, folia.ProcessorType.AUTO)
        self.assertTrue(processor in doc.provenance)

    def test2_addprocessor_nested(self):
        q = fql.Query(Qprovenance_nested)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.PosAnnotation)
        self.assertEqual(results[0].cls, "NOUN")
        doc = results[0].doc
        processor = results[0].processor
        self.assertEqual(processor.name, 'test.pos')
        self.assertEqual(processor.type, folia.ProcessorType.AUTO)
        self.assertEqual(processor.parent.name, 'test')
        self.assertEqual(processor.parent.type, folia.ProcessorType.AUTO)
        self.assertEqual(processor.parent.processors, [processor])
        self.assertTrue(processor.parent in doc.provenance)

    def test3_addprocessor_no_id(self):
        q = fql.Query(Qprovenance_no_id)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.PosAnnotation)
        self.assertEqual(results[0].cls, "NOUN")
        doc = results[0].doc
        processor = results[0].processor
        self.assertEqual(processor.name, 'test')
        self.assertEqual(processor.type, folia.ProcessorType.AUTO)
        self.assertTrue(processor in doc.provenance)

    def test4_addprocessor_nested_no_id(self):
        q = fql.Query(Qprovenance_nested_no_id)
        results = q(self.doc)
        self.assertIsInstance(results[0], folia.PosAnnotation)
        self.assertEqual(results[0].cls, "NOUN")
        doc = results[0].doc
        processor = results[0].processor
        self.assertEqual(processor.name, 'test.pos')
        self.assertEqual(processor.type, folia.ProcessorType.AUTO)
        self.assertEqual(processor.parent.name, 'test')
        self.assertEqual(processor.parent.type, folia.ProcessorType.AUTO)
        self.assertEqual(processor.parent.processors, [processor])
        self.assertTrue(processor.parent in doc.provenance)

    def test5_addprocessor_nested_no_id(self):
        q = fql.Query(Qprovenance_nested_no_id)
        results = q(self.doc)
        doc = results[0].doc
        processor1 = results[0].processor

        q2 = fql.Query(Qprovenance_nested_no_id2)
        results = q2(self.doc)
        processor = results[0].processor

        self.assertEqual(processor1, processor)
        self.assertEqual(processor.name, 'test.pos')
        self.assertEqual(processor.type, folia.ProcessorType.AUTO)
        self.assertEqual(len(processor.parent), 1)
        self.assertTrue(processor.parent in doc.provenance)

    def test6_addprocessor_nested_no_id(self):
        q = fql.Query(Qprovenance_nested_no_id)
        results = q(self.doc)
        doc = results[0].doc
        processor = results[0].processor
        self.assertEqual(results[0].cls, 'NOUN')
        self.assertEqual(processor.name, 'test.pos')
        self.assertEqual(processor.type, folia.ProcessorType.AUTO)

        q = fql.Query(Qprovenance_nested_no_id3)
        results = q(self.doc)
        processor2 = results[0].processor

        self.assertEqual(results[0].cls, 'NOUN2')
        self.assertEqual(processor2.name, 'test2.pos')
        self.assertEqual(processor2.type, folia.ProcessorType.AUTO)
        self.assertEqual(len(processor.parent), 2)
        self.assertTrue(processor.parent in doc.provenance)

    def test7_addprocessor_nested_no_id(self):
        q = fql.Query(Qprovenance_nested_no_id)
        results = q(self.doc)
        doc = results[0].doc
        processor1 = results[0].processor

        q = fql.Query(Qprovenance_nested_no_id_edit)
        results = q(self.doc)
        processor = results[0].processor
        self.assertEqual(processor.name, 'test2.pos')
        self.assertEqual(processor.type, folia.ProcessorType.AUTO)
        self.assertTrue(processor.parent in doc.provenance)

class Test6Alternatives(unittest.TestCase):
    """Alternatives"""
    def setUp(self):
        self.doc = folia.Document(string=FOLIAALTEXAMPLE)

    def test1a_select(self):
        """Alternatives - Select"""
        q = fql.Query(Qselectalt)
        results = q(self.doc)
        self.assertEqual(len(results), 2) #returns two alternatives
        self.assertIsInstance(results[0], folia.DomainAnnotation)
        self.assertEqual(results[0].cls, "furniture")
        self.assertIsInstance(results[0].parent, folia.Alternative)

    def test1b_select(self):
        """Alternatives - Select"""
        q = fql.Query(Qselectalt2)
        results = q(self.doc)
        self.assertEqual(len(results), 2) #returns two alternatives
        self.assertIsInstance(results[0], folia.Alternative)
        self.assertEqual(results[0][0].cls, "furniture")
        self.assertIsInstance(results[0][0], folia.DomainAnnotation)

    def test1c_select(self):
        """Alternatives - Select"""
        q = fql.Query(Qselectalt3)
        results = q(self.doc)
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], folia.DomainAnnotation)
        self.assertEqual(results[0].cls, "geology")
        self.assertIsInstance(results[0].parent, folia.Alternative)

    def test2_directedit(self):
        """Alternatives - Direct edit by ID (i.e. the dumb explicit way)"""
        q = fql.Query(Qdirecteditalt)
        results = q(self.doc)
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], folia.DomainAnnotation)
        self.assertEqual(results[0].cls, "water")
        self.assertIsInstance(results[0].parent, folia.Alternative)

    def test3_edit(self):
        """Alternatives - Edit by ID (implicitly)"""
        q = fql.Query(Qeditalt)
        results = q(self.doc)
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], folia.DomainAnnotation)
        self.assertEqual(results[0].cls, "water")
        self.assertIsInstance(results[0].parent, folia.Alternative)

    def test4a_add(self):
        """Alternatives - Add as alternative"""
        q = fql.Query(Qaddalt)
        results = q(self.doc)
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], folia.DomainAnnotation)
        self.assertEqual(results[0].cls, "general")
        self.assertIsInstance(results[0].parent, folia.Alternative)

    def test4b_add(self):
        """Alternatives - Add as alternative (with explicit ID)"""
        q = fql.Query(Qaddalt_exp)
        results = q(self.doc)
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], folia.DomainAnnotation)
        self.assertEqual(results[0].cls, "general")
        self.assertIsInstance(results[0].parent, folia.Alternative)
        self.assertEqual(results[0].parent.id, "example.p.1.s.1.w.4.alt.1" )

    def test4c_add(self):
        """Alternatives - Add as alternative (and return alternative)"""
        q = fql.Query(Qaddalt2)
        results = q(self.doc)
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], folia.Alternative)
        self.assertIsInstance(results[0][0], folia.DomainAnnotation)
        self.assertEqual(results[0][0].cls, "general")

class Test7AlternativeSpan(unittest.TestCase):
    """Alternatives"""
    def setUp(self):
        self.doc = folia.Document(string=FOLIAALTSPANEXAMPLE)

    def test1a_select(self):
        """Alternative Span - Select"""
        q = fql.Query(Qselectaltspan)
        results = q(self.doc)
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], folia.Chunk)
        self.assertEqual(results[0].text(), "The Dalai")
        self.assertIsInstance(results[0].parent, folia.ChunkingLayer)
        self.assertIsInstance(results[0].parent.parent, folia.AlternativeLayers)

    def test1b_select(self):
        """Alternative Span - Select"""
        q = fql.Query(Qselectaltspan2)
        results = q(self.doc)
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], folia.AlternativeLayers)
        self.assertEqual(results[0][0][0].text(), "The Dalai")

class Test7InternalRelations(unittest.TestCase):
    """Alternatives"""
    def setUp(self):
        self.doc = folia.Document(string=FOLIARELATIONEXAMPLE)

    def test1_add(self):
        """Internal Relations - Add a relation with link references"""
        q = fql.Query(Qrelation)
        results = q(self.doc)
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], folia.Relation)
        targets = results[0].targets()
        self.assertIsInstance(targets[0], folia.SyntacticUnit)
        self.assertEqual(targets[0].id, "s1.WNP-1")

    def test2_add_chained(self):
        """Internal Relations - Add a relation with multiple link references"""
        q = fql.Query(Qrelation_chained)
        results = q(self.doc)
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], folia.Relation)
        targets = results[0].targets()
        self.assertEqual(len(targets), 2)
        self.assertIsInstance(targets[0], folia.SyntacticUnit)
        self.assertEqual(targets[0].id, "s1.WNP-1")
        self.assertIsInstance(targets[1], folia.SyntacticUnit)
        self.assertEqual(targets[1].id, "s1.NP-PRD")

    def test3_edit_xrefs(self):
        """Internal relations - Edit link references"""
        q = fql.Query(Qrelation) #first do the add
        results = q(self.doc)
        q = fql.Query(Qrelation_edit_xrefs) #then do the edit
        results = q(self.doc)
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], folia.Relation)
        targets = results[0].targets()
        self.assertEqual(len(targets), 1)
        self.assertIsInstance(targets[0], folia.SyntacticUnit)
        self.assertEqual(targets[0].id, "s1.BEP-2")

class Test8ExternalRelations(unittest.TestCase):
    """Alternatives"""
    def setUp(self):
        self.doc = folia.Document(string=FOLIAEXRELATIONEXAMPLE)

    def test1_add(self):
        """External Relations - Add a relation referencing a URL and format"""
        q = fql.Query(Qrelation_external)
        results = q(self.doc)
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], folia.Relation)
        self.assertEqual(results[0].href, "http://dbpedia.org/page/India")
        self.assertEqual(results[0].format, "text/html")

if os.path.exists("folia-repo"):
    FOLIAPATH = "folia-repo"
elif os.path.exists("../folia-repo"):
    FOLIAPATH = "../folia-repo"
elif os.path.exists("../../folia-repo"):
    FOLIAPATH = "../../folia-repo"
else:
    raise Exception("FoLiA repository not found, did you run git submodule init and are you in the test directory?")

f = io.open(os.path.join(FOLIAPATH, 'examples','full-legacy.1.5.folia.xml'), 'r',encoding='utf-8')
FOLIAEXAMPLE = f.read()
f.close()

f = io.open(os.path.join(FOLIAPATH, 'examples','corrections.0.12.folia.xml'), 'r',encoding='utf-8')
FOLIACORRECTIONEXAMPLE = f.read()
f.close()

f = io.open(os.path.join(FOLIAPATH, 'examples','alternatives.2.0.0.folia.xml'), 'r',encoding='utf-8')
FOLIAALTEXAMPLE = f.read()
f.close()

f = io.open(os.path.join(FOLIAPATH, 'examples','alternatives-span.2.0.0.folia.xml'), 'r',encoding='utf-8')
FOLIAALTSPANEXAMPLE = f.read()
f.close()

f = io.open(os.path.join(FOLIAPATH, 'examples','syntactic-movement.2.0.0.folia.xml'), 'r',encoding='utf-8')
FOLIARELATIONEXAMPLE = f.read()
f.close()

f = io.open(os.path.join(FOLIAPATH, 'examples','entities-relations.2.0.0.folia.xml'), 'r',encoding='utf-8')
FOLIAEXRELATIONEXAMPLE = f.read()
f.close()

if __name__ == '__main__':
    unittest.main()
