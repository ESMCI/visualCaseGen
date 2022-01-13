import unittest
import sys
from cli import cmdCaseGen
from contextlib import contextmanager
from io import StringIO
import logging

logger = logging.getLogger()

class Checker():

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


    def search(self):

        # test one
        cmd = cmdCaseGen(exit_on_error=False)
        cmd.onecmd("INITTIME = 1850")
        with self.captured_output() as (out, err):
            cmd.onecmd("INITTIME")
        #print(out.getvalue().strip())
        cmd.onecmd("COMP_OCN = mom")
        cmd.onecmd("COMP_WAV = dwav")

        # test two
        cmd = cmdCaseGen(exit_on_error=False)
        cmd.onecmd("COMP_ATM = mom")

        # test three
        cmd = cmdCaseGen(exit_on_error=False)
        cmd.onecmd("COMP_ATM = cam")
        cmd.onecmd("COMP_ICE = dice")

if __name__ == '__main__':
    c = Checker()
    c.search()