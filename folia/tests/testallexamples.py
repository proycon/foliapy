#!/usr/bin/env python3

import folia.main as folia
import unittest
import types
import os.path
import glob
import sys

if os.path.exists("folia-repo"):
    FOLIAPATH = "folia-repo"
elif os.path.exists("../folia-repo"):
    FOLIAPATH = "../folia-repo"
elif os.path.exists("../../folia-repo"):
    FOLIAPATH = "../../folia-repo"
else:
    raise Exception("FoLiA repository not found, did you run git submodule init and are you in the test directory?")

class ExamplesTest(unittest.TestCase):
    """Simple Token & Structure Tests"""

def test_generator(filename, deepvalidation=False, erroneous=False,debug=False):
    if debug: print("Defining test for " + filename, " deepvalidation="+str(deepvalidation), "erroneous=",str(erroneous),file=sys.stderr)
    def test(self):
        if debug: print("Testing " + filename,file=sys.stderr)
        if erroneous:
            self.assertRaises(Exception, folia.Document, file=filename,autodeclare=False,deepvalidation=deepvalidation)
        else:
            folia.Document(file=filename, deepvalidation=deepvalidation)
    return test

for filename in glob.glob(os.path.join(FOLIAPATH,"examples","*.xml")):
    examplename = os.path.basename(filename)[:-10].replace('-','_').replace('.','_')
    setattr(ExamplesTest, "test_" + examplename, test_generator(filename,deepvalidation=examplename.find('deep') != -1))

for filename in glob.glob(os.path.join(FOLIAPATH,"examples","erroneous","*.xml")):
    examplename = os.path.basename(filename)[:-10].replace('-','_').replace('.','_')
    setattr(ExamplesTest, "test_err_" + examplename, test_generator(filename, deepvalidation=examplename.find('deep') != -1, erroneous=True))

if __name__ == '__main__':
    unittest.main()
