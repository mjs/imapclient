import sys
import glob
import imp
import unittest
from os.path import abspath, dirname, basename, join as joinpath

_mydir = abspath(joinpath(dirname(__file__)))

# Make sure that imapclient is imported from the right place
_import_dir = abspath(joinpath(_mydir, '..', '..'))
sys.path.insert(0, _import_dir)

def load_suite():
    full_suite = unittest.TestSuite()
    for modpath in glob.glob(joinpath(_mydir, 'test_*.py')):
        module_name = basename(modpath).split('.', 1)[0]
        module = imp.load_source(module_name, modpath)
        suite = unittest.defaultTestLoader.loadTestsFromModule(module)
        full_suite.addTest(suite)
    return full_suite

def run_suite():
    suite = load_suite()
    runner = unittest.TextTestRunner(verbosity=1)
    runner.run(suite)


