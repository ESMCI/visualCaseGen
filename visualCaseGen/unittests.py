import unittest
import sys
from cli import cmdCaseGen
from contextlib import contextmanager
from io import StringIO
import logging

logger = logging.getLogger("unittests")

class TestParamGen(unittest.TestCase):
    """ A unit test class for visualCaseGen. """

    @contextmanager
    def captured_output(self):
        """ A context manager to capture the output of cmd onecmd calls. The captured
        outputs are then compared with expected results. """
        new_out, new_err = StringIO(), StringIO()
        old_out, old_err = sys.stdout, sys.stderr
        try:
            sys.stdout, sys.stderr = new_out, new_err
            yield sys.stdout, sys.stderr
        finally:
            sys.stdout, sys.stderr = old_out, old_err

    def test_var_assignment(self):
        cmd =  cmdCaseGen("nuopc", exit_on_error=True)
        cmd.onecmd("OCN_GRID = tx0.66v1")
        with self.captured_output() as (out, err):
            cmd.onecmd("OCN_GRID")
        self.assertEqual(out.getvalue().strip(), "tx0.66v1")

    def test_var_assignment2(self):
        cmd =  cmdCaseGen("nuopc", exit_on_error=True)
        cmd.onecmd("ATM_GRID=T62")
        with self.captured_output() as (out, err):
            cmd.onecmd("ATM_GRID")
        self.assertEqual(out.getvalue().strip(), "T62")

if __name__ == '__main__':
    unittest.main()