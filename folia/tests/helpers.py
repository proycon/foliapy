
import re
import os
from sys import stderr
from folia.main import FOLIAVERSION, LIBVERSION

if 'TMPDIR' in os.environ:
    TMPDIR = os.environ['TMPDIR']
else:
    TMPDIR = '/tmp/'

def xmlnorm(xml, version = FOLIAVERSION, stripns=True):
    """normalize XML prior to comparison"""
    xml = re.sub(r' version="[^"]*" generator="[^"]*"', ' version="' + version + '" generator="foliapy-v' + LIBVERSION + '"', xml, re.MULTILINE)
    if stripns:
        xml = re.sub(r'xmlns:?\w?="[^"]*"', '', xml, re.MULTILINE)
    return xml

def xmlcheck(xml,expect, version=FOLIAVERSION):
    #obj1 = lxml.objectify.fromstring(expect)
    #expect = lxml.etree.tostring(obj1)
    with open(os.path.join(TMPDIR, 'foliatest.fragment.expect.xml'),'w',encoding='utf-8') as f:
        f.write(xmlnorm(xml, version))
    with open(os.path.join(TMPDIR , 'foliatest.fragment.out.xml'),'w', encoding='utf-8') as f:
        f.write(xmlnorm(xml, version))

    retcode = os.system('xmldiff ' + os.path.join(TMPDIR, 'foliatest.fragment.expect.xml') + ' ' + os.path.join(TMPDIR,'foliatest.fragment.out.xml'))
    passed = (retcode == 0)

    #obj2 = lxml.objectify.fromstring(xml)
    #xml = lxml.etree.tostring(obj2)
    #passed = (expect == xml)
    if not passed:
        print("XML fragments don't match:",file=stderr)
        print("--------------------------REFERENCE-------------------------------------",file=stderr)
        print(expect,file=stderr)
        print("--------------------------ACTUAL RESULT---------------------------------",file=stderr)
        print(xml,file=stderr)
        print("------------------------------------------------------------------------",file=stderr)
    return passed
