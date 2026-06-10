import doctest
import os
import sys
import unittest


def load_tests(loader, tests, ignore):
    from app import models
    tests.addTests(doctest.DocTestSuite(models))
    return tests


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root not in sys.path:
        sys.path.insert(0, root)
    unittest.main()
