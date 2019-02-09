#!/usr/bin/env python3

import folia.main as folia
import unittest
import types
import os.path
import glob

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

for filename in glob.glob(os.path.join(FOLIAPATH,"examples","*.xml")):
    examplename = os.path.basename(filename)[:-10].replace('-','_')
    setattr(ExamplesTest, "test_" + examplename, (lambda self: folia.Document(file=filename)))

if __name__ == '__main__':
    unittest.main()
